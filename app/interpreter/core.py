"""Top-level orchestrator: one LLM call for all notes, deterministic
validation, optional regex fallback, LRU cache. Never raises.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from typing import Any

from . import llm_client, prompt
from .fallback import fallback_interpret
from .normalize import normalise

CACHE_MAX = 256


@lru_cache(maxsize=CACHE_MAX)
def _cached_interpret(notes_key, capacity_kwh):
    """Cache LLM output keyed by canonical note tuple + capacity.

    Returns the raw LLM dict (or {} on failure). On an empty result we
    retry once after a short pause so a single transient failure does
    not poison the cache for this entry.
    """
    import time as _time
    notes_list = list(notes_key)
    user = prompt.build_user_message(notes_list, capacity_kwh)
    for _attempt in range(2):
        try:
            out = llm_client.call_llm_json(prompt.SYSTEM_PROMPT, user)
        except Exception:
            out = {}
        if isinstance(out, dict) and "notes" in out and isinstance(out["notes"], list):
            return out
        if _attempt == 0:
            _time.sleep(0.3)
    return {}


def interpret_notes(notes, battery):
    """Public entry point. Returns one interpretation entry per note.

    Never raises. Falls back to no_op on every failure mode.
    """
    notes = list(notes or [])
    battery = battery or {}
    try:
        capacity = float(battery.get("capacity_kwh") or 0.0)
    except (TypeError, ValueError):
        capacity = 0.0
    try:
        base_min = float(battery.get("minimum_energy_kwh") or 0.0)
    except (TypeError, ValueError):
        base_min = 0.0

    if not notes:
        return []

    canonical = tuple(str(n) for n in notes)

    raw = _cached_interpret(canonical, capacity)

    if not raw:
        # Single retry with the same payload (transient 5xx etc.)
        raw = _cached_interpret(canonical, capacity + 1e-6)
    if not raw:
        raw_entries = None
        try:
            fb = fallback_interpret(notes, battery)
            raw_entries = []
            for e in fb:
                entry = {
                    "note_index": e.get("note_index"),
                    "directive_type": e.get("directive_type"),
                    "start_hour": None,
                    "end_hour": None,
                    "solar_remaining_fraction": None,
                    "reserve_kwh": None,
                    "reserve_percent_of_capacity": None,
                    "max_grid_kwh": None,
                    "explanation": e.get("explanation"),
                }
                adj = e.get("structured_adjustment") or {}
                hours_list = adj.get("hours")
                if e.get("applies") and isinstance(hours_list, list) and hours_list:
                    # regex window uses end-exclusive (s, e); preserve it directly.
                    entry["start_hour"] = int(hours_list[0])
                    entry["end_hour"] = int(hours_list[-1])
                if e.get("directive_type") == "solar_reduction":
                    entry["solar_remaining_fraction"] = adj.get("factor")
                elif e.get("directive_type") == "minimum_battery_reserve":
                    entry["reserve_kwh"] = adj.get("minimum_energy_kwh")
                elif e.get("directive_type") == "max_grid_window":
                    entry["max_grid_kwh"] = adj.get("max_grid_kwh")
                raw_entries.append(entry)
        except Exception:
            raw_entries = None
        if raw_entries is None:
            return [
                {
                    "note_index": i,
                    "applies": False,
                    "directive_type": "no_op",
                    "structured_adjustment": None,
                    "explanation": "interpreter unavailable",
                }
                for i in range(len(notes))
            ]
    else:
        raw_entries = raw.get("notes", [])

    try:
        return normalise(raw_entries, notes, capacity, base_min)
    except Exception:
        return [
            {
                "note_index": i,
                "applies": False,
                "directive_type": "no_op",
                "structured_adjustment": None,
                "explanation": "interpreter unavailable",
            }
            for i in range(len(notes))
        ]

