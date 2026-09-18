# GridWise — Status & Handoff

> Historical handoff: the findings below were recorded before the current deployment. On 2026-09-18, `main` at `6b4d4fd` passed 113 API tests and all 10 live public samples (interpretation, cost within 0.01 BDT, and replay). The GHCR `v1` image was rebuilt from that commit and verified by a local `/health` check and authenticated registry pull. GHCR package visibility remains private, the video link remains TBD, and recent Railway logs show primary LLM rate limits. Railway is deployed with `railway up --detach --service gridwise`.

Last updated: 2026-09-18 20:22 local (`origin/alif` @ `3379393`).

## Skills used in this session

For this handoff/checklist pass, I actively drew on these skills / lenses (in addition to standard `puku-cli` baseline):

- `verification-before-completion`, `verify-and-stop` — gate every fact before stamping `[x]` in `CHECKLIST.md`.
- `using-superpowers`, `cavecrew`, `caveman:cavecrew-investigator` — read-only posture; one fact-gathering pass, no speculative edits.
- `requesting-code-review`, `ecc:code-review`, `caveman:cavecrew-reviewer` — lens for ownership violations and contract drift per branch.
- `ecc:security-scan` — secret pattern scan (sk-/ghp_/gho_/AIza/gsk_/xai-).
- `test-driven-development` — verified via 28-test pytest run on `alif`.
- `systematic-debugging` — applied to the live `no_op` regression (R1 below).
- `subagent-driven-development`, `parallel-agent` — could not fully use (single-process, time-boxed).
- `ecc:cost-tracking`, `ecc:cost-report` — concise output, no waste.
- `ecc:plan-canvas`, `writing-plans` lens — structure of this doc.
- `finishing-a-development-branch` — commit + push at the end.
- NOT used (intentionally): `brainstorming`, `writing-plans` (per `docs/MASTER_PLAN.md` instruction).

## Project in 5 lines

1. Public FastAPI service: `POST /optimize-energy` returns a 24-hour minimum-cost battery/grid schedule for 1-3 operator notes.
2. Pipeline: Operator notes -> LLM (Gemini primary, Groq fallback) -> guardrails/normalise -> scipy HiGHS LP optimiser -> replay validator -> strict JSON.
3. Live at `https://gridwise-production-0e08.up.railway.app`; Docker image `ghcr.io/abdullahalyf/gridwise:v1` (currently **private**).
4. 4-person team (Alif, Taseen, Tamjid, Jubayer), 4 feature branches; only Alif merges to `main`; Railway auto-deploys from `main`.
5. Repo `github.com/abdullahalyf/bup-hackathon-preli`. Plan in `docs/MASTER_PLAN.md`, contracts in `docs/CONTRACTS.md`.

## Architecture (text diagram)

```
   client (frontend or curl)
            |
            v
   +------------------+   12 s timeout (interp)
   |   FastAPI main   |--------------------+
   |   (app/main.py)  |                    |
   +------------------+                    v
            |                  +-------------------+
            |                  | ThreadPoolExecutor |
            |                  |   (interpreter)    |
            |                  +-------------------+
            |                            |
            |                            v
            |                  +-------------------+
            |                  |  app.interpreter  |
            |                  | llm_client/prompt |
            |                  | normalize/fallback|
            |                  |       core        |
            |                  +-------------------+
            v
   +------------------+        +-------------------+
   |  LRU response    |        |    guard rails    |
   | cache (max 256)  |<------>| (interp+plan shape|
   +------------------+        |  NaN, retry once) |
            |                  +-------------------+
            v
   +------------------+
   |  app.optimizer   |
   | solver / replay  |--> returns [] or violations
   +------------------+
            |
            v
   JSON response (exactly 7 keys, in order)
```

## Key links

| What | Value |
| --- | --- |
| GitHub repo | `github.com/abdullahalyf/bup-hackathon-preli` |
| Live URL | `https://gridwise-production-0e08.up.railway.app` |
| Live `/health` | `curl -s https://gridwise-production-0e08.up.railway.app/health` -> `{"status":"ok"}` (200, 469 ms) |
| Docker image (auth'd) | `ghcr.io/abdullahalyf/gridwise:v1` (private -- flip to public) |
| Railway project | `gridwise-production` (CLI: `railway link` then `railway variables`) |

## Team & ownership

| Member | Branch | Role | Files (after AGENTS.md merge on `alif`) |
| --- | --- | --- | --- |
| Alif | `alif` | Head / API / Deploy / only merger to main | `app/main.py`, `app/schemas.py`, `app/__init__.py`, `app/interpreter/__init__.py`, `app/optimizer/__init__.py`, `requirements.txt`, `.env.example`, `.gitignore`, `Dockerfile`, `.dockerignore`, `tests/test_api_layer.py`, deployment, `docs/*`, `tasks/*`, `AGENTS.md`, `CLAUDE.md` |
| Taseen | `taseen` | Optimizer engineer | `app/optimizer/solver.py`, `app/optimizer/replay.py`, `tests/test_optimizer.py` |
| Tamjid | `tamjid` | LLM engineer | `app/interpreter/core.py`, `prompt.py`, `llm_client.py`, `normalize.py`, `fallback.py`, `tests/test_interpreter.py` |
| Jubayer | `jubayer` | DevOps + QA + Docs + Frontend | `scripts/*`, `tests/test_api.py`, `data/paraphrases.json`, `frontend/*`, `README.md`, `docs/VIDEO_SCRIPT.md` |

## Work Unit status (from `docs/MASTER_PLAN.md`)

Legend: done = merged to main or live-verified · in-progress = on branch · not-started = no commits.

### Done so far (with commit hashes)

| WU | Owner | Commit (branch) | What |
| --- | --- | --- | --- |
| WU-0.1 | Alif | `7d49d89` (setup) | Repo bootstrap, skeleton, contracts |
| WU-0.2 | Alif | (off-repo, human) | Gemini + Groq keys obtained privately |
| WU-DEP-1 | Alif | `5493e36` (`alif`) + `ecb78e9` (`main`) | CORS, `/`, Docker local, Railway deploy |
| WU-API-1 | Alif | `5493e36` + `3379393` (`alif`) | API hardening, then safety net + cache + Docker hardening (current `alif` HEAD) |
| WU-OPT-1 | Taseen | `dcf205d` (`taseen`) | Effective limits builder (`solver.py`) |
| WU-OPT-2 | Taseen | `dcf205d` (`taseen`) | LP solver (HiGHS) — on taseen only, not yet on `main` |
| WU-OPT-3 | Taseen | `dcf205d` (`taseen`) | Replay validator — on taseen only |
| WU-OPT-4 | Taseen | `dcf205d` (`taseen`) | Robustness / infeasible fallback — on taseen only |
| WU-LLM-1 | Tamjid | `519a699` (`tamjid`) | LLM client (`app/interpreter/llm_client.py`) |
| WU-QA-1 | Jubayer | rolled into `scripts/run_samples.py` | Sample runner |
| WU-QA-2 | Jubayer | `36d122d` (`jubayer`) | Paraphrase set + checker |
| WU-QA-3 | Jubayer | `6034f89` (`jubayer`) | API tests (`tests/test_api.py`) |
| WU-FE-1 | Jubayer | `c3bfd98` (`jubayer`) | Frontend console |
| WU-DOC-1 | Jubayer | `c953770` (`jubayer`) | README |
| WU-DOC-2 | Jubayer | `2afe3bf` (`jubayer`) | Video script |
| WU-VER-1 | Alif | this session | Live verification + this checklist |

### In progress / NOT STARTED

| WU | Owner | State | Note |
| --- | --- | --- | --- |
| WU-LLM-2 | Tamjid | not on `tamjid` branch | System prompt + few-shot — not committed |
| WU-LLM-3 | Tamjid/Taseen | not on `tamjid` branch | Guardrails/normalize — not committed |
| WU-LLM-4 | Tamjid | not on `tamjid` branch | `interpret_notes` wiring — only stub on `main`/`alif` |
| WU-LLM-5 | Tamjid (+Taseen) | blocked by WU-LLM-4 | Paraphrase hardening — cannot run until LLM-4 lands |
| WU-DEP-2 | Alif | partial | GHCR image pushed but currently **private** — must flip to public |

## Known issues & risks

- **R1 (BLOCKER) — Live `/optimize-energy` returns `no_op` for every operator note.** `scripts/run_samples.py` reports `0/10` interpretation match against `https://gridwise-production-0e08.up.railway.app`. Total costs therefore come out 2-5x higher than expected. Owner: **Tamjid** — needs `core.py` wired to `llm_client.py` + `prompt.py` + `normalize.py`, then `app/interpreter/__init__.py` updated to export the real `interpret_notes`. Latency is fine (avg 285 ms, max 552 ms across the 10 cases).

- **R2 — `scripts/paraphrase_check.py` and `data/paraphrases.json` only on `origin/jubayer`.** Not on `alif`, `main`, `taseen`, or `tamjid`. Cannot run paraphrase suite locally without first merging Jubayer's branch to main.

- **R3 — `railway` CLI is not linked in this session.** Cannot list env var names without `railway link <project>` first. Visual confirmation on Railway dashboard is required before submission.

- **R4 — GHCR image is private.** `docker pull ghcr.io/abdullahalyf/gridwise:v1` anonymously returns `unauthorized`. Auth'd pull via `gh auth token` works. Must flip the package to public in GHCR settings before judges can pull. Settings URL: `https://github.com/users/abdullahalyf/packages/container/gridwise/settings`.

- **R5 — `tests/test_optimizer.py` only on `origin/taseen`.** Plan-guard end-to-end (replay violations, end neutrality, reserve floors, rate limits, balance, max-grid caps) cannot be re-run on `alif` until Taseen's branch is merged to main.

- **R6 — `main` was pushed directly.** Commits `96de14e`, `ecb78e9`, `b493859` are on `main` ahead of `alif` after `alif`'s merge. This bypassed the merge-to-main workflow but is acceptable since Alif is the only authorized merger. Going forward, keep `alif` as the staging branch.

- **R7 — End-neutrality, balance, paraphrase accuracy — all unverified end-to-end on live.** Depends on R1 + merging Taseen/Jubayer to main.

## Next actions in priority order

1. **(BLOCKER) Tamjid — land WU-LLM-2..4 on `tamjid`** so live LLM actually emits structured directives. Then re-run `python scripts/run_samples.py <LIVE_URL>` until 10/10 interpretation match.
2. **Alif — merge `origin/tamjid`, `origin/taseen`, `origin/jubayer` into `alif` (in that order)**, then push `alif -> main` to redeploy. Resolve AGENTS.md per `tasks/HOW_TO_WORK.md` rule "merge in order".
3. **Alif — flip GHCR package `gridwise` to public** so `docker pull ghcr.io/abdullahalyf/gridwise:v1` works for judges.
4. **Tamjid — re-run `python scripts/paraphrase_check.py`** (after R2) until accuracy >= 90% (per WU-LLM-5 acceptance).
5. **Alif — re-run C3 final verification** (per `docs/MASTER_PLAN.md` Section 7 C3): twice run `run_samples.py`, POST malformed JSON, secret grep, Docker pull+run, README placeholders filled.
6. **Jubayer — record the 3-min video** and put the link into `docs/VIDEO_SCRIPT.md` and submission form.
7. **Alif — flip the repo to public** after the hackathon deadline.
8. **Alif — final submission**: paste live URL, image tag, repo link, video link into the submission form.

## How to onboard (5 minutes for a brand-new agent)

### Read order

1. `AGENTS.md` — ownership rules (one-file-at-a-time, no cross-team edits).
2. `docs/STATUS.md` (this file) — current state, risks, next actions.
3. `docs/CONTRACTS.md` — public API shape + internal function signatures.
4. `docs/MASTER_PLAN.md` — full Work Unit board + prompts.
5. `tasks/<NAME>.md` — your role-specific checklist.

### Setup commands

```bash
# From a clean clone
git clone https://github.com/abdullahalyf/bup-hackathon-preli.git
cd bup-hackathon-preli
git fetch --all
git checkout <your-branch>     # alif | taseen | tamjid | jubayer
git pull origin <your-branch>
git pull origin main           # if instructed by Alif

# Python env
python -m venv .venv
. .venv/Scripts/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Env (DO NOT COMMIT)
cp .env.example .env
# Alif will share the LLM_API_KEY etc. privately; never commit .env
```

### Env var names (never commit values)

- `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` (Gemini primary)
- `LLM_FALLBACK_API_KEY`, `LLM_FALLBACK_BASE_URL`, `LLM_FALLBACK_MODEL` (Groq)
- `PORT` (default 8000), `LOG_LEVEL` (default INFO)

### Run tests

```bash
# Full suite (Alif branch has test_api_layer.py)
python -m pytest -q

# Live sample runner (use Jubayer version from origin/jubayer)
git show origin/jubayer:scripts/run_samples.py > scripts/run_samples.py
PYTHONPATH=. python scripts/run_samples.py https://gridwise-production-0e08.up.railway.app
rm scripts/run_samples.py   # do not commit; belongs to Jubayer

# Paraphrase accuracy (after merge of Jubayer to main)
git show origin/jubayer:data/paraphrases.json > data/paraphrases.json
git show origin/jubayer:scripts/paraphrase_check.py > scripts/paraphrase_check.py
PYTHONPATH=. python scripts/paraphrase_check.py

# Local API smoke
docker build -t gridwise . && docker run -d -p 8000:8000 --env-file .env gridwise
curl localhost:8000/health
```

### Git rules

- One branch per member. Only edit files listed in your ownership row.
- Commit + push to your branch every Work Unit.
- Only **Alif** merges to `main` (and only Alif pushes `main`).
- Never commit `.env`, secrets, tokens, or model keys.
- For new dependencies or contract changes, ask Alif first.

## Timeline (relative to hackathon start)

| Time | Event | Owner |
| --- | --- | --- |
| 1:40 | Checkpoint 1 (CP1) | Alif |
| 2:30 | Checkpoint 2 (CP2) | Alif |
| 2:45 | Feature freeze — bug fixes only | all |
| 3:15 | Live test + Docker push done | Alif |
| 3:40 | README + video recorded | Jubayer |
| 4:00 | Submit (live URL + image tag + video) | Alif |
