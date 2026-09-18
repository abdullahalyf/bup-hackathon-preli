"""LLM system prompt and user-message builder for GridWise.

Owner: Tamjid. Loaded by app.interpreter.core.

Contract (docs/CONTRACTS.md):
  The LLM must return a JSON object with shape
    {"notes":[{"note_index":N,"directive_type":"...","start_hour":H,
               "end_hour":H,"solar_remaining_fraction":F|null,
               "reserve_kwh":F|null,"reserve_percent_of_capacity":F|null,
               "max_grid_kwh":F|null,"explanation":"..."}]}
  The code in normalize.py expands start/end into a unique-ascending hours
  list and converts any percent-of-capacity reserve into kWh.

Rules the prompt teaches (also documented in docs/CONTRACTS.md):
  - Exactly one entry per operator note, in note_index order.
  - Time windows are start-inclusive, end-exclusive. "1 PM to 3 PM" -> [13,14].
  - Noon = 12. Midnight = 24 as end, 0 as start. "to midnight" -> end=24.
  - Wrap-around (e.g. 10 PM to 2 AM) becomes hours [0,1,22,23].
  - The factor in solar_reduction is the *remaining* fraction. "80% reduction",
    "drop to 20%", "one-fifth of normal" all -> 0.2. "Half" -> 0.5.
  - Notes about menus, events, next week, etc. that do not affect today's
    24-hour solar/battery/grid schedule are no_op.
  - Allowed directive_type values: solar_reduction, minimum_battery_reserve,
    no_charge_window, no_discharge_window, max_grid_window, no_op.
"""

from __future__ import annotations

import json
from typing import Iterable

# ---- Few-shot examples (10). Each is a complete, hand-written note -> LLM
# raw output pair. None of them copy wording from data/public_samples.json or
# any test paraphrases. They cover all 6 directive types, time ambiguity,
# wrap-around, percent-of-capacity, fractions, distractors, and no_op.

FEW_SHOT_EXAMPLES: list[dict] = [
    # 1) solar_reduction with "% reduction" phrasing and explicit 24-hour clock.
    {
        "note": "Cloud cover from 09:00 to 14:00 will slash our panels' output by 80 percent.",
        "output": {
            "notes": [{
                "note_index": 0,
                "directive_type": "solar_reduction",
                "start_hour": 9,
                "end_hour": 14,
                "solar_remaining_fraction": 0.2,
                "reserve_kwh": None,
                "reserve_percent_of_capacity": None,
                "max_grid_kwh": None,
                "explanation": "Solar usable fraction drops to 20% (80% reduction) during the cloud window.",
            }]
        },
    },
    # 2) solar_reduction with "drop to <fraction>" phrasing and word-form time.
    {
        "note": "Heavy dust: usable solar drops to a quarter of normal between one and three in the afternoon.",
        "output": {
            "notes": [{
                "note_index": 0,
                "directive_type": "solar_reduction",
                "start_hour": 13,
                "end_hour": 15,
                "solar_remaining_fraction": 0.25,
                "reserve_kwh": None,
                "reserve_percent_of_capacity": None,
                "max_grid_kwh": None,
                "explanation": "Solar usable fraction drops to 25% (one-quarter of normal) from 1 PM to 3 PM.",
            }]
        },
    },
    # 3) minimum_battery_reserve using "% of capacity" phrasing.
    {
        "note": "Hold a thirty percent emergency reserve in the battery from 7 PM through midnight.",
        "output": {
            "notes": [{
                "note_index": 0,
                "directive_type": "minimum_battery_reserve",
                "start_hour": 19,
                "end_hour": 24,
                "solar_remaining_fraction": None,
                "reserve_kwh": None,
                "reserve_percent_of_capacity": 30,
                "max_grid_kwh": None,
                "explanation": "Battery must keep >= 30% of capacity (converted to kWh by code) from 7 PM to midnight.",
            }]
        },
    },
    # 4) no_charge_window with maintenance-style phrasing.
    {
        "note": "Electrical team is swapping the inverter overnight, so do not charge the battery from 1 AM to 4 AM.",
        "output": {
            "notes": [{
                "note_index": 0,
                "directive_type": "no_charge_window",
                "start_hour": 1,
                "end_hour": 4,
                "solar_remaining_fraction": None,
                "reserve_kwh": None,
                "reserve_percent_of_capacity": None,
                "max_grid_kwh": None,
                "explanation": "Battery charging is forbidden from 1 AM to 4 AM.",
            }]
        },
    },
    # 5) no_discharge_window with a protection-testing reason.
    {
        "note": "Relay protection test scheduled between 6 PM and 8 PM - battery must not discharge during that window.",
        "output": {
            "notes": [{
                "note_index": 0,
                "directive_type": "no_discharge_window",
                "start_hour": 18,
                "end_hour": 20,
                "solar_remaining_fraction": None,
                "reserve_kwh": None,
                "reserve_percent_of_capacity": None,
                "max_grid_kwh": None,
                "explanation": "Battery discharge is disabled during the protection-test window.",
            }]
        },
    },
    # 6) max_grid_window with an explicit kWh cap and feeder wording.
    {
        "note": "The campus feeder is running on a temporary limit; cap grid imports at 120 kWh per hour from 5 PM to 10 PM.",
        "output": {
            "notes": [{
                "note_index": 0,
                "directive_type": "max_grid_window",
                "start_hour": 17,
                "end_hour": 22,
                "solar_remaining_fraction": None,
                "reserve_kwh": None,
                "reserve_percent_of_capacity": None,
                "max_grid_kwh": 120,
                "explanation": "Grid import capped at 120 kWh/hour from 5 PM to 10 PM.",
            }]
        },
    },
    # 7) Wrap-around window: 10 PM to 2 AM.
    {
        "note": "Charge the battery only between 10 PM and 2 AM tonight.",
        "output": {
            "notes": [{
                "note_index": 0,
                "directive_type": "no_discharge_window",
                "start_hour": 22,
                "end_hour": 2,
                "solar_remaining_fraction": None,
                "reserve_kwh": None,
                "reserve_percent_of_capacity": None,
                "max_grid_kwh": None,
                "explanation": "10 PM to 2 AM wraps midnight -> forbid discharge in hours [0,1,22,23] (charge allowed).",
            }]
        },
    },
    # 8) Trivial distractor (about next week) -> no_op, plus an unrelated real one.
    {
        "note": "Reminder: the campus cafeteria is changing its menu next month. Also, please keep the battery above 15 kWh from noon to six PM today.",
        "output": {
            "notes": [
                {
                    "note_index": 0,
                    "directive_type": "no_op",
                    "start_hour": 0,
                    "end_hour": 0,
                    "solar_remaining_fraction": None,
                    "reserve_kwh": None,
                    "reserve_percent_of_capacity": None,
                    "max_grid_kwh": None,
                    "explanation": "Next-month menu change does not affect today's 24-hour energy schedule.",
                },
                {
                    "note_index": 1,
                    "directive_type": "minimum_battery_reserve",
                    "start_hour": 12,
                    "end_hour": 18,
                    "solar_remaining_fraction": None,
                    "reserve_kwh": 15,
                    "reserve_percent_of_capacity": None,
                    "max_grid_kwh": None,
                    "explanation": "Battery must keep >= 15 kWh from noon to 6 PM.",
                },
            ]
        },
    },
    # 9) Distractor that mentions solar/battery but is about next week.
    {
        "note": "Next Monday, solar contractors will be on site and the battery will be inspected. Plan accordingly.",
        "output": {
            "notes": [{
                "note_index": 0,
                "directive_type": "no_op",
                "start_hour": 0,
                "end_hour": 0,
                "solar_remaining_fraction": None,
                "reserve_kwh": None,
                "reserve_percent_of_capacity": None,
                "max_grid_kwh": None,
                "explanation": "A note about next Monday does not affect today's 24-hour energy schedule.",
            }]
        },
    },
    # 10) Midnight edge case: "until midnight" -> end_hour 24.
    {
        "note": "From 8 AM until midnight the battery charger is offline.",
        "output": {
            "notes": [{
                "note_index": 0,
                "directive_type": "no_charge_window",
                "start_hour": 8,
                "end_hour": 24,
                "solar_remaining_fraction": None,
                "reserve_kwh": None,
                "reserve_percent_of_capacity": None,
                "max_grid_kwh": None,
                "explanation": "Midnight is encoded as end_hour 24; the resulting hours list is [8..23].",
            }]
        },
    },
]


SYSTEM_PROMPT = """You convert free-text operator notes from a campus microgrid into
structured JSON directives. Output ONLY a single JSON object (no prose, no
markdown fences). The object must match the schema in OUTPUT SCHEMA below.

ALLOWED DIRECTIVE TYPES (exactly one per note):
  1. solar_reduction           -- {"hours":[...], "factor": F} where F is the
                                 usable fraction remaining (0..1). An "80%
                                 reduction", "drop to 20%", "one-fifth of
                                 normal", and "a quarter" all map to F=0.2,
                                 0.2, 0.2, 0.25 respectively. "Half" -> 0.5.
  2. minimum_battery_reserve   -- {"hours":[...], "minimum_energy_kwh": N}.
                                 If the note says a percentage of capacity
                                 (e.g. "30% of capacity"), put that in
                                 reserve_percent_of_capacity and the code
                                 converts it to kWh; otherwise put N in
                                 reserve_kwh directly.
  3. no_charge_window          -- {"hours":[...]}
  4. no_discharge_window       -- {"hours":[...]}
  5. max_grid_window           -- {"hours":[...], "max_grid_kwh": N}
  6. no_op                     -- null structured_adjustment. Use this when
                                 the note does not affect today's 24-hour
                                 solar/battery/grid schedule (next week,
                                 next month, menu changes, social events,
                                 future inspections, generic commentary).

TIME RULES (critical):
  - You emit start_hour and end_hour (integers 0..24). Code builds the
    ascending unique hours list from these.
  - Windows are START-INCLUSIVE, END-EXCLUSIVE. "1 PM to 3 PM" -> start=13,
    end=15, which yields hours [13,14].
  - Noon = 12. Midnight = 0 as start, 24 as end. "Until midnight" -> end=24.
  - Wrap-around (e.g. "10 PM to 2 AM") is fine; emit start=22, end=2, and
    code will produce [0,1,22,23].
  - "13:00" is hour 13. Word forms: "one", "two", ..., "noon", "midnight"
    use the same integers. For solar/panel work, default to daytime.
  - Do NOT invent hours outside 0..24. Empty windows -> no_op.

FACTOR RULES (critical):
  - factor is the *remaining* usable fraction. "Cut by half" -> 0.5.
    "Drop to one-fifth" -> 0.2. "Reduce by 80%" -> 0.2. "Quarter of
    normal" -> 0.25. "100% reduction" -> 0. "No reduction" -> 1.0.

RELEVANCE RULE:
  - If the note is about something that does not affect today's solar,
    battery, or grid schedule, return no_op with explanation naming the
    reason ("next week", "next month", "menu", "event", "future").

OUTPUT SCHEMA (return exactly this shape, no extra keys):
{
  "notes": [
    {
      "note_index": <int 0..2, must appear exactly once per input note, in order>,
      "directive_type": "<one of the 6 allowed types above>",
      "start_hour": <int 0..24>,
      "end_hour":   <int 0..24, may be < start_hour for wrap-around>,
      "solar_remaining_fraction": <0..1 or null>,
      "reserve_kwh":              <>=0 or null>,
      "reserve_percent_of_capacity": <0..100 or null>,
      "max_grid_kwh":             <>=0 or null>,
      "explanation": "<one short sentence>"
    }
  ]
}

Use null for every numeric field that does not apply to the directive type.
Never invent a new directive type. Never omit note_index entries.

FEW-SHOT EXAMPLES (study, do not parrot verbatim):
"""


def _format_examples(examples: Iterable[dict]) -> str:
    blocks = []
    for idx, ex in enumerate(examples, start=1):
        blocks.append(
            f"Example {idx}\n"
            f"NOTE: {ex['note']}\n"
            f"OUTPUT: {json.dumps(ex['output'], separators=(', ', ': '))}"
        )
    return "\n\n".join(blocks)


_RENDERED_EXAMPLES = _format_examples(FEW_SHOT_EXAMPLES)
FULL_SYSTEM_PROMPT = SYSTEM_PROMPT + "\n" + _RENDERED_EXAMPLES + "\n"


def build_user_message(notes: list[str], capacity_kwh: float) -> str:
    """Build the user-role message that asks the LLM to interpret all notes."""
    payload = {
        "battery_capacity_kwh": capacity_kwh,
        "notes": [
            {"note_index": i, "text": note} for i, note in enumerate(notes)
        ],
    }
    return (
        "Interpret the following operator notes. Battery capacity_kwh = "
        f"{capacity_kwh:g}.\n"
        "Return the JSON object described in the system prompt exactly. "
        "One entry per note, in note_index order.\n"
        "INPUT:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


# Public name that downstream code will import. Exposed under the same name
# the brief uses.
SYSTEM_PROMPT = FULL_SYSTEM_PROMPT


__all__ = ["SYSTEM_PROMPT", "build_user_message", "FEW_SHOT_EXAMPLES"]
