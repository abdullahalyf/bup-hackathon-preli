"""Acceptance harness for the GridWise directive interpreter.

Runs the live LLM-backed interpreter against:
  - data/public_samples.json (10 cases)
  - 20 self-written paraphrases (defined below)

Reports per-case accuracy, average latency, and pass/fail summary.
Exits 0 when public accuracy is 10/10 AND paraphrases >= 90%%.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.interpreter import core

DEFAULT_BATTERY = {"capacity_kwh": 200, "minimum_energy_kwh": 10}

PARAPHRASES = [
    (
        ['Rooftop solar output halves between 9 AM and noon due to haze.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'solar_reduction', 'structured_adjustment': {'hours': [9, 10, 11], 'factor': 0.5}},
        ],
    ),
    (
        ['Tomorrow the cafeteria offers a new menu.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'no_op'},
        ],
    ),
    (
        ['Charger is offline from 1 AM to 3 AM for firmware update.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'no_charge_window', 'structured_adjustment': {'hours': [1, 2]}},
        ],
    ),
    (
        ['Do not discharge the battery between 8 AM and 9 AM during inverter check.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'no_discharge_window', 'structured_adjustment': {'hours': [8]}},
        ],
    ),
    (
        ['Limit grid draw to 60 kWh per hour from 10 PM to midnight.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'max_grid_window', 'structured_adjustment': {'hours': [22, 23], 'max_grid_kwh': 60}},
        ],
    ),
    (
        ['Reschedule committee meeting to next Friday.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'no_op'},
        ],
    ),
    (
        ['Solar drops to roughly one-fifth from 7 AM to 9 AM.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'solar_reduction', 'structured_adjustment': {'hours': [7, 8], 'factor': 0.2}},
        ],
    ),
    (
        ['Keep at least 30 kWh in the battery from 5 PM to 8 PM.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'minimum_battery_reserve', 'structured_adjustment': {'hours': [17, 18, 19], 'minimum_energy_kwh': 30}},
        ],
    ),
    (
        ['Reserve half of the battery from 11 AM to 2 PM.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'minimum_battery_reserve', 'structured_adjustment': {'hours': [11, 12, 13], 'minimum_energy_kwh': 100}},
        ],
    ),
    (
        ['Solar forecast zero from 6 PM to 8 PM due to inverter trip.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'solar_reduction', 'structured_adjustment': {'hours': [18, 19], 'factor': 0.0}},
        ],
    ),
    (
        ['Sports day registration opens next Monday.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'no_op'},
        ],
    ),
    (
        ['Charging is unavailable from 10 PM to 11 PM during relay work.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'no_charge_window', 'structured_adjustment': {'hours': [22]}},
        ],
    ),
    (
        ['Hold at least 25 percent of battery from noon to 4 PM.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'minimum_battery_reserve', 'structured_adjustment': {'hours': [12, 13, 14, 15], 'minimum_energy_kwh': 50}},
        ],
    ),
    (
        ['80 percent drop in solar output between 8 AM and 11 AM during panel wash.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'solar_reduction', 'structured_adjustment': {'hours': [8, 9, 10], 'factor': 0.2}},
        ],
    ),
    (
        ['Grid import must not exceed 100 kWh per hour from 4 PM to 6 PM.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'max_grid_window', 'structured_adjustment': {'hours': [16, 17], 'max_grid_kwh': 100}},
        ],
    ),
    (
        ['Library hours extend next month.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'no_op'},
        ],
    ),
    (
        ['No battery discharge from 11 PM to midnight for sensor calibration.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'no_discharge_window', 'structured_adjustment': {'hours': [23]}},
        ],
    ),
    (
        ['Forecast solar drops to about a tenth between 9 AM and 4 PM during wildfire smoke.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'solar_reduction', 'structured_adjustment': {'hours': [9, 10, 11, 12, 13, 14, 15], 'factor': 0.1}},
        ],
    ),
    (
        ['Keep at least 60 kWh reserve from 6 PM to 9 PM.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'minimum_battery_reserve', 'structured_adjustment': {'hours': [18, 19, 20], 'minimum_energy_kwh': 60}},
        ],
    ),
    (
        ['Cap grid import at 200 kWh per hour from 6 PM to 9 PM.'],
        {'capacity_kwh': 200, 'minimum_energy_kwh': 10},
        [
            {'directive_type': 'max_grid_window', 'structured_adjustment': {'hours': [18, 19, 20], 'max_grid_kwh': 200}},
        ],
    ),
]

def _check_entry(result, expected):
    """Compare a single interpretation entry against expected.

    Returns True when directive_type and structured_adjustment match.
    """
    if result.get("applies") is False:
        return expected.get("directive_type") == "no_op"
    if result.get("directive_type") != expected.get("directive_type"):
        return False
    exp = expected.get("structured_adjustment")
    got = result.get("structured_adjustment")
    if exp is None:
        return got is None
    if not isinstance(got, dict):
        return False
    for key, val in exp.items():
        if key not in got:
            return False
        if isinstance(val, float):
            if abs(float(got[key]) - val) > 0.01:
                return False
        else:
            if got[key] != val:
                return False
    return True

def run_public(samples_path):
    """Run the interpreter against data/public_samples.json.

    Returns (correct, total, avg_latency_s, details).
    """
    data = json.loads(Path(samples_path).read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    correct = 0
    total = 0
    latencies = []
    details = []
    for case in cases:
        inp = case.get("input", {})
        notes = inp.get("operator_notes", [])
        battery = {"capacity_kwh": 200, "minimum_energy_kwh": 10}
        expected = case.get("expected_output", {}).get("directive_interpretation", [])
        t0 = time.perf_counter()
        result = core.interpret_notes(notes, battery)
        latencies.append(time.perf_counter() - t0)
        case_pass = True
        for exp_entry in expected:
            idx = exp_entry.get("note_index", 0)
            got_entry = next((e for e in result if e.get("note_index") == idx), None)
            total += 1
            if got_entry is None or not _check_entry(got_entry, exp_entry):
                case_pass = False
                details.append((case.get("id"), idx, exp_entry, got_entry))
            else:
                correct += 1
    avg_latency = sum(latencies) / max(1, len(latencies))
    return correct, total, avg_latency, details

def run_paraphrases():
    """Run the interpreter against PARAPHRASES.

    Returns (correct, total, avg_latency_s, details).
    """
    correct = 0
    total = 0
    latencies = []
    details = []
    for idx, (notes, battery, expected_list) in enumerate(PARAPHRASES):
        t0 = time.perf_counter()
        result = core.interpret_notes(notes, battery)
        latencies.append(time.perf_counter() - t0)
        for j, exp in enumerate(expected_list):
            total += 1
            got = result[j] if j < len(result) else None
            if got is not None and _check_entry(got, exp):
                correct += 1
            else:
                details.append(("PARA-" + str(idx+1), j, exp, got))
    avg_latency = sum(latencies) / max(1, len(latencies))
    return correct, total, avg_latency, details



def _print_details(details, limit=10):
    if not details:
        return
    print("Failures (first {}):".format(min(limit, len(details))))
    for row in details[:limit]:
        case_id, idx, exp, got = row
        print("  {} note={} expected={} got={}".format(case_id, idx, exp, got))

def main():
    samples_path = PROJECT_ROOT / "data" / "public_samples.json"
    print("=" * 60)
    print("GridWise interpreter acceptance")
    print("=" * 60)

    cached_interpret = getattr(core, "_cached_interpret", None)
    if cached_interpret is not None and hasattr(cached_interpret, "cache_clear"):
        cached_interpret.cache_clear()

    pub_correct, pub_total, pub_lat, pub_details = run_public(samples_path)
    pub_pct = (100.0 * pub_correct / pub_total) if pub_total else 0.0

    para_correct, para_total, para_lat, para_details = run_paraphrases()
    para_pct = (100.0 * para_correct / para_total) if para_total else 0.0

    overall_avg = (pub_lat * pub_total + para_lat * para_total) / max(
        1, pub_total + para_total
    )

    print(
        "Public samples: {:>2}/{:>2} ({:5.1f}%, avg {:.2f}s/case)".format(
            pub_correct, pub_total, pub_pct, pub_lat
        )
    )
    print(
        "Paraphrases:    {:>2}/{:>2} ({:5.1f}%, avg {:.2f}s/case)".format(
            para_correct, para_total, para_pct, para_lat
        )
    )
    print("Overall avg latency: {:.2f}s over {} cases".format(
        overall_avg, pub_total + para_total
    ))

    _print_details(pub_details + para_details, limit=8)

    pub_ok = pub_total and pub_correct == pub_total
    para_ok = para_total and para_correct >= int(0.9 * para_total)
    latency_ok = overall_avg < 3.0

    passed = pub_ok and para_ok and latency_ok
    status = "PASS" if passed else "FAIL"
    print("=" * 60)
    print("Status: {}  (public_ok={}, paraphrase_ok={}, latency_ok={})".format(
        status, pub_ok, para_ok, latency_ok
    ))
    print("=" * 60)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
