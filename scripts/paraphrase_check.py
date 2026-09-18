"""
Paraphrase accuracy checker for the GridWise interpreter.

Reads `data/paraphrases.json` (a list of {note, capacity_kwh, expected}
items) and calls `app.interpreter.interpret_notes([note], battery)` for
each one. Compares the returned directive against the expected directive
within a 0.01 tolerance on numeric fields. Reports per-type accuracy,
overall accuracy, average latency, and the first N failing items.

Usage:
    python scripts/paraphrase_check.py [--file PATH] [--limit N] [--show N]

Exit code is 1 if any item fails.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# Allow `python scripts/paraphrase_check.py` from repo root.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.interpreter.core import interpret_notes  # noqa: E402

TOLERANCE = 0.01


# ---------------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------------

def _diff_structured(expected: Any, actual: Any, path: str = "") -> list[str]:
    """Return a list of mismatch descriptions between expected and actual."""
    diffs: list[str] = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        keys = sorted(set(expected) | set(actual))
        for k in keys:
            if k not in expected:
                diffs.append(f"{path}.{k}: unexpected key in actual={actual.get(k)!r}")
            elif k not in actual:
                diffs.append(f"{path}.{k}: missing key (expected={expected[k]!r})")
            else:
                diffs.extend(_diff_structured(expected[k], actual[k], f"{path}.{k}"))
        return diffs
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            diffs.append(
                f"{path}: list length expected={len(expected)} actual={len(actual)}"
            )
            return diffs
        for i, (e, a) in enumerate(zip(expected, actual)):
            diffs.extend(_diff_structured(e, a, f"{path}[{i}]"))
        return diffs
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if abs(float(expected) - float(actual)) > TOLERANCE:
            diffs.append(
                f"{path}: expected={expected!r} actual={actual!r} (tol={TOLERANCE})"
            )
        return diffs
    if expected != actual:
        diffs.append(f"{path}: expected={expected!r} actual={actual!r}")
    return diffs


def _matches(expected_entry: dict, actual_entry: dict) -> tuple[bool, list[str]]:
    """Compare a single paraphrase expectation to the interpreter output."""
    diffs: list[str] = []

    # applies
    if bool(expected_entry["applies"]) != bool(actual_entry.get("applies")):
        diffs.append(
            f"applies: expected={expected_entry['applies']!r} "
            f"actual={actual_entry.get('applies')!r}"
        )

    # directive_type
    exp_type = expected_entry["directive_type"]
    act_type = actual_entry.get("directive_type")
    if exp_type != act_type:
        diffs.append(
            f"directive_type: expected={exp_type!r} actual={act_type!r}"
        )

    # structured_adjustment (None vs None, or dict vs dict)
    exp_adj = expected_entry.get("structured_adjustment")
    act_adj = actual_entry.get("structured_adjustment")
    if (exp_adj is None) != (act_adj is None):
        diffs.append(
            f"structured_adjustment: expected={exp_adj!r} actual={act_adj!r}"
        )
    elif exp_adj is not None and act_adj is not None:
        diffs.extend(_diff_structured(exp_adj, act_adj, "structured_adjustment"))

    return (not diffs, diffs)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def _load_items(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise SystemExit(f"{path}: expected a JSON list of items")
    return data


def _run_one(case: dict) -> tuple[bool, list[str], float]:
    note = case["note"]
    capacity = float(case["capacity_kwh"])
    expected = case["expected"]

    battery = {
        "capacity_kwh": capacity,
        "initial_energy_kwh": capacity * 0.5,
    }

    start = time.perf_counter()
    result = interpret_notes([note], battery)
    latency_ms = (time.perf_counter() - start) * 1000.0

    if not isinstance(result, list) or len(result) != 1:
        return False, [f"interpret_notes returned unexpected shape: {result!r}"], latency_ms

    ok, diffs = _matches(expected, result[0])
    return ok, diffs, latency_ms


def main() -> int:
    parser = argparse.ArgumentParser(description="Paraphrase accuracy checker.")
    parser.add_argument(
        "--file",
        default=str(ROOT / "data" / "paraphrases.json"),
        help="Path to paraphrases JSON (default: data/paraphrases.json)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run only the first N items (for quick checks)",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=10,
        help="How many failing items to print in detail",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-item output, only print summary",
    )
    args = parser.parse_args()

    items = _load_items(Path(args.file))
    if args.limit is not None:
        items = items[: args.limit]

    if not items:
        print("No paraphrases to check.")
        return 0

    print(f"Running {len(items)} paraphrases against interpret_notes()...")
    print()

    total = 0
    passed = 0
    latencies: list[float] = []
    failures: list[tuple[int, dict, list[str]]] = []
    by_type_total: dict[str, int] = {}
    by_type_passed: dict[str, int] = {}

    for idx, case in enumerate(items, start=1):
        total += 1
        dtype = case["expected"]["directive_type"]
        by_type_total[dtype] = by_type_total.get(dtype, 0) + 1

        try:
            ok, diffs, latency_ms = _run_one(case)
        except Exception as exc:  # pragma: no cover - defensive
            ok, diffs, latency_ms = False, [f"exception: {exc!r}"], 0.0

        latencies.append(latency_ms)

        if ok:
            passed += 1
            by_type_passed[dtype] = by_type_passed.get(dtype, 0) + 1
            if not args.quiet:
                print(f"  [{idx:>3}] PASS  {latency_ms:7.2f} ms  ({dtype})  {case['note']}")
        else:
            failures.append((idx, case, diffs))
            if not args.quiet:
                print(f"  [{idx:>3}] FAIL  {latency_ms:7.2f} ms  ({dtype})  {case['note']}")

    # Per-type accuracy table
    print()
    print("Per-directive accuracy:")
    type_order = ["solar_reduction", "minimum_battery_reserve",
                  "no_charge_window", "no_discharge_window",
                  "max_grid_window", "no_op"]
    seen = set()
    for t in type_order:
        if t in by_type_total:
            p = by_type_passed.get(t, 0)
            print(f"  {t:<26} {p:>3}/{by_type_total[t]:<3} "
                  f"({100.0 * p / by_type_total[t]:5.1f}%)")
            seen.add(t)
    for t in sorted(by_type_total):
        if t in seen:
            continue
        p = by_type_passed.get(t, 0)
        print(f"  {t:<26} {p:>3}/{by_type_total[t]:<3} "
              f"({100.0 * p / by_type_total[t]:5.1f}%)")

    # Overall summary
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    accuracy = 100.0 * passed / total if total else 0.0
    print()
    print(f"Total: {passed}/{total} passed ({accuracy:.1f}%)")
    print(f"Avg latency: {avg_latency:.2f} ms over {len(latencies)} items")

    if failures:
        print()
        print(f"Failures ({len(failures)} total, showing first {min(args.show, len(failures))}):")
        for idx, case, diffs in failures[: args.show]:
            print(f"  [{idx:>3}] {case['expected']['directive_type']:<24} {case['note']}")
            for d in diffs:
                print(f"        - {d}")

    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
