"""Prompt construction for the GridWise directive interpreter.

The LLM must return a single JSON object whose `notes` array holds one entry
per operator note, in note_index order. Each entry carries enough raw fields
(start_hour, end_hour, solar_remaining_fraction, reserve_kwh,
reserve_percent_of_capacity, max_grid_kwh) for the deterministic normaliser
to expand it into a contract-valid directive.
"""

from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = (
    "You convert free-text operator notes into structured JSON for a 24-hour battery + grid scheduler. The battery has a stated capacity_kwh. You must return exactly one JSON object: {\"notes\":[...]} with one entry per note (in input order)."
    ""
    "Schema per entry (always include every field; use null when not applicable):"
    "  note_index                   int 0..2, position of the note in the list"
    "  directive_type               one of: \"solar_reduction\", \"minimum_battery_reserve\", \"no_charge_window\", \"no_discharge_window\", \"max_grid_window\", \"no_op\""
    "  start_hour                   int 0..24, first hour of the time window, 24 means end-of-day. Use null if no time window is implied."
    "  end_hour                     int 0..24, end of the window (exclusive). Must equal start_hour when the note names a single instant. Wrap-around windows may set end > 24 (e.g. 22->26 for 10 PM to 2 AM). Use null if no time window is implied."
    "  solar_remaining_fraction     float 0..1; fraction of solar still usable after the cut (1.0 - reduction). 0.2 means \"we lose 80%\". Null when not a solar reduction."
    "  reserve_kwh                  number >= 0 absolute kWh requirement; null when not a reserve."
    "  reserve_percent_of_capacity  float 0..1; null when not a percent reserve. Use this when the operator expresses the reserve as \"% of capacity\"."
    "  max_grid_kwh                 number >= 0 per-hour grid cap; null when not a grid cap."
    "  explanation                  short one-sentence reason in English."
    ""
    "Rules you must follow:"
    "1. Time windows are end-exclusive in the 24h clock. \"1 PM to 3 PM\" means hours [13,14], so start_hour=13, end_hour=15. \"Midnight to 4 AM\" -> [0,1,2,3], start=0, end=4. \"10 PM to 2 AM\" -> [22,23,0,1], start=22, end=26 (it wraps; the normaliser will unwrap it). Convert 12 AM=0, 12 PM=12."
    "2. Convert a \"% solar reduction\" into solar_remaining_fraction = 1 - pct/100. \"Cuts solar by half\" => 0.5. \"Roughly 25%\" => 0.25. \"One-fifth remaining\" => 0.2."
    "3. Convert a percent-of-capacity reserve: keep BOTH reserve_kwh and reserve_percent_of_capacity fields consistent. If the operator says \"half of the battery\", set reserve_percent_of_capacity=0.5 and leave reserve_kwh null; the normaliser converts it."
    "4. A directive only applies to \"today\" (the 24-hour schedule). Notes about next week, next month, future dates, distant calendars, sports deadlines, menus, room bookings, club notices, library hours, etc. that do NOT impact today energy plan must be classified as no_op with applies=true and structured_adjustment null in the final output (handled by the normaliser)."
    "5. A note can only carry ONE active directive_type. Pick the dominant one. Two notes can target different directive_types; each note has its own entry."
    "6. Output a single JSON object. No prose, no markdown, no commentary."
    ""
    "Few-shot examples (do not copy these literally into your answer):"
    ""
    "Example A (solar_reduction with clean window):"
    "Input notes: [\"Cloudy skies cut rooftop solar output by 60% from 8 AM until 11 AM.\"]"
    "JSON: {\"notes\":[{\"note_index\":0,\"directive_type\":\"solar_reduction\",\"start_hour\":8,\"end_hour\":11,\"solar_remaining_fraction\":0.4,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":null,\"explanation\":\"Forty percent of the forecast solar remains during the cloudy window.\"}]}"
    ""
    "Example B (solar_reduction single instant expressed as a fraction):"
    "Input notes: [\"Around 4 PM treat solar as one-fifth of forecast.\"]"
    "JSON: {\"notes\":[{\"note_index\":0,\"directive_type\":\"solar_reduction\",\"start_hour\":16,\"end_hour\":17,\"solar_remaining_fraction\":0.2,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":null,\"explanation\":\"Only 20% of solar is usable at 4 PM.\"}]}"
    ""
    "Example C (minimum_battery_reserve explicit kWh):"
    "Input notes: [\"Make sure 75 kWh stay in the battery during 5 PM-7 PM for the fire pumps.\"]"
    "JSON: {\"notes\":[{\"note_index\":0,\"directive_type\":\"minimum_battery_reserve\",\"start_hour\":17,\"end_hour\":19,\"solar_remaining_fraction\":null,\"reserve_kwh\":75,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":null,\"explanation\":\"Fire-pump reserve of 75 kWh for two hours.\"}]}"
    ""
    "Example D (minimum_battery_reserve percent of capacity):"
    "Input notes: [\"Reserve a third of the battery between 8 AM and noon for the chiller plant.\"]"
    "JSON: {\"notes\":[{\"note_index\":0,\"directive_type\":\"minimum_battery_reserve\",\"start_hour\":8,\"end_hour\":12,\"solar_remaining_fraction\":null,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":0.333,\"max_grid_kwh\":null,\"explanation\":\"Reserve one-third of capacity for the chiller window.\"}]}"
    ""
    "Example E (no_charge_window):"
    "Input notes: [\"The charging inverter is offline from midnight to 4 AM tonight.\"]"
    "JSON: {\"notes\":[{\"note_index\":0,\"directive_type\":\"no_charge_window\",\"start_hour\":0,\"end_hour\":4,\"solar_remaining_fraction\":null,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":null,\"explanation\":\"Charger inverter offline overnight; charging disabled 0-4.\"}]}"
    ""
    "Example F (no_discharge_window):"
    "Input notes: [\"Battery must not discharge during relay calibration from 2 PM to 3 PM.\"]"
    "JSON: {\"notes\":[{\"note_index\":0,\"directive_type\":\"no_discharge_window\",\"start_hour\":14,\"end_hour\":15,\"solar_remaining_fraction\":null,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":null,\"explanation\":\"Discharge blocked during calibration.\"}]}"
    ""
    "Example G (max_grid_window):"
    "Input notes: [\"Cap grid imports at 120 kWh per hour between 6 PM and 10 PM due to substation work.\"]"
    "JSON: {\"notes\":[{\"note_index\":0,\"directive_type\":\"max_grid_window\",\"start_hour\":18,\"end_hour\":22,\"solar_remaining_fraction\":null,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":120,\"explanation\":\"Substation work caps grid at 120 kWh/hr.\"}]}"
    ""
    "Example H (wrap-around window for no_charge_window):"
    "Input notes: [\"Charging is suspended from 11 PM to 1 AM during the tie-in cutover.\"]"
    "JSON: {\"notes\":[{\"note_index\":0,\"directive_type\":\"no_charge_window\",\"start_hour\":23,\"end_hour\":25,\"solar_remaining_fraction\":null,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":null,\"explanation\":\"Charger offline across midnight; window wraps.\"}]}"
    ""
    "Example I (no_op for irrelevant future event):"
    "Input notes: [\"The cafeteria switches to its winter menu next Monday.\"]"
    "JSON: {\"notes\":[{\"note_index\":0,\"directive_type\":\"no_op\",\"start_hour\":null,\"end_hour\":null,\"solar_remaining_fraction\":null,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":null,\"explanation\":\"Menu change affects no energy schedule today.\"}]}"
    ""
    "Example J (mixed batch: solar + charge outage + distractor):"
    "Input notes: [\"Half of solar from 1 PM to 2 PM.\", \"Charger maintenance 9-11 AM.\", \"Career fair next Thursday.\"]"
    "JSON: {\"notes\":["
    "  {\"note_index\":0,\"directive_type\":\"solar_reduction\",\"start_hour\":13,\"end_hour\":14,\"solar_remaining_fraction\":0.5,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":null,\"explanation\":\"Half of solar is usable 13-13.\"},"
    "  {\"note_index\":1,\"directive_type\":\"no_charge_window\",\"start_hour\":9,\"end_hour\":11,\"solar_remaining_fraction\":null,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":null,\"explanation\":\"Charger maintenance 9-10 blocks charging.\"},"
    "  {\"note_index\":2,\"directive_type\":\"no_op\",\"start_hour\":null,\"end_hour\":null,\"solar_remaining_fraction\":null,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":null,\"explanation\":\"Career fair next week is irrelevant to today schedule.\"}]}"
    ""
    "Example K (solar reduction with synonym):"
    "Input notes: [\"Forecast solar drops to about a tenth between 9 AM and 4 PM during wildfire smoke.\"]"
    "JSON: {\"notes\":[{\"note_index\":0,\"directive_type\":\"solar_reduction\",\"start_hour\":9,\"end_hour\":16,\"solar_remaining_fraction\":0.1,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":null,\"explanation\":\"Smoke cuts usable solar to ~10% for 9-15.\"}]}"
    ""
    "Example L (single-hour grid cap):"
    "Input notes: [\"7 PM exactly: limit the grid draw to 90 kWh that one hour.\"]"
    "JSON: {\"notes\":[{\"note_index\":0,\"directive_type\":\"max_grid_window\",\"start_hour\":19,\"end_hour\":20,\"solar_remaining_fraction\":null,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":90,\"explanation\":\"Single-hour grid cap at 19 covering 19-19.\"}]}"
    ""
    "Example M (no_op misdirection that mentions batteries):"
    "Input notes: [\"We are evaluating a new battery brand for procurement next quarter.\"]"
    "JSON: {\"notes\":[{\"note_index\":0,\"directive_type\":\"no_op\",\"start_hour\":null,\"end_hour\":null,\"solar_remaining_fraction\":null,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":null,\"explanation\":\"Future procurement decision; not a schedule directive.\"}]}"
    ""
    "Example N (two notes: percent reserve + grid cap):"
    "Input notes: [\"At least 40% of battery from 5 PM to 11 PM.\", \"Keep grid under 150 kWh from 7 PM to 11 PM.\"]"
    "JSON: {\"notes\":["
    "  {\"note_index\":0,\"directive_type\":\"minimum_battery_reserve\",\"start_hour\":17,\"end_hour\":23,\"solar_remaining_fraction\":null,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":0.4,\"max_grid_kwh\":null,\"explanation\":\"40% capacity reserve 17-22.\"},"
    "  {\"note_index\":1,\"directive_type\":\"max_grid_window\",\"start_hour\":19,\"end_hour\":23,\"solar_remaining_fraction\":null,\"reserve_kwh\":null,\"reserve_percent_of_capacity\":null,\"max_grid_kwh\":150,\"explanation\":\"Evening grid cap 150 kWh/hr 19-22.\"}]}"
    ""
    "Now classify the user notes below using the same JSON shape. Use null for fields that do not apply. Output only the JSON object."
)



def build_user_message(notes, capacity_kwh):
    """Return the user-turn payload sent to the LLM.

    capacity_kwh is included so the model can sanity-check percent reserves
    if it wants to convert them inline.
    """
    payload = {
        "capacity_kwh": capacity_kwh,
        "notes": [{"note_index": i, "text": n} for i, n in enumerate(notes)],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)
