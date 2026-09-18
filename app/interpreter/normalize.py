"""Deterministic normalisation of LLM output."""


from __future__ import annotations

from typing import Any

ALLOWED_TYPES = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
}

_EPS = 1e-9


def build_hours(start_hour, end_hour):
    """Return sorted unique hours covered by an end-exclusive window.

    Handles wrap-around (start=22, end=26 -> [22,23,0,1]). Returns None if
    either bound is missing/non-numeric or the window is empty.
    """
    if start_hour is None or end_hour is None:
        return None
    try:
        s = int(start_hour)
        e = int(end_hour)
    except (TypeError, ValueError):
        return None
    if s < 0 or e < s:
        return None
    if not (0 <= s <= 23):
        return None
    hours = []
    cursor = s
    safety = 0
    while cursor < e and safety < 48:
        hours.append(cursor % 24)
        cursor += 1
        safety += 1
        if len(hours) > 24:
            return None
    if not hours and s == e:
        return [s]
    return hours or None


def _clamp_factor(value):
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN check
        return None
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f

def _coerce_nonneg_number(value, default=None):
    if value is None:
        return default
    try:
        x = float(value)
    except (TypeError, ValueError):
        return default
    if x != x or x < 0.0:
        return default
    return x


def normalise(raw_entries, notes, capacity_kwh, base_minimum_energy_kwh=0.0):
    """Convert raw LLM entries to contract-valid directive entries.

    Always returns one entry per note, in note_index order. Entries that fail
    validation become no_op (applies=False, structured_adjustment=None).
    """
    try:
        cap = float(capacity_kwh)
    except (TypeError, ValueError):
        cap = 0.0
    try:
        base_min = float(base_minimum_energy_kwh)
    except (TypeError, ValueError):
        base_min = 0.0

    by_index = {}
    if isinstance(raw_entries, list):
        for entry in raw_entries:
            if not isinstance(entry, dict):
                continue
            try:
                idx = int(entry.get("note_index"))
            except (TypeError, ValueError):
                continue
            by_index[idx] = entry

    out = []
    for note_index, _note in enumerate(notes):
        raw = by_index.get(note_index)
        if raw is None:
            out.append(_no_op(note_index, "note not classified by model"))
            continue
        entry = _normalise_one(raw, note_index, cap, base_min)
        if entry is None:
            out.append(_no_op(note_index, "directive failed validation"))
        else:
            out.append(entry)
    return out


def _no_op(note_index, explanation):
    return {
        "note_index": note_index,
        "applies": False,
        "directive_type": "no_op",
        "structured_adjustment": None,
        "explanation": explanation,
    }

def _normalise_one(raw, note_index, cap, base_min):
    dtype = raw.get("directive_type")
    if not isinstance(dtype, str) or dtype not in ALLOWED_TYPES:
        return None
    explanation = raw.get("explanation")
    if not isinstance(explanation, str) or not explanation.strip():
        explanation = ""
    if dtype == "no_op":
        return {
            "note_index": note_index,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
            "explanation": explanation.strip(),
        }

    hours = build_hours(raw.get("start_hour"), raw.get("end_hour"))
    if hours is None or not hours:
        return None

    if dtype == "solar_reduction":
        factor = _clamp_factor(raw.get("solar_remaining_fraction"))
        if factor is None:
            return None
        return {
            "note_index": note_index,
            "applies": True,
            "directive_type": dtype,
            "structured_adjustment": {"hours": hours, "factor": factor},
            "explanation": explanation.strip(),
        }

    if dtype == "minimum_battery_reserve":
        rkwh = _coerce_nonneg_number(raw.get("reserve_kwh"))
        rpct = _clamp_factor(raw.get("reserve_percent_of_capacity"))
        if rkwh is None and rpct is None:
            return None
        if rkwh is None and rpct is not None:
            rkwh = round(rpct * cap, 6)
        if rkwh > cap + _EPS:
            rkwh = cap
        return {
            "note_index": note_index,
            "applies": True,
            "directive_type": dtype,
            "structured_adjustment": {"hours": hours, "minimum_energy_kwh": round(float(rkwh), 6)},
            "explanation": explanation.strip(),
        }

    if dtype == "no_charge_window" or dtype == "no_discharge_window":
        return {
            "note_index": note_index,
            "applies": True,
            "directive_type": dtype,
            "structured_adjustment": {"hours": hours},
            "explanation": explanation.strip(),
        }

    if dtype == "max_grid_window":
        cap_g = _coerce_nonneg_number(raw.get("max_grid_kwh"), default=0.0)
        if cap_g is None:
            return None
        return {
            "note_index": note_index,
            "applies": True,
            "directive_type": dtype,
            "structured_adjustment": {"hours": hours, "max_grid_kwh": round(float(cap_g), 6)},
            "explanation": explanation.strip(),
        }

    return None

