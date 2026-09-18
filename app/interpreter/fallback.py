"""Regex-based backup interpreter used when the LLM is unreachable.

Handles the common directive types from public samples. Returns one entry
per note in note_index order. Anything it cannot parse becomes no_op.

Public surface:
  fallback_interpret(notes, battery) -> list[dict]
"""

from __future__ import annotations

import re

from typing import Any

from .normalize import build_hours

_NO_OP = lambda idx, msg: {
    "note_index": idx,
    "applies": False,
    "directive_type": "no_op",
    "structured_adjustment": None,
    "explanation": msg,
}


_FUTURE_KEYWORDS = (
    "next week", "next month", "next quarter",
    "next monday", "next tuesday", "next wednesday",
    "next thursday", "next friday",
    "tomorrow", "upcoming", "menu",
    "room booking", "library", "club notice",
    "sports", "registration deadline",
    "career fair", "seminar",
    "cafeteria", "procurement",
)

def _to_24(hour, meridiem):
    if meridiem is None:
        return hour
    m = meridiem.lower()
    if m == "am":
        return 0 if hour == 12 else hour
    if m == "pm":
        return hour if hour == 12 else hour + 12
    return hour



def _is_future_only(text):
    low = text.lower()
    return any(k in low for k in _FUTURE_KEYWORDS)

def _parse_window(text):
    """Return (start_hour, end_hour) in 24h clock or None.

    Handles "X AM to Y PM", "X-Y", "X to Y", wrap midnight,
    and words like "noon" (12) / "midnight" (0) as bounds.
    """
    low = text.lower()
    if "noon" in low:
        low = low.replace("noon", "12")
    if "midnight" in low:
        low = low.replace("midnight", "0")
    m = re.search(r"(\d{1,2})(?::\d{2})?\s*(am|pm)?\s*(?:-|to|until|between)\s*(\d{1,2})(?::\d{2})?\s*(am|pm)?", low)
    if not m:
        # Also match the form "between X and Y" where the first bound precedes the connector.
        m = re.search(r"between\s+(\d{1,2})(?::\d{2})?\s*(am|pm)?\s*(?:and|to|until|-)\s*(\d{1,2})(?::\d{2})?\s*(am|pm)?", low)
        if not m:
            return None
    a = int(m.group(1))
    ma = m.group(2)
    b = int(m.group(3))
    mb = m.group(4)
    s = _to_24(a, ma)
    e = _to_24(b, mb)
    if e <= s:
        return None if e == s else (s, e + 24)
    return (s, e)


def _classify(text):
    """Return (directive_type, kwargs) or (no_op, {}) for a single note.

    Combines regex window detection with keyword-driven type selection.
    """
    low = text.lower()
    window = _parse_window(text)
    cap = None
    try:
        m = re.search(r"capacity[: ]+(\d+(?:\.\d+)?)", low)
        if m:
            cap = float(m.group(1))
    except Exception:
        pass

    # 1) solar reduction
    if "solar" in low or "rooftop" in low or "panel" in low:
        pct = None
        for kw, val in {
            "half": 0.5,
            "a third": 1/3,
            "a quarter": 0.25,
            "one-fifth": 0.2,
            "a fifth": 0.2,
            "a tenth": 0.1,
        }.items():
            if kw in low:
                pct = val
                break
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", low)
        if m:
            pct = 1 - float(m.group(1)) / 100.0
        if pct is None and ("zero" in low or "no solar" in low or "no usable" in low):
            pct = 0.0
        if pct is not None and window:
            return ("solar_reduction", {"hours": list(window), "factor": pct})


    # 2) battery reserve (kWh, percent, or fraction-word)
    # Note: skip when this is really a grid cap (covered by branch 5).
    if ("battery" in low or "reserve" in low) and not ("grid" in low or "import" in low or "feeder" in low):
        m = re.search(r"(\d+(?:\.\d+)?)\s*kwh", low)
        kwh = float(m.group(1)) if m else None
        pct = None
        m2 = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent)", low)
        if m2:
            pct = float(m2.group(1)) / 100.0
        if pct is None:
            for kw, val in {
                "half": 0.5,
                "a third": 1/3,
                "a quarter": 0.25,
                "one-fifth": 0.2,
                "a fifth": 0.2,
                "a tenth": 0.1,
                "one third": 1/3,
                "one quarter": 0.25,
            }.items():
                if kw in low:
                    pct = val
                    break
        if window and (kwh is not None or pct is not None):
            return ("minimum_battery_reserve", {"hours": list(window), "kwh": kwh, "pct": pct})

    # 3) no_charge
    if ("charger" in low or "charging" in low) and ("unavailable" in low or "offline" in low or "disabled" in low or "isolated" in low):
        if window:
            return ("no_charge_window", {"hours": list(window)})

    # 4) no_discharge
    if "discharge" in low and ("must not" in low or "do not" in low or "no " in low):
        if window:
            return ("no_discharge_window", {"hours": list(window)})

    # 5) max_grid
    if "grid" in low or "feeder" in low or "import" in low:
        m = re.search(r"(\d+(?:\.\d+)?)\s*kwh", low)
        cap_g = float(m.group(1)) if m else None
        if window and cap_g is not None:
            return ("max_grid_window", {"hours": list(window), "cap": cap_g})

    return ("no_op", {})


def fallback_interpret(notes, battery):
    """Produce one interpretation entry per note.

    battery is a dict with capacity_kwh, minimum_energy_kwh.
    """
    cap = 0.0
    try:
        cap = float((battery or {}).get("capacity_kwh") or 0.0)
    except (TypeError, ValueError):
        pass

    out = []
    for idx, note in enumerate(notes or []):
        if not isinstance(note, str) or not note.strip():
            out.append(_NO_OP(idx, "empty note"))
            continue
        if _is_future_only(note):
            out.append(_NO_OP(idx, "note is about a future or unrelated event"))
            continue
        dtype, kw = _classify(note)
        if dtype == "no_op":
            out.append(_NO_OP(idx, "note did not match any directive pattern"))
            continue
        hours = kw.get("hours")
        if not hours:
            out.append(_NO_OP(idx, "no time window detected"))
            continue
        if dtype == "solar_reduction":
            out.append({
                "note_index": idx,
                "applies": True,
                "directive_type": dtype,
                "structured_adjustment": {"hours": hours, "factor": kw["factor"]},
                "explanation": "regex fallback classified as " + dtype,
            })
        elif dtype == "minimum_battery_reserve":
            rk = kw.get("kwh")
            pct = kw.get("pct")
            if rk is None and pct is not None:
                rk = round(pct * cap, 6)
            if rk is None:
                out.append(_NO_OP(idx, "reserve magnitude missing"))
                continue
            out.append({
                "note_index": idx,
                "applies": True,
                "directive_type": dtype,
                "structured_adjustment": {"hours": hours, "minimum_energy_kwh": rk},
                "explanation": "regex fallback classified as " + dtype,
            })
        elif dtype == "no_charge_window" or dtype == "no_discharge_window":
            out.append({
                "note_index": idx,
                "applies": True,
                "directive_type": dtype,
                "structured_adjustment": {"hours": hours},
                "explanation": "regex fallback classified as " + dtype,
            })
        elif dtype == "max_grid_window":
            cap_g = kw.get("cap")
            if cap_g is None:
                out.append(_NO_OP(idx, "grid cap magnitude missing"))
                continue
            out.append({
                "note_index": idx,
                "applies": True,
                "directive_type": dtype,
                "structured_adjustment": {"hours": hours, "max_grid_kwh": cap_g},
                "explanation": "regex fallback classified as " + dtype,
            })
        else:
            out.append(_NO_OP(idx, "unsupported directive type"))
    return out
