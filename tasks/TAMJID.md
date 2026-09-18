# Tamjid — LLM engineer

**Mission:** Turn English operator notes into correct structured directives despite paraphrasing. This is worth the most points (25, and it affects 25 more). **Own:** `app/interpreter/core.py`, `prompt.py`, `llm_client.py`, `normalize.py`, `fallback.py`, `tests/test_interpreter.py`. **Do not touch:** everything else, including `app/interpreter/__init__.py`.

Read `AGENTS.md`, `docs/CONTRACTS.md`, and `tasks/HOW_TO_WORK.md` first. Times are relative to hackathon start. Report at 0:50, 1:40, and 2:30. Feature freeze: 2:45.

## Technical spec

The LLM returns JSON shaped like `{"notes":[{"note_index":0,"directive_type":"...","start_hour":0,"end_hour":1,"solar_remaining_fraction":null,"reserve_kwh":null,"reserve_percent_of_capacity":null,"max_grid_kwh":null,"explanation":"..."}]}`. Unused fields are `null`. The LLM gives start/end; code builds the hours list and converts percent of capacity to kWh.

End is exclusive. Noon = 12. Midnight is 24 as an end and 0 as a start. Accept `13:00`; infer AM/PM from context where needed (solar/panel work is daytime). A wrap-around window such as 10 PM to 2 AM becomes `[0,1,22,23]`. A factor is the *remaining* solar fraction: “80% reduction”, “drop to 20%”, and “one-fifth of normal” all mean 0.2; “half” means 0.5. A note about menus, events, or next week/month that does not affect this 24-hour solar/battery/grid schedule is `no_op`.

Guardrails allow only the six types in `docs/CONTRACTS.md`; require each `note_index` exactly once, non-empty unique ascending hours in 0–23, factor in `[0,1]`, reserve in `[0,capacity]`, and finite non-negative max grid. If an LLM call fails or a note is invalid, retry once, then use conservative regex fallback for that note, then `no_op` with explanation `Could not be interpreted safely`. Never raise or invent a type.

### Step 1 — Setup + first LLM call ⏱ 0:15–0:30
**Goal:** Make the first OpenAI-compatible JSON call without leaking the key.
**বাংলায়:** প্রজেক্ট চালু করো আর LLM key দিয়ে একটা টেস্ট কল করো।
**Paste into Puku:** Read AGENTS.md, docs/CONTRACTS.md and tasks/TAMJID.md. Implement app/interpreter/llm_client.py: function call_llm(system: str, user: str) -> dict using the openai SDK with env LLM_API_KEY, LLM_BASE_URL (optional), LLM_MODEL; temperature 0; JSON mode; timeout 10s; 1 retry; never log the key. Add a __main__ block that sends a tiny test prompt and prints the parsed JSON.
**Check:** `python -m app.interpreter.llm_client` prints valid JSON in under 3 seconds when the provider is reachable.
**Commit:** `git add app/interpreter/llm_client.py && git commit -m "tamjid: step 1 llm client" && git push`
**Done when:** The test call works and no credential is printed.

### Step 2 — Prompt ⏱ 0:30–0:55
**Goal:** Write the system prompt and message builder with varied examples.
**বাংলায়:** LLM-এর জন্য নিয়ম আর উদাহরণসহ system prompt লেখো।
**Paste into Puku:** Implement Step 2 of tasks/TAMJID.md in app/interpreter/prompt.py: SYSTEM_PROMPT and build_user_message(notes, capacity_kwh). Include all 6 types, time rules, factor rules, relevance rule, the raw output JSON schema, and 10 varied few-shot examples that are NOT copies of the public sample notes.
**Check:** `python -c "from app.interpreter.prompt import SYSTEM_PROMPT; print(len(SYSTEM_PROMPT))"` works. Report to Alif at 0:50.
**Commit:** `git add app/interpreter/prompt.py && git commit -m "tamjid: step 2 prompt" && git push`
**Done when:** Prompt covers the specification and has 10 original examples.

### Step 3 — Guardrails ⏱ 0:55–1:25
**Goal:** Normalize and validate the LLM output into the public interpretation shape.
**বাংলায়:** LLM-এর উত্তর যাচাই আর ঠিক format-এ রূপান্তর।
**Paste into Puku:** Implement Step 3 of tasks/TAMJID.md in app/interpreter/normalize.py: normalize(raw: dict, notes: list[str], capacity: float) -> (entries, bad_indexes). Build hours from start/end (wrap-around, 24), percent->kWh, all guardrails, final entry shape from docs/CONTRACTS.md. Unit tests with mocked raw outputs in tests/test_interpreter.py: wrap-around, midnight, percent->kWh, invalid factor, missing note, unknown type, duplicate index.
**Check:** `pytest tests/test_interpreter.py -q` passes.
**Commit:** `git add app/interpreter/normalize.py tests/test_interpreter.py && git commit -m "tamjid: step 3 guardrails" && git push`
**Done when:** Valid entries normalize, and invalid entries are identified by index.

### Step 4 — Wire it up ⏱ 1:25–1:50
**Goal:** Replace the no-op stub with the LLM, retry, fallback, and cache pipeline.
**বাংলায়:** সব অংশ জোড়া লাগিয়ে আসল interpret_notes চালু করো।
**Paste into Puku:** Implement Step 4 of tasks/TAMJID.md: replace the stub in app/interpreter/core.py. interpret_notes calls the LLM once for all notes, normalizes, retries once on failure, uses fallback.py (simple regex backup per note) and finally no_op. In-memory cache keyed by (tuple(notes), capacity). Never raise.
**Check:** `python scripts/run_samples.py` (from Jubayer, or pull main) → 10/10 interpretation match; or use a quick script over `data/public_samples.json`. Report at 1:40.
**Commit:** `git add app/interpreter/core.py app/interpreter/fallback.py tests/test_interpreter.py && git commit -m "tamjid: step 4 interpreter" && git push`
**Done when:** All public interpretations match and failures return safe no-ops.

### Step 5 — Paraphrase hardening ⏱ 1:50–2:30
**Goal:** Reach at least 90% accuracy on Jubayer's paraphrases with average latency under 3 seconds.
**বাংলায়:** অন্যভাবে লেখা নোট দিয়ে টেস্ট করে prompt উন্নত করো।
**Paste into Puku:** Run python scripts/paraphrase_check.py. For each failure, improve SYSTEM_PROMPT rules/few-shots (never hard-code the exact test sentences). Repeat until accuracy >= 90%.
**Check:** `python scripts/paraphrase_check.py` reports at least 90% accuracy and average latency under 3 seconds.
**Commit:** `git add app/interpreter/prompt.py app/interpreter/core.py app/interpreter/normalize.py app/interpreter/fallback.py tests/test_interpreter.py && git commit -m "tamjid: step 5 paraphrases" && git push`
**Done when:** Tell Alif to merge at 2:30.

### Step 6 — After freeze ⏱ 2:45–3:15
**Goal:** Fix only interpreter bugs and check live latency.
**বাংলায়:** লাইভ সার্ভিসে সময় মাপো এবং শুধু নিজের ফাইলের ভুল ঠিক করো।
**Paste into Puku:** Fix bugs only in your files; check latency on the live URL.
**Check:** `python scripts/run_samples.py <LIVE_URL>` passes with p95 under 5 seconds.
**Commit:** `git add app/interpreter/core.py app/interpreter/prompt.py app/interpreter/llm_client.py app/interpreter/normalize.py app/interpreter/fallback.py tests/test_interpreter.py && git commit -m "tamjid: step 6 live fixes" && git push` (only if files changed).
**Done when:** Live interpretation is correct and Alif has the latency report.
