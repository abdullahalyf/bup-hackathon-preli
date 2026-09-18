# How to work

## First-time setup

```bash
git clone https://github.com/abdullahalyf/bup-hackathon-preli.git
cd bup-hackathon-preli
git checkout <your-name>              # alif / taseen / tamjid / jubayer
python -m venv .venv
source .venv/bin/activate             # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                  # Alif will send the key privately
```

Run the app: `uvicorn app.main:app --reload --port 8000`, then open <http://localhost:8000/health>.

After every step: run the step's **Check**, `git add` only your files, commit, and push. Get latest main when Alif says: `git pull origin main`.

Never edit another member's file, commit `.env`, push to main, or run `git push --force`.

Checkpoint report at **0:50 / 1:40 / 2:30**: `Name | Current step | Done steps | Test result (paste) | Blocked?`

If stuck more than 20 minutes, send Alif the error and what you tried.

Start every Puku session with: `Read AGENTS.md, docs/CONTRACTS.md and tasks/<NAME>.md. I am on Step N. Only edit files I own.`

Feature freeze is **2:45**. After that, fix bugs and finish live verification only.

| Member | Branch | Role | Owns |
| --- | --- | --- | --- |
| Alif | `alif` | Head / API integrator / only person who merges to main | `app/main.py`, `app/schemas.py`, `app/__init__.py`, `app/interpreter/__init__.py`, `app/optimizer/__init__.py`, `requirements.txt`, `.env.example`, `.gitignore`, `docs/*`, `tasks/*`, `AGENTS.md`, `CLAUDE.md`, `tests/test_api_layer.py` |
| Taseen | `taseen` | Optimizer engineer | `app/optimizer/solver.py`, `app/optimizer/replay.py`, `tests/test_optimizer.py` |
| Tamjid | `tamjid` | LLM engineer | `app/interpreter/core.py`, `prompt.py`, `llm_client.py`, `normalize.py`, `fallback.py`, `tests/test_interpreter.py` |
| Jubayer | `jubayer` | DevOps + QA + Docs | `scripts/*`, `tests/test_api.py`, `data/paraphrases.json`, `Dockerfile`, `.dockerignore`, `README.md`, `docs/VIDEO_SCRIPT.md` |
