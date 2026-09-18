CODEX PROMPT — GridWise Team Setup (step-by-step tasks for everyone)

How to use (Alif):

git clone https://github.com/abdullahalyf/bup-hackathon-preli.git && cd bup-hackathon-preli
Put organizer files: data/public_samples.json (sample JSON), docs/spec/ (both PDFs), and this file as docs/CODEX_TEAM_SETUP_PROMPT.md.
Tell Codex: "Read docs/CODEX_TEAM_SETUP_PROMPT.md and execute everything below the line exactly."
TASK

Set up the repository for a 4-person, 4-hour hackathon project GridWise. Create:

the full code skeleton with working stubs (API runs end-to-end immediately),
shared docs (rules + contracts),
one step-by-step task file per member in tasks/, written verbatim from the content given below.

Do NOT implement the real optimizer or LLM logic. Only stubs + docs.

Project in 3 lines: Public FastAPI service. POST /optimize-energy receives 24h energy data + 1–3 English operator notes → an LLM turns notes into structured directives → deterministic guardrails validate them → an LP optimizer builds the minimum-cost 24h battery/grid schedule → strict JSON. An automated judge replays and scores it.

PART A — FILE STRUCTURE TO CREATE
bup-hackathon-preli/
├── AGENTS.md                  # rules for AI CLIs (Puku/Codex read first)
├── CLAUDE.md                  # identical copy of AGENTS.md
├── README.md                  # placeholder (Jubayer writes the real one)
├── requirements.txt
├── .gitignore
├── .env.example
├── .dockerignore
├── Dockerfile                 # minimal working
├── docs/
│   ├── CONTRACTS.md           # single source of truth: API + internal contracts
│   └── spec/                  # (organizer PDFs, already placed)
├── tasks/
│   ├── HOW_TO_WORK.md         # git + workflow for everyone
│   ├── ALIF.md
│   ├── TASEEN.md
│   ├── TAMJID.md
│   └── JUBAYER.md
├── data/
│   ├── public_samples.json    # (organizer file, already placed)
│   └── paraphrases.json       # []
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── schemas.py
│   ├── interpreter/
│   │   ├── __init__.py        # from .core import interpret_notes
│   │   ├── core.py            # STUB
│   │   ├── prompt.py          # placeholder
│   │   ├── llm_client.py      # placeholder
│   │   ├── normalize.py       # placeholder
│   │   └── fallback.py        # placeholder
│   └── optimizer/
│       ├── __init__.py        # from .solver import optimize
│       ├── solver.py          # STUB
│       └── replay.py          # STUB
├── tests/
│   ├── test_optimizer.py      # trivial passing test
│   ├── test_interpreter.py    # trivial passing test
│   └── test_api.py            # trivial passing test
└── scripts/
    ├── run_samples.py         # print("TODO")
    └── paraphrase_check.py    # print("TODO")
Ownership (put this table in AGENTS.md, CLAUDE.md, README.md, tasks/HOW_TO_WORK.md)
Member	Branch	Role	Owns
Alif	alif	Head / API integrator / only person who merges to main	app/main.py, app/schemas.py, app/__init__.py, app/interpreter/__init__.py, app/optimizer/__init__.py, requirements.txt, .env.example, .gitignore, docs/*, tasks/*, AGENTS.md, CLAUDE.md
Taseen	taseen	Optimizer engineer	app/optimizer/solver.py, app/optimizer/replay.py, tests/test_optimizer.py
Tamjid	tamjid	LLM engineer	app/interpreter/core.py, prompt.py, llm_client.py, normalize.py, fallback.py, tests/test_interpreter.py
Jubayer	jubayer	DevOps + QA + Docs	scripts/*, tests/test_api.py, data/paraphrases.json, Dockerfile, .dockerignore, README.md, docs/VIDEO_SCRIPT.md
PART B — SHARED CONTENT
B1. docs/CONTRACTS.md (write in full, with one complete realistic 24-hour example request and response)

Endpoints

GET /health → 200 {"status":"ok"}
POST /optimize-energy

Request

json
{
  "scenario_id": "string",
  "operator_notes": ["1..3 non-empty strings"],
  "hours": [{"hour": 0, "demand_kwh": 0, "solar_kwh": 0, "tariff_bdt_per_kwh": 0}],
  "battery": {"capacity_kwh": 0, "initial_energy_kwh": 0, "minimum_energy_kwh": 0,
              "max_charge_kwh_per_hour": 0, "max_discharge_kwh_per_hour": 0}
}

hours: exactly 24 entries, hour 0–23 each once.

Response (exact keys, no extras)

json
{
  "scenario_id": "echo",
  "directive_interpretation": [{"note_index": 0, "applies": true, "directive_type": "solar_reduction",
                                "structured_adjustment": {"hours": [13, 14], "factor": 0.2}, "explanation": "..."}],
  "hourly_plan": [{"hour": 0, "grid_kwh": 0, "solar_used_kwh": 0, "battery_action": "charge|discharge|idle",
                   "battery_kwh": 0, "battery_energy_after_kwh": 0}],
  "total_grid_kwh": 0, "total_cost_bdt": 0, "peak_grid_kwh": 0, "plan_summary": "..."
}

Directive types

Type	structured_adjustment	Math effect
solar_reduction	{"hours":[...], "factor": 0..1}	effective_solar[h] = solar[h] × factor (factor = fraction REMAINING; "80% reduction" → 0.2)
minimum_battery_reserve	{"hours":[...], "minimum_energy_kwh": n}	E_after[h] ≥ max(base minimum, n)
no_charge_window	{"hours":[...]}	charge[h] = 0
no_discharge_window	{"hours":[...]}	discharge[h] = 0
max_grid_window	{"hours":[...], "max_grid_kwh": n}	grid[h] ≤ n
no_op	null	nothing

Interpretation rules: one entry per note in note_index order; no_op ⇒ applies=false + null; others ⇒ applies=true; hours unique ints 0–23 ascending; windows start-inclusive, end-exclusive ("1 PM to 3 PM" → [13,14]); LLM is mandatory in the interpretation path (regex only as backup).

Energy rules (judge replays, tolerance 0.01): grid + solar_used + discharge = demand + charge; 0 ≤ solar_used ≤ effective_solar; charge E += battery_kwh, discharge E -= battery_kwh, idle battery_kwh = 0; active_min ≤ E_after ≤ capacity; hourly rate limits; E_after[23] == initial_energy_kwh; minimize Σ grid × tariff; totals must match hourly_plan.

Errors: malformed/structurally invalid → 400 {"error": "..."}; unexpected → 500 {"error":"internal error"}; never leak traces/secrets.

Internal contracts (change only with Alif's approval)

python
app.interpreter.interpret_notes(notes: list[str], battery: dict) -> list[dict]   # never raises
app.optimizer.optimize(hours: list[dict], battery: dict, directives: list[dict]) -> dict
    # keys: hourly_plan, total_grid_kwh, total_cost_bdt, peak_grid_kwh, status ("optimal"|"relaxed"|"fallback"); never raises
app.optimizer.replay.replay_check(hours, battery, directives, response: dict) -> list[str]   # [] = valid

main.py passes only entries with applies == True to optimize().

Env vars: LLM_API_KEY, LLM_BASE_URL (optional, OpenAI-compatible), LLM_MODEL, PORT (default 8000).

B2. AGENTS.md / CLAUDE.md

Project summary (3 lines above) + ownership table + rules:

Read docs/CONTRACTS.md and your tasks/<NAME>.md before coding.
Only edit files you own. Never touch another member's files.
Do one step at a time from your task file. Commit + push after every step.
Never commit .env, keys or tokens. Never print secrets.
Run the step's check command before committing.
Need a new dependency or contract change → ask Alif.
Stuck > 20 minutes → tell Alif immediately.
B3. Code stubs
requirements.txt: fastapi, uvicorn[standard], pydantic>=2, openai, scipy, numpy, requests, httpx, pytest, python-dotenv.
.gitignore: Python defaults, .venv/, __pycache__/, .env. .env.example: the 4 env var names, empty values.
app/schemas.py: pydantic v2 request models — 24 unique hours 0–23, finite non-negative numbers, 1–3 non-empty notes, minimum ≤ initial ≤ capacity.
app/main.py: /health; /optimize-energy → sort hours → interpret_notes → filter applies → optimize → response in exact key order; deterministic plan_summary (applied directive types + total cost); RequestValidationError and JSON decode errors → 400; global exception handler → 500; load .env via python-dotenv if present; __main__ runs uvicorn on 0.0.0.0:$PORT.
app/interpreter/core.py STUB: every note → {"note_index": i, "applies": false, "directive_type": "no_op", "structured_adjustment": null, "explanation": "stub"}.
app/optimizer/solver.py STUB: battery idle, solar_used = min(solar, demand), grid = demand − solar_used, E = initial, totals computed, status = "fallback".
app/optimizer/replay.py STUB: return [].
Dockerfile: python:3.11-slim, install requirements, copy app, EXPOSE 8000, CMD uvicorn --host 0.0.0.0 --port ${PORT:-8000} (shell form).
PART C — TASK FILES (write these verbatim into tasks/)

Every step in every task file uses this exact format:

### Step N — <title>   ⏱ <time box>
**Goal:** ...
**বাংলায়:** <one-line Bangla summary>
**Paste into Puku:**
    <English prompt>
**Check:**
    <commands + expected result>
**Commit:**
    git add <files> && git commit -m "<name>: step N <short>" && git push
**Done when:** ...

Times are relative to the hackathon start (0:00). Checkpoints: 0:50, 1:40, 2:30. Feature freeze: 2:45.

C1. tasks/HOW_TO_WORK.md

Content:

First time setup
bash
  git clone https://github.com/abdullahalyf/bup-hackathon-preli.git
  cd bup-hackathon-preli
  git checkout <your-name>              # alif / taseen / tamjid / jubayer
  python -m venv .venv
  source .venv/bin/activate             # Windows: .venv\Scripts\activate
  pip install -r requirements.txt
  cp .env.example .env                  # Alif will send the key privately
Run the app: uvicorn app.main:app --reload --port 8000 → open http://localhost:8000/health.
After every step: run the step's Check → git add only your files → commit → git push.
Get latest main (when Alif says): git pull origin main.
Never: edit someone else's file, commit .env, push to main, run git push --force.
Checkpoint report format (send to Alif at 0:50 / 1:40 / 2:30): Name | Current step | Done steps | Test result (paste) | Blocked?
Stuck > 20 min → send Alif the error + what you tried.
Every Puku session starts with: Read AGENTS.md, docs/CONTRACTS.md and tasks/<NAME>.md. I am on Step N. Only edit files I own.
Ownership table.
C2. tasks/TASEEN.md — Optimizer engineer

Mission: Build the math engine: given hours, battery, directives → valid, minimum-cost 24h plan. This part must be 100% correct. Files you own: app/optimizer/solver.py, app/optimizer/replay.py, tests/test_optimizer.py. Do not touch: everything else (including app/optimizer/__init__.py).

Technical spec (reference for all steps)

LP with scipy.optimize.linprog(method="highs"). 5 variables per hour: g, s, c, d, E (120 total).
Bounds: g ≥ 0; 0 ≤ s ≤ eff_solar[h]; 0 ≤ c ≤ max_charge (0 in no_charge hours); 0 ≤ d ≤ max_discharge (0 in no_discharge hours); min_h ≤ E ≤ capacity; g ≤ cap[h] in max_grid hours.
Equalities: g + s + d − c = demand[h]; E[h] − E[h−1] − c + d = 0 (E[−1] = initial); E[23] = initial.
Overlaps: solar factors multiply; reserve = max(base, all directives); grid cap = min(all).
Objective: Σ tariff[h]·g[h] + 1e−6·Σ(c[h] + d[h]).
Post-process: net = c − d; net > 1e−7 → charge, < −1e−7 → discharge, else idle with battery_kwh = 0; round to 6 decimals; recompute E cumulatively from rounded values; grid = demand + charge − discharge − solar_used (if negative, reduce solar_used); totals from final plan.
Infeasible: drop max_grid → reserve → no_discharge → no_charge, retry each (status="relaxed"); last resort stub logic (status="fallback"). Never raise.
Step 1 — Setup ⏱ 0:15–0:25

Goal: environment ready, stub app runs. বাংলায়: প্রজেক্ট চালু করে দেখো সব কাজ করছে কিনা। Paste into Puku: Read AGENTS.md, docs/CONTRACTS.md and tasks/TASEEN.md. Explain the optimizer spec to me in simple words. Do not write code yet. Check: pytest -q passes; uvicorn app.main:app --port 8000 + curl localhost:8000/health → {"status":"ok"}. Commit: nothing. Done when: you understand the LP spec.

Step 2 — Effective limits builder ⏱ 0:25–0:45

Goal: build_limits(hours, battery, directives) -> dict returning per-hour lists: eff_solar, min_energy, max_charge, max_discharge, max_grid (None = no cap). বাংলায়: directive গুলো থেকে প্রতি ঘণ্টার সীমা বের করার ফাংশন। Paste into Puku: Implement Step 2 of tasks/TASEEN.md in app/optimizer/solver.py (keep the existing optimize stub working). Add unit tests in tests/test_optimizer.py for each directive type and overlaps. Check: pytest tests/test_optimizer.py -q passes. Commit: git add app/optimizer/solver.py tests/test_optimizer.py && git commit -m "taseen: step 2 limits builder" && git push

Step 3 — LP solver ⏱ 0:45–1:20

Goal: real optimize() using the spec (LP + post-process + totals). বাংলায়: আসল LP দিয়ে সবচেয়ে কম খরচের প্ল্যান বানাও। Paste into Puku: Implement Step 3 of tasks/TASEEN.md: replace the optimize stub with the LP solver exactly as in the Technical spec. Add a test that runs all 10 cases from data/public_samples.json using expected_output.directive_interpretation entries with applies==true as directives and asserts abs(total_cost_bdt - expected_output.total_cost_bdt) <= 0.01. Check: pytest tests/test_optimizer.py -q → all 10 costs match. Commit + push. Tell Alif at checkpoint 1:40 → first merge.

Step 4 — Replay validator ⏱ 1:20–1:50

Goal: replay_check() independently verifies: 24 unique hours; finite non-negative values; action/battery_kwh consistency; transitions; bounds incl. reserve; rate limits; solar ≤ effective; energy balance; no_charge/no_discharge/max_grid; end neutrality; totals match plan (tol 0.01). বাংলায়: judge-এর মতো নিজেরাই প্ল্যান যাচাই করার কোড। Paste into Puku: Implement Step 4 of tasks/TASEEN.md in app/optimizer/replay.py. Add tests: all 10 samples return [], and hand-broken plans (bad balance, violated no_charge, wrong final energy, wrong totals) return violations. Check: pytest tests/test_optimizer.py -q passes. Commit + push.

Step 5 — Robustness ⏱ 1:50–2:30

Goal: infeasible handling + edge cases never crash: zero tariff, zero solar, huge solar, initial == capacity, minimum == initial, reserve above capacity, conflicting directives, solve time < 200 ms. বাংলায়: অদ্ভুত ইনপুটেও যেন crash না করে। Paste into Puku: Implement Step 5 of tasks/TASEEN.md: infeasible fallback chain and edge-case tests. optimize() must never raise and every returned plan must pass replay_check against the directives actually applied. Check: pytest tests/test_optimizer.py -q passes. Commit + push. Tell Alif → merge at 2:30.

Step 6 — After freeze ⏱ 2:45–3:15

Goal: run python scripts/run_samples.py <LIVE_URL> with Jubayer; fix only bugs in your files.

C3. tasks/TAMJID.md — LLM engineer

Mission: Turn English operator notes into correct structured directives, robust to paraphrasing. This is worth the most points (25 + affects 25 more). Files you own: app/interpreter/core.py, prompt.py, llm_client.py, normalize.py, fallback.py, tests/test_interpreter.py. Do not touch: everything else (including app/interpreter/__init__.py).

Technical spec (reference for all steps)

LLM raw output (JSON): {"notes":[{"note_index", "directive_type", "start_hour", "end_hour", "solar_remaining_fraction", "reserve_kwh", "reserve_percent_of_capacity", "max_grid_kwh", "explanation"}]}; unused fields null. LLM gives start/end; CODE builds the hours list and converts percent → kWh.
Time rules: end-exclusive; noon = 12; midnight as end = 24, as start = 0; "13:00" style; AM/PM from context (solar/panel work = daytime); wrap-around ("10 PM to 2 AM" → [0,1,22,23]).
Factor rule: "80% reduction" → 0.2; "drop to 20%" → 0.2; "one-fifth of normal" → 0.2; "half" → 0.5.
Relevance: no_op if the note does not change solar, battery, or grid limits for THIS 24h schedule (menus, events, next week/month).
Guardrails: allowed types only; each note_index exactly once; hours non-empty unique 0–23 ascending; factor ∈ [0,1]; 0 ≤ reserve ≤ capacity; max_grid finite ≥ 0.
Failure chain: LLM error/invalid note → retry once → fallback.py regex for that note → else no_op "Could not be interpreted safely". Never raise, never invent a type.
Step 1 — Setup + first LLM call ⏱ 0:15–0:30

বাংলায়: প্রজেক্ট চালু করো আর LLM key দিয়ে একটা টেস্ট কল করো। Paste into Puku: Read AGENTS.md, docs/CONTRACTS.md and tasks/TAMJID.md. Implement app/interpreter/llm_client.py: function call_llm(system: str, user: str) -> dict using the openai SDK with env LLM_API_KEY, LLM_BASE_URL (optional), LLM_MODEL; temperature 0; JSON mode; timeout 10s; 1 retry; never log the key. Add a __main__ block that sends a tiny test prompt and prints the parsed JSON. Check: python -m app.interpreter.llm_client prints valid JSON in < 3 s. Commit: git add app/interpreter/llm_client.py && git commit -m "tamjid: step 1 llm client" && git push

Step 2 — Prompt ⏱ 0:30–0:55

বাংলায়: LLM-এর জন্য নিয়ম আর উদাহরণসহ system prompt লেখো। Paste into Puku: Implement Step 2 of tasks/TAMJID.md in app/interpreter/prompt.py: SYSTEM_PROMPT and build_user_message(notes, capacity_kwh). Include all 6 types, time rules, factor rules, relevance rule, the raw output JSON schema, and 10 varied few-shot examples that are NOT copies of the public sample notes. Check: python -c "from app.interpreter.prompt import SYSTEM_PROMPT; print(len(SYSTEM_PROMPT))" works. Commit + push. Checkpoint 0:50: report to Alif.

Step 3 — Guardrails ⏱ 0:55–1:25

বাংলায়: LLM-এর উত্তর যাচাই আর ঠিক format-এ রূপান্তর। Paste into Puku: Implement Step 3 of tasks/TAMJID.md in app/interpreter/normalize.py: normalize(raw: dict, notes: list[str], capacity: float) -> (entries, bad_indexes). Build hours from start/end (wrap-around, 24), percent->kWh, all guardrails, final entry shape from docs/CONTRACTS.md. Unit tests with mocked raw outputs in tests/test_interpreter.py: wrap-around, midnight, percent->kWh, invalid factor, missing note, unknown type, duplicate index. Check: pytest tests/test_interpreter.py -q passes. Commit + push.

Step 4 — Wire it up ⏱ 1:25–1:50

বাংলায়: সব অংশ জোড়া লাগিয়ে আসল interpret_notes চালু করো। Paste into Puku: Implement Step 4 of tasks/TAMJID.md: replace the stub in app/interpreter/core.py. interpret_notes calls the LLM once for all notes, normalizes, retries once on failure, uses fallback.py (simple regex backup per note) and finally no_op. In-memory cache keyed by (tuple(notes), capacity). Never raise. Check: python scripts/run_samples.py (from Jubayer, or pull main) → 10/10 interpretation match; or a quick script over data/public_samples.json. Commit + push. Checkpoint 1:40 report.

Step 5 — Paraphrase hardening ⏱ 1:50–2:30

বাংলায়: অন্যভাবে লেখা নোট দিয়ে টেস্ট করে prompt উন্নত করো। Paste into Puku: Run python scripts/paraphrase_check.py. For each failure, improve SYSTEM_PROMPT rules/few-shots (never hard-code the exact test sentences). Repeat until accuracy >= 90%. Check: python scripts/paraphrase_check.py ≥ 90%, avg latency < 3 s. Commit + push. Tell Alif → merge at 2:30.

Step 6 — After freeze ⏱ 2:45–3:15

Bug fixes only in your files; check latency on the live URL.

C4. tasks/JUBAYER.md — DevOps + QA + Docs

Mission: Make it live, prove it works, document it. You own 20+ easy points (deployment, Docker, README). Files you own: scripts/*, tests/test_api.py, data/paraphrases.json, Dockerfile, .dockerignore, README.md, docs/VIDEO_SCRIPT.md. Do not touch: everything else.

Step 1 — Setup + Docker ⏱ 0:15–0:30

বাংলায়: Docker দিয়ে লোকালে অ্যাপ চালাও। Paste into Puku: Read AGENTS.md, docs/CONTRACTS.md and tasks/JUBAYER.md. Make the Dockerfile production-ready (python:3.11-slim, no secrets, EXPOSE 8000, host 0.0.0.0, port ${PORT:-8000}) and a good .dockerignore (.env, .venv, .git, __pycache__, tests cache). Check: docker build -t gridwise . && docker run -p 8000:8000 gridwise → curl localhost:8000/health ok. Commit + push.

Step 2 — Deploy (MOST URGENT) ⏱ 0:30–0:50

বাংলায়: ইন্টারনেটে deploy করে public URL বানাও। Actions: Railway (or Render) → New Project → Deploy from GitHub → this repo, branch main → set env vars LLM_API_KEY, LLM_MODEL (and LLM_BASE_URL if needed; Alif gives values privately) → generate public domain. Check: from your phone/another network: curl https://<url>/health → {"status":"ok"}. Send URL to Alif at checkpoint 0:50. Auto-deploy from main must be ON.

Step 3 — Sample runner ⏱ 0:50–1:15

বাংলায়: ১০টা sample পাঠিয়ে ফলাফল মিলানোর স্ক্রিপ্ট। Paste into Puku: Implement scripts/run_samples.py: for each case in data/public_samples.json POST case["input"] to BASE_URL (CLI arg, else env BASE_URL, else http://localhost:8000). Print per case: id, HTTP status, latency, interpretation match per note (applies, directive_type, structured_adjustment with 0.01 tolerance) vs expected_output.directive_interpretation, cost diff vs expected_output.total_cost_bdt, and violations from app.optimizer.replay.replay_check(input hours, battery, applied expected directives, response). Print summary incl. p95 latency. Exit 1 on any failure. Check: python scripts/run_samples.py runs (stub results will fail — that's expected now). Commit + push.

Step 4 — Paraphrase test set ⏱ 1:15–1:45

বাংলায়: judge-এর মতো ৪০টা ঘুরিয়ে লেখা নোট বানাও। Paste into Puku: Create data/paraphrases.json: 40 hand-written varied operator notes, each {"note", "capacity_kwh", "expected": {"applies", "directive_type", "structured_adjustment"}}. Cover all 6 types (~7 each + 8 no_op). Include 24h times ("13:00"), word times ("one until three"), noon/midnight, wrap-around, "% reduction" vs "drop to %", fractions ("one-fifth", "a quarter"), "% of capacity" reserves, grid limits in different words (import, intake, feeder, transformer), and tricky distractors mentioning solar/battery but about next week or unrelated. Follow docs/CONTRACTS.md rules exactly (end-exclusive hours, factor = remaining fraction). Then implement scripts/paraphrase_check.py: call app.interpreter.interpret_notes([note], {"capacity_kwh": capacity, ...}) per item, compare with 0.01 tolerance, print accuracy, avg latency, and each failure (note, expected, got). Check: python scripts/paraphrase_check.py runs. Send file to Tamjid (push + tell him). Commit + push. Checkpoint 1:40 report.

Step 5 — API tests ⏱ 1:45–2:05

Paste into Puku: Implement tests/test_api.py with FastAPI TestClient: /health 200 {"status":"ok"}; invalid JSON -> 400; 23 hours -> 400; 0 notes -> 400; 4 notes -> 400; duplicate hour -> 400; valid sample -> 200 with exactly the 7 response keys, 24 plan entries, entries in note_index order. Check: pytest tests/test_api.py -q passes. Commit + push.

Step 6 — README ⏱ 2:05–2:45

বাংলায়: ১০ নম্বরের README লেখো। Paste into Puku: Write README.md: overview; architecture diagram (text) LLM -> guardrails -> LP optimizer -> replay validator; model/provider; LLM role; guardrails list; optimizer (scipy HiGHS LP) formulation summary; env var names (no values); clean local quickstart (clone, venv, install, .env, run); curl for /health and /optimize-energy; public-sample test command + expected result; pytest command; Docker pull/run with exact image tag placeholder; project structure + team ownership; dependencies & credits (FastAPI, scipy, openai SDK, AI assistants used); known limitations; secret handling. Commit + push.

Step 7 — After freeze: live test + Docker push ⏱ 2:45–3:15
python scripts/run_samples.py https://<live-url> → all pass, p95 < 5 s. Report to Alif.
docker build -t <dockerhub-user>/gridwise:v1 . && docker push <dockerhub-user>/gridwise:v1; test docker pull + docker run -p 8000:8000 -e LLM_API_KEY=... -e LLM_MODEL=... <image> → /health ok. Put the exact tag in README.
Step 8 — Video ⏱ 3:15–3:45

Paste into Puku: Write docs/VIDEO_SCRIPT.md: a 3-minute script (problem 30s, architecture 60s, LLM->guardrails->optimizer demo 60s, how to run/test 30s). Record screen + voice, max 3:00, upload, give link to Alif.

C5. tasks/ALIF.md — Head

Mission: Keep everyone unblocked, keep main always running, merge, submit.

Step 1 — Bootstrap ⏱ 0:00–0:15
Run this Codex prompt; verify acceptance checks (Part D).
Push main, create branches alif taseen tamjid jubayer, add collaborators (Settings → Collaborators).
Send each member: repo link + "read tasks/HOW_TO_WORK.md then tasks/<NAME>.md".
Send LLM key privately (never in git/chat group screenshots).
Step 2 — API hardening ⏱ 0:15–0:50
Check app/main.py against docs/CONTRACTS.md: 400 cases, 500 handler, exact key order, scenario_id echo, only applies==true passed to optimizer.
Add timing log per request (no secrets). Ensure total request timeout safety (< 30 s).
Checkpoint 0:50: collect reports; confirm Jubayer's live URL.
Step 3 — Merges ⏱ 1:40 and 2:30
GitHub → Pull request <branch> → main. Order: Taseen → Tamjid → Jubayer.
After each merge: git pull origin main && pytest -q && python scripts/run_samples.py.
Tell everyone: git pull origin main.
Paste any failure to Claude for root-cause + fix prompt.
Step 4 — Freeze & verify ⏱ 2:45–3:15
No new features. python scripts/run_samples.py <LIVE_URL> all green, p95 < 5 s.
Check: /health from outside, no .env in git history (git log --all -- .env empty).
Step 5 — Submit ⏱ 3:45–4:00

Checklist: live base URL · GitHub repo link (public after deadline) · Docker image exact tag · README complete · video link ≤ 3:00 · env var names documented · no secrets anywhere.

PART D — ACCEPTANCE CRITERIA (Codex must run and show results)
bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000 &
sleep 3
curl -s localhost:8000/health                                   # {"status":"ok"}
python -c "import json,requests;c=json.load(open('data/public_samples.json'))['cases'][0]['input'];r=requests.post('http://localhost:8000/optimize-energy',json=c);print(r.status_code,list(r.json().keys()))"
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8000/optimize-energy -H 'Content-Type: application/json' -d '{bad'   # 400
pytest -q                                                        # all pass
ls tasks/                                                        # HOW_TO_WORK.md ALIF.md TASEEN.md TAMJID.md JUBAYER.md

(Docker check optional if Docker is not installed locally.)

PART E — FINAL GIT STEP
bash
git add . && git commit -m "setup: skeleton, contracts, step-by-step team tasks" && git push origin main
for b in alif taseen tamjid jubayer; do git branch $b && git push -u origin $b; done
OUTPUT

File tree, acceptance-check results, and a 5-line message Alif can send to the team.