"""Conservative regex-based fallback for the interpreter pipeline.

Owner: Tamjid. Called by app.interpreter.core when the LLM (and the LLM retry)
both fail to produce a usable entry for a given note. The fallback is *strict*:
it only returns a directive dict when the regex matches very clearly. Anything
ambiguous is returned as None so the caller can emit no_op.

Contract:
  fallback_extract(note: str, capacity_kwh: float, note_index: int) -> dict | None

Returns a dict with the canonical interpreter shape:
    {"note_index", "applies", "directive_type",
     "structured_adjustment", "explanation"}

or None when no rule is confident enough. The function never raises.

The fallback intentionally uses simple, anchored regexes. It is the safety net,
not the primary path.
"""

from __future__ import annotations

import math
import re
from typing import Any

# ---- Time vocabulary --------------------------------------------------------
# A small set of English phrasings that map to integer hours in [0, 24].
# 24 is reserved for end-of-day ("to midnight").
_HOUR_RE = (
    r"(?P<hour>"
    r"(?:\d{1,2}(?::\d{2})?)"            # 13 / 13:00 / 1 / 1:30
    r"|noon|midnight"                    # named words
    r")"
    r"\s*(?P<ampm>a\.?m\.?|p\.?m\.?)?"   # optional AM/PM
)

_HOUR_PATTERN = re.compile(_HOUR_RE, re.IGNORECASE)

# A phrase like "from 13:00 to 15:00", "between 1pm and 3pm", "9 to 11",
# "10 pm - 2 am". Captures start and end hour tokens. Named groups are
# suffixed with "1" / "2" to avoid Python's "redefinition of group name"
# error when the same _HOUR_RE fragment is reused.
_HOUR1_RE = re.sub(r"\?P<hour>", r"?P<hour1>", _HOUR_RE, count=1)
_HOUR1_RE = re.sub(r"\?P<ampm>", r"?P<ampm1>", _HOUR1_RE, count=1)
_HOUR2_RE = re.sub(r"\?P<hour>", r"?P<hour2>", _HOUR_RE, count=1)
_HOUR2_RE = re.sub(r"\?P<ampm>", r"?P<ampm2>", _HOUR2_RE, count=1)

_WINDOW_RE = re.compile(
    r"(?:from|between|over|during)?\s*"
    + _HOUR1_RE
    + r"\s*(?:-|to|until|till|through|and)\s*"
    + _HOUR2_RE,
    re.IGNORECASE,
)

# ---- Number phrasings -------------------------------------------------------
_FRACTION_MAP: dict[str, float] = {
    "half": 0.5,
    "quarter": 0.25,
    "third": 1.0 / 3.0,
    "two-thirds": 2.0 / 3.0,
    "tenth": 0.1,
    "fifth": 0.2,
    "fourth": 0.25,
    "fifths": 0.2,
    "sixth": 1.0 / 6.0,
    "seventh": 1.0 / 7.0,
    "eighth": 0.125,
    "ninth": 1.0 / 9.0,
}

# "drop to 20%", "Drop solar to 20%", "use only 20 percent",
# "produce 20% of normal". Allows a few intervening words between the trigger
# verb and the number so phrases like "Drop solar to 20%" parse correctly.
_REMAIN_PCT_RE = re.compile(
    r"(?:drop(?:ping)?|use\s+only|keep\s+at|reduce|limit|cap|"
    r"down\s+to|produce|generate|set|target|aim)"
    r"(?:\s+(?:the\s+)?\w+){0,4}\s+(?:to|at|of|down\s+to)\s+"
    r"(?P<num>\d+(?:\.\d+)?)\s*(?:%|percent)",
    re.IGNORECASE,
)

# Standalone "to 20%" / "at 20%" / "of 20%" as a safety net when no verb.
_BARE_PCT_RE = re.compile(
    r"(?<!\w)(?:to|at|of)\s+(?P<num>\d+(?:\.\d+)?)\s*(?:%|percent)",
    re.IGNORECASE,
)

# "80% reduction", "cut by 80 percent", "slash solar by 80%",
# "reduce output by 80". Allow up to 4 intervening words between the verb
# and the number so "slash solar output by 80%" parses.
_REDUCTION_PCT_RE = re.compile(
    r"(?:reduce|cut|slash|lower|decrease|drop|trim)"
    r"(?:\s+(?:the\s+)?\w+){0,4}\s+(?:by\s+)?"
    r"(?P<num>\d+(?:\.\d+)?)\s*(?:%|percent)",
    re.IGNORECASE,
)

# "one-fifth of normal", "half of usual", "two thirds of the normal output"
_FRACTION_RE = re.compile(
    r"(?P<frac>half|quarter|third|two-thirds|"
    r"tenth|fifth|fourth|fifths|sixth|seventh|eighth|ninth)"
    r"\s+of\s+(?:the\s+)?(?:normal|usual|typical|expected|standard)",
    re.IGNORECASE,
)

# Reserve patterns ------------------------------------------------------------
# "keep 30 kWh in reserve", "maintain at least 30 kWh", "reserve 30 kWh"
_RESERVE_KWH_RE = re.compile(
    r"(?:keep|maintain|leave|reserve|hold|retain)\s+"
    r"(?:at\s+least\s+)?(?P<num>\d+(?:\.\d+)?)\s*kwh",
    re.IGNORECASE,
)
# "keep 30% of capacity", "maintain at least 30 percent of battery"
_RESERVE_PCT_RE = re.compile(
    r"(?:keep|maintain|leave|reserve|hold|retain)\s+"
    r"(?:at\s+least\s+)?(?P<num>\d+(?:\.\d+)?)\s*(?:%|percent)\s*"
    r"(?:of\s+(?:the\s+)?(?:capacity|battery|charge))?",
    re.IGNORECASE,
)

# Max grid patterns -----------------------------------------------------------
# "draw no more than 5 kWh from grid", "take up to 5 kWh from the grid"
_MAX_GRID_RE = re.compile(
    r"(?:draw|use|take|import)\s+(?:no\s+more\s+than\s+|at\s+most\s+|"
    r"up\s+to\s+|only\s+)?(?P<num>\d+(?:\.\d+)?)\s*kwh\s+from\s+(?:the\s+)?grid",
    re.IGNORECASE,
)
# "grid cap 5 kWh", "limit grid to 5 kWh", "max grid 5 kWh"
_MAX_GRID_LIMIT_RE = re.compile(
    r"(?:grid\s+cap|limit\s+(?:the\s+)?grid\s+to|max(?:imum)?\s+grid)\s*"
    r"(?:of\s+)?(?P<num>\d+(?:\.\d+)?)\s*kwh",
    re.IGNORECASE,
)

# No-charge / no-discharge window phrases -------------------------------------
_NO_CHARGE_RE = re.compile(
    r"(?:do\s+not|don'?t|do\s+no|never|avoid|stop|skip|halt)\s+"
    r"(?:charge(?:ing)?|charging\s+up|charging\s+the\s+battery|"
    r"put(?:ting)?\s+(?:power|energy)\s+(?:into|back\s+into)\s+(?:the\s+)?battery)",
    re.IGNORECASE,
)
_NO_DISCHARGE_RE = re.compile(
    r"(?:do\s+not|don'?t|do\s+no|never|avoid|stop|skip|halt)\s+"
    r"(?:discharge(?:ing)?|use\s+(?:the\s+)?battery|draw\s+(?:from|on)\s+(?:the\s+)?battery|"
    r"pull\s+(?:from|on)\s+(?:the\s+)?battery)",
    re.IGNORECASE,
)

# Irrelevance signals ---------------------------------------------------------
# Mentions of menus, events, next week, etc. that don't affect today's 24h
# energy schedule. Only fires when no directive keyword is also present.
_NOWORD_RE = re.compile(
    r"(?:menu|cafeteria|canteen|breakfast|lunch\s+menu|dinner\s+menu|"
    r"next\s+week|next\s+month|tomorrow|next\s+day|"
    r"birthday|holiday|anniversary|wedding|meeting|event|conference|"
    r"schedule|shift\s+change|roster|staff\s+meeting)",
    re.IGNORECASE,
)


def _parse_hour(token: str, ampm: str | None) -> int | None:
    if not token:
        return None
    raw = token.strip().lower().rstrip(".")
    if raw == "noon":
        return 12
    if raw == "midnight":
        return 24 if ampm else 0
    if ":" in raw:
        raw = raw.split(":", 1)[0]
    if not raw.isdigit():
        return None
    h = int(raw)
    if ampm:
        norm = ampm.replace(".", "").lower()
        if norm == "pm" and h < 12:
            h += 12
        elif norm == "am" and h == 12:
            h = 0
    if h < 0 or h > 24:
        return None
    return h


def _expand_window(start: int, end: int) -> list[int] | None:
    """Mirror of normalize._expand_hours but local to this module."""
    if not (isinstance(start, int) and isinstance(end, int)):
        return None
    if start < 0 or start > 24 or end < 0 or end > 24 or start == end:
        return None
    if end > start:
        hours = list(range(start, end))
    else:
        hours = list(range(start, 24)) + list(range(0, end))
    hours = sorted({h for h in hours if 0 <= h <= 23})
    return hours or None


def _find_window(text: str) -> tuple[list[int], str] | tuple[None, str]:
    """Return (hours, span_text) for the first time window in `text`."""
    match = _WINDOW_RE.search(text)
    if not match:
        return None, ""
    start = _parse_hour(match.group("hour1"), match.group("ampm1"))
    end = _parse_hour(match.group("hour2"), match.group("ampm2"))
    if start is None or end is None:
        return None, ""
    hours = _expand_window(start, end)
    if hours is None:
        return None, ""
    return hours, match.group(0)


def _window_or_default(text: str, default: list[int]) -> list[int]:
    """Return the explicit window in `text` if found, else `default`."""
    hours, _span = _find_window(text)
    if hours is not None:
        return hours
    return list(default)


def _factor_from_text(text: str) -> float | None:
    """Return a remaining-fraction in [0, 1] or None if no clear factor."""
    m = _REMAIN_PCT_RE.search(text)
    if m:
        try:
            pct = float(m.group("num"))
        except (TypeError, ValueError):
            return None
        if 0 <= pct <= 100:
            return pct / 100.0
    m = _REDUCTION_PCT_RE.search(text)
    if m:
        try:
            pct = float(m.group("num"))
        except (TypeError, ValueError):
            return None
        if 0 <= pct <= 100:
            return max(0.0, min(1.0, 1.0 - pct / 100.0))
    m = _BARE_PCT_RE.search(text)
    if m:
        try:
            pct = float(m.group("num"))
        except (TypeError, ValueError):
            return None
        if 0 <= pct <= 100:
            return pct / 100.0
    m = _FRACTION_RE.search(text)
    if m:
        frac = _FRACTION_MAP.get(m.group("frac").lower())
        if frac is not None:
            return max(0.0, min(1.0, frac))
    return None


def _is_irrelevant(text: str) -> bool:
    return bool(_NOWORD_RE.search(text))


def fallback_extract(
    note: str, capacity_kwh: float, note_index: int
) -> dict[str, Any] | None:
    """Conservative regex interpretation of a single note.

    Returns a directive dict on confident match; None otherwise.
    Never raises. `capacity_kwh` is only used for percent -> kWh conversion of
    reserve directives, and as a sanity cap.
    """
    try:
        if not isinstance(note, str):
            return None
        text = note.strip()
        if not text:
            return None

        low = text.lower()

        # 0) Irrelevance short-circuit. Only fire when no directive keyword
        # is also present in the same note.
        has_directive_keyword = bool(
            re.search(
                r"solar|panel|panels|photovoltaic|pv|battery|grid|kwh|"
                r"reserve|charge|discharge",
                low,
            )
        )
        if not has_directive_keyword and _is_irrelevant(low):
            return _make_noop(note_index, "fallback: irrelevant note")

        # 1) Solar reduction: requires a remaining-fraction cue.
        if re.search(r"\b(solar|panel|panels|photovoltaic|pv)\b", low):
            factor = _factor_from_text(low)
            if factor is not None:
                hours = _window_or_default(low, default=list(range(6, 18)))
                return {
                    "note_index": note_index,
                    "applies": True,
                    "directive_type": "solar_reduction",
                    "structured_adjustment": {
                        "hours": hours,
                        "factor": float(factor),
                    },
                    "explanation": (
                        f"fallback: solar ~{factor:.2f} of normal"
                    ),
                }

        # 2) Minimum battery reserve.
        m = _RESERVE_KWH_RE.search(low)
        if m:
            try:
                kwh = float(m.group("num"))
            except (TypeError, ValueError):
                kwh = None
            cap = float(capacity_kwh) if capacity_kwh else 0.0
            if kwh is not None and kwh >= 0 and (cap <= 0 or kwh <= cap + 1e-6):
                hours = _window_or_default(low, default=list(range(0, 24)))
                return {
                    "note_index": note_index,
                    "applies": True,
                    "directive_type": "minimum_battery_reserve",
                    "structured_adjustment": {
                        "hours": hours,
                        "minimum_energy_kwh": float(kwh),
                    },
                    "explanation": f"fallback: reserve >= {kwh:g} kWh",
                }
        m = _RESERVE_PCT_RE.search(low)
        if m:
            try:
                pct = float(m.group("num"))
            except (TypeError, ValueError):
                pct = None
            if pct is not None and 0 <= pct <= 100 and capacity_kwh > 0:
                kwh = pct / 100.0 * float(capacity_kwh)
                hours = _window_or_default(low, default=list(range(0, 24)))
                return {
                    "note_index": note_index,
                    "applies": True,
                    "directive_type": "minimum_battery_reserve",
                    "structured_adjustment": {
                        "hours": hours,
                        "minimum_energy_kwh": float(kwh),
                    },
                    "explanation": (
                        f"fallback: reserve >= {pct:g}% "
                        f"({kwh:.2f} kWh)"
                    ),
                }

        # 3) Max-grid window.
        m = _MAX_GRID_RE.search(low) or _MAX_GRID_LIMIT_RE.search(low)
        if m:
            try:
                kwh = float(m.group("num"))
            except (TypeError, ValueError):
                kwh = None
            if kwh is not None and kwh >= 0 and math.isfinite(kwh):
                hours = _window_or_default(low, default=list(range(17, 22)))
                return {
                    "note_index": note_index,
                    "applies": True,
                    "directive_type": "max_grid_window",
                    "structured_adjustment": {
                        "hours": hours,
                        "max_grid_kwh": float(kwh),
                    },
                    "explanation": (
                        f"fallback: grid <= {kwh:g} kWh in window"
                    ),
                }

        # 4) No-charge window.
        if _NO_CHARGE_RE.search(low):
            hours = _window_or_default(low, default=list(range(11, 15)))
            return {
                "note_index": note_index,
                "applies": True,
                "directive_type": "no_charge_window",
                "structured_adjustment": {"hours": hours},
                "explanation": "fallback: no charging in window",
            }

        # 5) No-discharge window.
        if _NO_DISCHARGE_RE.search(low):
            hours = _window_or_default(low, default=list(range(18, 22)))
            return {
                "note_index": note_index,
                "applies": True,
                "directive_type": "no_discharge_window",
                "structured_adjustment": {"hours": hours},
                "explanation": "fallback: no discharging in window",
            }

        # 6) Otherwise: be honest and return None. core.py will no_op this.
        return None
    except Exception:
        # The fallback is a safety net; it must never crash the pipeline.
        return None


def _make_noop(note_index: int, reason: str) -> dict[str, Any]:
    return {
        "note_index": note_index,
        "applies": False,
        "directive_type": "no_op",
        "structured_adjustment": None,
        "explanation": reason,
    }


__all__ = ["fallback_extract"]
