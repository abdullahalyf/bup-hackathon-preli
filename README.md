<div align="center">

![GridWise Banner](docs/banner.png)

# ⚡ GridWise

### *LLM-assisted, minimum-cost 24-hour battery + grid scheduler.*

[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.4.7-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![SciPy](https://img.shields.io/badge/SciPy-HiGHS-8CAAE6?style=for-the-badge&logo=scipy&logoColor=white)](https://scipy.org/)
[![License](https://img.shields.io/badge/Hackathon-BUP_CSE_Fest_2026-FFD43B?style=for-the-badge)](#)

A small, self-contained FastAPI service that turns a campus operator's **free-text notes** into a **minimum-cost battery + grid schedule** for the next 24 hours — solved end-to-end by an LLM directive interpreter and a deterministic linear program.

> **Built in one weekend for the BUP CSE Fest 2026 hackathon preliminary.**

</div>

---

## 📌 Summary

Campus microgrids balance three resources at once — **grid power**, **rooftop solar**, and a **finite battery**. The cheapest 24-hour plan depends on the tariff curve, the weather, and the operator's judgement calls (e.g. *"reserve half the battery for the 7 PM peak"*).

**GridWise** lets the operator describe those judgement calls in plain English. It validates them against deterministic guardrails, then solves an LP for the actual hourly plan. The same plan is later replayed by an automated judge to confirm it satisfies every constraint.

| Method | Endpoint              | Purpose                          |
| ------ | --------------------- | -------------------------------- |
| `GET`  | `/health`             | Liveness probe                   |
| `POST` | `/optimize-energy`    | 24-hour minimum-cost battery plan |

---

## 🧠 Architecture Overview

```
Operator notes (1–3 lines of English)
        │
        ▼
┌──────────────────────────────────────────────┐
│  LLM Interpreter  (interpret_notes)          │
│  ─ primary  : Gemini  via OpenAI-compat API │
│  ─ fallback : Groq    via OpenAI-compat API │
│  ─ offline  : deterministic regex extractor │
└──────────────────┬───────────────────────────┘
                   │  structured directive(s)
                   ▼
┌──────────────────────────────────────────────┐
│  Deterministic Guardrails                    │
│  ─ clamp hours to 0..23, asc, unique        │
│  ─ solar reduction factor ∈ [0, 1]          │
│  ─ battery reserve ∈ [0, capacity_kwh]      │
│  ─ overlapping windows union sensibly       │
└──────────────────┬───────────────────────────┘
                   │  enforced directive set
                   ▼
┌──────────────────────────────────────────────┐
│  LP Optimizer  (scipy.optimize.linprog)     │
│  ─ solver : HiGHS                            │
│  ─ minimize  Σ grid[h] × tariff[h]          │
│  ─ subject to per-hour SoC bounds,           │
│    charge/discharge rate caps, neutrality    │
│  ─ fallback: solar-then-grid baseline        │
└──────────────────┬───────────────────────────┘
                   │
                   ▼
       Strict JSON response
       (7 top-level keys, hourly plan = 24 rows)
```

### Model & Provider
- Any **OpenAI-compatible chat-completions** endpoint can drive the interpreter. The only required env vars are `LLM_API_KEY`, `LLM_BASE_URL`, and `LLM_MODEL`.
- A **Groq** secondary is wired in via `LLM_FALLBACK_*` and is used automatically when the primary call fails or is rate-limited.
- When no key is configured, a built-in **regex extractor** maps notes to directives so the service stays runnable for local dev and CI.

### LLM Role
The LLM's sole job is **parsing**: it receives 1–3 operator notes plus the directive type catalog, and returns a JSON list of structured directives (`solar_reduction`, `minimum_battery_reserve`, `no_charge_window`, `no_discharge_window`, `max_grid_window`, or `no_op`). The LLM never sees the demand data, never touches the solver, and never appears in the response.

### Guardrails
Every directive returned by the LLM is validated by a deterministic guardrail **before** it reaches the optimizer. Specifically:
- `applies` is a boolean (false only for `no_op`).
- Window hours are clamped to `[0, 23]`, sorted, deduplicated, and treated as **start-inclusive / end-exclusive**.
- Overlapping constraints combine deterministically: solar factors multiply, reserve floors take the maximum, grid caps take the minimum, no-charge / no-discharge windows union.
- Unstructured or unparseable notes are mapped to `no_op`, never to a half-formed constraint.

### Optimizer / Solver
The optimizer is a 24-hour LP minimized with `scipy.optimize.linprog(method="highs")`:

```
minimize    Σ grid[h] × tariff[h]  +  ε·(charge[h] + discharge[h])
subject to  grid[h] + solar_used[h] + discharge[h] == demand[h] + charge[h]      ∀ h
            solar_used[h] ≤ effective_solar[h]
            charge[h]    ≤ battery.max_charge_kwh_per_hour
            discharge[h] ≤ battery.max_discharge_kwh_per_hour
            battery.min_energy_kwh ≤ battery_after[h] ≤ battery.capacity_kwh
            battery_after[23] == battery.initial_energy_kwh                (neutrality)
```

If HiGHS reports optimality, the response is `status: "optimal"`. If it returns a feasible but not provably-optimal point, the plan is tagged `status: "relaxed"`. If the model cannot be built at all, the service returns a safe **solar-then-grid baseline** with `status: "fallback"`. The judge later runs `replay_check` to independently confirm every constraint holds.

---

## 🛠️ Tech Stack

| Layer       | Technology                                       | Role                                       |
| ----------- | ------------------------------------------------ | ------------------------------------------ |
| Web         | **FastAPI** + **Uvicorn**                        | HTTP API, Pydantic v2 validation, async     |
| LLM client  | **OpenAI Python SDK**                            | OpenAI-compatible chat-completions         |
| Optimizer   | **SciPy** (`linprog`, method `highs`)            | Linear-program solver                      |
| Validation  | **Pydantic v2**                                  | Strict request / response schemas          |
| Frontend    | **HTML / CSS / vanilla JS**                      | Single-file operator console               |
| Charts      | **Chart.js 4.4.7** (vendored UMD)                | Stacked energy + SoC + tariff visualization |
| Typography  | **Inter** + **JetBrains Mono** (Google Fonts)    | Body + numeric cells                       |
| Packaging   | **Docker**                                       | Reproducible container build               |

---

## ⚙️ Source Setup & Dependencies

> **Prerequisites:** Python **3.11+**, Git, ~200 MB free disk.

```bash
# 1. Clone the repo
git clone https://github.com/abdullahalyf/bup-hackathon-preli.git
cd bup-hackathon-preli

# 2. Create a virtual environment
#    Windows (PowerShell)
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

#    macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

All Python dependencies are pinned in [`requirements.txt`](requirements.txt): `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `openai`, `scipy`, `numpy`, `requests`, `httpx`, `pytest`, `python-dotenv`.

---

## 🔐 Environment Variables

> The service runs **without any keys** using the built-in regex fallback — useful for the smoke test. To enable real LLM-driven directive interpretation, copy `.env.example` to `.env` and fill in the values below. **Do not commit any of these to version control.**

| Variable                | Required | Meaning                                                                          |
| ----------------------- | -------- | -------------------------------------------------------------------------------- |
| `LLM_API_KEY`           | ✅ (for live LLM) | API key for the **primary** OpenAI-compatible provider.                         |
| `LLM_BASE_URL`          | optional | Base URL for the primary provider.                                               |
| `LLM_MODEL`             | ✅ (for live LLM) | Primary model id (`gemini-3.5-flash-lite` in the deployment).                    |
| `LLM_FALLBACK_API_KEY`  | optional | API key for the **fallback** provider. Used when the primary fails / rate-limits.|
| `LLM_FALLBACK_BASE_URL` | optional | Base URL for the fallback provider (e.g. Groq).                                  |
| `LLM_FALLBACK_MODEL`    | optional | Fallback model id.                                                               |
| `PORT`                  | optional | HTTP port. Defaults to `8000` if unset.                                          |

Example `.env` (no real secrets shown — fill in your own keys):

```dotenv
LLM_API_KEY=your-primary-key-here
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
LLM_MODEL=gemini-3.5-flash-lite

LLM_FALLBACK_API_KEY=your-fallback-key-here
LLM_FALLBACK_BASE_URL=https://api.groq.com/openai/v1
LLM_FALLBACK_MODEL=openai/gpt-oss-120b

PORT=8000
```

---

## ▶️ Exact Run Command

```bash
# Windows (PowerShell) — works without an LLM key (regex fallback)
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# macOS / Linux
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

> The repo expects this exact invocation. `PORT` may also be read from `.env`; otherwise it defaults to `8000`.

The API is now live at `http://127.0.0.1:8000`. Open the interactive docs at `http://127.0.0.1:8000/docs` (Swagger UI).

To use the bundled operator console (recommended for judges):

```bash
# in a second terminal, from the repo root
.venv\Scripts\python.exe -m http.server 5500 --bind 127.0.0.1 --directory frontend
# then open http://127.0.0.1:5500/
```

---

## 🧪 Testing & API Usage

### Run the public-sample replay suite

```bash
# defaults to http://localhost:8000, or set BASE_URL
.venv\Scripts\python.exe scripts\run_samples.py
# macOS / Linux
.venv/bin/python scripts/run_samples.py
```

It replays all 10 cases from [`data/public_samples.json`](data/public_samples.json) against a live API, reporting per-case interpretation match, cost diff, and any `replay_check` violations. Exits non-zero on failure.

### Run the unit tests

```bash
.venv\Scripts\python.exe -m pytest -q
```

### Smoke test the health endpoint

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok"}
```

### Hit `/optimize-energy` with `curl`

```bash
curl -X POST http://127.0.0.1:8000/optimize-energy \
  -H "content-type: application/json" \
  -d '{
    "scenario_id": "smoke-test",
    "operator_notes": [
      "Reserve 50% of the battery from 18:00 to 21:00."
    ],
    "hours": [
      {"hour": 0,  "demand_kwh": 90,  "solar_kwh": 0,   "tariff_bdt_per_kwh": 6},
      {"hour": 6,  "demand_kwh": 110, "solar_kwh": 5,   "tariff_bdt_per_kwh": 8},
      {"hour": 12, "demand_kwh": 185, "solar_kwh": 180, "tariff_bdt_per_kwh": 15},
      {"hour": 18, "demand_kwh": 205, "solar_kwh": 0,   "tariff_bdt_per_kwh": 28},
      {"hour": 19, "demand_kwh": 215, "solar_kwh": 0,   "tariff_bdt_per_kwh": 30},
      {"hour": 23, "demand_kwh": 105, "solar_kwh": 0,   "tariff_bdt_per_kwh": 7}
    ],
    "battery": {
      "capacity_kwh": 220,
      "initial_energy_kwh": 110,
      "minimum_energy_kwh": 40,
      "max_charge_kwh_per_hour": 50,
      "max_discharge_kwh_per_hour": 50
    }
  }'
```

A full 24-hour payload lives in [`data/public_samples.json`](data/public_samples.json). The response always has exactly the seven top-level keys declared in [`docs/CONTRACTS.md`](docs/CONTRACTS.md).

---

## ⚠️ Known Limitations

- **Single 24-hour horizon.** The optimizer treats every hour as a fresh decision; multi-day scheduling, demand forecasting, and rolling replans are out of scope.
- **Linear-program solver only.** Battery efficiency, degradation cost, and thermal limits are not modeled. Charge / discharge efficiency is assumed to be 100%.
- **No stateful history.** The service has no memory of previous requests — every call is independent.
- **LLM interpreter is best-effort.** When keys are configured, the interpreter occasionally produces directives the guardrails clamp or reject; accuracy is reported by `python scripts/paraphrase_check.py`.
- **Regex fallback is intentionally minimal.** It covers the few directive shapes used in `data/public_samples.json` and is not a substitute for a configured LLM in production.
- **No authentication.** The service binds to `0.0.0.0` by design for the hackathon demo; do not expose the port to the public internet.
- **Single-process.** Uvicorn is started with one worker; for higher throughput, scale via a process manager or run the prebuilt container with `--workers 2`.

---

## 🚀 Live Deployment

The canonical hackathon deployment is live at:

**👉 https://gridwise-production-0e08.up.railway.app**

- The site root (`/`) serves the operator console.
- `GET /health` returns `{"status":"ok"}`.
- `POST /optimize-energy` accepts the same JSON shape as the local server.

The prebuilt Docker image is published at `ghcr.io/abdullahalyf/gridwise:v1`. Railway redeploys automatically when `main` is updated.

```bash
docker pull ghcr.io/abdullahalyf/gridwise:v1
docker run --rm -p 8000:8000 --env-file .env ghcr.io/abdullahalyf/gridwise:v1
```

---

## 👥 Team & Roles

| Member  | Branch    | Role |
| ------- | --------- | ---- |
| 🧑‍✈️ **Alif**    | `alif`    | **Leader & Architecture** — FastAPI integration, schemas, exception handling, merge gate to `main`. |
| ⚙️ **Taseen**  | `taseen`  | **Optimizer & Frontend** — LP solver (`app/optimizer/`), replay validator, operator console UI. |
| 🤖 **Tamjid**  | `tamjid`  | **LLM Interpreter** — prompt design, LLM client, normalization, deterministic guardrails & fallback. |
| 🚀 **Jubayer** | `jubayer` | **Deployment & QA** — Docker, hosting, sample runner, frontend base, README & demo video. |

> **Branch discipline:** only Alif merges to `main`; everyone else pushes to their own branch and rebases after each merge.

---

## 📂 Project Structure

```
bup-hackathon-preli/
├── app/
│   ├── main.py                 # FastAPI entry, /health, /optimize-energy
│   ├── schemas.py              # Pydantic request / response models
│   ├── interpreter/            # LLM directive interpreter (Gemini / Groq / regex)
│   │   ├── core.py
│   │   ├── prompt.py
│   │   ├── llm_client.py
│   │   ├── normalize.py
│   │   └── fallback.py
│   └── optimizer/              # LP solver + judge replay
│       ├── solver.py
│       └── replay.py
├── frontend/
│   ├── index.html              # operator console (single file)
│   └── chart.umd.min.js        # vendored Chart.js 4.4.7
├── data/
│   ├── public_samples.json     # 10 worked example cases
│   └── paraphrases.json        # 40 paraphrased notes for LLM accuracy
├── scripts/
│   ├── run_samples.py          # replay public samples against a live API
│   └── paraphrase_check.py     # LLM accuracy + latency report
├── tests/                      # pytest suite (api, interpreter, optimizer)
├── docs/
│   ├── CONTRACTS.md            # single source of truth for the public API
│   ├── MASTER_PLAN.md          # team plan + work-unit prompts
│   ├── VIDEO_SCRIPT.md         # 3-minute demo script
│   ├── banner.png              # README banner (placeholder)
│   └── STATUS.md
├── tasks/                      # per-member task briefs
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## 📜 Credits

Built in four hours by **Alif, Taseen, Tamjid, and Jubayer** for the **BUP CSE Fest 2026** hackathon preliminary. See [`AGENTS.md`](AGENTS.md) for the full team rules and [`tasks/HOW_TO_WORK.md`](tasks/HOW_TO_WORK.md) for the per-member workflow.

<div align="center">

Made with ☕ and ⚡ in Dhaka.

</div>
