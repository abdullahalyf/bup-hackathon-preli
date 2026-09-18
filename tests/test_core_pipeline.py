"""Unit tests for app.interpreter.core.interpret_notes.

Owner: Tamjid. Covers the full pipeline with monkeypatched LLM calls so the
tests never hit a network. Verifies:
  - exactly len(notes) entries always
  - never raises on any combination of LLM failures
  - cache hit short-circuits the LLM
  - retry path merges fixed entries
  - regex fallback fills any remaining bad indexes
  - bad input (None, non-list notes) does not crash
"""

from __future__ import annotations

import pytest

import app.interpreter.core as core


_BATTERY = {
    "capacity_kwh": 500.0,
    "initial_energy_kwh": 250.0,
    "minimum_energy_kwh": 0.0,
    "max_charge_kwh_per_hour": 50.0,
    "max_discharge_kwh_per_hour": 50.0,
}


@pytest.fixture(autouse=True)
def _clear_cache():
    core._reset_cache()
    yield
    core._reset_cache()


def _good_raw_solar(note_index: int = 0):
    return {
        "notes": [
            {
                "note_index": note_index,
                "directive_type": "solar_reduction",
                "start_hour": 13,
                "end_hour": 15,
                "solar_remaining_fraction": 0.2,
                "reserve_kwh": None,
                "reserve_percent_of_capacity": None,
                "max_grid_kwh": None,
                "explanation": "test",
            }
        ]
    }


def _bad_raw_empty():
    return {"notes": []}


def test_happy_path_single_note(monkeypatch):
    monkeypatch.setattr(core, "call_llm", lambda system, user: _good_raw_solar(0))
    out = core.interpret_notes(
        ["Drop solar to 20% from 13:00 to 15:00."], _BATTERY
    )
    assert len(out) == 1
    entry = out[0]
    assert entry["note_index"] == 0
    assert entry["applies"] is True
    assert entry["directive_type"] == "solar_reduction"
    assert entry["structured_adjustment"]["factor"] == pytest.approx(0.2)
    assert 13 in entry["structured_adjustment"]["hours"]
    assert 14 in entry["structured_adjustment"]["hours"]


def test_happy_path_multiple_notes(monkeypatch):
    def fake_call(system, user):
        return {
            "notes": [
                {
                    "note_index": 0,
                    "directive_type": "solar_reduction",
                    "start_hour": 13,
                    "end_hour": 15,
                    "solar_remaining_fraction": 0.2,
                    "reserve_kwh": None,
                    "reserve_percent_of_capacity": None,
                    "max_grid_kwh": None,
                    "explanation": "solar",
                },
                {
                    "note_index": 1,
                    "directive_type": "no_op",
                    "start_hour": None,
                    "end_hour": None,
                    "solar_remaining_fraction": None,
                    "reserve_kwh": None,
                    "reserve_percent_of_capacity": None,
                    "max_grid_kwh": None,
                    "explanation": "menu only",
                },
            ]
        }

    monkeypatch.setattr(core, "call_llm", fake_call)
    out = core.interpret_notes(
        ["Drop solar to 20% from 13 to 15.", "Lunch menu: rice and dal."],
        _BATTERY,
    )
    assert [e["note_index"] for e in out] == [0, 1]
    assert out[0]["applies"] is True
    assert out[0]["directive_type"] == "solar_reduction"
    assert out[1]["applies"] is False
    assert out[1]["directive_type"] == "no_op"


def test_llm_returns_invalid_raw_goes_to_fallback(monkeypatch):
    """LLM returns a dict missing 'notes' entirely. The pipeline should
    produce one no_op per note, then use the regex fallback for any note
    whose text still matches a directive pattern."""
    monkeypatch.setattr(core, "call_llm", lambda system, user: {"foo": "bar"})
    out = core.interpret_notes(
        ["Drop solar to 20% from 13:00 to 15:00."], _BATTERY
    )
    assert len(out) == 1
    # The regex fallback should pick this up.
    assert out[0]["directive_type"] == "solar_reduction"
    assert out[0]["applies"] is True


def test_llm_returns_none_goes_to_fallback_and_never_raises(monkeypatch):
    """Both LLM and retry LLM fail. The regex fallback must still try."""
    monkeypatch.setattr(core, "call_llm", lambda system, user: None)
    out = core.interpret_notes(
        [
            "Drop solar to 20% from 13:00 to 15:00.",
            "Keep 30 kWh in reserve all day.",
            "Gibberish that matches nothing.",
        ],
        _BATTERY,
    )
    assert len(out) == 3
    assert out[0]["directive_type"] == "solar_reduction"
    assert out[1]["directive_type"] == "minimum_battery_reserve"
    assert out[2]["directive_type"] == "no_op"


def test_llm_raises_both_calls_never_propagates(monkeypatch):
    from app.interpreter.llm_client import LLMClientError

    def always_fail(system, user):
        raise LLMClientError("simulated outage")

    monkeypatch.setattr(core, "call_llm", always_fail)
    # Should not raise; should still return len(notes) dicts.
    out = core.interpret_notes(
        ["Drop solar to 20% from 13:00 to 15:00."], _BATTERY
    )
    assert len(out) == 1
    # Regex fallback should have caught it.
    assert out[0]["directive_type"] == "solar_reduction"


def test_retry_fixes_bad_note(monkeypatch):
    """First LLM call marks one note bad. Retry fixes that note only."""
    call_count = {"n": 0}

    def fake_call(system, user):
        call_count["n"] += 1
        if call_count["n"] == 1:
            # First call: omit note_index=1 entirely => marked bad.
            return _good_raw_solar(0)
        # Retry: emit both notes correctly.
        return {
            "notes": [
                {
                    "note_index": 0,
                    "directive_type": "solar_reduction",
                    "start_hour": 13,
                    "end_hour": 15,
                    "solar_remaining_fraction": 0.2,
                    "reserve_kwh": None,
                    "reserve_percent_of_capacity": None,
                    "max_grid_kwh": None,
                    "explanation": "solar",
                },
                {
                    "note_index": 1,
                    "directive_type": "minimum_battery_reserve",
                    "start_hour": 0,
                    "end_hour": 24,
                    "solar_remaining_fraction": None,
                    "reserve_kwh": 30.0,
                    "reserve_percent_of_capacity": None,
                    "max_grid_kwh": None,
                    "explanation": "reserve",
                },
            ]
        }

    monkeypatch.setattr(core, "call_llm", fake_call)
    out = core.interpret_notes(
        [
            "Drop solar to 20% from 13 to 15.",
            "Keep 30 kWh in reserve.",
        ],
        _BATTERY,
    )
    assert len(out) == 2
    # First note came from first LLM call.
    assert out[0]["directive_type"] == "solar_reduction"
    assert "[retry]" not in out[0]["explanation"]
    # Second note came from retry.
    assert out[1]["directive_type"] == "minimum_battery_reserve"
    assert "[retry]" in out[1]["explanation"]
    assert call_count["n"] == 2


def test_retry_still_bad_falls_through_to_regex(monkeypatch):
    """Both first call and retry produce invalid output. Regex fallback wins."""
    monkeypatch.setattr(core, "call_llm", lambda system, user: _bad_raw_empty())
    out = core.interpret_notes(
        ["Drop solar to 20% from 13:00 to 15:00."], _BATTERY
    )
    assert len(out) == 1
    assert out[0]["directive_type"] == "solar_reduction"


def test_cache_hit_avoids_second_llm_call(monkeypatch):
    calls = {"n": 0}

    def fake_call(system, user):
        calls["n"] += 1
        return _good_raw_solar(0)

    monkeypatch.setattr(core, "call_llm", fake_call)
    notes = ["Drop solar to 20% from 13:00 to 15:00."]
    first = core.interpret_notes(notes, _BATTERY)
    second = core.interpret_notes(notes, _BATTERY)
    assert calls["n"] == 1  # cache short-circuited the second call.
    assert first[0]["directive_type"] == "solar_reduction"
    assert second[0]["directive_type"] == "solar_reduction"


def test_cache_distinguishes_capacity(monkeypatch):
    calls = {"n": 0}

    def fake_call(system, user):
        calls["n"] += 1
        return _good_raw_solar(0)

    monkeypatch.setattr(core, "call_llm", fake_call)
    smaller = {**_BATTERY, "capacity_kwh": 100.0}
    bigger = {**_BATTERY, "capacity_kwh": 500.0}
    notes = ["Drop solar to 20% from 13:00 to 15:00."]
    core.interpret_notes(notes, smaller)
    core.interpret_notes(notes, bigger)
    assert calls["n"] == 2  # different capacity => cache miss


def test_empty_notes_returns_empty_list(monkeypatch):
    monkeypatch.setattr(core, "call_llm", lambda system, user: _good_raw_solar(0))
    assert core.interpret_notes([], _BATTERY) == []


def test_non_list_notes_handled(monkeypatch):
    monkeypatch.setattr(core, "call_llm", lambda system, user: _good_raw_solar(0))
    # Should not raise; should be treated as empty list.
    assert core.interpret_notes(None, _BATTERY) == []  # type: ignore[arg-type]
    out = core.interpret_notes(
        ["Drop solar to 20% from 13:00 to 15:00.", None], _BATTERY
    )
    # Coerces non-strings to str, so length is preserved.
    assert len(out) == 2
    assert out[0]["directive_type"] == "solar_reduction"


def test_battery_can_be_pydantic_model(monkeypatch):
    monkeypatch.setattr(core, "call_llm", lambda system, user: _good_raw_solar(0))
    from app.schemas import Battery

    b = Battery(
        capacity_kwh=500.0,
        initial_energy_kwh=100.0,
        minimum_energy_kwh=0.0,
        max_charge_kwh_per_hour=50.0,
        max_discharge_kwh_per_hour=50.0,
    )
    out = core.interpret_notes(
        ["Drop solar to 20% from 13:00 to 15:00."], b
    )
    assert out[0]["directive_type"] == "solar_reduction"


def test_battery_missing_capacity_returns_zero_capacity_path(monkeypatch):
    monkeypatch.setattr(core, "call_llm", lambda system, user: _good_raw_solar(0))
    out = core.interpret_notes(
        ["Drop solar to 20% from 13:00 to 15:00."], {}
    )
    assert out[0]["directive_type"] == "solar_reduction"


def test_never_raises_on_junk_inputs(monkeypatch):
    # LLM also says no_op for this junk; the pipeline must respect it.
    def noop_call(system, user):
        return {
            "notes": [
                {
                    "note_index": 0,
                    "directive_type": "no_op",
                    "start_hour": None,
                    "end_hour": None,
                    "solar_remaining_fraction": None,
                    "reserve_kwh": None,
                    "reserve_percent_of_capacity": None,
                    "max_grid_kwh": None,
                    "explanation": "no clear directive",
                }
            ]
        }

    monkeypatch.setattr(core, "call_llm", noop_call)
    # None battery must not crash; "???" is gibberish and LLM says no_op.
    out = core.interpret_notes(["???"], None)  # type: ignore[arg-type]
    assert len(out) == 1
    assert out[0]["directive_type"] == "no_op"


def test_output_shape_matches_consumer_contract(monkeypatch):
    monkeypatch.setattr(core, "call_llm", lambda system, user: _good_raw_solar(0))
    out = core.interpret_notes(
        ["Drop solar to 20% from 13:00 to 15:00."], _BATTERY
    )
    entry = out[0]
    # Must match the dict shape app.main reads.
    assert set(entry.keys()) == {
        "note_index",
        "applies",
        "directive_type",
        "structured_adjustment",
        "explanation",
    }
    assert isinstance(entry["note_index"], int)
    assert isinstance(entry["applies"], bool)
    assert isinstance(entry["directive_type"], str)
