"""Unit tests for the directive interpreter. The LLM is mocked so the
tests run offline without any network or env vars.
"""

from __future__ import annotations

import pytest

from app.interpreter import core, fallback, llm_client, normalize, prompt


# --- build_hours unit tests ---

def test_build_hours_basic():
    assert normalize.build_hours(13, 15) == [13, 14]

def test_build_hours_wrap_midnight():
    assert normalize.build_hours(22, 26) == [22, 23, 0, 1]

def test_build_hours_single_hour():
    assert normalize.build_hours(19, 19) == [19]

def test_build_hours_midnight_to_4():
    assert normalize.build_hours(0, 4) == [0, 1, 2, 3]

def test_build_hours_invalid():
    assert normalize.build_hours(None, 5) is None
    assert normalize.build_hours(13, 12) is None
    assert normalize.build_hours(0, 25) is None
    assert normalize.build_hours(-1, 5) is None

# --- normalise unit tests ---

def test_normalise_solar_reduction():
    raw = [{"note_index": 0, "directive_type": "solar_reduction",
             "start_hour": 12, "end_hour": 14,
             "solar_remaining_fraction": 0.25, "explanation": "half"}]
    out = normalize.normalise(raw, ["note"], 200.0, 5.0)
    assert out[0]["applies"] is True
    assert out[0]["directive_type"] == "solar_reduction"
    assert out[0]["structured_adjustment"] == {"hours": [12, 13], "factor": 0.25}

def test_normalise_reserve_percent():
    raw = [{"note_index": 0, "directive_type": "minimum_battery_reserve",
             "start_hour": 18, "end_hour": 21,
             "reserve_kwh": None, "reserve_percent_of_capacity": 0.5,
             "explanation": "half"}]
    out = normalize.normalise(raw, ["note"], 200.0, 5.0)
    assert out[0]["applies"] is True
    assert out[0]["structured_adjustment"][ "minimum_energy_kwh"] == 100.0

def test_normalise_reserve_kwh():
    raw = [{"note_index": 0, "directive_type": "minimum_battery_reserve",
             "start_hour": 18, "end_hour": 22,
             "reserve_kwh": 90, "explanation": "90 kWh"}]
    out = normalize.normalise(raw, ["note"], 200.0, 5.0)
    assert out[0]["structured_adjustment"][ "minimum_energy_kwh"] == 90

def test_normalise_no_op_keeps_applies_false():
    raw = [{"note_index": 0, "directive_type": "no_op",
             "start_hour": None, "end_hour": None,
             "explanation": "future event"}]
    out = normalize.normalise(raw, ["note"], 200.0, 5.0)
    assert out[0]["applies"] is False
    assert out[0]["structured_adjustment"] is None

def test_normalise_invalid_type_drops_to_no_op():
    raw = [{"note_index": 0, "directive_type": "bad_type", "start_hour": 0, "end_hour": 1}]
    out = normalize.normalise(raw, ["note"], 200.0, 5.0)
    assert out[0]["applies"] is False
    assert out[0]["directive_type"] == "no_op"

def test_normalise_factor_clamped():
    raw = [{"note_index": 0, "directive_type": "solar_reduction",
             "start_hour": 0, "end_hour": 1,
             "solar_remaining_fraction": 1.5, "explanation": "over"}]
    out = normalize.normalise(raw, ["note"], 200.0, 5.0)
    assert out[0]["structured_adjustment"][ "factor"] == 1.0


# --- core.interpret_notes mocked-LLM tests ---

class _FakeProvider:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

def _patch_llm(monkeypatch, payload):
    def fake(system, user, timeout=llm_client.TIMEOUT_S):
        return dict(payload)
    monkeypatch.setattr(llm_client, "call_llm_json", fake)
    core._cached_interpret.cache_clear()

def test_interpret_returns_one_entry_per_note(monkeypatch):
    payload = {"notes": [{"note_index": 0, "directive_type": "no_op", "start_hour": None, "end_hour": None, "explanation": "n/a"}, {"note_index": 1, "directive_type": "no_op", "start_hour": None, "end_hour": None, "explanation": "n/a"}]}
    _patch_llm(monkeypatch, payload)
    result = core.interpret_notes([ "a", "b"], {"capacity_kwh": 200, "minimum_energy_kwh": 5})
    assert [r["note_index"] for r in result] == [0, 1]
    assert all(r["applies"] is False for r in result)

def test_interpret_handles_llm_failure(monkeypatch):
    def fake(system, user, timeout=llm_client.TIMEOUT_S):
        return {}
    monkeypatch.setattr(llm_client, "call_llm_json", fake)
    core._cached_interpret.cache_clear()
    result = core.interpret_notes([ "Career fair next Thursday"], {"capacity_kwh": 200, "minimum_energy_kwh": 5})
    assert result[0]["directive_type"] == "no_op"
    assert result[0]["applies"] is False

def test_interpret_parses_real_sample(monkeypatch):
    payload = {"notes": [{"note_index": 0, "directive_type": "solar_reduction", "start_hour": 12, "end_hour": 14, "solar_remaining_fraction": 0.25, "reserve_kwh": None, "reserve_percent_of_capacity": None, "max_grid_kwh": None, "explanation": "panel clean"}, {"note_index": 1, "directive_type": "no_op", "start_hour": None, "end_hour": None, "solar_remaining_fraction": None, "reserve_kwh": None, "reserve_percent_of_capacity": None, "max_grid_kwh": None, "explanation": "next month"}]}
    _patch_llm(monkeypatch, payload)
    notes = ["wash panels noon to 2 PM", "sports next month"]
    battery = {"capacity_kwh": 200, "minimum_energy_kwh": 2}
    result = core.interpret_notes(notes, battery)
    assert result[0]["directive_type"] == "solar_reduction"
    assert result[0]["structured_adjustment"] == {"hours": [12, 13], "factor": 0.25}
    assert result[1]["directive_type"] == "no_op"
    assert result[1]["applies"] is False

def test_interpret_never_raises(monkeypatch):
    def boom(system, user, timeout=llm_client.TIMEOUT_S):
        raise RuntimeError("network")
    monkeypatch.setattr(llm_client, "call_llm_json", boom)
    core._cached_interpret.cache_clear()
    out = core.interpret_notes([ "Charger maintenance 9 AM to 11 AM"], {"capacity_kwh": 200, "minimum_energy_kwh": 2})
    assert isinstance(out, list)
    assert len(out) == 1


# --- fallback tests ---

def test_fallback_handles_future_event():
    out = fallback.fallback_interpret([ "Sports reg deadline next month"], {"capacity_kwh": 200})
    assert out[0]["applies"] is False

def test_fallback_extracts_solar_window():
    out = fallback.fallback_interpret([ "Half of solar from 1 PM to 2 PM"], {"capacity_kwh": 200})
    assert out[0]["directive_type"] == "solar_reduction"
    assert out[0]["structured_adjustment"][ "hours"] == [13, 14]

# --- prompt helpers ---

def test_build_user_message_includes_capacity():
    msg = prompt.build_user_message([ "a", "b"], 150.5)
    import json
    parsed = json.loads(msg)
    assert parsed["capacity_kwh"] == 150.5
    assert [n["note_index"] for n in parsed["notes"]] == [0, 1]

