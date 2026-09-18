# Alif — head and API integrator

**Mission:** Keep everyone unblocked, keep main running, merge, and submit. You are the only person who merges to main. **Own:** `app/main.py`, `app/schemas.py`, `app/__init__.py`, `app/interpreter/__init__.py`, `app/optimizer/__init__.py`, `requirements.txt`, `.env.example`, `.gitignore`, `docs/*`, `tasks/*`, `AGENTS.md`, `CLAUDE.md`, `tests/test_api_layer.py`.

Read `AGENTS.md`, `docs/CONTRACTS.md`, and `tasks/HOW_TO_WORK.md` first. Times are relative to hackathon start. Checkpoints: 0:50, 1:40, 2:30. Feature freeze: 2:45.

### Step 1 — Bootstrap ⏱ 0:00–0:15
**Goal:** Publish the runnable skeleton and create team branches and access.
**বাংলায়:** শুরুতে skeleton যাচাই করে main আর সবার branch তৈরি করো।
**Paste into Puku:** Run this Codex prompt; verify acceptance checks (Part D). Push main, create branches alif taseen tamjid jubayer, add collaborators (Settings → Collaborators). Send each member the repo link and “read tasks/HOW_TO_WORK.md then tasks/<NAME>.md”. Send the LLM key privately; never put it in git or a group-chat screenshot.
**Check:** `pytest -q`, `/health`, a valid sample request, invalid JSON → 400, and `ls tasks/` all pass; confirm all four remote branches and collaborator invitations.
**Commit:** `git add . && git commit -m "setup: skeleton, contracts, step-by-step team tasks" && git push origin main`
**Done when:** Teammates can clone, check out their branches, and run the API.

### Step 2 — API hardening ⏱ 0:15–0:50
**Goal:** Verify response and error contracts and keep requests within 30 seconds.
**বাংলায়:** API-র ভুল ইনপুট, ফলাফলের format আর সময়সীমা যাচাই করো।
**Paste into Puku:** Check app/main.py against docs/CONTRACTS.md: 400 cases, 500 handler, exact key order, scenario_id echo, only applies==true passed to optimizer. Add timing log per request (no secrets). Ensure total request timeout safety (< 30 s). Collect checkpoint reports at 0:50 and confirm Jubayer's live URL.
**Check:** `pytest tests/test_api.py -q` and one measured API request pass; logs contain no notes or secrets.
**Commit:** `git add app/main.py app/schemas.py && git commit -m "alif: step 2 API hardening" && git push` (only if files changed; ask Jubayer to edit `tests/test_api.py`).
**Done when:** API contract is verified and the live URL is known.

### Step 3 — Merges ⏱ 1:40 and 2:30
**Goal:** Merge team work in order, keeping main green.
**বাংলায়:** Taseen, Tamjid, Jubayer-এর কাজ ক্রমে merge করে টেস্ট চালাও।
**Paste into Puku:** GitHub → Pull request from each branch to main. Order: Taseen → Tamjid → Jubayer. After each merge run `git pull origin main && pytest -q && python scripts/run_samples.py`. Tell everyone to run `git pull origin main`. Paste any failure to Claude for a root-cause explanation and a fix prompt.
**Check:** `pytest -q` and `python scripts/run_samples.py` pass after each merge once the relevant implementation is available.
**Commit:** Merge via pull requests; no separate direct commit is required.
**Done when:** All member changes are on main and the test suite passes.

### Step 4 — Freeze & verify ⏱ 2:45–3:15
**Goal:** Stop feature work and verify the public deployment.
**বাংলায়:** নতুন ফিচার বন্ধ করে লাইভ সার্ভিস ও গোপন তথ্য যাচাই করো।
**Paste into Puku:** No new features. Run `python scripts/run_samples.py <LIVE_URL>`; require all green and p95 < 5 s. Check `/health` from outside. Check that `git log --all -- .env` is empty.
**Check:** Live sample runner passes; external health works; no `.env` appears in git history.
**Commit:** Bug-fix commits only if necessary, in owned files; run checks before pushing.
**Done when:** The final deployed main is green and secrets have not been committed.

### Step 5 — Submit ⏱ 3:45–4:00
**Goal:** Submit all required artifacts before the deadline.
**বাংলায়:** সময়ের মধ্যে সব লিংক আর তথ্য জমা দাও।
**Paste into Puku:** Checklist: live base URL · GitHub repo link (public after deadline) · Docker image exact tag · README complete · video link ≤ 3:00 · env var names documented · no secrets anywhere.
**Check:** Open each link and confirm the submitted values match the verified artifacts.
**Commit:** No code commit unless a final owned-file correction is needed.
**Done when:** Submission confirmation is recorded before 4:00.
