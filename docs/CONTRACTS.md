# GridWise contracts

This is the single source of truth for the public API and the interfaces between team modules. Contract changes require Alif's approval.

## Public API

`GET /health` returns HTTP 200 and `{"status":"ok"}`.

`POST /optimize-energy` accepts JSON with these fields:

| Field | Rule |
| --- | --- |
| `scenario_id` | Non-empty string, echoed in the response. |
| `operator_notes` | Array of 1–3 non-empty English strings. |
| `hours` | Exactly 24 entries; integer `hour` 0–23 appears once each. Each entry has finite non-negative `demand_kwh`, `solar_kwh`, and `tariff_bdt_per_kwh`. Input order can vary. |
| `battery` | Finite non-negative `capacity_kwh`, `initial_energy_kwh`, `minimum_energy_kwh`, `max_charge_kwh_per_hour`, `max_discharge_kwh_per_hour`; minimum ≤ initial ≤ capacity. |

The response has exactly these seven keys, in this order: `scenario_id`, `directive_interpretation`, `hourly_plan`, `total_grid_kwh`, `total_cost_bdt`, `peak_grid_kwh`, `plan_summary`. The plan has one entry for each hour 0–23, in order. Each entry has exactly `hour`, `grid_kwh`, `solar_used_kwh`, `battery_action` (`charge`, `discharge`, or `idle`), `battery_kwh` (non-negative magnitude), and `battery_energy_after_kwh`. All numeric outputs must be finite.

Malformed JSON or a structurally invalid request returns HTTP 400 `{"error":"..."}`. An unexpected failure returns HTTP 500 `{"error":"internal error"}`. Never expose a traceback, key, token, or raw provider response.

## Directives

There is exactly one interpretation entry per operator note, in `note_index` order, with exactly `note_index`, `applies`, `directive_type`, `structured_adjustment`, and `explanation`. A `no_op` has `applies: false` and `structured_adjustment: null`; every other type has `applies: true`. Hours are unique integers 0–23 in ascending order. Time windows include their start and exclude their end: 1 PM to 3 PM means `[13,14]`. The LLM must be used in the interpretation path; regex is only a backup.

| `directive_type` | `structured_adjustment` | Effect |
| --- | --- | --- |
| `solar_reduction` | `{"hours":[...],"factor":0..1}` | `effective_solar[h] = solar[h] × factor`. Factor is the fraction remaining: 80% reduction means 0.2. |
| `minimum_battery_reserve` | `{"hours":[...],"minimum_energy_kwh":n}` | `E_after[h] ≥ max(base minimum, n)`. |
| `no_charge_window` | `{"hours":[...]}` | `charge[h] = 0`. |
| `no_discharge_window` | `{"hours":[...]}` | `discharge[h] = 0`. |
| `max_grid_window` | `{"hours":[...],"max_grid_kwh":n}` | `grid[h] ≤ n`. |
| `no_op` | `null` | No schedule change. |

Overlapping solar factors multiply. Reserve floors take the maximum. Grid caps take the minimum. No-charge and no-discharge windows union.

## Energy and scoring rules

The judge replays the plan with 0.01 tolerance:

* Each hour: `grid + solar_used + discharge = demand + charge`.
* `0 ≤ solar_used ≤ effective_solar`, and grid, charge, and discharge are non-negative.
* Charging adds `battery_kwh` to stored energy; discharging subtracts it; idle uses zero. The action sets the applicable hourly rate limit.
* `active_minimum ≤ E_after ≤ capacity` at every hour, including reserve directives.
* `E_after[23] = initial_energy_kwh`.
* `total_grid_kwh = Σ grid`, `total_cost_bdt = Σ grid × tariff`, `peak_grid_kwh = max(grid)`.
* Minimize `Σ grid × tariff` while honoring the constraints. The optimizer adds a tiny charge/discharge penalty to avoid pointless cycling.

## Internal Python contracts

```python
app.interpreter.interpret_notes(notes: list[str], battery: dict) -> list[dict]
# Never raises. Returns interpretations in note order.

app.optimizer.optimize(hours: list[dict], battery: dict, directives: list[dict]) -> dict
# Keys: hourly_plan, total_grid_kwh, total_cost_bdt, peak_grid_kwh,
# status ("optimal" | "relaxed" | "fallback"). Never raises.

app.optimizer.replay.replay_check(hours, battery, directives, response: dict) -> list[str]
# [] means valid; otherwise human-readable violations.
```

`app.main` sorts the 24 hours, passes all notes to the interpreter, and passes only interpretations with `applies == True` to `optimize`. `status` is internal and is not a public response key. Environment variables: `LLM_API_KEY`, optional OpenAI-compatible `LLM_BASE_URL`, `LLM_MODEL`, and `PORT` (default 8000).

## Complete 24-hour example

This example keeps the battery idle, so the calculation is easy to replay by hand. The 1 PM–3 PM panel reduction leaves 1 kWh of usable solar in hours 13 and 14. At 8 BDT/kWh, 80 grid kWh costs 640 BDT.

Request:

```json
{
  "scenario_id": "campus-day-01",
  "operator_notes": ["Panel cleaning cuts solar output by 50% from 1 PM to 3 PM today.", "The pastry menu changes next week."],
  "hours": [
    {"hour":0,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8},
    {"hour":1,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8},
    {"hour":2,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8},
    {"hour":3,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8},
    {"hour":4,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8},
    {"hour":5,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8},
    {"hour":6,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8},
    {"hour":7,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8},
    {"hour":8,"demand_kwh":4,"solar_kwh":2,"tariff_bdt_per_kwh":8},
    {"hour":9,"demand_kwh":4,"solar_kwh":2,"tariff_bdt_per_kwh":8},
    {"hour":10,"demand_kwh":4,"solar_kwh":2,"tariff_bdt_per_kwh":8},
    {"hour":11,"demand_kwh":4,"solar_kwh":2,"tariff_bdt_per_kwh":8},
    {"hour":12,"demand_kwh":4,"solar_kwh":2,"tariff_bdt_per_kwh":8},
    {"hour":13,"demand_kwh":4,"solar_kwh":2,"tariff_bdt_per_kwh":8},
    {"hour":14,"demand_kwh":4,"solar_kwh":2,"tariff_bdt_per_kwh":8},
    {"hour":15,"demand_kwh":4,"solar_kwh":2,"tariff_bdt_per_kwh":8},
    {"hour":16,"demand_kwh":4,"solar_kwh":2,"tariff_bdt_per_kwh":8},
    {"hour":17,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8},
    {"hour":18,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8},
    {"hour":19,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8},
    {"hour":20,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8},
    {"hour":21,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8},
    {"hour":22,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8},
    {"hour":23,"demand_kwh":4,"solar_kwh":0,"tariff_bdt_per_kwh":8}
  ],
  "battery": {"capacity_kwh":10,"initial_energy_kwh":5,"minimum_energy_kwh":2,"max_charge_kwh_per_hour":2,"max_discharge_kwh_per_hour":2}
}
```

Response illustrating the contract (the initial no-op stub will return no-op interpretations until Tamjid implements the LLM):

```json
{
  "scenario_id": "campus-day-01",
  "directive_interpretation": [
    {"note_index":0,"applies":true,"directive_type":"solar_reduction","structured_adjustment":{"hours":[13,14],"factor":0.5},"explanation":"Panel cleaning halves solar availability from 1 PM to 3 PM."},
    {"note_index":1,"applies":false,"directive_type":"no_op","structured_adjustment":null,"explanation":"A next-week menu change does not affect today's energy schedule."}
  ],
  "hourly_plan": [
    {"hour":0,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":1,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":2,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":3,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":4,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":5,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":6,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":7,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":8,"grid_kwh":2,"solar_used_kwh":2,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":9,"grid_kwh":2,"solar_used_kwh":2,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":10,"grid_kwh":2,"solar_used_kwh":2,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":11,"grid_kwh":2,"solar_used_kwh":2,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":12,"grid_kwh":2,"solar_used_kwh":2,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":13,"grid_kwh":3,"solar_used_kwh":1,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":14,"grid_kwh":3,"solar_used_kwh":1,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":15,"grid_kwh":2,"solar_used_kwh":2,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":16,"grid_kwh":2,"solar_used_kwh":2,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":17,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":18,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":19,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":20,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":21,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":22,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5},
    {"hour":23,"grid_kwh":4,"solar_used_kwh":0,"battery_action":"idle","battery_kwh":0,"battery_energy_after_kwh":5}
  ],
  "total_grid_kwh":80,
  "total_cost_bdt":640,
  "peak_grid_kwh":4,
  "plan_summary":"Applied directives: solar_reduction; total cost: 640.000000 BDT."
}
```
