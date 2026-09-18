# Jubayer — DevOps, QA, and docs

**Mission:** Make GridWise live, prove it works, and document it. You own 20+ easy points from deployment, Docker, and the README. **Own:** `scripts/*`, `tests/test_api.py`, `data/paraphrases.json`, `Dockerfile`, `.dockerignore`, `README.md`, `docs/VIDEO_SCRIPT.md`. **Do not touch:** everything else.

Read `AGENTS.md`, `docs/CONTRACTS.md`, and `tasks/HOW_TO_WORK.md` first. Times are relative to hackathon start. Report at 0:50, 1:40, and 2:30. Feature freeze: 2:45.

### Step 1 — Setup + Docker ⏱ 0:15–0:30
**Goal:** Run the stub API in a production-ready container.
**বাংলায়:** Docker দিয়ে লোকালে অ্যাপ চালাও।
**Paste into Puku:** Read AGENTS.md, docs/CONTRACTS.md and tasks/JUBAYER.md. Make the Dockerfile production-ready (python:3.11-slim, no secrets, EXPOSE 8000, host 0.0.0.0, port ${PORT:-8000}) and a good .dockerignore (.env, .venv, .git, __pycache__, tests cache).
**Check:** `docker build -t gridwise . && docker run -p 8000:8000 gridwise` → `curl localhost:8000/health` returns `{"status":"ok"}`.
**Commit:** `git add Dockerfile .dockerignore && git commit -m "jubayer: step 1 docker" && git push`
**Done when:** The container serves `/health`.

### Step 2 — Deploy (MOST URGENT) ⏱ 0:30–0:50
**Goal:** Publish the main branch and share a public base URL.
**বাংলায়:** ইন্টারনেটে deploy করে public URL বানাও।
**Paste into Puku:** Railway (or Render) → New Project → Deploy from GitHub → this repo, branch main → set env vars LLM_API_KEY, LLM_MODEL (and LLM_BASE_URL if needed; Alif gives values privately) → generate public domain. Turn auto-deploy from main ON.
**Check:** From your phone or another network, `curl https://<url>/health` → `{"status":"ok"}`.
**Commit:** No code commit; send the URL to Alif at 0:50.
**Done when:** The public health endpoint works and Alif has its URL.

### Step 3 — Sample runner ⏱ 0:50–1:15
**Goal:** Compare each organizer sample against the API and replay validator.
**বাংলায়:** ১০টা sample পাঠিয়ে ফলাফল মিলানোর স্ক্রিপ্ট।
**Paste into Puku:** Implement scripts/run_samples.py: for each case in data/public_samples.json POST case["input"] to BASE_URL (CLI arg, else env BASE_URL, else http://localhost:8000). Print per case: id, HTTP status, latency, interpretation match per note (applies, directive_type, structured_adjustment with 0.01 tolerance) vs expected_output.directive_interpretation, cost diff vs expected_output.total_cost_bdt, and violations from app.optimizer.replay.replay_check(input hours, battery, applied expected directives, response). Print summary including p95 latency. Exit 1 on any failure.
**Check:** `python scripts/run_samples.py` runs; stub results failing is expected at this stage.
**Commit:** `git add scripts/run_samples.py && git commit -m "jubayer: step 3 sample runner" && git push`
**Done when:** All 10 cases are reported and failures produce exit code 1.

### Step 4 — Paraphrase test set ⏱ 1:15–1:45
**Goal:** Create 40 hand-written judge-like notes and an accuracy script.
**বাংলায়:** judge-এর মতো ৪০টা ঘুরিয়ে লেখা নোট বানাও।
**Paste into Puku:** Create data/paraphrases.json: 40 hand-written varied operator notes, each {"note", "capacity_kwh", "expected": {"applies", "directive_type", "structured_adjustment"}}. Cover all 6 types (~7 each + 8 no_op). Include 24h times ("13:00"), word times ("one until three"), noon/midnight, wrap-around, "% reduction" vs "drop to %", fractions ("one-fifth", "a quarter"), "% of capacity" reserves, grid limits in different words (import, intake, feeder, transformer), and tricky distractors mentioning solar/battery but about next week or unrelated. Follow docs/CONTRACTS.md exactly (end-exclusive hours, factor = remaining fraction). Then implement scripts/paraphrase_check.py: call app.interpreter.interpret_notes([note], {"capacity_kwh": capacity, ...}) per item, compare with 0.01 tolerance, print accuracy, avg latency, and each failure (note, expected, got).
**Check:** `python scripts/paraphrase_check.py` runs. Send the file to Tamjid after pushing; report at 1:40.
**Commit:** `git add data/paraphrases.json scripts/paraphrase_check.py && git commit -m "jubayer: step 4 paraphrase set" && git push`
**Done when:** Tamjid can run the 40-note accuracy check.

### Step 5 — API tests ⏱ 1:45–2:05
**Goal:** Cover health, errors, and the exact response shape.
**বাংলায়:** API-র ঠিক এবং ভুল ইনপুটের টেস্ট লেখো।
**Paste into Puku:** Implement tests/test_api.py with FastAPI TestClient: /health 200 {"status":"ok"}; invalid JSON -> 400; 23 hours -> 400; 0 notes -> 400; 4 notes -> 400; duplicate hour -> 400; valid sample -> 200 with exactly the 7 response keys, 24 plan entries, entries in note_index order.
**Check:** `pytest tests/test_api.py -q` passes.
**Commit:** `git add tests/test_api.py && git commit -m "jubayer: step 5 API tests" && git push`
**Done when:** All listed API behaviors are tested.

### Step 6 — README ⏱ 2:05–2:45
**Goal:** Write a complete README for judges and teammates.
**বাংলায়:** ১০ নম্বরের README লেখো।
**Paste into Puku:** Write README.md: overview; architecture diagram (text) LLM -> guardrails -> LP optimizer -> replay validator; model/provider; LLM role; guardrails list; optimizer (scipy HiGHS LP) formulation summary; env var names (no values); clean local quickstart (clone, venv, install, .env, run); curl for /health and /optimize-energy; public-sample test command + expected result; pytest command; Docker pull/run with exact image tag placeholder; project structure + team ownership; dependencies & credits (FastAPI, scipy, openai SDK, AI assistants used); known limitations; secret handling.
**Check:** Review every command and link; `pytest -q` passes.
**Commit:** `git add README.md && git commit -m "jubayer: step 6 README" && git push`
**Done when:** Someone new can run and understand the project from README alone.

### Step 7 — After freeze: live test + Docker push ⏱ 2:45–3:15
**Goal:** Verify the live API and publish a tagged Docker image.
**বাংলায়:** লাইভ টেস্ট চালাও এবং Docker image প্রকাশ করো।
**Paste into Puku:** Run python scripts/run_samples.py https://<live-url> until all pass with p95 < 5 s; report to Alif. Build and push with `docker build -t <dockerhub-user>/gridwise:v1 . && docker push <dockerhub-user>/gridwise:v1`; test `docker pull` and `docker run -p 8000:8000 -e LLM_API_KEY=... -e LLM_MODEL=... <image>` then `/health`; put the exact tag in README.
**Check:** Live sample runner passes and pulled image serves `/health`.
**Commit:** `git add README.md && git commit -m "jubayer: step 7 image tag" && git push` (only if README changed).
**Done when:** Alif has the live test result and exact image tag.

### Step 8 — Video ⏱ 3:15–3:45
**Goal:** Produce a video of at most three minutes.
**বাংলায়:** তিন মিনিটের ডেমো ভিডিও বানাও।
**Paste into Puku:** Write docs/VIDEO_SCRIPT.md: a 3-minute script (problem 30s, architecture 60s, LLM->guardrails->optimizer demo 60s, how to run/test 30s). Record screen + voice, max 3:00, upload, give link to Alif.
**Check:** Watch the uploaded video; duration ≤ 3:00 and link opens.
**Commit:** `git add docs/VIDEO_SCRIPT.md && git commit -m "jubayer: step 8 video script" && git push`
**Done when:** Alif has the working video link.
