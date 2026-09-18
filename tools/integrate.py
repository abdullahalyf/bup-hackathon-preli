"""Integrate team branches, verify, and optionally publish a checkpoint."""
from __future__ import annotations

import argparse
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
LIVE_URL = "https://gridwise-production-0e08.up.railway.app"
BRANCHES = ("alif", "jubayer", "taseen")
DOC_CONFLICTS = {"AGENTS.md", "CLAUDE.md"}


def run(*args: str, timeout: int = 180, **kwargs) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, encoding="utf-8",
                          errors="replace", capture_output=True, timeout=timeout, **kwargs)


def clean() -> bool:
    return not run("git", "status", "--porcelain").stdout.strip()


def errors_from(output: str) -> list[str]:
    terms = ("failed", "error", "traceback", "assert", "timeout", "mismatch", "violation")
    return [line.strip()[:240] for line in output.splitlines()
            if any(term in line.lower() for term in terms)][:30]


def runner_not_ready() -> bool:
    script = ROOT / "scripts" / "run_samples.py"
    if not script.is_file():
        return True
    return script.read_text(encoding="utf-8").strip() in {"print(\"TODO\")", "print('TODO')"}


def sample_check(url: str | None = None) -> tuple[str, str, list[str]]:
    script = ROOT / "scripts" / "run_samples.py"
    if runner_not_ready():
        return "SKIPPED (runner not ready)", "-", []
    try:
        result = run(sys.executable, str(script), *([url] if url else []), timeout=240,
                     env={**os.environ, "PYTHONPATH": str(ROOT) + os.pathsep + os.environ.get("PYTHONPATH", "")})
    except subprocess.TimeoutExpired:
        return "timeout", "-", ["sample runner timed out"]
    output = result.stdout + result.stderr
    times = [float(value) for value in re.findall(r"latency=\s*([\d.]+)ms", output)]
    if times:
        ordered = sorted(times)
        position = (len(ordered) - 1) * 0.95
        low = int(position)
        high = min(low + 1, len(ordered) - 1)
        p95 = f"{(ordered[low] + (ordered[high] - ordered[low]) * (position - low)) / 1000:.3f}s"
    else:
        match = re.search(r"p95_latency=([\d.]+)ms", output)
        p95 = f"{float(match.group(1)) / 1000:.3f}s" if match else "-"
    summary = next((line.strip() for line in reversed(output.splitlines())
                    if "summary" in line.lower()), "")
    issues = errors_from(output) if result.returncode else []
    if not re.search(r"total=10\s+failed=0([^0-9]|$)", summary):
        issues.append("public sample gate not verified: expected total=10 failed=0")
    return summary[:50] or "fail", p95, issues


def local_sample_check() -> tuple[str, str, list[str]]:
    if runner_not_ready():
        return sample_check()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    url = f"http://127.0.0.1:{port}"
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port)], cwd=ROOT, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if server.poll() is not None:
                return "unavailable", "-", ["local app exited before health check"]
            try:
                with urlopen(url + "/health", timeout=2) as response:
                    if response.status == 200:
                        return sample_check(url)
            except (HTTPError, URLError, TimeoutError, OSError):
                pass
            time.sleep(0.5)
        return "unavailable", "-", ["local health did not become ready"]
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()


def resolve_document_conflicts(paths: list[str]) -> bool:
    if set(paths) - DOC_CONFLICTS:
        return False
    temp_dir = ROOT / ".tmp" / "integrate_conflicts"
    temp_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        stages = []
        for stage in (2, 1, 3):
            result = run("git", "show", f":{stage}:{path}")
            if result.returncode:
                return False
            file = temp_dir / f"{path}.{stage}"
            file.write_text(result.stdout, encoding="utf-8")
            stages.append(file)
        merged = run("git", "merge-file", "--union", "-p", *(str(file) for file in stages))
        if merged.returncode not in (0, 1) or "<<<<<<<" in merged.stdout:
            return False
        (ROOT / path).write_text(merged.stdout, encoding="utf-8")
        if run("git", "add", "--", path).returncode:
            return False
    return run("git", "commit", "--no-edit").returncode == 0


def app_check() -> subprocess.CompletedProcess[str]:
    code = ("from fastapi.testclient import TestClient; "
            "from app.main import app; "
            "r=TestClient(app).get('/health'); "
            "assert r.status_code==200 and r.json()=={'status':'ok'}")
    return run(sys.executable, "-c", code, timeout=45)


def test_check() -> subprocess.CompletedProcess[str]:
    return run(sys.executable, "-m", "pytest", "-q", timeout=240)


def merge_branch(branch: str) -> tuple[str, str, list[str]]:
    merge = run("git", "merge", "--no-ff", "--no-edit", f"origin/{branch}")
    if merge.returncode:
        conflicts = run("git", "diff", "--name-only", "--diff-filter=U").stdout.splitlines()
        if not conflicts or not resolve_document_conflicts(conflicts):
            run("git", "merge", "--abort")
            return "conflict", "-", [f"{branch}: unresolved conflict: {', '.join(conflicts) or merge.stderr.strip()}"]
    tests = test_check()
    app = app_check()
    if tests.returncode or app.returncode:
        # This merge commit is the only commit added after the clean-tree check.
        undo = run("git", "reset", "--hard", "HEAD~1")
        detail = errors_from(tests.stdout + tests.stderr + app.stdout + app.stderr)
        if undo.returncode:
            detail.append(f"{branch}: undo failed: {undo.stderr.strip()}")
        return "undone", "fail", detail or [f"{branch}: verification failed"]
    match = re.search(r"(\d+ passed[^\n]*)", tests.stdout)
    return "yes", match.group(1)[:35] if match else "pass", []


def wait_health() -> tuple[bool, str]:
    deadline = time.monotonic() + 120
    last = "no response"
    while time.monotonic() < deadline:
        try:
            with urlopen(LIVE_URL + "/health", timeout=5) as response:
                if response.status == 200:
                    return True, "200"
                last = f"HTTP {response.status}"
        except HTTPError as exc:
            last = f"HTTP {exc.code}"
        except (URLError, TimeoutError, OSError) as exc:
            last = type(exc).__name__
        time.sleep(3)
    return False, last


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="preview merges; do not merge, push, or deploy")
    parser.add_argument("--skip-deploy", action="store_true", help="merge and push, but do not deploy")
    args = parser.parse_args()
    rows: list[list[str]] = []
    failure_lines: list[str] = []
    try:
        if Path(run("git", "rev-parse", "--show-toplevel").stdout.strip()).resolve() != ROOT.resolve():
            raise RuntimeError("must run from the main worktree")
        if run("git", "branch", "--show-current").stdout.strip() != "main":
            raise RuntimeError("main must be checked out in this worktree")
        if not args.dry_run and not clean():
            raise RuntimeError("worktree has uncommitted changes")
        for command in (("git", "fetch", "--all"), ("git", "checkout", "main"),
                        ("git", "pull", "origin", "main")):
            result = run(*command)
            if result.returncode:
                raise RuntimeError(f"{' '.join(command)}: {result.stderr.strip()}")
        if not args.dry_run and not clean():
            raise RuntimeError("worktree changed after pull")
        for branch in BRANCHES:
            ref = f"origin/{branch}"
            exists = run("git", "rev-parse", "--verify", ref)
            if exists.returncode:
                rows.append([branch, "missing", "-", "-", "-", "-", "remote branch absent"])
                continue
            ancestor = run("git", "merge-base", "--is-ancestor", ref, "HEAD")
            if ancestor.returncode == 0:
                rows.append([branch, "skip", "-", "-", "-", "-", "nothing new"])
                continue
            if args.dry_run:
                rows.append([branch, "pending", "-", "-", "-", "-", "preview only"])
                continue
            merged, tested, issues = merge_branch(branch)
            rows.append([branch, merged, tested, "-", "-", "-", "; ".join(issues[:1])])
            failure_lines.extend(issues)
        local, local_p95, issues = sample_check() if args.dry_run else local_sample_check()
        failure_lines.extend(issues)
        if not rows:
            rows.append(["main", "-", "-", "-", "-", "-", ""])
        rows.append(["checkpoint", "-", "-", local, "-", local_p95, "local samples"])
        if not args.dry_run:
            # Public-sample correctness is a required gate before publication.
            if issues or any(row[1] in ("conflict", "undone", "missing") for row in rows):
                failure_lines.append("push/deploy skipped: integration or sample gate failed")
            else:
                push = run("git", "push", "origin", "main")
                if push.returncode:
                    failure_lines.append(f"push failed: {push.stderr.strip()}")
                elif not args.skip_deploy:
                    deploy = run("railway", "up", "--detach", timeout=240)
                    if deploy.returncode:
                        failure_lines.append(f"deploy failed: {deploy.stderr.strip()}")
                    else:
                        healthy, status = wait_health()
                        if not healthy:
                            failure_lines.append(f"live health failed: {status}")
                        else:
                            live, live_p95, live_issues = sample_check(LIVE_URL)
                            rows[-1][4], rows[-1][5] = live, live_p95
                            failure_lines.extend(live_issues)
                            rows[-1][6] = "live health 200"
        print("| branch | merged | pytest | local samples | live samples | p95 | notes |")
        print("| --- | --- | --- | --- | --- | --- | --- |")
        for row in rows:
            print("| " + " | ".join(cell.replace("|", "/").replace("\n", " ") for cell in row) + " |")
        for line in failure_lines[:30]:
            print(line)
        return 1 if failure_lines else 0
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print("| branch | merged | pytest | local samples | live samples | p95 | notes |")
        print("| --- | --- | --- | --- | --- | --- | --- |")
        print(f"| main | - | - | - | - | - | {str(exc).replace('|', '/')} |")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
