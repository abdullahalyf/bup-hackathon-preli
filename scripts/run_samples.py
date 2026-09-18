"""Replay the public sample pack against the GridWise API.

For each case in ``data/public_samples.json`` we POST ``case["input"]`` to
``/optimize-energy`` (URL defaults to ``BASE_URL`` env var or
``http://localhost:8000``) and report:

* HTTP status, latency (ms)
* Per-note interpretation match (applies, directive_type, structured_adjustment)
* Cost difference vs the expected total_cost_bdt
* Violations reported by ``app.optimizer.replay.replay_check``

Exit code 1 on any failure (non-200, interpretation mismatch, replay violation,
or |cost diff| > 0.01).
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import httpx

# Replay validator lives in app.optimizer.replay (stub or full impl).
from app.optimizer.replay import replay_check

ROOT = Path(__file__).resolve().parent.parent
SAMPLES_PATH = ROOT / "data" / "public_samples.json"
TOLERANCE = 0.01


def _diff_structured(expected: Any, actual: Any) -> bool:
    """Compare two structured_adjustment dicts within 0.01 tolerance."""

    if expected is None and actual is None:
        return True
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return False
    if set(expected.keys()) != set(actual.keys()):
        return False
    for key, exp_val in expected.items():
        act_val = actual.get(key)
        if isinstance(exp_val, list) and isinstance(act_val, list):
            if [int(v) for v in exp_val] != [int(v) for v in act_val]:
                return False
        elif isinstance(exp_val, (int, float)) and isinstance(act_val, (int, float)):
            if abs(float(exp_val) - float(act_val)) > TOLERANCE:
                return False
        else:
            if exp_val != act_val:
                return False
    return True


def _evaluate_note(expected_entry: dict, actual_entry: dict) -> list[str]:
    """Return a list of mismatch reasons (empty if all good)."""

    problems: list[str] = []
    if bool(expected_entry.get("applies")) != bool(actual_entry.get("applies")):
        problems.append(
            f"applies expected={expected_entry.get('applies')} got={actual_entry.get('applies')}"
        )
    if expected_entry.get("directive_type") != actual_entry.get("directive_type"):
        problems.append(
            f"directive_type expected={expected_entry.get('directive_type')} "
            f"got={actual_entry.get('directive_type')}"
        )
    if not _diff_structured(
        expected_entry.get("structured_adjustment"),
        actual_entry.get("structured_adjustment"),
    ):
        problems.append(
            f"structured_adjustment expected={expected_entry.get('structured_adjustment')} "
            f"got={actual_entry.get('structured_adjustment')}"
        )
    return problems


def run_case(client: httpx.Client, base_url: str, case: dict) -> dict:
    """Run a single case; return a result dict with status, latency, problems."""

    case_id = case.get("id", "?")
    payload = case["input"]
    expected = case.get("expected_output") or {}
    url = base_url.rstrip("/") + "/optimize-energy"

    started = time.perf_counter()
    try:
        response = client.post(url, json=payload, timeout=60.0)
        latency_ms = (time.perf_counter() - started) * 1000.0
    except Exception as exc:  # pragma: no cover - network errors
        return {
            "id": case_id,
            "status": "network_error",
            "latency_ms": (time.perf_counter() - started) * 1000.0,
            "problems": [f"request failed: {exc}"],
            "cost_diff": None,
        }

    result: dict = {
        "id": case_id,
        "status": response.status_code,
        "latency_ms": latency_ms,
        "problems": [],
        "cost_diff": None,
    }

    if response.status_code != 200:
        result["problems"].append(
            f"HTTP {response.status_code}: {response.text.strip()[:200]}"
        )
        return result

    body = response.json()
    expected_interp = expected.get("directive_interpretation", [])
    actual_interp = body.get("directive_interpretation", [])
    if len(expected_interp) != len(actual_interp):
        result["problems"].append(
            f"directive_interpretation length expected={len(expected_interp)} "
            f"got={len(actual_interp)}"
        )
    else:
        for index, (exp_entry, act_entry) in enumerate(zip(expected_interp, actual_interp)):
            note_problems = _evaluate_note(exp_entry, act_entry)
            for problem in note_problems:
                result["problems"].append(f"note {index}: {problem}")

    expected_cost = expected.get("total_cost_bdt")
    actual_cost = body.get("total_cost_bdt")
    if expected_cost is not None and actual_cost is not None:
        cost_diff = float(actual_cost) - float(expected_cost)
        result["cost_diff"] = cost_diff
        if abs(cost_diff) > TOLERANCE:
            result["problems"].append(
                f"total_cost_bdt diff {cost_diff:+.4f} exceeds tolerance {TOLERANCE}"
            )

    try:
        violations = replay_check(
            payload["hours"],
            payload["battery"],
            body.get("directive_interpretation", []),
            body,
        )
    except Exception as exc:  # pragma: no cover - validator bug
        violations = [f"replay_check raised: {exc}"]
    if violations:
        for violation in violations:
            result["problems"].append(f"replay: {violation}")

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "base_url",
        nargs="?",
        default=os.getenv("BASE_URL", "http://localhost:8000"),
        help="GridWise base URL (default: $BASE_URL or http://localhost:8000)",
    )
    parser.add_argument(
        "--samples",
        default=str(SAMPLES_PATH),
        help="Path to public_samples.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    samples_path = Path(args.samples)
    if not samples_path.is_file():
        print(f"samples file not found: {samples_path}", file=sys.stderr)
        return 1
    data = json.loads(samples_path.read_text(encoding="utf-8"))
    cases = data.get("cases") or []

    print(f"GridWise sample runner -> {args.base_url}")
    print(f"cases: {len(cases)} | tolerance: {TOLERANCE}")
    print("-" * 78)

    latencies: list[float] = []
    failures = 0

    with httpx.Client() as client:
        for case in cases:
            outcome = run_case(client, args.base_url, case)
            latencies.append(outcome["latency_ms"])
            cost = outcome["cost_diff"]
            cost_str = f"{cost:+.4f}" if cost is not None else "n/a"
            problems = outcome["problems"]
            ok = not problems
            if not ok:
                failures += 1
            status_str = "OK " if ok else "FAIL"
            print(
                f"[{status_str}] {outcome['id']:<10} HTTP={outcome['status']:<3} "
                f"latency={outcome['latency_ms']:7.1f}ms cost_diff={cost_str} "
                f"problems={len(problems)}"
            )
            for problem in problems:
                print(f"    - {problem}")

    print("-" * 78)
    if latencies:
        p95 = (
            statistics.quantiles(latencies, n=20)[-1]
            if len(latencies) >= 5
            else max(latencies)
        )
    else:
        p95 = 0.0
    print(
        f"summary: total={len(cases)} failed={failures} "
        f"avg_latency={statistics.mean(latencies) if latencies else 0:.1f}ms "
        f"p95_latency={p95:.1f}ms"
    )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
