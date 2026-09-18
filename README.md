# GridWise

GridWise is a 4-person, 4-hour hackathon project. This repository currently contains a runnable FastAPI skeleton. The interpreter returns `no_op` and the optimizer uses a grid-and-solar baseline until the team implements the real LLM and LP modules.

| Member | Branch | Role | Owns |
| --- | --- | --- | --- |
| Alif | `alif` | Head / API integrator / only person who merges to main | `app/main.py`, `app/schemas.py`, `app/__init__.py`, `app/interpreter/__init__.py`, `app/optimizer/__init__.py`, `requirements.txt`, `.env.example`, `.gitignore`, `docs/*`, `tasks/*`, `AGENTS.md`, `CLAUDE.md` |
| Taseen | `taseen` | Optimizer engineer | `app/optimizer/solver.py`, `app/optimizer/replay.py`, `tests/test_optimizer.py` |
| Tamjid | `tamjid` | LLM engineer | `app/interpreter/core.py`, `prompt.py`, `llm_client.py`, `normalize.py`, `fallback.py`, `tests/test_interpreter.py` |
| Jubayer | `jubayer` | DevOps + QA + Docs | `scripts/*`, `tests/test_api.py`, `data/paraphrases.json`, `Dockerfile`, `.dockerignore`, `README.md`, `docs/VIDEO_SCRIPT.md` |

See [the API contract](docs/CONTRACTS.md) and [team workflow](tasks/HOW_TO_WORK.md). Jubayer owns the full README in Step 6 of his task file.
