"""Judge simulator: POST scenarios to a GridWise /optimize-energy endpoint,
verify schema, interpretation, plan validity, and quality.

Usage:
    python tools/judge_sim.py <BASE_URL>

Exit code is always 0; results are printed as a table + summary.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any

import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.optimizer import optimize as local_optimize  # noqa: E402
from app.optimizer.replay import replay_check as local_replay_check  # noqa: E402

REQUIRED_OUTPUT_KEYS = [
    "scenario_id",
    "directive_interpretation",
    "hourly_plan",
    "total_grid_kwh",
    "total_cost_bdt",
    "peak_grid_kwh",
    "plan_summary",
]

ALLOWED_DIRECTIVES = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
}

ALLOWED_ACTIONS = {"charge", "discharge", "idle"}

TOL = 0.01


def http_post_json(url: str, payload: dict, timeout: float = 30.0) -> tuple[int, dict, float]:
    """POST JSON to URL. Returns (status, decoded_json_or_error_dict, latency_seconds)."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
            elapsed = time.perf_counter() - t0
            try:
                return resp.status, json.loads(data), elapsed
            except json.JSONDecodeError:
                return resp.status, {"_raw": data}, elapsed
    except urllib.error.HTTPError as e:
        elapsed = time.perf_counter() - t0
        try:
            body_text = e.read().decode("utf-8")
        except Exception:
            body_text = ""
        return e.code, {"_http_error": body_text or str(e)}, elapsed
    except urllib.error.URLError as e:
        elapsed = time.perf_counter() - t0
        return 0, {"_url_error": str(e)}, elapsed
    except Exception as e:  # pragma: no cover
        elapsed = time.perf_counter() - t0
        return 0, {"_exception": str(e)}, elapsed


def check_schema(response: dict) -> tuple[bool, list[str]]:
    """Validate the seven required top-level keys and basic hourly_plan shape."""
    errs: list[str] = []
    if not isinstance(response, dict):
        return False, ["response is not a dict"]
    keys = list(response.keys())
    if keys != REQUIRED_OUTPUT_KEYS:
        errs.append(f"key order/missing: got {keys}, expected {REQUIRED_OUTPUT_KEYS}")
    plan = response.get("hourly_plan")
    if not isinstance(plan, list):
        errs.append("hourly_plan missing or not a list")
        return False, errs
    if len(plan) != 24:
        errs.append(f"hourly_plan length {len(plan)} != 24")
        return False, errs
    plan_hours = [entry.get("hour") for entry in plan]
    if plan_hours != list(range(24)):
        errs.append(f"hourly_plan hours not 0..23 in order: {plan_hours}")
    return (not errs), errs


def check_interpretation(expected: list[dict], got: list[dict]) -> tuple[bool, list[str]]:
    """Compare got to expected. Match on note_index order, applies, directive_type,
    and structured_adjustment (hours list, factor/value numeric, 0.01 tolerance)."""
    errs: list[str] = []
    if not isinstance(got, list):
        return False, ["directive_interpretation is not a list"]
    if len(got) != len(expected):
        errs.append(f"interp length {len(got)} != expected {len(expected)}")
        return False, errs
    for i, (exp, g) in enumerate(zip(expected, got)):
        if g.get("note_index") != exp.get("note_index"):
            errs.append(f"note[{i}].note_index: got {g.get('note_index')}, expected {exp.get('note_index')}")
        if g.get("applies") != exp.get("applies"):
            errs.append(f"note[{i}].applies: got {g.get('applies')}, expected {exp.get('applies')}")
        if g.get("directive_type") != exp.get("directive_type"):
            errs.append(
                f"note[{i}].directive_type: got {g.get('directive_type')}, expected {exp.get('directive_type')}"
            )
        # Validate enum compliance
        if g.get("directive_type") not in ALLOWED_DIRECTIVES:
            errs.append(f"note[{i}].directive_type invalid: {g.get('directive_type')}")
        # Validate applies <-> no_op rules
        is_no_op = g.get("directive_type") == "no_op"
        if is_no_op:
            if g.get("applies") is not False:
                errs.append(f"note[{i}]: no_op must have applies=false")
            if g.get("structured_adjustment") is not None:
                errs.append(f"note[{i}]: no_op must have structured_adjustment=null")
        else:
            if g.get("applies") is not True:
                errs.append(f"note[{i}]: non-no_op must have applies=true")
        # Compare structured_adjustment (deep equality on lists, 0.01 on numbers)
        exp_adj = exp.get("structured_adjustment")
        got_adj = g.get("structured_adjustment")
        if (exp_adj is None) != (got_adj is None):
            errs.append(f"note[{i}]: structured_adjustment nullness mismatch (got {got_adj}, expected {exp_adj})")
            continue
        if exp_adj is None:
            continue
        for key, exp_val in exp_adj.items():
            got_val = got_adj.get(key)
            if key == "hours":
                if list(got_val or []) != list(exp_val or []):
                    errs.append(
                        f"note[{i}].structured_adjustment.hours: got {got_val}, expected {exp_val}"
                    )
            elif isinstance(exp_val, (int, float)) and isinstance(got_val, (int, float)):
                if abs(float(got_val) - float(exp_val)) > TOL:
                    errs.append(
                        f"note[{i}].structured_adjustment.{key}: got {got_val}, expected {exp_val}"
                    )
            else:
                if got_val != exp_val:
                    errs.append(
                        f"note[{i}].structured_adjustment.{key}: got {got_val}, expected {exp_val}"
                    )
    return (not errs), errs


def recalc_cost(hours_by_h: dict[int, dict], plan: list[dict]) -> float:
    total = 0.0
    for entry in plan:
        h = entry["hour"]
        tariff = float(hours_by_h[h].get("tariff_bdt_per_kwh", 0.0))
        total += float(entry.get("grid_kwh", 0.0)) * tariff
    return total


def run_one(case: dict, base_url: str) -> dict:
    """Run a single scenario through the live endpoint and score it."""
    cid = case["id"]
    payload = case["input"]
    expected_interp = case["expected_interpretation"]
    hours_by_h = {h["hour"]: h for h in payload["hours"]}

    row = {
        "id": cid,
        "notes": len(payload["operator_notes"]),
        "applied_expected": sum(1 for d in expected_interp if d.get("applies")),
        "schema_ok": False,
        "interp_ok": False,
        "valid_ok": False,
        "reported_cost": None,
        "recalc_cost": None,
        "optimal_cost": None,
        "quality_ratio": None,
        "latency_ms": None,
        "http_status": None,
        "errors": [],
    }

    status, body, elapsed = http_post_json(f"{base_url.rstrip('/')}/optimize-energy", payload)
    row["http_status"] = status
    row["latency_ms"] = round(elapsed * 1000, 2)

    if status != 200 or not isinstance(body, dict):
        row["errors"].append(f"HTTP {status}: {str(body)[:160]}")
        return row

    ok, errs = check_schema(body)
    row["schema_ok"] = ok
    if not ok:
        row["errors"].extend(errs)
        return row

    ok, errs = check_interpretation(expected_interp, body.get("directive_interpretation", []))
    row["interp_ok"] = ok
    if not errs:
        pass
    else:
        row["errors"].extend([f"interp: {e}" for e in errs[:3]])

    # Recalculate cost from returned plan, then compute our optimal cost using
    # the EXPECTED directives (what the judge would compare against).
    plan = body.get("hourly_plan", [])
    row["reported_cost"] = float(body.get("total_cost_bdt", 0.0))
    row["recalc_cost"] = round(recalc_cost(hours_by_h, plan), 6)

    applied_expected = [d for d in expected_interp if d.get("applies")]
    violations = local_replay_check(
        payload["hours"],
        payload["battery"],
        applied_expected,
        body,
    )
    row["valid_ok"] = len(violations) == 0
    if violations:
        row["errors"].extend([f"validity: {v}" for v in violations[:3]])

    # Compute our own optimal cost locally for the quality ratio.
    local_res = local_optimize(payload["hours"], payload["battery"], applied_expected)
    row["optimal_cost"] = float(local_res["total_cost_bdt"])
    if row["optimal_cost"] > 0:
        row["quality_ratio"] = round(row["reported_cost"] / row["optimal_cost"], 4)

    return row


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(s[int(k)])
    return float(s[f] + (s[c] - s[f]) * (k - f))


def print_table(rows: list[dict]) -> None:
    print(f"\n{'id':<10} {'notes':>5} {'appl':>4} {'sch':>4} {'int':>4} {'val':>4} "
          f"{'rep$':>10} {'opt$':>10} {'q':>6} {'ms':>8} {'http':>4}")
    print("-" * 90)
    for r in rows:
        sch = "OK" if r["schema_ok"] else "FAIL"
        itp = "OK" if r["interp_ok"] else "FAIL"
        val = "OK" if r["valid_ok"] else "FAIL"
        rep = r["reported_cost"]
        opt = r["optimal_cost"]
        q = r["quality_ratio"]
        rep_s = f"{rep:.2f}" if isinstance(rep, (int, float)) else "n/a"
        opt_s = f"{opt:.2f}" if isinstance(opt, (int, float)) else "n/a"
        q_s = f"{q:.3f}" if isinstance(q, (int, float)) else "n/a"
        print(f"{r['id']:<10} {r['notes']:>5} {r['applied_expected']:>4} {sch:>4} {itp:>4} {val:>4} "
              f"{rep_s:>10} {opt_s:>10} {q_s:>6} {r['latency_ms']:>8.1f} {str(r['http_status']):>4}")


def print_failures(rows: list[dict]) -> None:
    fails = [r for r in rows if r["errors"]]
    if not fails:
        return
    print(f"\nFailures ({len(fails)}):")
    for r in fails:
        print(f"\n  {r['id']} (http={r['http_status']}, schema={r['schema_ok']}, interp={r['interp_ok']}, valid={r['valid_ok']}):")
        for e in r["errors"][:5]:
            print(f"    - {e}")


def summarize(rows: list[dict]) -> None:
    n = len(rows)
    schema_pass = sum(1 for r in rows if r["schema_ok"])
    interp_pass = sum(1 for r in rows if r["interp_ok"])
    valid_pass = sum(1 for r in rows if r["valid_ok"])
    qualities = [r["quality_ratio"] for r in rows if isinstance(r["quality_ratio"], (int, float))]
    lats = [r["latency_ms"] for r in rows if isinstance(r["latency_ms"], (int, float))]
    print("\n=== SUMMARY ===")
    print(f"  Cases:                {n}")
    print(f"  Schema pass:          {schema_pass}/{n} ({100.0*schema_pass/n:.1f}%)")
    print(f"  Interpretation acc:   {interp_pass}/{n} ({100.0*interp_pass/n:.1f}%)")
    print(f"  Validity pass:        {valid_pass}/{n} ({100.0*valid_pass/n:.1f}%)")
    if qualities:
        print(f"  Avg quality ratio:    {statistics.mean(qualities):.4f}")
        print(f"  Max quality ratio:    {max(qualities):.4f}")
    if lats:
        print(f"  Avg latency (ms):     {statistics.mean(lats):.1f}")
        print(f"  P95 latency (ms):     {percentile(lats, 95):.1f}")


def main() -> int:
    ap = argparse.ArgumentParser(description="GridWise hidden-style judge simulator")
    ap.add_argument("base_url", help="Base URL (e.g. http://localhost:8000)")
    ap.add_argument(
        "--data",
        default=str(ROOT / "data" / "hidden_like.json"),
        help="Path to hidden_like.json",
    )
    args = ap.parse_args()

    with open(args.data, "r", encoding="utf-8") as f:
        pack = json.load(f)
    cases = pack["cases"]
    print(f"Target: {args.base_url}")
    print(f"Loaded {len(cases)} cases from {args.data}")

    rows: list[dict] = []
    for case in cases:
        try:
            rows.append(run_one(case, args.base_url))
        except Exception as e:
            rows.append({
                "id": case["id"],
                "notes": len(case["input"]["operator_notes"]),
                "applied_expected": sum(1 for d in case["expected_interpretation"] if d.get("applies")),
                "schema_ok": False,
                "interp_ok": False,
                "valid_ok": False,
                "reported_cost": None,
                "recalc_cost": None,
                "optimal_cost": None,
                "quality_ratio": None,
                "latency_ms": None,
                "http_status": None,
                "errors": [f"runner exception: {e}"],
            })

    print_table(rows)
    print_failures(rows)
    summarize(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
