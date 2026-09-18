"""LLM interpretation pipeline for operator notes.

Owner: Tamjid. Exposed as app.interpreter.interpret_notes.

Contract (docs/CONTRACTS.md and tasks/TAMJID.md):
  interpret_notes(notes: list[str], battery: dict) -> list[dict]

  - Always returns exactly len(notes) entries in input order.
  - Never raises. Any failure -> a no_op entry with an explanatory message.
  - Each returned dict matches the canonical shape consumed by app.main:
      {"note_index": int, "applies": bool, "directive_type": str,
       "structured_adjustment": dict | None, "explanation": str}

Pipeline:
  1. Cache hit (same notes + capacity_kwh) -> return cached dicts.
  2. Build the LLM user message (capacity_kwh + indexed notes).
  3. Call call_llm(system, user). On any failure, skip to fallback.
  4. Feed the raw dict to normalize(). Get back (entries, bad_indexes).
  5. For each bad index, retry the LLM once with a focused "fix this note"
     re-prompt. Merge the retry's good entries back into the result.
  6. For any index still bad, call fallback.fallback_extract() on the raw
     note string. If the regex is confident, use that result; otherwise emit
     no_op with explanation "could not interpret safely".
  7. Cache the final dict list and return it.

The pipeline never depends on app.schemas (Alif's file). Battery input is
treated as a dict (OptimizeRequest already passes it as such via .model_dump()).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .fallback import fallback_extract
from .llm_client import LLMClientError, call_llm
from .normalize import DirectiveInterpretation, normalize
from .prompt import SYSTEM_PROMPT, build_user_message

log = logging.getLogger(__name__)

# In-memory result cache. Keyed by (tuple(notes), capacity_kwh). Notes are
# converted to a tuple so the dict key is hashable; the value is the list of
# result dicts already produced for that input. Per-process only.
_CACHE: dict[tuple[tuple[str, ...], float], list[dict[str, Any]]] = {}

# Maximum number of distinct bad-note indexes we will re-prompt in a single
# retry. Keeps the second LLM call under token budget and bounded latency.
_MAX_RETRY_NOTES = 5


def _entry_to_dict(entry: DirectiveInterpretation) -> dict[str, Any]:
    """Convert a DirectiveInterpretation Pydantic model to a dict."""
    return {
        "note_index": 0,  # overwritten by the caller to the real index
        "applies": entry.applies,
        "directive_type": entry.directive_type,
        "structured_adjustment": entry.structured_adjustment,
        "explanation": entry.explanation,
    }


def _noop_dict(note_index: int, reason: str) -> dict[str, Any]:
    return {
        "note_index": note_index,
        "applies": False,
        "directive_type": "no_op",
        "structured_adjustment": None,
        "explanation": reason,
    }


def _capacity_kwh(battery: Any) -> float:
    """Read capacity_kwh from a Battery model, a dict, or an object."""
    if battery is None:
        return 0.0
    if isinstance(battery, dict):
        v = battery.get("capacity_kwh", 0.0)
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0
    if hasattr(battery, "capacity_kwh"):
        try:
            return float(battery.capacity_kwh)
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _build_retry_user_message(
    notes: list[str],
    capacity_kwh: float,
    bad_indexes: list[int],
    previous_attempt: dict[str, Any] | None,
) -> str:
    """Build a focused re-prompt asking the LLM to fix specific bad notes."""
    capped = [i for i in bad_indexes[:_MAX_RETRY_NOTES] if 0 <= i < len(notes)]
    payload = {
        "battery_capacity_kwh": capacity_kwh,
        "bad_note_indexes": capped,
        "notes": [
            {"note_index": i, "text": notes[i]} for i in capped
        ],
        "previous_attempt_notes": (
            previous_attempt.get("notes")
            if isinstance(previous_attempt, dict)
            else None
        ),
        "instruction": (
            "Your previous response failed guardrails for the listed "
            "note indexes. Re-emit ONLY those note_indexes as a "
            "`{\"notes\":[...]}` JSON object. Each re-emitted entry must "
            "pass the schema: note_index in range, allowed directive_type, "
            "valid window, factor in [0,1], reserve <= capacity, "
            "max_grid_kwh finite >= 0. Use null for unused fields."
        ),
    }
    return (
        "Retry: fix the bad notes listed below.\n"
        "Return strictly the `notes` array as JSON.\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def _safe_call_llm(system: str, user: str) -> dict[str, Any] | None:
    """Wrap call_llm so a hard failure surfaces as None rather than raise."""
    try:
        return call_llm(system, user)
    except LLMClientError as exc:
        log.warning("interpret_notes: LLM failed (%s); continuing", exc)
        return None
    except Exception as exc:  # pragma: no cover - defensive
        log.warning(
            "interpret_notes: unexpected LLM error (%s: %s); continuing",
            exc.__class__.__name__,
            exc,
        )
        return None


def _retry_bad_notes(
    notes: list[str],
    capacity_kwh: float,
    bad_indexes: list[int],
    previous_attempt: dict[str, Any] | None,
) -> dict[int, DirectiveInterpretation]:
    """One-shot retry: ask the LLM to fix the listed bad notes.

    Returns a mapping note_index -> DirectiveInterpretation for the indexes
    the retry managed to fix. Indexes the retry still gets wrong are absent
    from the returned dict and will be handled by the regex fallback.

    Only applies if the retry entry actually has `applies=True` OR has a
    non-empty explanation that looks like a deliberate LLM answer. The
    no_op fallback that normalize() emits for unparseable raw responses is
    intentionally NOT considered a fix, so the regex fallback still gets a
    chance.
    """
    if not bad_indexes:
        return {}
    retry_user = _build_retry_user_message(
        notes, capacity_kwh, bad_indexes, previous_attempt
    )
    retry_raw = _safe_call_llm(SYSTEM_PROMPT, retry_user)
    if retry_raw is None:
        return {}
    fixed_entries, retry_bad = normalize(retry_raw, notes, capacity_kwh)
    fixed: dict[int, DirectiveInterpretation] = {}
    for idx in bad_indexes[:_MAX_RETRY_NOTES]:
        if not (0 <= idx < len(fixed_entries)):
            continue
        if idx in retry_bad:
            # The retry still got this one wrong; let the regex fallback try.
            continue
        entry = fixed_entries[idx]
        if entry is None:
            continue
        if not entry.applies and entry.directive_type == "no_op":
            # The retry emitted a clean no_op for this note. Treat as a real
            # LLM answer (the LLM legitimately saw no directive). Only accept
            # if its explanation is non-empty (normalize fills explanation
            # with "LLM omitted entry..." for garbage, so non-empty here means
            # the retry actually parsed an entry for this index).
            if not (entry.explanation or "").strip():
                continue
        fixed[idx] = entry
    return fixed


def _apply_fallback(
    notes: list[str], capacity_kwh: float, indexes: list[int]
) -> dict[int, dict[str, Any]]:
    """For each still-bad note, try the regex fallback."""
    out: dict[int, dict[str, Any]] = {}
    for idx in indexes:
        if not (0 <= idx < len(notes)):
            continue
        result = fallback_extract(notes[idx], capacity_kwh, idx)
        if result is not None:
            out[idx] = result
    return out


def interpret_notes(notes: list[str], battery: Any) -> list[dict[str, Any]]:
    """Interpret a list of operator notes into per-note directive dicts.

    Always returns exactly `len(notes)` dicts in input order. Never raises.
    """
    # 0) Defensive: normalize input.
    if not isinstance(notes, list):
        notes = []
    safe_notes: list[str] = [str(n) for n in notes]

    capacity_kwh = _capacity_kwh(battery)

    # 1) Cache lookup.
    cache_key = (tuple(safe_notes), capacity_kwh)
    if cache_key in _CACHE:
        return [dict(entry) for entry in _CACHE[cache_key]]

    n = len(safe_notes)
    if n == 0:
        return []

    # 2) First LLM call.
    user_msg = build_user_message(safe_notes, capacity_kwh)
    raw = _safe_call_llm(SYSTEM_PROMPT, user_msg)

    # 3) Normalize. If raw is None we still get back (entries, bad_indexes)
    # of length n with everything marked bad.
    entries, bad_indexes = normalize(raw, safe_notes, capacity_kwh)

    # 4) Retry once for any bad indexes (capped at _MAX_RETRY_NOTES).
    fixed_by_retry: dict[int, DirectiveInterpretation] = {}
    if bad_indexes:
        try:
            fixed_by_retry = _retry_bad_notes(
                safe_notes, capacity_kwh, bad_indexes, raw
            )
        except Exception as exc:  # pragma: no cover - defensive
            log.warning(
                "interpret_notes: retry raised (%s: %s); skipping",
                exc.__class__.__name__,
                exc,
            )
            fixed_by_retry = {}

    # 5) For still-bad indexes, try the regex fallback.
    still_bad: list[int] = []
    for idx in bad_indexes:
        if idx in fixed_by_retry:
            continue
        if not (0 <= idx < n):
            continue
        still_bad.append(idx)
    fallback_hits = _apply_fallback(safe_notes, capacity_kwh, still_bad)

    # 6) Assemble final per-note dict list in input order.
    final: list[dict[str, Any]] = []
    for idx, original in enumerate(safe_notes):
        if idx in fixed_by_retry:
            entry = fixed_by_retry[idx]
            d = _entry_to_dict(entry)
            d["note_index"] = idx
            base = (d.get("explanation") or "").strip()
            d["explanation"] = (base + " [retry]").strip()
            final.append(d)
        elif idx in fallback_hits:
            final.append(fallback_hits[idx])
        else:
            entry = entries[idx] if 0 <= idx < len(entries) else None
            if entry is not None and (
                entry.applies or entry.directive_type != "no_op"
            ):
                d = _entry_to_dict(entry)
                d["note_index"] = idx
                final.append(d)
            else:
                final.append(
                    _noop_dict(
                        idx,
                        "could not interpret safely: "
                        f"{original[:60]!r}",
                    )
                )

    # 7) Cache. Callers must not mutate the cached dicts; we hand out copies.
    _CACHE[cache_key] = [dict(entry) for entry in final]
    return final


def _reset_cache() -> None:
    """Test-only helper: clear the in-memory result cache."""
    _CACHE.clear()


__all__ = ["interpret_notes", "_reset_cache"]
