# Taseen — optimizer engineer

**Mission:** Build the math engine: hours, battery, and directives → a valid, minimum-cost 24-hour plan. This part must be 100% correct. **Own:** `app/optimizer/solver.py`, `app/optimizer/replay.py`, `tests/test_optimizer.py`. **Do not touch:** everything else, including `app/optimizer/__init__.py`.

Read `AGENTS.md`, `docs/CONTRACTS.md`, and `tasks/HOW_TO_WORK.md` first. Times are relative to hackathon start. Report at 0:50, 1:40, and 2:30. Feature freeze: 2:45.

## Technical spec

Use `scipy.optimize.linprog(method="highs")`. Per hour: five variables `g, s, c, d, E`, so 120 variables total. Bounds: `g ≥ 0`; `0 ≤ s ≤ effective_solar[h]`; `0 ≤ c ≤ max_charge` (zero in no-charge hours); `0 ≤ d ≤ max_discharge` (zero in no-discharge hours); `minimum_h ≤ E ≤ capacity`; and `g ≤ cap[h]` in max-grid hours. Equalities: `g + s + d − c = demand[h]`; `E[h] − E[h−1] − c + d = 0` (previous energy at hour 0 is initial); `E[23] = initial`. Overlaps: multiply solar factors, take maximum reserve and minimum grid cap. Objective: `Σ tariff[h]·g[h] + 1e−6·Σ(c[h] + d[h])`.

Post-process: `net = c − d`. If net > `1e−7`, action is charge; if net < `−1e−7`, discharge; otherwise idle with `battery_kwh = 0`. Round to six decimals; recompute stored energy cumulatively from rounded values; set grid to `demand + charge − discharge − solar_used` (if negative, reduce solar_used); calculate totals from the final plan. On infeasibility, drop constraints in order: max-grid, reserve, no-discharge, no-charge, retrying after each removal (`status="relaxed"`). Last resort: baseline stub (`status="fallback"`). Never raise.

### Step 1 — Setup ⏱ 0:15–0:25
**Goal:** Environment ready; stub app runs; understand the LP specification.
**বাংলায়:** প্রজেক্ট চালু করে দেখো সব কাজ করছে কিনা।
**Paste into Puku:** Read AGENTS.md, docs/CONTRACTS.md and tasks/TASEEN.md. Explain the optimizer spec to me in simple words. Do not write code yet.
**Check:** `pytest -q` passes; run `uvicorn app.main:app --port 8000`, then `curl localhost:8000/health` → `{"status":"ok"}`.
**Commit:** Nothing for this setup step.
**Done when:** You understand the LP spec and the stub service works.

### Step 2 — Effective limits builder ⏱ 0:25–0:45
**Goal:** `build_limits(hours, battery, directives) -> dict` with per-hour lists `eff_solar`, `min_energy`, `max_charge`, `max_discharge`, and `max_grid` (`None` means no cap).
**বাংলায়:** directive গুলো থেকে প্রতি ঘণ্টার সীমা বের করার ফাংশন।
**Paste into Puku:** Implement Step 2 of tasks/TASEEN.md in app/optimizer/solver.py (keep the existing optimize stub working). Add unit tests in tests/test_optimizer.py for each directive type and overlaps.
**Check:** `pytest tests/test_optimizer.py -q` passes.
**Commit:** `git add app/optimizer/solver.py tests/test_optimizer.py && git commit -m "taseen: step 2 limits builder" && git push`
**Done when:** Every directive and overlap produces the expected hourly limits.

### Step 3 — LP solver ⏱ 0:45–1:20
**Goal:** Replace the stub with the real LP, post-processing, and totals.
**বাংলায়:** আসল LP দিয়ে সবচেয়ে কম খরচের প্ল্যান বানাও।
**Paste into Puku:** Implement Step 3 of tasks/TASEEN.md: replace the optimize stub with the LP solver exactly as in the Technical spec. Add a test that runs all 10 cases from data/public_samples.json using expected_output.directive_interpretation entries with applies==true as directives and asserts abs(total_cost_bdt - expected_output.total_cost_bdt) <= 0.01.
**Check:** `pytest tests/test_optimizer.py -q` → all 10 costs match.
**Commit:** `git add app/optimizer/solver.py tests/test_optimizer.py && git commit -m "taseen: step 3 LP solver" && git push`
**Done when:** All 10 costs match; tell Alif at the 1:40 checkpoint for the first merge.

### Step 4 — Replay validator ⏱ 1:20–1:50
**Goal:** Independently validate the plan: 24 unique hours; finite non-negative values; action and magnitude consistency; transitions; capacity and reserve; rate limits; effective solar; energy balance; no-charge/no-discharge/max-grid; end neutrality; totals (tolerance 0.01).
**বাংলায়:** judge-এর মতো নিজেরাই প্ল্যান যাচাই করার কোড।
**Paste into Puku:** Implement Step 4 of tasks/TASEEN.md in app/optimizer/replay.py. Add tests: all 10 samples return [], and hand-broken plans (bad balance, violated no_charge, wrong final energy, wrong totals) return violations.
**Check:** `pytest tests/test_optimizer.py -q` passes.
**Commit:** `git add app/optimizer/replay.py tests/test_optimizer.py && git commit -m "taseen: step 4 replay validator" && git push`
**Done when:** Valid samples pass and each broken plan is rejected.

### Step 5 — Robustness ⏱ 1:50–2:30
**Goal:** Handle infeasible cases and zero tariff, zero solar, huge solar, initial = capacity, minimum = initial, reserve above capacity, conflicting directives, and solve time under 200 ms.
**বাংলায়:** অদ্ভুত ইনপুটেও যেন crash না করে।
**Paste into Puku:** Implement Step 5 of tasks/TASEEN.md: infeasible fallback chain and edge-case tests. optimize() must never raise and every returned plan must pass replay_check against the directives actually applied.
**Check:** `pytest tests/test_optimizer.py -q` passes.
**Commit:** `git add app/optimizer/solver.py app/optimizer/replay.py tests/test_optimizer.py && git commit -m "taseen: step 5 robustness" && git push`
**Done when:** Edge cases pass; tell Alif to merge at 2:30.

### Step 6 — After freeze ⏱ 2:45–3:15
**Goal:** Check the live service with Jubayer; fix bugs only in your files.
**বাংলায়:** লাইভ সার্ভিসে নমুনাগুলো চালিয়ে শুধু নিজের ফাইলের ভুল ঠিক করো।
**Paste into Puku:** Run python scripts/run_samples.py <LIVE_URL> with Jubayer. Fix only bugs in your files.
**Check:** `python scripts/run_samples.py <LIVE_URL>` passes.
**Commit:** `git add app/optimizer/solver.py app/optimizer/replay.py tests/test_optimizer.py && git commit -m "taseen: step 6 live fixes" && git push` (only if files changed).
**Done when:** Live samples pass and Alif has the report.
