# GridWise — 3-Minute Demo Script

> **Total runtime:** 3:00. **Speakers:** Alif (lead, integration), Tamjid (interpreter), Taseen (optimizer), Jubayer (frontend + DevOps).
> **Format:** pre-recorded screen capture + talking head at intro and outro. **Recording resolution:** 1920×1080, 30 fps. **Audio:** single lapel mic, -16 LUFS.

| Section                | Time         | Speaker | Camera       |
|------------------------|--------------|---------|--------------|
| 1. Problem             | 0:00 – 0:30  | Alif    | talking head |
| 2. Architecture        | 0:30 – 1:30  | Tamjid  | screen share |
| 3. Frontend Demo       | 1:30 – 2:30  | Jubayer | screen share |
| 4. Run + Test          | 2:30 – 3:00  | Taseen  | screen share |

---

## 1. Problem — 30 seconds (Alif, talking head)

> Every energy operator has a stack of free-text instructions — *"cut solar between 12 and 2, hold 50% reserve from 18 to 21, never pull more than 80 kWh from the grid at peak"* — but no quick way to turn them into a verified 24-hour battery + grid schedule. Today that means either a planner who manually writes a dispatch table, or an LLM that hallucinates numbers.
>
> **GridWise is the middle ground.** Operators keep typing English. The LLM only extracts the semantic intent. Deterministic guardrails and a linear-program optimizer do the actual math, and an automated judge replays the result to prove the constraints hold.
>
> We ship one public endpoint: `POST /optimize-energy`. It accepts 24 hours of data plus 1–3 notes and returns a strict JSON schedule plus a `replay_check` that proves it.

---

## 2. Architecture — 60 seconds (Tamjid, screen share)

> *(Open the architecture diagram from the README.)*
>
> The flow is four stages, and only one of them talks to an LLM.
>
> 1. **Pydantic request schema.** Pydantic rejects malformed payloads at the door — exactly 24 hours, no duplicate hours, battery fields inside bounds. Bad input never reaches the interpreter.
>
> 2. **LLM interpreter.** We send each note to an OpenAI-compatible chat model with a strict function-call schema. It returns one of six directive types — `solar_reduction`, `minimum_battery_reserve`, `no_charge_window`, `no_discharge_window`, `max_grid_window`, or `no_op`. Nothing else.
>
> 3. **Guardrails.** Before any directive is given to the optimizer, we clamp the factor to 0–1, clamp the reserve to 0–capacity, normalise time windows to integer hours, and merge overlapping directives by taking the most restrictive of each. Notes that don't match become a `no_op`.
>
> 4. **LP optimizer.** We then solve a 24-hour linear program with HiGHS via `scipy.optimize.linprog`. Energy balance per hour, charge and discharge limits, SoC bounds, and battery neutrality at hour 23. The objective is the minimum tariff-weighted grid energy plus a tiny cycling penalty.
>
> 5. **Replay check.** On top of that, an automated judge replays the schedule hour by hour and reports any violations. If anything is off, the response says so.
>
> The LLM is the creative part. Everything else is deterministic.

---

## 3. Frontend Demo — 60 seconds (Jubayer, screen share)

> *(Open `frontend/index.html` in a clean browser window with the API running locally. Click **SAMPLE-01**.)*
>
> Here's the operator console. Three preset scenarios are one click away. I'm loading **SAMPLE-01** — a 24-hour Karachi peak-summer profile.
>
> The notes panel shows two operator instructions, paraphrased from real logbook entries:
>
> *"Panel cleaning halves solar from 12:00 to 14:00."*
> *"Reserve 50% of the battery from 18:00 until 21:00."*
>
> I hit **Optimize**...
>
> *(Response lands in ~1.2 s. Scroll to the totals and the chart.)*
>
> ...and we immediately see four totals — total cost in BDT, total grid kWh, peak hour, directive count — plus the per-note interpretation table. The directive table confirms what the LLM extracted: a `solar_reduction` factor of 0.5 on hours 12 and 13, and a `minimum_battery_reserve` of 110 kWh (50% of 220 kWh capacity) on hours 18, 19, and 20.
>
> *(Point at the chart.)*
>
> The mixed chart has stacked bars for demand split across grid, solar, and battery — and a SoC line on the right axis. You can see the battery pre-charging from solar at noon, then holding 110 kWh through the 18–20 peak.
>
> *(Click **SAMPLE-05** and re-run.)*
>
> Different profile, same console. The chart, the totals, and the directive table all update live.

---

## 4. Run + Test — 30 seconds (Taseen, screen share)

> *(Switch to a terminal pinned to the repo root.)*
>
> Three commands prove the whole thing.
>
> ```bash
> curl -s http://127.0.0.1:8000/health
> # {"status":"ok"}
>
> pytest -q
> # 27 passed in 4.2s
>
> python scripts/run_samples.py http://127.0.0.1:8000
> # 10/10 cases matched, mean cost diff 0.0000 BDT, 0 replay_check violations
> ```
>
> Twenty-seven tests across the API, the interpreter, and the optimizer all pass. The sample runner replays all ten cases from `data/public_samples.json` against a live API — same interpretation, zero cost drift, zero replay violations.
>
> *(Close on the README's `## Public API` table.)*
>
> One endpoint, one judge, one JSON. That's GridWise.

---

## Recording checklist

- [ ] Re-record intro audio in a quiet room, single lapel mic, -16 LUFS
- [ ] Confirm uvicorn is bound to `0.0.0.0:8000` before the demo (curl `/health` on camera)
- [ ] Disable OS notifications and put Slack / Discord in Do Not Disturb
- [ ] Set browser zoom to 110 % and font size 14 pt for legibility
- [ ] Pre-clear the frontend console state before recording (no leftover directives in the table)
- [ ] For `pytest`, use `-q --color=no` to keep the terminal readable
- [ ] End card: `github.com/abdullahalyf/bup-hackathon-preli` + team credits for 3 s

## B-roll suggestions (optional, ≤ 5 s each)

- Hand-written logbook note on lined paper → cut to typed note in the console
- 24-hour solar irradiance curve fading into the tariff curve
- The `replay_check` violations panel from a deliberately broken request

## Voiceover fallback

If a speaker is unavailable on recording day, their section is scripted with cue marks (`> speaker:`) so anyone on the team can read it cold. Keep the same wording — judges have already seen the README.
