# GridWise team rules

GridWise is a public FastAPI service. `POST /optimize-energy` receives 24-hour energy data and 1–3 English operator notes. An LLM turns notes into structured directives, deterministic guardrails validate them, and an LP optimizer builds a minimum-cost battery/grid schedule as strict JSON. An automated judge replays and scores the response.
Work plan, work units and prompts: docs/MASTER_PLAN.md

| Member | Branch | Role | Owns |
| --- | --- | --- | --- |
| Alif | `alif` | Head / API integrator / deployment / only person who merges to main | `app/main.py`, `app/schemas.py`, `app/__init__.py`, `app/interpreter/__init__.py`, `app/optimizer/__init__.py`, `requirements.txt`, `.env.example`, `.gitignore`, `Dockerfile`, `.dockerignore`, `tests/test_api_layer.py`, deployment, `docs/*`, `tasks/*`, `AGENTS.md`, `CLAUDE.md`, `tools/*` |
| Taseen | `taseen` | Optimizer engineer | `app/optimizer/solver.py`, `app/optimizer/replay.py`, `tests/test_optimizer.py` |
| Tamjid | `tamjid` | LLM engineer | `app/interpreter/core.py`, `prompt.py`, `llm_client.py`, `normalize.py`, `fallback.py`, `tests/test_interpreter.py` |
| Jubayer | `jubayer` | DevOps + QA + Docs + frontend | `scripts/*`, `tests/test_api.py`, `data/paraphrases.json`, `frontend/*`, `README.md`, `docs/VIDEO_SCRIPT.md` |

1. Read `docs/CONTRACTS.md` and your `tasks/<NAME>.md` before coding.
2. Only edit files you own. Never touch another member's files.
3. Do one step at a time from your task file. Commit and push after every step.
4. Never commit `.env`, keys, or tokens. Never print secrets.
5. Run the step's check command before committing.
6. Need a new dependency or contract change? Ask Alif.
7. Stuck more than 20 minutes? Tell Alif immediately.
