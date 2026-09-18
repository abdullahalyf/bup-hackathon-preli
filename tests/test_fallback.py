"""Unit tests for app.interpreter.fallback (regex fallback).

Owner: Tamjid. These tests cover the conservative regex path that
core.py uses when the LLM (and the LLM retry) cannot produce a
usable entry. The fallback should never raise, and should only
return a dict when the regex is confident.
"""

from __future__ import annotations

import pytest

from app.interpreter.fallback import fallback_extract


def _is_noop(result):
    return (
        result is not None
        and result.get("applies") is False
        and result.get("directive_type") == "no_op"
    )


def _is_apply(result):
    return result is not None and result.get("applies") is True


# --- Solar reduction ---------------------------------------------------------

def test_fallback_solar_drop_to_percent():
    r = fallback_extract("Drop solar to 20% from 13:00 to 15:00.", 500.0, 0)
    assert _is_apply(r)
    assert r["directive_type"] == "solar_reduction"
    assert r["structured_adjustment"]["factor"] == pytest.approx(0.2)
    assert 13 in r["structured_adjustment"]["hours"]
    assert 14 in r["structured_adjustment"]["hours"]


def test_fallback_solar_80_percent_reduction():
    r = fallback_extract("Slash solar output by 80% during afternoon.", 500.0, 0)
    assert _is_apply(r)
    assert r["directive_type"] == "solar_reduction"
    assert r["structured_adjustment"]["factor"] == pytest.approx(0.2)


def test_fallback_solar_one_fifth_of_normal():
    r = fallback_extract(
        "Panels will produce only one-fifth of normal from 09:00 to 12:00.",
        500.0,
        0,
    )
    assert _is_apply(r)
    assert r["directive_type"] == "solar_reduction"
    assert r["structured_adjustment"]["factor"] == pytest.approx(0.2)
    hours = r["structured_adjustment"]["hours"]
    assert 9 in hours and 10 in hours and 11 in hours


def test_fallback_solar_half_of_normal():
    r = fallback_extract("Solar at half of usual today.", 500.0, 0)
    assert _is_apply(r)
    assert r["directive_type"] == "solar_reduction"
    assert r["structured_adjustment"]["factor"] == pytest.approx(0.5)


# --- Reserve -----------------------------------------------------------------

def test_fallback_reserve_kwh_explicit():
    r = fallback_extract("Keep at least 30 kWh in reserve all day.", 500.0, 0)
    assert _is_apply(r)
    assert r["directive_type"] == "minimum_battery_reserve"
    assert r["structured_adjustment"]["minimum_energy_kwh"] == pytest.approx(30.0)


def test_fallback_reserve_percent_of_capacity():
    r = fallback_extract("Maintain 20% of capacity in reserve.", 500.0, 0)
    assert _is_apply(r)
    assert r["directive_type"] == "minimum_battery_reserve"
    assert r["structured_adjustment"]["minimum_energy_kwh"] == pytest.approx(100.0)


def test_fallback_reserve_kwh_with_window():
    r = fallback_extract(
        "Reserve 50 kWh between 17:00 and 21:00.",
        500.0,
        0,
    )
    assert _is_apply(r)
    assert r["directive_type"] == "minimum_battery_reserve"
    hours = r["structured_adjustment"]["hours"]
    assert 17 in hours and 20 in hours and 21 not in hours


# --- Max grid window ---------------------------------------------------------

def test_fallback_max_grid_draw_amount():
    r = fallback_extract(
        "Draw no more than 5 kWh from grid between 18:00 and 21:00.",
        500.0,
        0,
    )
    assert _is_apply(r)
    assert r["directive_type"] == "max_grid_window"
    assert r["structured_adjustment"]["max_grid_kwh"] == pytest.approx(5.0)
    hours = r["structured_adjustment"]["hours"]
    assert 18 in hours and 20 in hours


def test_fallback_max_grid_limit_phrase():
    r = fallback_extract("Limit grid to 8 kWh from 17:00 to 22:00.", 500.0, 0)
    assert _is_apply(r)
    assert r["directive_type"] == "max_grid_window"
    assert r["structured_adjustment"]["max_grid_kwh"] == pytest.approx(8.0)


# --- Charge / discharge windows ---------------------------------------------

def test_fallback_no_charge_window():
    r = fallback_extract(
        "Do not charge the battery from 12:00 to 14:00.",
        500.0,
        0,
    )
    assert _is_apply(r)
    assert r["directive_type"] == "no_charge_window"
    hours = r["structured_adjustment"]["hours"]
    assert 12 in hours and 14 not in hours


def test_fallback_no_discharge_window():
    r = fallback_extract(
        "Don't discharge the battery between 18:00 and 21:00.",
        500.0,
        0,
    )
    assert _is_apply(r)
    assert r["directive_type"] == "no_discharge_window"
    hours = r["structured_adjustment"]["hours"]
    assert 18 in hours and 20 in hours and 21 not in hours


# --- Irrelevance / no-op -----------------------------------------------------

def test_fallback_irrelevant_note_returns_noop():
    r = fallback_extract("Cafeteria menu tomorrow: biryani.", 500.0, 0)
    assert _is_noop(r)


def test_fallback_irrelevant_with_directive_keyword_still_extracts():
    # "menu" is in the irrelevance list, but the note also mentions a
    # battery directive, so the regex should win and produce a directive.
    r = fallback_extract(
        "Lunch menu: please keep 40 kWh in reserve.",
        500.0,
        0,
    )
    assert _is_apply(r)
    assert r["directive_type"] == "minimum_battery_reserve"


def test_fallback_garbage_returns_none():
    assert fallback_extract("", 500.0, 0) is None
    assert fallback_extract("   ", 500.0, 0) is None
    assert fallback_extract("Random chatter with no directive.", 500.0, 0) is None


# --- Defensive: never raises ------------------------------------------------

@pytest.mark.parametrize(
    "bad_input",
    [None, 123, ["list"], {"dict": True}, object()],
)
def test_fallback_never_raises_on_bad_input(bad_input):
    result = fallback_extract(bad_input, 500.0, 0)  # type: ignore[arg-type]
    # Either None or a dict; never an exception.
    assert result is None or isinstance(result, dict)


def test_fallback_never_raises_with_garbage_capacity():
    # Bad capacity shouldn't crash either; just means percent->kWh path
    # is skipped.
    r = fallback_extract("Keep 20% of capacity in reserve.", -1.0, 0)
    # With negative capacity, percent path guards -> None.
    assert r is None


# --- note_index is plumbed through ------------------------------------------

def test_fallback_preserves_note_index():
    r = fallback_extract("Drop solar to 50% from 09:00 to 10:00.", 500.0, 7)
    assert r["note_index"] == 7


# --- Wrap-around window ------------------------------------------------------

def test_fallback_window_wraps_midnight():
    r = fallback_extract(
        "Solar down to 20% from 22:00 to 02:00.",
        500.0,
        0,
    )
    assert _is_apply(r)
    hours = r["structured_adjustment"]["hours"]
    assert 22 in hours and 23 in hours and 0 in hours and 1 in hours
    assert 2 not in hours
