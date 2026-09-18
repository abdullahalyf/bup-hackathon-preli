# GridWise

> **LLM-assisted 24-hour battery + grid schedule builder.** Operator types free-text notes; GridWise turns them into machine-checkable directives, then solves a minimum-cost schedule with hard energy and reserve constraints.

GridWise is a small public FastAPI service built for the BUP CSE Fest 2026 hackathon preliminary.

- `POST /optimize-energy` accepts 24 hours of demand / solar / tariff data plus 1–3 free-text operator notes
- An LLM interpreter turns each note into a structured directive (`solar_reduction`, `minimum_battery_reserve`, `no_charge_window`, `no_discharge_window`, `max_grid_window`, `no_op`)
- Deterministic guardrails validate and clamp the directives
- A linear-program optimizer builds the minimum-cost battery + grid plan
- An automated judge replays and scores the response against the same constraints

---

## Architecture

```
                          ┌───────────────────────────┐
   Operator notes ──────▶│  Pydantic request schema  │
   (1–3 English lines)   │   (app/main.py, schemas)  │
                          └─────────────┬─────────────┘
                                        │
                          ┌─────────────▼─────────────┐
                          │   LLM Interpreter         │
                          │   interpret_notes(...)    │
                          │   structured directive +  │
                          │   deterministic guardrail │
                          └─────────────┬─────────────┘
                                        │ applies == true
                          ┌─────────────▼─────────────┐
                          │   LP Optimizer (HiGHS)    │
                          │   optimize(...)           │
                          │   min Σ grid×tariff       │
                          └─────────────┬─────────────┘
                                        │
                          ┌─────────────▼─────────────┐
                          │   HTTP response (strict   │
                          │   JSON, 7 top-level keys) │
                          └───────────────────────────┘
                                        │
                          ┌─────────────▼─────────────┐
                          │   replay_check (judge)    │
                          │   energy / reserve /      │
                          │   neutrality checks       │
                          └───────────────────────────┘
```

---

## Team & ownership

| Member  | Branch   | Role                                    | Owns |
|---------|----------|-----------------------------------------|------|
| Alif    | `alif`   | Head / API integrator / merges to `main` | `app/main.py`, `app/schemas.py`, `app/__init__.py`, `app/interpreter/__init__.py`, `app/optimizer/__init__.py`, `requirements.txt`, `.env.example`, `.gitignore`, `Dockerfile`, `.dockerignore`, `docs/*`, `tasks/*`, `AGENTS.md`, `CLAUDE.md` |
| Taseen  | `taseen` | Optimizer engineer                      | `app/optimizer/solver.py`, `app/optimizer/replay.py`, `tests/test_optimizer.py` |
| Tamjid  | `tamjid` | LLM engineer                            | `app/interpreter/core.py`, `prompt.py`, `llm_client.py`, `normalize.py`, `fallback.py`, `tests/test_interpreter.py` |
| Jubayer | `jubayer`| DevOps + QA + Docs + frontend           | `scripts/*`, `tests/test_api.py`, `data/paraphrases.json`, `frontend/*`, `README.md`, `docs/VIDEO_SCRIPT.md` |

Branch discipline: only Alif pushes to `main`. Everyone else pushes to their own branch.

---

## Model & provider

The interpreter speaks to **any OpenAI-compatible chat-completions endpoint** via the official `openai` Python SDK. Configure in `.env`:

| Variable                | Meaning                                      |
|-------------------------|----------------------------------------------|
| `LLM_API_KEY`           | Required. API key for the primary provider.  |
| `LLM_BASE_URL`          | Optional. Defaults to OpenAI's public URL.   |
| `LLM_MODEL`             | Required. Provider model id (e.g. `gpt-4o-mini`). |
| `LLM_FALLBACK_API_KEY`  | Optional. Secondary key used if the primary call fails or is rate-limited. |
| `LLM_FALLBACK_BASE_URL` | Optional. Fallback base URL.                 |
| `LLM_FALLBACK_MODEL`    | Optional. Fallback model id.                 |
| `PORT`                  | Optional. Defaults to `8000`.                |

When no key is present, `app/interpreter/core.py` falls back to a deterministic regex extractor so the service stays runnable for development and CI.

---

## Guardrails (interpreter)

The interpreter never returns an unstructured string. Every directive is validated by deterministic guardrails before reaching the optimizer:

- `applies` is a boolean; `no_op` is the only type with `applies: false`.
- Time windows are integer hours 0–23 in ascending order, unique, and start-inclusive / end-exclusive (so 1 PM → 3 PM means `[13, 14]`).
- `factor` for `solar_reduction` is clamped to `[0, 1]`.
- `minimum_energy_kwh` for `minimum_battery_reserve` is clamped to `[0, capacity_kwh]`.
- `max_grid_kwh` for `max_grid_window` must be non-negative and finite.
- Overlapping solar factors multiply; reserve floors take the maximum; grid caps take the minimum; no-charge and no-discharge windows union.
- Any note that doesn't match a known directive type becomes `no_op` with `structured_adjustment: null`.

---

## Optimizer formulation

Given 24 hours `h` of `demand[h]`, `effective_solar[h]`, `tariff[h]`, `battery.max_charge`, `battery.max_discharge`, `battery.min`, `battery.cap`, and the directives above:

```
for each hour h:
    grid[h], solar_used[h], charge[h], discharge[h] >= 0
    grid[h] + solar_used[h] + discharge[h] == demand[h] + charge[h]
    solar_used[h] <= effective_solar[h]
    charge[h]    <= max_charge_kwh_per_hour
    discharge[h] <= max_discharge_kwh_per_hour
    min_energy <= battery_after[h] <= capacity_kwh

battery_after[0] = initial_energy_kwh + charge[0] - discharge[0]
battery_after[h] = battery_after[h-1] + charge[h] - discharge[h]
battery_after[23] == initial_energy_kwh          # neutrality

minimize Σ grid[h] × tariff[h] + ε·(charge[h] + discharge[h])
```

`ε` is a tiny penalty that discourages pointless cycling without changing the optimum for any non-degenerate input. The solver is HiGHS through `scipy.optimize.linprog`. If HiGHS can't prove optimality, the service returns a `status: "relaxed"` plan; if the model can't be built at all, it falls back to a safe solar-then-grid baseline with `status: "fallback"`.

---

## Public API

| Method | Path                | Body / Returns                                                              |
|--------|---------------------|-----------------------------------------------------------------------------|
| GET    | `/health`           | `{"status":"ok"}`                                                           |
| POST   | `/optimize-energy`  | Request: `scenario_id`, `operator_notes` (1–3), `hours` (24), `battery`. Response: `scenario_id`, `directive_interpretation`, `hourly_plan`, `total_grid_kwh`, `total_cost_bdt`, `peak_grid_kwh`, `plan_summary`. |

The full request / response shape, the seven supported directive types, and the judge replay rules live in [`docs/CONTRACTS.md`](docs/CONTRACTS.md).

---

## Quickstart

```bash
# 1. Clone and enter the repo
git clone https://github.com/abdullahalyf/bup-hackathon-preli.git
cd bup-hackathon-preli

# 2. Create a virtualenv and install
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt      # PowerShell
# source .venv/bin/activate && pip install -r requirements.txt   # bash

# 3. Optional: configure an LLM provider
cp .env.example .env
# edit .env and set LLM_API_KEY / LLM_MODEL

# 4. Run the API
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 5. Smoke test
curl -s http://127.0.0.1:8000/health
# {"status":"ok"}
```

### `curl` example for `/optimize-energy`

The full 24-hour payload for every case lives in [`data/public_samples.json`](data/public_samples.json). A minimal demo request:

```bash
curl -X POST http://127.0.0.1:8000/optimize-energy \
  -H "content-type: application/json" \
  -d @- <<'JSON'
{
  "scenario_id": "smoke-test",
  "operator_notes": [
    "Panel cleaning halves solar from 12:00 to 14:00.",
    "Reserve 50% of the battery from 18:00 until 21:00."
  ],
  "hours": [
    {"hour":0,"demand_kwh":90,"solar_kwh":0,"tariff_bdt_per_kwh":6},
    {"hour":1,"demand_kwh":85,"solar_kwh":0,"tariff_bdt_per_kwh":6},
    {"hour":2,"demand_kwh":80,"solar_kwh":0,"tariff_bdt_per_kwh":5},
    {"hour":3,"demand_kwh":80,"solar_kwh":0,"tariff_bdt_per_kwh":5},
    {"hour":4,"demand_kwh":85,"solar_kwh":0,"tariff_bdt_per_kwh":5},
    {"hour":5,"demand_kwh":95,"solar_kwh":0,"tariff_bdt_per_kwh":6},
    {"hour":6,"demand_kwh":110,"solar_kwh":5,"tariff_bdt_per_kwh":8},
    {"hour":7,"demand_kwh":130,"solar_kwh":20,"tariff_bdt_per_kwh":10},
    {"hour":8,"demand_kwh":150,"solar_kwh":50,"tariff_bdt_per_kwh":12},
    {"hour":9,"demand_kwh":165,"solar_kwh":90,"tariff_bdt_per_kwh":14},
    {"hour":10,"demand_kwh":175,"solar_kwh":130,"tariff_bdt_per_kwh":16},
    {"hour":11,"demand_kwh":180,"solar_kwh":160,"tariff_bdt_per_kwh":16},
    {"hour":12,"demand_kwh":185,"solar_kwh":180,"tariff_bdt_per_kwh":15},
    {"hour":13,"demand_kwh":180,"solar_kwh":170,"tariff_bdt_per_kwh":14},
    {"hour":14,"demand_kwh":170,"solar_kwh":140,"tariff_bdt_per_kwh":13},
    {"hour":15,"demand_kwh":165,"solar_kwh":90,"tariff_bdt_per_kwh":14},
    {"hour":16,"demand_kwh":170,"solar_kwh":45,"tariff_bdt_per_kwh":18},
    {"hour":17,"demand_kwh":185,"solar_kwh":10,"tariff_bdt_per_kwh":22},
    {"hour":18,"demand_kwh":205,"solar_kwh":0,"tariff_bdt_per_kwh":28},
    {"hour":19,"demand_kwh":215,"solar_kwh":0,"tariff_bdt_per_kwh":30},
    {"hour":20,"demand_kwh":205,"solar_kwh":0,"tariff_bdt_per_kwh":26},
    {"hour":21,"demand_kwh":175,"solar_kwh":0,"tariff_bdt_per_kwh":18},
    {"hour":22,"demand_kwh":135,"solar_kwh":0,"tariff_bdt_per_kwh":10},
    {"hour":23,"demand_kwh":105,"solar_kwh":0,"tariff_bdt_per_kwh":7}
  ],
  "battery": {
    "capacity_kwh":220,
    "initial_energy_kwh":110,
    "minimum_energy_kwh":40,
    "max_charge_kwh_per_hour":50,
    "max_discharge_kwh_per_hour":50
  }
}
JSON
```

---

## Frontend

Open `frontend/index.html` in a browser (after the API is running) or serve it locally:

```bash
.venv\Scripts\python.exe -m http.server 5500 --bind 127.0.0.1 --directory frontend
# then open http://127.0.0.1:5500/
```

The console loads three preset scenarios (SAMPLE-01 / 03 / 05) and lets you edit the notes and the 24-hour JSON before clicking **Optimize**. Results show totals, the directive interpretation table, an hourly plan table, and a Chart.js mixed chart with stacked energy bars + battery SoC line + tariff line.

---

## Tests & samples

| Command | What it does |
|---------|--------------|
| `pytest tests/test_api.py` | API-layer tests: `/health`, malformed JSON, 23 hours, 0 / 4 notes, duplicate hour, valid sample shape, battery invariant. |
| `pytest tests/test_interpreter.py` | Interpreter unit tests (owned by Tamjid). |
| `pytest tests/test_optimizer.py`  | Optimizer unit + replay tests (owned by Taseen). |
| `python scripts/run_samples.py [BASE_URL]` | Replays all 10 cases from `data/public_samples.json` against a live API and reports per-case interpretation match, cost diff, and any `replay_check` violations. Exits 1 on failure. |
| `python scripts/paraphrase_check.py` | Runs the 40 paraphrased operator notes in `data/paraphrases.json` through `interpret_notes`, prints per-type and overall accuracy plus average latency. |

---

## Docker

The prebuilt image is published to GitHub Container Registry:

```bash
docker pull ghcr.io/abdullahalyf/bup-hackathon-preli:<IMAGE_TAG>
docker run --rm -p 8000:8000 \
  -e LLM_API_KEY=sk-... \
  -e LLM_MODEL=gpt-4o-mini \
  ghcr.io/abdullahalyf/bup-hackathon-preli:<IMAGE_TAG>
# then curl http://127.0.0.1:8000/health
```

`<IMAGE_TAG>` is provided in the team submission channel (e.g. `v0.1.0` or the SHA of the latest `main` commit). To build locally instead:

```bash
docker build -t gridwise:dev .
docker run --rm -p 8000:8000 gridwise:dev
```

---

## Live deployment

The canonical hackathon deployment lives at **`<LIVE_URL>`** (filled in by Alif before submission). The image above is pinned to `<IMAGE_TAG>`.

---

## Project structure

```
app/
  __init__.py
  main.py                 # FastAPI entry, exception handlers, /health, /optimize-energy
  schemas.py              # Pydantic request models with strict validation
  interpreter/
    core.py               # interpret_notes(...) — LLM call + deterministic guardrail
  optimizer/
    solver.py             # optimize(...) — LP via scipy.optimize.linprog (HiGHS)
    replay.py             # replay_check(...) — judge-side replay of the plan
data/
  public_samples.json     # 10 fully worked example cases for the sample runner
  paraphrases.json        # 40 paraphrased notes for the LLM accuracy checker
scripts/
  run_samples.py          # replays public_samples.json against a live API
  paraphrase_check.py     # reports LLM interpreter accuracy + latency
tests/
  test_api.py             # FastAPI TestClient — every owned branch of the API
frontend/
  index.html              # single-file operator console (Chart.js from cdnjs)
docs/
  CONTRACTS.md            # single source of truth for the public API
  MASTER_PLAN.md          # team plan + work-unit prompts
  VIDEO_SCRIPT.md         # 3-minute demo script
tasks/
  *.md                    # per-member task files (read first!)
```

---

## Credits

Built in four hours by Alif (integration), Taseen (optimizer), Tamjid (LLM interpreter), and Jubayer (DevOps + QA + frontend + docs) for BUP CSE Fest 2026. See [`AGENTS.md`](AGENTS.md) for the full team rules and [`tasks/HOW_TO_WORK.md`](tasks/HOW_TO_WORK.md) for the per-member workflow.
