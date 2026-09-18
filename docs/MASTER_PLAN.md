# GridWise — মাস্টার প্ল্যান (BUP CSE Fest 2026 Preliminary)

> **কীভাবে ব্যবহার করবে:** এই ফাইলটা repo-তে `docs/MASTER_PLAN.md` নামে রাখো। প্রতিটা কাজ একটা **Work Unit (WU)**। প্রতিটার পাশে একজন **প্রস্তাবিত মালিক** দেওয়া আছে, কিন্তু সেটা **fixed না**। যার হাত খালি, সে পরের unlocked WU নিতে পারবে, শুধু গ্রুপে জানিয়ে দেবে। সব prompt ইংরেজিতে, সরাসরি Codex বা Puku-তে পেস্ট করার জন্য।

---

## ০. এক নজরে

| বিষয় | সিদ্ধান্ত |
|---|---|
| কী বানাচ্ছি | Public API: `GET /health`, `POST /optimize-energy` |
| Pipeline | LLM → Guardrails → LP Optimizer → Replay check → JSON |
| Stack | Python 3.11, FastAPI, Pydantic v2, scipy HiGHS, openai SDK, pytest, Docker |
| LLM | **Gemini** (মূল, ফ্রি) + **Groq** (ব্যাকআপ, ফ্রি), দুটোই OpenAI-compatible |
| Deploy | Railway (Dockerfile থেকে, main-এ push করলে auto-deploy) |
| Repo | github.com/abdullahalyf/bup-hackathon-preli |
| Branches | `main` (merge করবে শুধু Alif), `alif`, `taseen`, `tamjid`, `jubayer` |
| নম্বর | LLM 25 · Application 25 · Optimization 10 · Schema 10 · Performance 10 · Deploy 10 · README 10 |

**প্রস্তাবিত রোল:** Alif = Head / API / Deploy · Taseen = Optimizer · Tamjid = LLM · Jubayer = QA + Frontend + Docs

---

## ১. কাজ ভাগের নিয়ম (সবাই মানবে)

1. **এক ফাইলে একসাথে একজন।** কেউ কোনো WU নিলে সেই WU-র ফাইলগুলো তার "lock"-এ থাকে। গ্রুপে লিখবে: `🔒 WU-LLM-3 নিলাম — <নাম>`, শেষ হলে: `✅ WU-LLM-3 done`।
2. **নিজের branch-এ কাজ,** প্রতিটা WU শেষে commit + push। `main`-এ push করবে শুধু Alif।
3. **Dependency আগে।** "Needs" কলামের WU শেষ না হলে সেই WU শুরু করা যাবে না।
4. **২০ মিনিটের নিয়ম।** কোথাও ২০ মিনিট আটকে থাকলে `BLOCKED` লিখে Alif-কে জানাবে, তারপর পরের WU ধরবে।
5. **2:45-এর পর কোনো নতুন feature না,** শুধু bug fix।
6. **Key বা `.env` কখনো git-এ যাবে না।**

---

## ২. Stage ও সময়সূচি (শুরু = 0:00)

| Stage | সময় | লক্ষ্য | শেষে যা থাকবে |
|---|---|---|---|
| **S0 Setup** | 0:00–0:20 | Repo, key, env | সবাই লোকালে `/health` চালাতে পারছে |
| **S1 Foundation** | 0:20–0:50 | প্রতিটা অংশের ভিত্তি + **live deploy** | Live URL, LLM call চলছে, sample runner তৈরি |
| **S2 Core build** | 0:50–1:40 | আসল optimizer + interpreter | ১০টা sample-এর cost মিলছে, interpreter চলছে |
| 🔀 **Checkpoint 1** | 1:40 | Integration #1 | main-এ পুরো pipeline চলছে |
| **S3 Hardening** | 1:40–2:30 | Paraphrase, robustness, frontend | Paraphrase ≥ 90%, crash নেই |
| 🔀 **Checkpoint 2** | 2:30 | Integration #2 | সব কিছু main-এ |
| 🧊 **S4 Freeze & Verify** | 2:45–3:15 | Live URL-এ টেস্ট, fix, Docker push | ১০/১০ live-এ পাস, p95 < 5s |
| **S5 Docs & Video** | 3:15–3:40 | README, ভিডিও | README সম্পূর্ণ, ভিডিও ≤ ৩ মিনিট |
| **S6 Submit** | 3:40–4:00 | জমা | সব লিংক জমা হয়ে গেছে |

---

## ৩. Work Unit বোর্ড

> মালিক = প্রস্তাবিত (বদলানো যাবে)। Files = ওই WU-র lock।

### S0 — Setup

| ID | কাজ | প্রস্তাবিত মালিক | Needs | Files | Done যখন |
|---|---|---|---|---|---|
| WU-0.1 | Repo bootstrap (skeleton, tasks, branches, invites) | Alif (Codex) | — | সব | ✅ হয়ে গেছে / চলছে |
| WU-0.2 | Gemini + Groq ফ্রি key নেওয়া (**মানুষের কাজ**) | Alif | — | — | দুটো key ব্যক্তিগতভাবে পাঠানো হয়েছে |
| WU-0.3 | লোকাল env setup | সবাই | 0.1 | `.env` (local) | লোকালে `/health` ok |

### S1 — Foundation

| ID | কাজ | প্রস্তাবিত মালিক | Needs | Files | Done যখন |
|---|---|---|---|---|---|
| WU-DEP-1 | CORS + `/` route + Docker local + **Railway deploy** | Alif | 0.2 | `app/main.py`, `Dockerfile`, `.dockerignore`, `.env.example`, `AGENTS.md` | Live `/health` ok |
| WU-OPT-1 | Effective limits builder | Taseen | 0.3 | `app/optimizer/solver.py`, `tests/test_optimizer.py` | unit test পাস |
| WU-LLM-1 | LLM client + model বাছাই + Groq fallback | Tamjid | 0.2 | `app/interpreter/llm_client.py` | JSON test call < 3s |
| WU-QA-1 | `scripts/run_samples.py` | Jubayer | 0.3 | `scripts/run_samples.py` | stub-এর বিরুদ্ধে চলছে |

### S2 — Core build

| ID | কাজ | প্রস্তাবিত মালিক | Needs | Files | Done যখন |
|---|---|---|---|---|---|
| WU-OPT-2 | LP solver (HiGHS) | Taseen | OPT-1 | `solver.py`, `test_optimizer.py` | ১০/১০ cost মিলছে (±0.01) |
| WU-LLM-2 | System prompt + few-shot | Tamjid | LLM-1 | `app/interpreter/prompt.py` | import হচ্ছে, নিয়ম সম্পূর্ণ |
| WU-LLM-3 | Guardrails / normalize | Tamjid **বা Taseen** (OPT-2 শেষ হলে) | — | `normalize.py`, `tests/test_interpreter.py` | unit test পাস |
| WU-LLM-4 | `interpret_notes` wiring + cache + fallback | Tamjid | LLM-1,2,3 | `core.py`, `fallback.py` | public sample ১০/১০ interpretation |
| WU-QA-2 | ৪০টা paraphrase + checker | Jubayer | — | `data/paraphrases.json`, `scripts/paraphrase_check.py` | ফাইল push হয়েছে → "PARAPHRASES READY" |
| WU-API-1 | main.py hardening (timing log, error path) | Alif | DEP-1 | `app/main.py`, `app/schemas.py` | test_api পাস |

### 🔀 Checkpoint 1 (1:40) → **PROMPT C1**

### S3 — Hardening

| ID | কাজ | প্রস্তাবিত মালিক | Needs | Files | Done যখন |
|---|---|---|---|---|---|
| WU-OPT-3 | Replay validator | Taseen | OPT-2 | `app/optimizer/replay.py` | sample → `[]`, ভাঙা plan → violation |
| WU-OPT-4 | Infeasible fallback + edge case | Taseen | OPT-2 | `solver.py`, `test_optimizer.py` | কখনো crash করে না |
| WU-LLM-5 | Paraphrase hardening | Tamjid (+ Taseen সাহায্য) | LLM-4, QA-2 | `prompt.py`, `normalize.py` | accuracy ≥ 90%, latency < 3s |
| WU-QA-3 | `tests/test_api.py` | Jubayer | — | `tests/test_api.py` | পাস |
| WU-FE-1 | Frontend (এক ফাইল, শুধু ভিডিওর জন্য) | Jubayer | QA-2 | `frontend/index.html` | লোকালে দেখা যাচ্ছে |

### 🔀 Checkpoint 2 (2:30) → **PROMPT C1** (আবার)

### S4–S6 — Freeze, Docs, Submit

| ID | কাজ | প্রস্তাবিত মালিক | Needs | Files | Done যখন |
|---|---|---|---|---|---|
| WU-VER-1 | Live full test + p95 | Alif | CP2 | — | ১০/১০, p95 < 5s |
| WU-FIX-* | Bug fix (যা আসবে) | যার ফাইল | VER-1 | নির্দিষ্ট ফাইল | test সবুজ |
| WU-DEP-2 | Docker Hub push + pull টেস্ট | Alif | CP2 | — | exact tag |
| WU-DOC-1 | README (১০ নম্বর) | Jubayer | CP2 | `README.md` | quickstart কাজ করছে |
| WU-DOC-2 | ভিডিও স্ক্রিপ্ট + রেকর্ড | Jubayer + Alif | DOC-1 | `docs/VIDEO_SCRIPT.md` | ≤ 3:00 ভিডিও |
| WU-SUB-1 | Submit + deadline-এর পরে repo public | Alif | সব | — | জমা হয়ে গেছে |

---

## ৪. Skills ব্যবহারের নিয়ম

Codex আর Puku-তে যদি skills ইনস্টল করা থাকে (যেমন superpowers প্লাগইন), তাহলে এগুলো ব্যবহার করবে:

| কখন | Skill | কেন |
|---|---|---|
| যেকোনো session-এর শুরুতে | `using-superpowers` | কোন skill কখন লাগবে সেটা ঠিক করতে |
| কোড লেখার আগে | `test-driven-development` | acceptance test আগে, তারপর কোড |
| যেকোনো bug বা fail হলে | `systematic-debugging` | আগে root cause, তারপর fix |
| "done" বলার আগে | `verification-before-completion` | command চালিয়ে প্রমাণ দেখাতে হবে |
| merge-এর আগে | `requesting-code-review` | contract মিলছে কিনা যাচাই |
| review feedback পেলে | `receiving-code-review` | অন্ধভাবে না মেনে যাচাই করে নেওয়া |
| একাধিক আলাদা bug একসাথে | `parallel-agent` / `subagent-driven-development` | সমান্তরালে ঠিক করা |
| Branch শেষ করার সময় | `finishing-a-development-branch` | পরিষ্কারভাবে push |
| Frontend | `frontend-design` (থাকলে) | সুন্দর UI |

**⚠️ বাদ দেবে:** `brainstorming` আর `writing-plans`। প্ল্যান এই ফাইলেই আছে, ওগুলো চালালে শুধু সময় নষ্ট হবে।

---

## ৫. সব prompt-এর আগে এই HEADER বসাবে

```
ROLE: Coding agent for a 4-hour hackathon (GridWise). Repo: github.com/abdullahalyf/bup-hackathon-preli. My branch: <BRANCH>.

SKILLS: First check which skills you have (plugin/skills folders). Use these when present; if a skill is missing, follow its principle anyway:
- using-superpowers at start
- test-driven-development: write the acceptance test first, then code
- systematic-debugging for any failure (root cause before fix)
- verification-before-completion: never say "done" without showing the command output
- requesting-code-review before I push work meant for merge
Do NOT run brainstorming or writing-plans — the plan is fixed in docs/MASTER_PLAN.md. Speed matters.

CONTEXT: Read AGENTS.md, docs/CONTRACTS.md and docs/MASTER_PLAN.md (only the WU I'm doing).
RULES: Only edit the files listed for my WU. Never push main, never force-push, never commit .env/keys. Commit + push to my branch when the WU's Done check passes. Stuck 3 attempts → print "BLOCKED: <WU> <error>" and stop.
SETUP (if needed): git fetch origin ; git checkout <BRANCH> ; git pull origin <BRANCH> ; git pull origin main ; python -m venv .venv ; activate ; pip install -r requirements.txt
OUTPUT at end: "WU-<id> DONE | files | check output (≤5 lines)".
```

---

## ৬. প্রতিটা WU-এর prompt (HEADER-এর পরে পেস্ট করবে)

### WU-DEP-1 — Deploy (Codex, Alif)
```
TASK WU-DEP-1: Ownership update + deploy. I am Alif (owner, I may push main).
1. git checkout main ; git pull.
2. AGENTS.md + CLAUDE.md: Dockerfile, .dockerignore, deployment -> Alif; frontend/ -> Jubayer. .env.example: add LLM_FALLBACK_API_KEY, LLM_FALLBACK_BASE_URL, LLM_FALLBACK_MODEL (names only).
3. app/main.py: CORSMiddleware (all origins, GET/POST); serve frontend/index.html at GET / if it exists. Don't change /health or /optimize-energy. pytest -q. Commit + push main.
4. Ask me once for Gemini + Groq keys if my local .env lacks them (never print/commit).
5. docker build -t gridwise . ; docker run -d -p 8000:8000 --env-file .env gridwise ; curl localhost:8000/health
6. Railway from GitHub repo, branch main, Dockerfile, auto-deploy ON, set all LLM_* vars. Use railway CLI if logged in; otherwise print a short click-by-click guide and wait for my URL.
7. Verify live: GET /health, POST data/public_samples.json cases[0].input; print status + latency.
8. Print: LIVE URL.
```

### WU-OPT-1 — Limits builder
```
TASK WU-OPT-1: In app/optimizer/solver.py implement build_limits(hours, battery, directives) -> dict of 24-length lists: eff_solar, min_energy, max_charge, max_discharge, max_grid (None = no cap). Rules: solar factors multiply on overlap; reserve = max(base minimum, directives); grid cap = min; no_charge -> max_charge 0; no_discharge -> max_discharge 0; no_op ignored. Keep the existing optimize() stub working. Tests in tests/test_optimizer.py for each directive type and overlaps.
Done check: pytest tests/test_optimizer.py -q
```

### WU-OPT-2 — LP solver
```
TASK WU-OPT-2: Replace the optimize() stub in app/optimizer/solver.py with an LP using scipy.optimize.linprog(method="highs"), exactly per the Technical spec in tasks/TASEEN.md (5 vars/hour g,s,c,d,E; balance; SOC transitions; E[23]=initial; bounds from build_limits; objective sum(tariff*g)+1e-6*sum(c+d); post-process net action, 6-decimal rounding, recompute E and grid, totals from final plan). Test: all 10 cases in data/public_samples.json using expected_output.directive_interpretation entries with applies==true; assert |total_cost_bdt - expected| <= 0.01.
Done check: pytest tests/test_optimizer.py -q  (10/10 costs match)
```

### WU-OPT-3 — Replay validator
```
TASK WU-OPT-3: Implement replay_check(hours, battery, directives, response) -> list[str] in app/optimizer/replay.py, tolerance 0.01: 24 unique hours; finite non-negative; action/battery_kwh consistency (idle => 0); SOC transitions; bounds incl. reserve directives; rate limits; solar_used <= effective solar; energy balance; no_charge/no_discharge/max_grid; E[23]==initial; totals and peak match plan. Tests: 10 samples -> []; hand-broken plans -> violations.
Done check: pytest tests/test_optimizer.py -q
```

### WU-OPT-4 — Robustness
```
TASK WU-OPT-4: optimize() must never raise. On infeasible: retry dropping max_grid -> reserve -> no_discharge -> no_charge (status "relaxed"); last resort idle-battery plan (status "fallback"). Edge-case tests: zero tariff, zero solar, solar > demand all day, initial==capacity, minimum==initial, reserve > capacity, conflicting directives. Every returned plan passes replay_check for the directives actually applied. Each solve < 200 ms.
Done check: pytest tests/test_optimizer.py -q
```

### WU-LLM-1 — LLM client
```
TASK WU-LLM-1: app/interpreter/llm_client.py: call_llm(system, user) -> dict. Primary: LLM_API_KEY, LLM_BASE_URL (Gemini OpenAI-compatible: https://generativelanguage.googleapis.com/v1beta/openai/), LLM_MODEL. Fallback: LLM_FALLBACK_API_KEY, LLM_FALLBACK_BASE_URL (Groq: https://api.groq.com/openai/v1), LLM_FALLBACK_MODEL. Ask me once for both keys -> local .env only.
- For each provider call GET {base}/models; pick a fast non-reasoning model (Gemini flash / flash-lite; Groq llama 70B-class). Test a JSON call on each, pick ones < 3 s; write to .env; report names.
- temperature 0, JSON mode, timeout 8 s; primary -> on error/timeout/429 -> fallback. Disable thinking/reasoning if supported. Never log keys. Parse JSON robustly (strip ``` fences).
- __main__ block runs a tiny test.
Done check: python -m app.interpreter.llm_client prints valid JSON in < 3 s.
```

### WU-LLM-2 — Prompt
```
TASK WU-LLM-2: app/interpreter/prompt.py: SYSTEM_PROMPT and build_user_message(notes, capacity_kwh). LLM must return {"notes":[{note_index, directive_type, start_hour, end_hour, solar_remaining_fraction, reserve_kwh, reserve_percent_of_capacity, max_grid_kwh, explanation}]} (unused = null). Include: 6 types with meaning; time rules (end-exclusive, noon=12, midnight end=24, "13:00", AM/PM from context — solar/panel work is daytime, wrap-around); factor = fraction REMAINING ("80% reduction"->0.2, "drop to 20%"->0.2, "one-fifth"->0.2, "half"->0.5, "a quarter of normal"->0.25); relevance rule (no_op unless it changes solar/battery/grid for THIS 24h schedule; next week/month or unrelated -> no_op); 10 varied few-shot examples NOT copied from public samples. Never hard-code test sentences.
Done check: python -c "from app.interpreter.prompt import SYSTEM_PROMPT,build_user_message;print(len(SYSTEM_PROMPT))"
```

### WU-LLM-3 — Guardrails
```
TASK WU-LLM-3: app/interpreter/normalize.py: normalize(raw, notes, capacity) -> (entries, bad_indexes). start/end -> hours (end-exclusive, 24 = midnight, wrap-around), sorted unique 0-23 non-empty; reserve percent -> kWh; checks: allowed type, each note_index exactly once, factor in [0,1], 0 <= reserve <= capacity, max_grid finite >= 0; build final entries exactly per docs/CONTRACTS.md (no_op: applies false + null; others applies true). Unit tests with mocked raw outputs in tests/test_interpreter.py: wrap-around, midnight, percent->kWh, bad factor, missing/duplicate index, unknown type.
Done check: pytest tests/test_interpreter.py -q
```

### WU-LLM-4 — Wiring
```
TASK WU-LLM-4: Replace stub in app/interpreter/core.py: interpret_notes(notes, battery) -> one LLM call for all notes -> normalize -> retry once for bad notes -> fallback.py (simple regex backup per note) -> else no_op "Could not be interpreted safely". In-memory cache keyed by (tuple(notes), capacity). Never raise, never invent types, always len(notes) entries in order.
Done check: python scripts/run_samples.py (or a /tmp script over data/public_samples.json) -> 10/10 interpretation match.
```

### WU-LLM-5 — Paraphrase hardening
```
TASK WU-LLM-5: Run python scripts/paraphrase_check.py. Group failures by cause (time parsing, factor, relevance, type confusion). Fix with general rules/few-shots in prompt.py or deterministic normalization in normalize.py — never paste the test sentences. Re-run until accuracy >= 90% and avg latency < 3 s. Also re-run run_samples to confirm no regression.
Done check: paraphrase_check >= 90% AND run_samples interpretation 10/10.
```

### WU-QA-1 — Sample runner
```
TASK WU-QA-1: scripts/run_samples.py: POST every case["input"] from data/public_samples.json to BASE_URL (argv[1] or env BASE_URL or http://localhost:8000). Per case print: id, HTTP status, latency, per-note match (applies, directive_type, structured_adjustment, 0.01 tol) vs expected_output.directive_interpretation, cost diff vs expected_output.total_cost_bdt, violations from app.optimizer.replay.replay_check(input hours, battery, expected applied directives, response). Summary: passed/10, p95 latency. Exit 1 on any failure.
Done check: python scripts/run_samples.py runs to the end.
```

### WU-QA-2 — Paraphrase set
```
TASK WU-QA-2: data/paraphrases.json: 40 varied notes, each {"note","capacity_kwh","expected":{"applies","directive_type","structured_adjustment"}}; ~7 per directive type + 8 no_op. Include 24h times, word times ("one until three"), noon/midnight, wrap-around, "% reduction" vs "drop to %", fractions ("one-fifth", "a quarter"), "% of capacity", grid-limit synonyms (import, intake, feeder, transformer, substation), charger/relay/inverter wording, and tricky distractors (solar/battery mentioned but next week, or purely informational). Follow docs/CONTRACTS.md exactly. scripts/paraphrase_check.py: run app.interpreter.interpret_notes([note], battery-with-capacity) per item, compare (0.01 tol), print accuracy, avg latency, each failure. Push, then print "PARAPHRASES READY".
Done check: python scripts/paraphrase_check.py runs.
```

### WU-QA-3 — API tests
```
TASK WU-QA-3: tests/test_api.py (FastAPI TestClient): /health 200 {"status":"ok"}; invalid JSON -> 400; 23 hours -> 400; duplicate hour -> 400; 0 notes -> 400; 4 notes -> 400; valid sample -> 200 with exactly 7 keys, 24 plan entries, interpretation entries in note_index order, scenario_id echoed.
Done check: pytest tests/test_api.py -q
```

### WU-FE-1 — Frontend
```
TASK WU-FE-1 (time box 40 min): frontend/index.html — one file, vanilla HTML/CSS/JS, Chart.js from https://cdnjs.cloudflare.com, no build step. Use the frontend-design skill if available.
- Load buttons for 3 embedded sample inputs (copied from data/public_samples.json).
- Editable notes + JSON textarea; "Optimize" POSTs to /optimize-energy (same origin; optional API URL field).
- Show interpretation table, totals cards (cost, total grid, peak), hourly plan table, chart (grid / solar used / battery bars + battery energy line + tariff line).
- Clean dark professional UI, responsive, friendly errors.
Done check: open http://localhost:8000/ (or the file directly with API URL) and run a sample successfully.
```

### WU-API-1 — API hardening
```
TASK WU-API-1: app/main.py + app/schemas.py: verify against docs/CONTRACTS.md — 400 for malformed/structural errors, 500 generic handler (no traces), exact response key order, scenario_id echo, only applies==true passed to optimize. Add per-request timing log (no secrets). Guard total time: if interpretation fails/times out, still return 200 with safe no_op entries rather than 5xx. Run pytest -q.
Done check: pytest -q passes.
```

### WU-DOC-1 — README
```
TASK WU-DOC-1: README.md (worth 10 points): overview; architecture (LLM -> guardrails -> LP optimizer -> replay validator) with a text diagram; model/provider (Gemini primary, Groq fallback, model names); LLM role; guardrails list; optimizer formulation summary (scipy HiGHS LP); env var NAMES only; clean quickstart (clone, venv, pip install, cp .env.example .env, run uvicorn); curl /health and /optimize-energy; public-sample test command + expected result; pytest; Docker pull/run with <IMAGE_TAG>; live URL <LIVE_URL>; project structure + team; dependencies & credits (incl. AI assistants); known limitations; secret handling.
Done check: follow the quickstart in a fresh folder and it works.
```

### WU-DOC-2 — Video script
```
TASK WU-DOC-2: docs/VIDEO_SCRIPT.md — 3:00 max: problem (30s), architecture diagram (45s), live demo via frontend: notes -> interpretation -> plan chart (60s), guardrails + replay validation (25s), how to run/test (20s). Include exact on-screen actions per segment.
```

---

## ৭. Checkpoint prompt (Alif, Codex-এ দেবে)

### PROMPT C1 — Integration (1:40 আর 2:30-এ)
```
TASK C1 FAST INTEGRATION (I am Alif; you may push main). Use skills: requesting-code-review, systematic-debugging, verification-before-completion.
1. git checkout main ; git pull origin main ; git fetch --all
2. Merge in order origin/taseen, origin/tamjid, origin/jubayer, origin/alif (skip if nothing new). Conflicts: AGENTS.md ownership decides. If a merge stops the app from starting, undo only that merge.
3. Quick review: do module signatures still match docs/CONTRACTS.md? Report mismatches.
4. Run: pytest -q ; python scripts/run_samples.py
5. git push origin main (Railway auto-deploys). Wait ~60 s. Run: python scripts/run_samples.py <LIVE_URL>
6. Print ONE table: branch | merged | pytest | samples /10 | cost mismatches | interpretation mismatches | p95 | live ok. Then only failing lines (max 30).
```

### PROMPT C2 — Parallel bug fix (fail হলে)
```
TASK C2: Here are failures from integration: <PASTE>. Use systematic-debugging to find the root cause of each. If failures are independent, use parallel-agent/subagent-driven-development. Fix only the minimal code, add a regression test for each, run pytest -q and scripts/run_samples.py, verification-before-completion, then commit to main and push. Report root cause + fix per failure in one line each.
```

### PROMPT C3 — Final verification (2:45-এর পরে)
```
TASK C3 FINAL VERIFY. Use verification-before-completion.
1. python scripts/run_samples.py <LIVE_URL> twice; report pass count and p95 (must be < 5 s).
2. curl -X POST malformed JSON to live -> expect 400.
3. git ls-files | grep -E '(^|/)\.env$' must be empty; grep the repo for anything that looks like an API key.
4. Docker: build, tag <dockerhub-user>/gridwise:v1, push; then docker rmi + docker pull + docker run -p 8000:8000 --env-file .env and curl /health. Print exact image tag.
5. Put LIVE_URL and IMAGE_TAG into README placeholders. Commit + push.
6. Print the submission checklist with ✅/❌.
```

---

## ৮. পিছিয়ে পড়লে কী কাটবে (এই ক্রমে)

1. Frontend (ভিডিওতে API response দেখালেই চলবে)
2. `fallback.py` regex (ব্যর্থ হলে সরাসরি no_op)
3. WU-OPT-4-এর edge-case test (শুধু crash না করাটা নিশ্চিত রাখো)
4. Paraphrase ৪০ থেকে ২০-এ নামানো

**কখনো কাটবে না:** Deploy, `/health`, সঠিক schema, LP optimizer, LLM interpretation, README, Docker image।

---

## ৯. জরুরি সমস্যা হলে

| সমস্যা | সমাধান |
|---|---|
| Gemini 429 / quota শেষ | Groq fallback আপনা-আপনি চলবে। দুটোই শেষ হলে আরেকজনের Google account দিয়ে নতুন key নাও |
| Latency > 5s | ছোট model (flash-lite), thinking বন্ধ, cache, সব note একটা call-এ |
| LP infeasible | Replay output দেখো → সাধারণত hours ভুল বা reserve > capacity (LLM ভুল) |
| Railway fail | Render → New Web Service → Docker → env vars বসাও |
| Merge conflict | AGENTS.md-এর ownership অনুযায়ী মালিকের version রাখো |
| কেউ BLOCKED | Error Claude-কে দাও → fix prompt |

---

## ১০. Submission checklist

- [ ] Live base URL (`/health` আর `/optimize-energy` বাইরে থেকে চলছে)
- [ ] GitHub repo লিংক (**deadline-এর পরে public করবে**)
- [ ] Docker image-এর exact tag, pull + run কাজ করছে
- [ ] README: quickstart, env var, model, architecture, curl, sample test, Docker, limitations
- [ ] ৩ মিনিটের ভিডিও লিংক (সবাই দেখতে পারে)
- [ ] কোথাও কোনো secret নেই

---

## ১১. Checkpoint status বোর্ড (গ্রুপে এই ফরম্যাটে)

```
⏱ Time left: __ | Stage: S_
✅ Done: WU-...
🔨 In progress: WU-... (<name>)
⛔ Blocked: ...
➡️ Next: Alif: __ | Taseen: __ | Tamjid: __ | Jubayer: __
✂️ Cut?: ...
```
