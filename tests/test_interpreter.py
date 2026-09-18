"""Unit tests for app.interpreter.normalize (WU-LLM-3).

Owner: Tamjid.

Each test feeds a mocked raw LLM dict into normalize() and asserts:
  - exactly len(notes) entries in input order
  - the per-entry DirectiveInterpretation fields are correct (type, applies,
    structured_adjustment, etc.)
  - bad_indexes correctly reports malformed inputs

No network calls are made. The LLM is mocked entirely.
"""
from __future__ import annotations

import math

from app.interpreter.normalize import normalize


# --- 1. basic shape: one note -> one entry ---------------------------------

def test_single_solar_reduction_round_trip():
    raw = {"notes": [{
        "note_index": 0,
        "directive_type": "solar_reduction",
        "start_hour": 13,
        "end_hour": 15,
        "solar_remaining_fraction": 0.2,
        "reserve_kwh": None,
        "reserve_percent_of_capacity": None,
        "max_grid_kwh": None,
        "explanation": "drop to 20%",
    }]}
    entries, bad = normalize(raw, ["drop solar to 20% from 13:00 to 15:00"], 500.0)
    assert bad == []
    assert len(entries) == 1
    e = entries[0]
    assert e.directive_type == "solar_reduction"
    assert e.applies is True
    sa = e.structured_adjustment
    assert sa is not None
    assert sa["hours"] == [13, 14]
    assert math.isclose(sa["factor"], 0.2, abs_tol=1e-9)


def test_no_op_emitted_for_unrelated_note():
    raw = {"notes": [{
        "note_index": 0,
        "directive_type": "no_op",
        "start_hour": 0,
        "end_hour": 0,
        "solar_remaining_fraction": None,
        "reserve_kwh": None,
        "reserve_percent_of_capacity": None,
        "max_grid_kwh": None,
        "explanation": "next week menu change",
    }]}
    entries, bad = normalize(raw, ["Next month the cafeteria changes its menu."], 500.0)
    assert bad == []
    assert len(entries) == 1
    e = entries[0]
    assert e.directive_type == "no_op"
    assert e.applies is False
    assert e.structured_adjustment is None


# --- 2. hours expansion: wrap-around, midnight end=24 ----------------------

def test_wraparound_window_emits_both_sides():
    raw = {"notes": [{
        "note_index": 0,
        "directive_type": "no_discharge_window",
        "start_hour": 22,
        "end_hour": 2,
        "solar_remaining_fraction": None,
        "reserve_kwh": None,
        "reserve_percent_of_capacity": None,
        "max_grid_kwh": None,
        "explanation": "10 PM to 2 AM",
    }]}
    entries, bad = normalize(raw, ["Charge only between 10 PM and 2 AM."], 500.0)
    assert bad == []
    e = entries[0]
    assert e.directive_type == "no_discharge_window"
    assert e.applies is True
    assert e.structured_adjustment["hours"] == [0, 1, 22, 23]


def test_midnight_end_24_yields_full_late_day():
    raw = {"notes": [{
        "note_index": 0,
        "directive_type": "no_charge_window",
        "start_hour": 8,
        "end_hour": 24,
        "solar_remaining_fraction": None,
        "reserve_kwh": None,
        "reserve_percent_of_capacity": None,
        "max_grid_kwh": None,
        "explanation": "until midnight",
    }]}
    entries, bad = normalize(raw, ["Charger offline 8 AM until midnight."], 500.0)
    assert bad == []
    e = entries[0]
    assert e.directive_type == "no_charge_window"
    assert e.structured_adjustment["hours"] == list(range(8, 24))


# --- 3. percent_of_capacity -> kWh -----------------------------------------

def test_reserve_percent_converted_to_kwh():
    raw = {"notes": [{
        "note_index": 0,
        "directive_type": "minimum_battery_reserve",
        "start_hour": 19,
        "end_hour": 24,
        "solar_remaining_fraction": None,
        "reserve_kwh": None,
        "reserve_percent_of_capacity": 30,
        "max_grid_kwh": None,
        "explanation": "30% reserve overnight",
    }]}
    entries, bad = normalize(raw, ["Hold 30% emergency reserve overnight."], 500.0)
    assert bad == []
    e = entries[0]
    assert e.directive_type == "minimum_battery_reserve"
    sa = e.structured_adjustment
    assert math.isclose(sa["minimum_energy_kwh"], 150.0, abs_tol=1e-9)
    assert sa["hours"] == list(range(19, 24))


# --- 4. each directive type ------------------------------------------------

def test_minimum_battery_reserve_with_kwh_passthrough():
    raw = {"notes": [{
        "note_index": 0,
        "directive_type": "minimum_battery_reserve",
        "start_hour": 12,
        "end_hour": 18,
        "solar_remaining_fraction": None,
        "reserve_kwh": 15,
        "reserve_percent_of_capacity": None,
        "max_grid_kwh": None,
        "explanation": "15 kWh from noon to 6 PM",
    }]}
    entries, bad = normalize(raw, ["Keep >= 15 kWh from noon to 6 PM."], 500.0)
    assert bad == []
    e = entries[0]
    assert e.directive_type == "minimum_battery_reserve"
    assert math.isclose(e.structured_adjustment["minimum_energy_kwh"], 15.0, abs_tol=1e-9)
    assert e.structured_adjustment["hours"] == [12, 13, 14, 15, 16, 17]


def test_max_grid_window_carries_kwh_cap():
    raw = {"notes": [{
        "note_index": 0,
        "directive_type": "max_grid_window",
        "start_hour": 17,
        "end_hour": 22,
        "solar_remaining_fraction": None,
        "reserve_kwh": None,
        "reserve_percent_of_capacity": None,
        "max_grid_kwh": 120,
        "explanation": "feeder temp limit",
    }]}
    entries, bad = normalize(raw, ["Cap grid imports at 120 kWh/h, 5 PM to 10 PM."], 500.0)
    assert bad == []
    e = entries[0]
    assert e.directive_type == "max_grid_window"
    assert math.isclose(e.structured_adjustment["max_grid_kwh"], 120.0, abs_tol=1e-9)
    assert e.structured_adjustment["hours"] == [17, 18, 19, 20, 21]


# --- 5. multi-note: order preserved, one bad_index -------------------------

def test_two_notes_preserve_input_order_and_both_present():
    raw = {"notes": [
        {
            "note_index": 0,
            "directive_type": "no_op",
            "start_hour": 0, "end_hour": 0,
            "solar_remaining_fraction": None, "reserve_kwh": None,
            "reserve_percent_of_capacity": None, "max_grid_kwh": None,
            "explanation": "menu",
        },
        {
            "note_index": 1,
            "directive_type": "minimum_battery_reserve",
            "start_hour": 12, "end_hour": 18,
            "solar_remaining_fraction": None, "reserve_kwh": 15,
            "reserve_percent_of_capacity": None, "max_grid_kwh": None,
            "explanation": ">=15 kWh",
        },
    ]}
    entries, bad = normalize(
        raw,
        ["Cafeteria menu changes next month.", "Keep >= 15 kWh noon-6 PM."],
        500.0,
    )
    assert bad == []
    assert len(entries) == 2
    assert entries[0].directive_type == "no_op"
    assert entries[1].directive_type == "minimum_battery_reserve"
    assert entries[1].structured_adjustment["minimum_energy_kwh"] == 15.0


# --- 6. guardrails: bad factor, missing index, duplicate, unknown type -----

def test_factor_out_of_range_marks_bad_index():
    raw = {"notes": [{
        "note_index": 0,
        "directive_type": "solar_reduction",
        "start_hour": 13, "end_hour": 15,
        "solar_remaining_fraction": 1.5,  # > 1 is illegal
        "reserve_kwh": None, "reserve_percent_of_capacity": None,
        "max_grid_kwh": None, "explanation": "bogus",
    }]}
    entries, bad = normalize(raw, ["Solar 150% from 13:00 to 15:00."], 500.0)
    assert 0 in bad
    assert entries[0].directive_type == "no_op"
    assert entries[0].applies is False
    assert entries[0].explanation != ""


def test_missing_note_index_marked_bad_and_replaced_with_noop():
    raw = {"notes": [{
        "note_index": 1,  # but notes list has only [0] -> out-of-range entry is dropped
        "directive_type": "no_charge_window",
        "start_hour": 1, "end_hour": 4,
        "solar_remaining_fraction": None, "reserve_kwh": None,
        "reserve_percent_of_capacity": None, "max_grid_kwh": None,
        "explanation": "swap inverter",
    }]}
    notes = ["Don't charge 1 AM to 4 AM."]
    entries, bad = normalize(raw, notes, 500.0)
    # Note 0 is "missing" (the LLM never produced an entry for it); index 1
    # was out-of-range so it's silently dropped — only 0 is bad.
    assert 0 in bad
    assert entries[0].directive_type == "no_op"
    assert entries[0].applies is False


def test_duplicate_note_index_marked_bad_and_other_present():
    raw = {"notes": [
        {
            "note_index": 0,
            "directive_type": "no_charge_window",
            "start_hour": 1, "end_hour": 4,
            "solar_remaining_fraction": None, "reserve_kwh": None,
            "reserve_percent_of_capacity": None, "max_grid_kwh": None,
            "explanation": "first",
        },
        {
            "note_index": 0,
            "directive_type": "solar_reduction",
            "start_hour": 9, "end_hour": 14,
            "solar_remaining_fraction": 0.2,
            "reserve_kwh": None, "reserve_percent_of_capacity": None,
            "max_grid_kwh": None,
            "explanation": "duplicate",
        },
    ]}
    entries, bad = normalize(
        raw,
        ["Don't charge 1-4 AM.", "Solar 20% 9-14."],
        500.0,
    )
    assert 0 in bad
    # the LLM is ambiguous on note 0; core.py will replace it via retry/fallback
    assert entries[0].directive_type == "no_op"


def test_unknown_directive_type_marked_bad():
    raw = {"notes": [{
        "note_index": 0,
        "directive_type": "force_grid",  # not in the allowed set
        "start_hour": 0, "end_hour": 0,
        "solar_remaining_fraction": None, "reserve_kwh": None,
        "reserve_percent_of_capacity": None, "max_grid_kwh": None,
        "explanation": "made up",
    }]}
    entries, bad = normalize(raw, ["Force the grid to 100%."], 500.0)
    assert 0 in bad
    assert entries[0].directive_type == "no_op"


# --- 7. extra defense-in-depth checks --------------------------------------

def test_reserve_above_capacity_marked_bad():
    raw = {"notes": [{
        "note_index": 0,
        "directive_type": "minimum_battery_reserve",
        "start_hour": 0, "end_hour": 24,
        "solar_remaining_fraction": None,
        "reserve_kwh": 999999.0,  # way above 500 capacity
        "reserve_percent_of_capacity": None, "max_grid_kwh": None,
        "explanation": "absurd reserve",
    }]}
    entries, bad = normalize(raw, ["Keep battery above 999999 kWh."], 500.0)
    assert 0 in bad
    assert entries[0].directive_type == "no_op"


def test_negative_hours_or_above_24_marked_bad():
    raw = {"notes": [{
        "note_index": 0,
        "directive_type": "no_charge_window",
        "start_hour": -1, "end_hour": 5,
        "solar_remaining_fraction": None, "reserve_kwh": None,
        "reserve_percent_of_capacity": None, "max_grid_kwh": None,
        "explanation": "negative start",
    }]}
    entries, bad = normalize(raw, ["Don't charge before midnight."], 500.0)
    assert 0 in bad
    assert entries[0].directive_type == "no_op"


def test_window_start_equal_end_marked_bad():
    raw = {"notes": [{
        "note_index": 0,
        "directive_type": "no_charge_window",
        "start_hour": 10, "end_hour": 10,  # empty window
        "solar_remaining_fraction": None, "reserve_kwh": None,
        "reserve_percent_of_capacity": None, "max_grid_kwh": None,
        "explanation": "empty",
    }]}
    entries, bad = normalize(raw, ["Don't charge at exactly 10 AM."], 500.0)
    assert 0 in bad
    assert entries[0].directive_type == "no_op"


# --- 8. end-of-list fallback: extra LLM entries for non-existent notes -----

def test_extra_entries_for_nonexistent_indexes_are_ignored_but_count_matches_notes():
    raw = {"notes": [
        {
            "note_index": 0,
            "directive_type": "no_charge_window",
            "start_hour": 1, "end_hour": 4,
            "solar_remaining_fraction": None, "reserve_kwh": None,
            "reserve_percent_of_capacity": None, "max_grid_kwh": None,
            "explanation": "ok",
        },
        {
            "note_index": 5,  # out of range -> silently dropped, not reported as bad
            "directive_type": "solar_reduction",
            "start_hour": 9, "end_hour": 14,
            "solar_remaining_fraction": 0.5,
            "reserve_kwh": None, "reserve_percent_of_capacity": None,
            "max_grid_kwh": None,
            "explanation": "ignored",
        },
    ]}
    entries, bad = normalize(raw, ["Don't charge 1-4 AM."], 500.0)
    assert bad == []  # note 0 was filled in OK; index 5 was out-of-range
    assert len(entries) == 1
    assert entries[0].directive_type == "no_charge_window"
