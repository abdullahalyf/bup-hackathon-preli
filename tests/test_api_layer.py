"""Integration tests for the public API layer (app.main).

These tests exercise only the layer owned by Alif: routes, validation,
error envelopes, response shape, and ordering.  The interpreter and
optimizer are monkeypatched so the real implementations are not required
to pass.
"""

from __future__ import annotations

import json
import math
import time

import pytest
from fastapi.testclient import TestClient

from app.main import _reset_cache_for_tests, app


@pytest.fixture(autouse=True)
def _clear_response_cache():
    """Each test starts with an empty LRU cache so results don't leak."""
    _reset_cache_for_tests()
    yield
    _reset_cache_for_tests()


# ------------------------------------------------------------- helpers / fixtures

def _battery(**overrides):
    base = {
        "capacity_kwh": 10.0,
        "initial_energy_kwh": 5.0,
        "minimum_energy_kwh": 2.0,
        "max_charge_kwh_per_hour": 2.0,
        "max_discharge_kwh_per_hour": 2.0,
    }
    base.update(overrides)
    return base


def _hours(*, shuffle: bool = False, duplicate_hour: bool = False):
    base = [
        {"hour": h, "demand_kwh": 4.0, "solar_kwh": 0.0 if h < 8 or h > 16 else 2.0,
         "tariff_bdt_per_kwh": 8.0}
        for h in range(24)
    ]
    if duplicate_hour and len(base) >= 2:
        base[1] = dict(base[0])
    if shuffle:
        base = list(reversed(base))
    return base


def _valid_request(**overrides):
    body = {
        "scenario_id": "campus-day-01",
        "operator_notes": ["Keep battery ready for evening peak."],
        "hours": _hours(),
        "battery": _battery(),
    }
    body.update(overrides)
    return body


def _client():
    return TestClient(app)


# Successful dummy interpretations (size matches operator_notes).
def _dummy_success(notes, battery):
    return [
        {
            "note_index": i,
            "applies": True,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [13, 14], "factor": 0.5},
            "explanation": f"dummy {i}",
        }
        for i in range(len(notes))
    ]


def _dummy_success_optimize(hours, battery, directives):
    plan = [
        {
            "hour": entry["hour"],
            "grid_kwh": 4.0 - min(entry["solar_kwh"], 4.0),
            "solar_used_kwh": min(entry["solar_kwh"], 4.0),
            "battery_action": "idle",
            "battery_kwh": 0.0,
            "battery_energy_after_kwh": battery["initial_energy_kwh"],
        }
        for entry in hours
    ]
    total_grid = sum(p["grid_kwh"] for p in plan)
    return {
        "hourly_plan": plan,
        "total_grid_kwh": total_grid,
        "total_cost_bdt": total_grid * 8.0,
        "peak_grid_kwh": max((p["grid_kwh"] for p in plan), default=0.0),
        "status": "optimal",
    }


# ------------------------------------------------------------------- health

def test_health_ok():
    c = _client()
    r = c.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ---------------------------------------------------- input-shape regressions

def test_invalid_json_returns_400():
    c = _client()
    r = c.post(
        "/optimize-energy",
        content=b"{not json",
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 400
    body = r.json()
    assert "error" in body
    # Must not leak Pydantic internals or traceback text.
    text = json.dumps(body).lower()
    assert "traceback" not in text
    assert "pydantic" not in text


def test_twenty_three_hours_returns_400():
    c = _client()
    body = _valid_request()
    body["hours"] = _hours()[:-1]
    r = c.post("/optimize-energy", json=body)
    assert r.status_code == 400


def test_duplicate_hour_returns_400():
    c = _client()
    body = _valid_request(hours=_hours(duplicate_hour=True))
    r = c.post("/optimize-energy", json=body)
    assert r.status_code == 400


def test_hour_out_of_range_returns_400():
    c = _client()
    hours = _hours()
    hours[-1]["hour"] = 24
    r = c.post("/optimize-energy", json=_valid_request(hours=hours))
    assert r.status_code == 400


@pytest.mark.parametrize("bad_notes", [
    [],                              # 0 notes
    ["a", "b", "c", "d"],            # 4 notes
    ["   "],                         # whitespace-only
    ["valid", "   "],                # one blank
    [""],                            # empty string
])
def test_bad_notes_return_400(bad_notes):
    c = _client()
    r = c.post("/optimize-energy", json=_valid_request(operator_notes=bad_notes))
    assert r.status_code == 400


def test_negative_demand_returns_400():
    c = _client()
    hours = _hours()
    hours[0]["demand_kwh"] = -1.0
    r = c.post("/optimize-energy", json=_valid_request(hours=hours))
    assert r.status_code == 400


def test_nan_solar_returns_400():
    # json.dumps refuses NaN by default; build the payload as raw JSON text
    # so the test actually exercises the server's NaN handling.
    c = _client()
    body = _valid_request()
    body["hours"][0]["solar_kwh"] = "NaN"  # JSON literal, will be parsed by FastAPI
    # Pydantic v2 will reject the string "NaN" for a float field with
    # allow_inf_nan=False; we expect a 400 either way.
    r = c.post(
        "/optimize-energy",
        content=json.dumps(body).encode(),
        headers={"content-type": "application/json"},
    )
    assert r.status_code == 400


def test_initial_greater_than_capacity_returns_400():
    c = _client()
    r = c.post(
        "/optimize-energy",
        json=_valid_request(battery=_battery(initial_energy_kwh=20.0)),
    )
    assert r.status_code == 400


def test_minimum_greater_than_initial_returns_400():
    c = _client()
    r = c.post(
        "/optimize-energy",
        json=_valid_request(battery=_battery(minimum_energy_kwh=8.0, initial_energy_kwh=5.0)),
    )
    assert r.status_code == 400


def test_missing_battery_field_returns_400():
    c = _client()
    body = _valid_request()
    body["battery"] = {k: v for k, v in body["battery"].items() if k != "max_charge_kwh_per_hour"}
    r = c.post("/optimize-energy", json=body)
    assert r.status_code == 400


# ---------------------------------------------------- happy path / public sample

def test_valid_request_returns_expected_shape(monkeypatch):
    monkeypatch.setattr("app.main.interpret_notes", _dummy_success)
    monkeypatch.setattr("app.main.optimize", _dummy_success_optimize)
    c = _client()
    r = c.post("/optimize-energy", json=_valid_request())
    assert r.status_code == 200
    body = r.json()

    # Exact key order from the contract.
    assert list(body.keys()) == [
        "scenario_id",
        "directive_interpretation",
        "hourly_plan",
        "total_grid_kwh",
        "total_cost_bdt",
        "peak_grid_kwh",
        "plan_summary",
    ]
    # Echo.
    assert body["scenario_id"] == "campus-day-01"
    # Interpretation length == number of notes.
    assert len(body["directive_interpretation"]) == 1
    # Plan covers all 24 hours.
    assert len(body["hourly_plan"]) == 24
    assert [p["hour"] for p in body["hourly_plan"]] == list(range(24))
    # All numeric outputs finite.
    for p in body["hourly_plan"]:
        for k, v in p.items():
            if isinstance(v, (int, float)):
                assert math.isfinite(float(v))


def test_valid_public_sample_case_0(monkeypatch):
    monkeypatch.setattr("app.main.interpret_notes", _dummy_success)
    monkeypatch.setattr("app.main.optimize", _dummy_success_optimize)
    samples = json.load(open("data/public_samples.json"))
    case = samples["cases"][0]
    c = _client()
    r = c.post("/optimize-energy", json=case["input"])
    assert r.status_code == 200
    body = r.json()
    assert body["scenario_id"] == case["input"]["scenario_id"]
    assert list(body.keys()) == [
        "scenario_id",
        "directive_interpretation",
        "hourly_plan",
        "total_grid_kwh",
        "total_cost_bdt",
        "peak_grid_kwh",
        "plan_summary",
    ]
    assert len(body["hourly_plan"]) == 24
    assert [p["hour"] for p in body["hourly_plan"]] == list(range(24))
    assert len(body["directive_interpretation"]) == len(case["input"]["operator_notes"])


def test_shuffled_hours_emit_sorted_plan(monkeypatch):
    monkeypatch.setattr("app.main.interpret_notes", _dummy_success)
    monkeypatch.setattr("app.main.optimize", _dummy_success_optimize)
    body = _valid_request(hours=_hours(shuffle=True))
    c = _client()
    r = c.post("/optimize-energy", json=body)
    assert r.status_code == 200
    plan = r.json()["hourly_plan"]
    assert [p["hour"] for p in plan] == list(range(24))


# ------------------------------------------------ interpreter failure tolerance

def test_interpreter_raises_still_returns_200_with_no_ops(monkeypatch):
    def boom(_notes, _battery):
        raise RuntimeError("LLM is on fire")

    monkeypatch.setattr("app.main.interpret_notes", boom)
    monkeypatch.setattr("app.main.optimize", _dummy_success_optimize)
    c = _client()
    r = c.post("/optimize-energy", json=_valid_request())
    assert r.status_code == 200
    body = r.json()
    entries = body["directive_interpretation"]
    assert len(entries) == len(_valid_request()["operator_notes"])
    assert all(e["applies"] is False and e["structured_adjustment"] is None for e in entries)


# ------------------------------------------------ optimizer failure -> 500

def test_optimizer_raises_returns_500_without_traceback(monkeypatch):
    def boom(_hours, _battery, _directives):
        raise RuntimeError("solver exploded\nTraceback (most recent call last):\n  ...")

    monkeypatch.setattr("app.main.interpret_notes", _dummy_success)
    monkeypatch.setattr("app.main.optimize", boom)
    c = _client()
    r = c.post("/optimize-energy", json=_valid_request())
    assert r.status_code == 500
    body = r.json()
    assert body == {"error": "internal error"}
    text = json.dumps(body).lower()
    assert "traceback" not in text
    assert "solver exploded" not in text


# ----------------------------------------------- interpretation guard

def test_bad_interpreter_outputs_become_no_ops(monkeypatch):
    """Interpreter returns malformed payloads — they must become no_op
    entries; the public response is still 200 and well-shaped."""

    def bad_interp(_notes, _battery):
        return [
            # Wrong count: only 1 entry for 2 notes
            {
                "note_index": 0,
                "applies": True,
                "directive_type": "solar_reduction",
                "structured_adjustment": {"hours": [25], "factor": 1.5},  # bad hours & factor
                "explanation": "",
            },
            # Garbage entry
            "not a dict",
            # Duplicate note_index, unsorted hours, ok factor
            {
                "note_index": 0,
                "applies": True,
                "directive_type": "solar_reduction",
                "structured_adjustment": {"hours": [14, 13], "factor": 0.5},
                "explanation": "x",
            },
            # Unknown directive type
            {
                "note_index": 1,
                "applies": True,
                "directive_type": "no_such_thing",
                "structured_adjustment": {"hours": [10]},
                "explanation": "x",
            },
        ]

    monkeypatch.setattr("app.main.interpret_notes", bad_interp)
    monkeypatch.setattr("app.main.optimize", _dummy_success_optimize)
    body = _valid_request(operator_notes=["note one", "note two"])
    c = _client()
    r = c.post("/optimize-energy", json=body)
    assert r.status_code == 200
    resp = r.json()
    assert list(resp.keys())[:1] == ["scenario_id"]
    # All three notes mapped to no_op (the only entry for index 0 is a bad one;
    # index 1 has bad type; index 2 is filled by the duplicate guard with no_op).
    interp = resp["directive_interpretation"]
    assert len(interp) == 2
    assert [e["note_index"] for e in interp] == [0, 1]
    for entry in interp:
        assert entry["applies"] is False
        assert entry["directive_type"] == "no_op"
        assert entry["structured_adjustment"] is None
        assert isinstance(entry["explanation"], str) and entry["explanation"]
    # Plan still 24 hours.
    assert [p["hour"] for p in resp["hourly_plan"]] == list(range(24))


# ----------------------------------------------- plan guard

def test_plan_guard_recomputes_totals(monkeypatch):
    """Optimizer lies about totals; the response totals match the recomputed plan."""

    def lying_optimize(hours, battery, directives):
        plan = [
            {
                "hour": h["hour"],
                "grid_kwh": 2.0,
                "solar_used_kwh": 1.0,
                "battery_action": "idle",
                "battery_kwh": 0.0,
                "battery_energy_after_kwh": battery["initial_energy_kwh"],
            }
            for h in hours
        ]
        return {
            "hourly_plan": plan,
            "total_grid_kwh": 999.0,   # wrong
            "total_cost_bdt": 9999.0,  # wrong
            "peak_grid_kwh": 1.0,      # wrong
            "status": "optimal",
        }

    monkeypatch.setattr("app.main.interpret_notes", _dummy_success)
    monkeypatch.setattr("app.main.optimize", lying_optimize)
    c = _client()
    r = c.post("/optimize-energy", json=_valid_request())
    assert r.status_code == 200
    body = r.json()
    # 24 hours × 2 grid_kwh × 8 BDT = 384 cost, 48 grid total, 2 peak.
    assert body["total_grid_kwh"] == 48.0
    assert body["total_cost_bdt"] == 384.0
    assert body["peak_grid_kwh"] == 2.0


def test_optimizer_nan_returns_generic_500(monkeypatch):
    """Optimizer returns NaN — generic 500, no traceback, no internals leaked."""

    def nan_optimize(hours, battery, directives):
        plan = [
            {
                "hour": h["hour"],
                "grid_kwh": float("nan") if h["hour"] == 5 else 2.0,
                "solar_used_kwh": 0.0,
                "battery_action": "idle",
                "battery_kwh": 0.0,
                "battery_energy_after_kwh": battery["initial_energy_kwh"],
            }
            for h in hours
        ]
        return {
            "hourly_plan": plan,
            "total_grid_kwh": float("nan"),
            "total_cost_bdt": 0.0,
            "peak_grid_kwh": 0.0,
            "status": "optimal",
        }

    monkeypatch.setattr("app.main.interpret_notes", _dummy_success)
    monkeypatch.setattr("app.main.optimize", nan_optimize)
    c = _client()
    r = c.post("/optimize-energy", json=_valid_request())
    assert r.status_code == 500
    body = r.json()
    assert body == {"error": "internal error"}
    text = json.dumps(body).lower()
    assert "traceback" not in text
    assert "nan" not in text


# ----------------------------------------------- LRU cache

def test_cache_hit_on_repeat_request(monkeypatch):
    """Second identical request must be served from the cache: faster and equal."""
    monkeypatch.setattr("app.main.interpret_notes", _dummy_success)
    monkeypatch.setattr("app.main.optimize", _dummy_success_optimize)
    c = _client()
    body = _valid_request()

    t0 = time.perf_counter()
    r1 = c.post("/optimize-energy", json=body)
    first_ms = (time.perf_counter() - t0) * 1000.0
    assert r1.status_code == 200
    body1 = r1.json()

    t0 = time.perf_counter()
    r2 = c.post("/optimize-energy", json=body)
    second_ms = (time.perf_counter() - t0) * 1000.0
    assert r2.status_code == 200
    body2 = r2.json()

    assert body1 == body2
    # Cache hit must be no slower than the first request (in practice, much faster).
    assert second_ms <= first_ms + 1.0


# ----------------------------------------------- interpreter timeout fallback

def test_slow_interpreter_returns_200_with_no_ops_under_15s(monkeypatch):
    """A 14-second interpreter is killed by the 12 s timeout and falls back to
    no_op entries; total request < 15 s."""

    def slow_interp(_notes, _battery):
        time.sleep(14.0)
        return []

    monkeypatch.setattr("app.main.interpret_notes", slow_interp)
    monkeypatch.setattr("app.main.optimize", _dummy_success_optimize)
    c = _client()
    started = time.perf_counter()
    r = c.post("/optimize-energy", json=_valid_request())
    elapsed = time.perf_counter() - started
    assert r.status_code == 200, f"expected 200 got {r.status_code} after {elapsed:.2f}s"
    assert elapsed < 15.0, f"took {elapsed:.2f}s, must be < 15s"
    body = r.json()
    assert all(e["applies"] is False for e in body["directive_interpretation"])
    assert len(body["directive_interpretation"]) == 1
