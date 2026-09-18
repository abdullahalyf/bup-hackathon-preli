"""Guardrails / normalize: turn a raw LLM dict into per-note Directive entries.

Owner: Tamjid.

Contract (docs/CONTRACTS.md):
  Raw LLM JSON is shaped:
    {"notes":[{note_index, directive_type, start_hour, end_hour,
               solar_remaining_fraction, reserve_kwh,
               reserve_percent_of_capacity, max_grid_kwh, explanation}]}

  normalize() returns:
    (entries, bad_indexes)
      entries: a list of N DirectiveInterpretation-compatible objects, one
               per input note, in the input order of `notes`.
      bad_indexes: list of note_index values that were rejected by the
               guardrails. Core will retry/fallback/no-op those.

Rules implemented here:
  - Exactly one entry per note. Always len(entries) == len(notes).
  - Each note_index appears at most once; duplicates are flagged bad.
  - directive_type must be one of the six allowed values, else flagged.
  - hours are start-inclusive, end-exclusive, ascending, unique, in [0,23].
  - Wrap-around: end < start yields [0..end-1] union [start..23].
  - Midnight end = 24 is valid (covers up to hour 23 inclusive).
  - Solar factor must lie in [0, 1].
  - reserve_kwh must be in [0, capacity]; reserve_percent_of_capacity in
    [0, 100]; max_grid_kwh must be finite and >= 0.
  - percent is converted to kWh deterministically.
  - On any guardrail failure for a note, its entry becomes no_op (applies
    false, structured_adjustment=None) and its index is added to bad_indexes.
"""
from __future__ import annotations

import math
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field


# --- Per-note directive model -------------------------------------------------
#
# We deliberately do NOT import this from app.schemas (Alif owns that file).
# The optimizer will read these entries; its solver (Taseen) builds its own
# limits dict from the per-type `structured_adjustment` payload below.

class DirectiveEntry(BaseModel):
    """One interpreted operator note, ready for the optimizer.

    Mirrors docs/CONTRACTS.md:
      applies: True iff this note changes today's energy schedule.
      directive_type: one of the six allowed values.
      structured_adjustment: payload consumed by the optimizer (or None for no_op).
      explanation: short free-text rationale (also surfaced in the API response).
    """

    model_config = ConfigDict(extra="forbid")

    applies: bool
    directive_type: str
    structured_adjustment: dict[str, Any] | None = None
    explanation: str = ""


# Backwards-compatibility alias so the rest of the codebase (and any tests
# that imported the previous name) still works.
DirectiveInterpretation = DirectiveEntry


ALLOWED_TYPES = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
}

# Tolerance for kWh checks. Replay validator uses 0.01; align here too.
_KWH_TOL = 1e-6


def _expand_hours(start_hour: int, end_hour: int) -> list[int] | None:
    """Return the ascending unique hours [0..23] covered by a window, or None
    if the window is invalid.

    Rules:
      - start_hour and end_hour must be ints in [0, 24].
      - end_hour == start_hour is an empty window -> invalid.
      - end_hour > start_hour: hours = list(range(start_hour, end_hour))
        filtered to [0, 23]; end_hour==24 is fine (covers up to 23).
      - end_hour < start_hour: wrap-around -> [0..end-1] + [start..23].
    """
    if not (isinstance(start_hour, int) and isinstance(end_hour, int)):
        return None
    if start_hour < 0 or start_hour > 24:
        return None
    if end_hour < 0 or end_hour > 24:
        return None
    if start_hour == end_hour:
        return None  # empty window

    if end_hour > start_hour:
        hours = list(range(start_hour, end_hour))
    else:
        # wrap-around
        hours = list(range(start_hour, 24)) + list(range(0, end_hour))

    # Clamp + dedupe + sort. Range-based output is already ascending and
    # unique, but a defensive pass costs nothing.
    hours = sorted({h for h in hours if 0 <= h <= 23})
    if not hours:
        return None
    return hours


def _noop_entry(reason: str) -> DirectiveInterpretation:
    return DirectiveInterpretation(
        applies=False,
        directive_type="no_op",
        structured_adjustment=None,
        explanation=reason,
    )


def _entry_from_dict(
    raw: dict, capacity_kwh: float
) -> tuple[DirectiveInterpretation | None, str | None]:
    """Validate a single raw note entry.

    Returns (entry, None) on success or (None, reason) on guardrail failure.
    A returned entry is always a DirectiveInterpretation; no_op is also a
    valid DirectiveInterpretation, so success cases are not None.
    """
    dtype = raw.get("directive_type")
    if dtype not in ALLOWED_TYPES:
        return None, f"unknown directive_type={dtype!r}"

    start_hour = raw.get("start_hour")
    end_hour = raw.get("end_hour")
    explanation = raw.get("explanation") or ""
    factor = raw.get("solar_remaining_fraction")
    reserve_kwh = raw.get("reserve_kwh")
    reserve_pct = raw.get("reserve_percent_of_capacity")
    max_grid_kwh = raw.get("max_grid_kwh")

    # --- no_op: ignore all the numeric baggage, return a clean no_op. ---
    if dtype == "no_op":
        return DirectiveInterpretation(
            applies=False,
            directive_type="no_op",
            structured_adjustment=None,
            explanation=explanation or "no_op",
        ), None

    # --- All other types must have a non-empty, valid window. ---
    hours = _expand_hours(start_hour, end_hour)
    if hours is None:
        return None, (
            f"invalid window start={start_hour} end={end_hour} for type={dtype}"
        )

    # --- Per-type guardrails. ---
    if dtype == "solar_reduction":
        if factor is None or not isinstance(factor, (int, float)):
            return None, "solar_reduction missing solar_remaining_fraction"
        if math.isnan(factor) or math.isinf(factor):
            return None, "solar_reduction non-finite factor"
        if not (0.0 <= float(factor) <= 1.0 + _KWH_TOL):
            return None, f"solar_reduction factor out of [0,1]: {factor}"
        return DirectiveInterpretation(
            applies=True,
            directive_type="solar_reduction",
            structured_adjustment={
                "hours": hours,
                "factor": float(factor),
            },
            explanation=explanation,
        ), None

    if dtype == "minimum_battery_reserve":
        # Either an explicit kWh or a percentage of capacity; never both.
        if reserve_kwh is not None and reserve_pct is not None:
            return None, "reserve has both kwh and percent"
        if reserve_kwh is None and reserve_pct is None:
            return None, "minimum_battery_reserve missing reserve value"
        if reserve_kwh is not None:
            if not isinstance(reserve_kwh, (int, float)) or math.isnan(reserve_kwh):
                return None, "reserve_kwh non-numeric"
            if reserve_kwh < -_KWH_TOL:
                return None, f"reserve_kwh negative: {reserve_kwh}"
            if reserve_kwh > capacity_kwh + _KWH_TOL:
                return None, (
                    f"reserve_kwh {reserve_kwh} > capacity {capacity_kwh}"
                )
            min_kwh = float(reserve_kwh)
        else:
            if not isinstance(reserve_pct, (int, float)) or math.isnan(reserve_pct):
                return None, "reserve_percent_of_capacity non-numeric"
            if not (0.0 <= float(reserve_pct) <= 100.0 + _KWH_TOL):
                return None, (
                    f"reserve_percent_of_capacity {reserve_pct} out of [0,100]"
                )
            min_kwh = float(reserve_pct) / 100.0 * float(capacity_kwh)
        return DirectiveInterpretation(
            applies=True,
            directive_type="minimum_battery_reserve",
            structured_adjustment={
                "hours": hours,
                "minimum_energy_kwh": float(min_kwh),
            },
            explanation=explanation,
        ), None

    if dtype == "no_charge_window":
        return DirectiveInterpretation(
            applies=True,
            directive_type="no_charge_window",
            structured_adjustment={"hours": hours},
            explanation=explanation,
        ), None

    if dtype == "no_discharge_window":
        return DirectiveInterpretation(
            applies=True,
            directive_type="no_discharge_window",
            structured_adjustment={"hours": hours},
            explanation=explanation,
        ), None

    if dtype == "max_grid_window":
        if max_grid_kwh is None:
            return None, "max_grid_window missing max_grid_kwh"
        if not isinstance(max_grid_kwh, (int, float)) or math.isnan(max_grid_kwh):
            return None, "max_grid_kwh non-numeric"
        if math.isinf(max_grid_kwh):
            return None, "max_grid_kwh infinite"
        if max_grid_kwh < -_KWH_TOL:
            return None, f"max_grid_kwh negative: {max_grid_kwh}"
        return DirectiveInterpretation(
            applies=True,
            directive_type="max_grid_window",
            structured_adjustment={
                "hours": hours,
                "max_grid_kwh": float(max_grid_kwh),
            },
            explanation=explanation,
        ), None

    # Should be unreachable because of the ALLOWED_TYPES guard above.
    return None, f"unhandled directive_type={dtype!r}"


def normalize(
    raw: dict | None,
    notes: Iterable[str],
    capacity_kwh: float,
) -> tuple[list[DirectiveInterpretation], list[int]]:
    """Convert the raw LLM dict into per-note DirectiveInterpretation entries.

    Always returns len(notes) entries in input order. Returns a list of
    bad note_index values for guardrail failures; core.py uses this to
    decide what to retry or fall back to.

    The function itself never raises for malformed input — a totally broken
    `raw` simply produces a list of no_op entries plus bad_indexes [0..N-1].
    """
    notes_list = list(notes)
    n = len(notes_list)

    # Defensive: always return one entry per input note.
    fallback = [
        _noop_entry("could not interpret safely")
        for _ in range(n)
    ]

    if not isinstance(raw, dict):
        return fallback, list(range(n))

    raw_notes = raw.get("notes")
    if not isinstance(raw_notes, list):
        return fallback, list(range(n))

    # Bucket LLM outputs by note_index so we can detect duplicates and gaps.
    by_index: dict[int, list[dict]] = {}
    for entry in raw_notes:
        if not isinstance(entry, dict):
            continue
        idx = entry.get("note_index")
        if isinstance(idx, bool) or not isinstance(idx, int):
            continue
        if not (0 <= idx < n):
            # LLM invented an index we don't have a note for. Drop it.
            continue
        by_index.setdefault(idx, []).append(entry)

    bad_indexes: list[int] = []
    entries: list[DirectiveInterpretation] = list(fallback)

    for idx in range(n):
        bucket = by_index.get(idx, [])
        if not bucket:
            # LLM never produced an entry for this note.
            entries[idx] = _noop_entry("LLM omitted entry for this note")
            bad_indexes.append(idx)
            continue
        if len(bucket) > 1:
            # Duplicate -> ambiguous. Mark bad and leave as no_op.
            entries[idx] = _noop_entry(
                f"LLM returned {len(bucket)} entries for note_index={idx}"
            )
            bad_indexes.append(idx)
            continue

        entry, err = _entry_from_dict(bucket[0], capacity_kwh)
        if err is not None or entry is None:
            entries[idx] = _noop_entry(f"normalize: {err}")
            bad_indexes.append(idx)
        else:
            entries[idx] = entry

    return entries, bad_indexes
