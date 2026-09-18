# GridWise verification checklist

Legend: `[x]` verified pass · `[!]` partial / risk · `[ ]` not yet verified
Owner shortcut: A=Alif · T=Taseen · M=Tamjid · J=Jubayer

Run date: 2026-09-18 20:22 (local). All results were captured on branch
`alif` (HEAD `3379393`) with `origin/main` at `b493859`. See `docs/STATUS.md`
for the human handoff.

---

## 1. API contract & schema

| Item | Status | Command to verify | Current result |
| --- | --- | --- | --- |
| `GET /health` returns 200 + `{"status":"ok"}` | `[x]` | `curl -s -w '\n%{http_code}' http://localhost:8000/health` (or live URL) | Local docker: `{"status":"ok"}` HTTP 200. Live: HTTP 200, 469 ms. |
| `POST /optimize-energy` returns 200 with **exactly 7 keys in order** | `[x]` | `python -m pytest tests/test_api_layer.py::test_valid_request_returns_expected_shape -q` | Passes (28/28 in suite). |
| `hourly_plan` has 24 entries, `hour` 0–23 ascending | `[x]` | `pytest tests/test_api_layer.py -k "shuffled_hours or plan or totals" -q` | Pass. |
| All numeric outputs finite (no NaN/inf in body) | `[x]` | `pytest tests/test_api_layer.py::test_optimizer_nan_returns_generic_500 -q` | NaN -> 500 generic, no leak. |
| `scenario_id` echoed verbatim | `[x]` | `pytest tests/test_api_layer.py::test_valid_public_sample_case_0 -q` | Pass. |
| 400 on malformed JSON / wrong hour count / duplicate hours / bad notes | `[x]` | `pytest tests/test_api_layer.py -k "invalid or duplicate or notes or hour" -q` | All pass. |
| 500 envelope never leaks traceback/key/pydantic | `[x]` | `pytest tests/test_api_layer.py::test_optimizer_raises_returns_500_without_traceback -q` | Pass. |

## 2. LLM interpretation (per `docs/CONTRACTS.md` Directives)

| Item | Status | Command to verify | Current result |
| --- | --- | --- | --- |
| Exactly one entry per note, in `note_index` order | `[!]` | `PYTHONPATH=. python scripts/run_samples.py <LIVE_URL>` | 10/10 cases return **all notes as `no_op`**. Length and order are correct, but **`applies=true` never fires** -- see Risk R1. |
| Allowed `directive_type` only (6 types incl. `no_op`) | `[x]` | `pytest tests/test_api_layer.py::test_bad_interpreter_outputs_become_no_ops -q` | Bad types -> `no_op` per Alif guard. |
| `hours` are ints 0-23, unique, ascending, non-empty | `[x]` | Same test; `_coerce_hours` rejects `[25]`, dups, unsorted. | Pass. |
| `factor` in `[0,1]` (fraction remaining, e.g. 80% reduction -> 0.2) | `[!]` | `pytest tests/test_api_layer.py::test_bad_interpreter_outputs_become_no_ops` checks 1.5->no_op; live correctness depends on Tamjid's prompt. | Alif guard verified; LLM still all-`no_op` so live end-to-end not verified. |
| `minimum_energy_kwh` in `[0, capacity]` | `[!]` | Live via paraphrase set (Jubayer). | Same: LLM not yet returning structured directives on live. |
| `max_grid_kwh >= 0`, finite | `[!]` | Same. | Same. |
| `no_op` has `applies:false, structured_adjustment:null` | `[x]` | Live case 0 returns `no_op` with `applies:false, structured_adjustment:null`. | Confirmed via `run_samples.py` output. |
| Time windows end-exclusive (`13:00-15:00` -> `[13,14]`) | `[!]` | `python scripts/paraphrase_check.py` against Jubayer's 40 cases. | Not runnable locally -- files live on `origin/jubayer` only; not on `alif`. See Risk R2. |
| Wrap-around, midnight=24, noon=12, AM/PM from context | `[ ]` | Same. | Not verified on live; depends on Tamjid's prompt + normalize. |
| Relevance rule: next-week / unrelated -> `no_op` | `[!]` | Same. | Not verified end-to-end yet. |
| One LLM call for all notes (not per note) | `[ ]` | `grep -n "client.chat\|completions" app/interpreter/core.py` on `tamjid` branch | Not on alif branch. |

## 3. Guardrails

| Item | Status | Command to verify | Current result |
| --- | --- | --- | --- |
| Interpretation guard (bad shape -> `no_op`) | `[x]` | `pytest tests/test_api_layer.py::test_bad_interpreter_outputs_become_no_ops -q` | Pass. |
| Plan guard: force 24 entries; tiny negatives -> 0; `idle` => `battery_kwh=0` | `[x]` | `pytest tests/test_api_layer.py -k "plan or nan or totals" -q` | Pass. |
| Totals recomputed from plan (never trust optimizer) | `[x]` | `pytest tests/test_api_layer.py::test_plan_guard_recomputes_totals -q` | Pass -- wrong optimizer totals overridden. |
| Replay check (`app.optimizer.replay.replay_check`) called when available, retry once | `[x]` | `grep -n "_run_with_retry\|_replay_check" app/main.py`; covered by integration. | Wired; stub on main returns `[]` so retry is a no-op. |
| NaN/inf anywhere -> 500 generic | `[x]` | `pytest tests/test_api_layer.py::test_optimizer_nan_returns_generic_500 -q` | Pass. |
| Bad input -> 400 (no 5xx) | `[x]` | `pytest tests/test_api_layer.py -k "invalid or notes or hour" -q` | Pass. |

## 4. Optimizer and energy rules (per `docs/CONTRACTS.md` Energy and scoring rules)

| Item | Status | Command to verify | Current result |
| --- | --- | --- | --- |
| Per-hour balance: `grid + solar_used + discharge = demand + charge` | `[!]` | `pytest tests/test_optimizer.py -q` (on Taseen's branch) | Local alif has no tests; needs Taseen's replay validator + plan to satisfy this. |
| `0 <= solar_used <= effective_solar` | `[!]` | Same. | Not verified. |
| `E_after[23] == initial_energy_kwh` (end neutrality) | `[!]` | Same. | Not verified on live; samples 1-10 currently fail because no directives apply -> optimizer still must balance. |
| `active_minimum <= E_after <= capacity` per hour | `[!]` | Same. | Not verified. |
| Action vs rate limits: `charge <= max_charge_kwh_per_hour`, `discharge <= max_discharge_kwh_per_hour` | `[!]` | Same. | Not verified. |
| Reserve directives raise floor (`E_after >= max(base, n)`) | `[!]` | Same. | Not verified on live. |
| No-charge / no-discharge windows enforced | `[!]` | Same. | Not verified on live. |
| Max-grid cap honored | `[!]` | Same. | Not verified on live. |
| Optimizer never raises (infeasible -> `relaxed`/`fallback`) | `[!]` | `pytest tests/test_optimizer.py -k "infeasible or edge or fallback" -q` | Not present on alif branch; needs Taseen branch. |
| All plans pass replay_check | `[!]` | `python scripts/run_samples.py <LIVE_URL>` (after LLM is live) | 10/10 currently fail for **interpretation** reasons, not plan reasons -- once LLM works we can isolate. |

## 5. Optimization quality (10/10 cost match)

| Item | Status | Command to verify | Current result |
| --- | --- | --- | --- |
| Each `SAMPLE-NN` matches `expected.total_cost_bdt` within 0.01 | `[ ]` | `PYTHONPATH=. python scripts/run_samples.py <LIVE_URL>` | **0/10**. All fail because interpretation returns `no_op`, so `grid = demand - solar` baseline runs and is much costlier than the directive-driven expected plan. Sample 1 expected `38365`, current `+220` diff means current runs the no-op schedule. |
| LP formulation matches Tech spec (5 vars/hour, balance, SOC, E[23]=initial) | `[!]` | `cat app/optimizer/solver.py` on Taseen branch | Not on alif branch; needs review on merge. |
| Total cost objective = sum `tariff * grid` + tiny cycling penalty | `[!]` | Same. | Not on alif. |

## 6. Performance

| Item | Status | Command to verify | Current result |
| --- | --- | --- | --- |
| `/health` < 60 s cold start | `[x]` | `time curl -s -o /dev/null http://localhost:8020/health` (docker local) | < 1 s. Live 469 ms. |
| Live `p95 latency < 5 s` | `[x]` | `python scripts/run_samples.py <LIVE_URL>` summary | avg 285 ms, max 552 ms across 10 cases. Well under 5 s. |
| No 5xx on valid input | `[x]` | Same. | All 10 returned HTTP 200. |
| No 5xx on malformed input | `[x]` | `curl -X POST -d '{bad' .../optimize-energy` (live) | Returned 400 in earlier tests; check on alif after integration. |
| LRU cache hit on identical repeat (max 256) | `[x]` | `pytest tests/test_api_layer.py::test_cache_hit_on_repeat_request -q` | Pass. |
| Interpreter timeout (12 s) falls back to no_op < 15 s | `[x]` | `pytest tests/test_api_layer.py::test_slow_interpreter_returns_200_with_no_ops_under_15s -q` | Pass (under 15 s with no_op entries). |

## 7. Error handling

| Item | Status | Command to verify | Current result |
| --- | --- | --- | --- |
| 400 envelope: `{"error":"invalid request"}` | `[x]` | `pytest tests/test_api_layer.py::test_invalid_json_returns_400 -q` | Pass. |
| 500 envelope: `{"error":"internal error"}` | `[x]` | `pytest tests/test_api_layer.py::test_optimizer_raises_returns_500_without_traceback -q` | Pass. |
| No traceback / pydantic / key text in any response | `[x]` | `grep -i "traceback\|pydantic" body` in tests | Confirmed. |
| CORS allows GET/POST | `[x]` | `grep -n "CORSMiddleware" app/main.py` | Present, `allow_origins=["*"]`. |

## 8. Security

| Item | Status | Command to verify | Current result |
| --- | --- | --- | --- |
| No `.env` / `.env.*` (excl. `.env.example`) tracked | `[x]` | `git ls-files \| grep -E '(^\|/)\.env$'` | Empty. |
| No `sk-`, `ghp_`, `gho_`, `AIza...`, `gsk_...`, `xai-...` in any committed diff | `[x]` | `for b in alif taseen tamjid jubayer; do git diff origin/main...origin/$b \| grep -E 'sk-\|ghp_\|gho_\|AIza[0-9A-Za-z_-]{20,}\|gsk_\|xai-[A-Za-z0-9]{20,}'; done` | Empty. |
| No `BEGIN.*PRIVATE KEY` | `[x]` | Same grep with `BEGIN .* PRIVATE KEY` | Empty. |
| Logs do not include `LLM_API_KEY` value | `[x]` | `grep -rn "LLM_API_KEY" app/ \| grep -v os.getenv` | Only `os.getenv("LLM_API_KEY")` calls; values are referenced, never logged. |
| Docker image not run as root | `[x]` | `docker exec <container> id` -> `uid=1000(gridwise)` | Confirmed. |

## 9. Deployment

| Item | Status | Command to verify | Current result |
| --- | --- | --- | --- |
| Live base URL serves `/health` | `[x]` | `curl -s -w '%{http_code}' https://gridwise-production-0e08.up.railway.app/health` | `{"status":"ok"}` HTTP 200, 469 ms. |
| Live `/optimize-energy` accepts valid input | `[x]` | `python scripts/run_samples.py <LIVE_URL>` | 10/10 HTTP 200. |
| Auto-deploy from `main` enabled | `[!]` | Railway dashboard -> service -> settings | Not verified from CLI here (`railway link` not done in this session). Visual confirmation only. |
| Env vars present (names only): `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_FALLBACK_*`, `PORT` | `[ ]` | `railway variables` (requires `railway link`) | Not listable from this session -- see Risk R3. |
| Service is on port 8000 (or `${PORT}`) | `[x]` | `docker run -p 8020:8000 ...` local; Railway dashboard | Local: 8000. |

## 10. Docker

| Item | Status | Command to verify | Current result |
| --- | --- | --- | --- |
| Dockerfile: `python:3.11-slim`, `pip --no-cache-dir`, non-root, `PYTHONUNBUFFERED=1`, `EXPOSE 8000` | `[x]` | `grep -nE "FROM\|pip install\|EXPOSE\|USER\|PYTHONUNBUFFERED" Dockerfile` | All present. |
| HEALTHCHECK on `/health` | `[x]` | `docker inspect --format='{{.State.Health.Status}}' <container>` | `healthy`. |
| CMD uvicorn with `--workers 2` and `${PORT:-8000}` | `[x]` | `docker run ...` and `curl localhost:8020/health` | `{"status":"ok"}` HTTP 200. |
| Public GHCR image pullable anonymously | `[ ]` | `docker logout ghcr.io && docker pull ghcr.io/abdullahalyf/gridwise:v1` | **FAILS `unauthorized`**. Image is private. Auth'd pull with `gh auth token` works. See Risk R4. |
| Authenticated GHCR pull + run serves `/health` | `[x]` | `echo $(gh auth token) \| docker login ghcr.io -u abdullahalyf --password-stdin && docker pull ... && docker run -p 8021:8000 ghcr.io/abdullahalyf/gridwise:v1` | `{"status":"ok"}` HTTP 200. |
| `.dockerignore` excludes secrets / .git / .env / tests / data | `[x]` | `cat .dockerignore` | Yes. |

## 11. README reproducibility

| Item | Status | Command to verify | Current result |
| --- | --- | --- | --- |
| README.md exists (Jubayer-owned) | `[x]` | `test -f README.md && wc -l README.md` | Present on `origin/jubayer` (commit `c953770`). Not on alif branch directly. |
| README includes quickstart, env vars, architecture, curl, sample test, Docker, limitations, secret handling | `[!]` | `grep -nE "quickstart\|curl\|docker\|limitation\|secret" README.md` (Jubayer) | Need full read on merge to main. |
| `.env.example` lists every env var name (no values) | `[!]` | `cat .env.example` | Should list `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_FALLBACK_API_KEY`, `LLM_FALLBACK_BASE_URL`, `LLM_FALLBACK_MODEL`, `PORT`, `LOG_LEVEL`. |
| Live URL placeholder present in README | `[ ]` | `grep -n "gridwise-production-0e08" README.md` | TBD on `WU-DOC-1` close. |

## 12. Video

| Item | Status | Command to verify | Current result |
| --- | --- | --- | --- |
| `docs/VIDEO_SCRIPT.md` exists (<= 3:00, problem/architecture/demo/guardrails/run) | `[!]` | `git show origin/jubayer:docs/VIDEO_SCRIPT.md \| head` | Exists on Jubayer branch (commit `2afe3bf`). Not on alif. |
| Recorded video URL provided | `[ ]` | (manual) | Not yet. |

## 13. Submission

| Item | Status | Command to verify | Current result |
| --- | --- | --- | --- |
| GitHub repo URL | `[x]` | `git remote -v` | `github.com/abdullahalyf/bup-hackathon-preli`. |
| Repo made public after deadline | `[ ]` | GitHub -> settings -> visibility | Not yet (still private). |
| Live base URL submitted | `[x]` | (this checklist) | `https://gridwise-production-0e08.up.railway.app`. |
| Docker image tag submitted | `[x]` | (this checklist) | `ghcr.io/abdullahalyf/gridwise:v1` (private -- must be flipped to public before judges pull). |
| README with quickstart, model, env, Docker, live URL | `[!]` | See Section 11 | Pending final merge. |
| Video link submitted | `[ ]` | Manual | Pending. |
| No secrets anywhere in repo | `[x]` | See Section 8 | Confirmed. |

---

## Risk summary (cross-cuts)

- **R1 -- Live API returns `no_op` for every operator note.** `scripts/run_samples.py` 0/10 interpretation match. Pipeline falls back to no-directive schedule, costing 2-5x the expected total. **Owner: Tamjid (highest priority)**.
- **R2 -- Jubayer's `scripts/paraphrase_check.py` and `data/paraphrases.json` only live on `origin/jubayer`** -- not present on `alif`, `main`, or `taseen`/`tamjid`. Need them merged to run paraphrase suite locally.
- **R3 -- `railway` CLI not linked in this session**, so env-var name list cannot be confirmed. Visual check on dashboard is required before submission.
- **R4 -- GHCR image is private.** Anonymous `docker pull` returns `unauthorized`. Must flip to public in GHCR settings before judges can pull.
- **R5 -- `tests/test_optimizer.py` lives only on `origin/taseen`**. Plan-guard end-to-end (replay violations, end neutrality, reserve floors) cannot be re-run on `alif` until Taseen's branch is merged to main.
