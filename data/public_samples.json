{
  "_meta": {
    "title": "GridWise — Public LLM-Assisted Sample Case Pack",
    "event": "BUP CSE Fest 2026 · Hackathon · Online Preliminary",
    "version": "2.0",
    "endpoint": "POST /optimize-energy",
    "case_count": 10,
    "compatible_with": {
      "problem_statement": "BUP_CSE_FEST_2026_Preliminary_Problem_Statement_GridWise_LLM",
      "participant_guide": "BUP_CSE_FEST_2026_Participant_Guide_and_Evaluation_Rubric_GridWise_LLM"
    },
    "description": "Ten fully worked public examples for the LLM-assisted GridWise preliminary. Each case includes 1–3 operator notes, the expected machine-checkable directive interpretation, and one valid optimal 24-hour reference schedule. These are public examples only and are not hidden judge cases.",
    "how_to_use": [
      "Read the full Problem Statement and Participant Guide before using this pack.",
      "POST each case.input object to POST /optimize-energy.",
      "Compare directive_interpretation against the public reference semantics. Free-text explanation wording does not need to match byte-for-byte.",
      "Replay the returned hourly_plan against the interpreted directives, effective solar, battery rules, energy balance, and end-of-day neutrality.",
      "Equivalent optimal schedules are accepted; the hourly action sequence does not need to match the reference schedule byte-for-byte.",
      "Do not hard-code public note wording, case IDs, numeric values, or reference schedules. Hidden notes may paraphrase the same directive."
    ],
    "schema_notes": {
      "input_required_fields": [
        "scenario_id",
        "operator_notes",
        "hours",
        "battery"
      ],
      "operator_notes": "Array of 1–3 non-empty natural-language strings.",
      "hour_required_fields": [
        "hour",
        "demand_kwh",
        "solar_kwh",
        "tariff_bdt_per_kwh"
      ],
      "battery_required_fields": [
        "capacity_kwh",
        "initial_energy_kwh",
        "minimum_energy_kwh",
        "max_charge_kwh_per_hour",
        "max_discharge_kwh_per_hour"
      ],
      "output_required_fields": [
        "scenario_id",
        "directive_interpretation",
        "hourly_plan",
        "total_grid_kwh",
        "total_cost_bdt",
        "peak_grid_kwh",
        "plan_summary"
      ],
      "directive_interpretation_required_fields": [
        "note_index",
        "applies",
        "directive_type",
        "structured_adjustment",
        "explanation"
      ],
      "hourly_plan_required_fields": [
        "hour",
        "grid_kwh",
        "solar_used_kwh",
        "battery_action",
        "battery_kwh",
        "battery_energy_after_kwh"
      ]
    },
    "allowed_enums": {
      "directive_type": [
        "solar_reduction",
        "minimum_battery_reserve",
        "no_charge_window",
        "no_discharge_window",
        "max_grid_window",
        "no_op"
      ],
      "battery_action": [
        "charge",
        "discharge",
        "idle"
      ]
    },
    "interpretation_rules": [
      "Return exactly one directive_interpretation entry per operator note, in note_index order.",
      "For no_op: applies must be false and structured_adjustment must be null.",
      "For every non-no_op directive: applies must be true.",
      "Directive hours must be unique integers from 0 through 23 in ascending order.",
      "Time windows are start-inclusive and end-exclusive: 1 PM to 3 PM maps to hours [13, 14].",
      "For solar_reduction, factor is the usable fraction remaining. An 80% reduction means factor = 0.2.",
      "The LLM interpretation must be validated deterministically before directives are applied to optimization."
    ],
    "constraint_reminders": [
      "hours and hourly_plan must each contain exactly 24 unique entries for hours 0 through 23.",
      "Every hour must satisfy: grid_kwh + solar_used_kwh + battery_discharge_kwh = demand_kwh + battery_charge_kwh.",
      "solar_used_kwh must not exceed effective solar after any solar_reduction directive is applied.",
      "Battery energy must remain between the active minimum reserve and capacity.",
      "battery_kwh must respect the hourly charge/discharge rate limit and must be 0 for idle.",
      "no_charge_window forces battery charge to 0 in the listed hours.",
      "no_discharge_window forces battery discharge to 0 in the listed hours.",
      "minimum_battery_reserve raises the minimum allowed battery_energy_after_kwh in the listed hours.",
      "max_grid_window caps grid_kwh in each listed hour.",
      "At the end of hour 23, battery_energy_after_kwh must equal initial_energy_kwh.",
      "total_grid_kwh, total_cost_bdt, and peak_grid_kwh must match values recalculated from hourly_plan.",
      "Absolute differences up to 0.01 kWh or 0.01 BDT are treated as equivalent unless the official judge package specifies a stricter value."
    ],
    "equivalence_note": "The expected_output for each case is one valid optimal reference result. Another schedule may also be accepted if it satisfies the same directive ground truth and all GridWise constraints and achieves equivalent optimal cost within the official tolerance."
  },
  "cases": [
    {
      "id": "SAMPLE-01",
      "label": "Solar cleaning + distractor",
      "input": {
        "scenario_id": "SAMPLE-01",
        "operator_notes": [
          "Facilities will wash the rooftop solar panels from noon until 2 PM. During cleaning, usable solar should be treated as roughly 25% of the forecast.",
          "The sports office moved next month's registration deadline."
        ],
        "hours": [
          {
            "hour": 0,
            "demand_kwh": 90,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 1,
            "demand_kwh": 85,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 2,
            "demand_kwh": 80,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 3,
            "demand_kwh": 80,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 4,
            "demand_kwh": 85,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 5,
            "demand_kwh": 95,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 6,
            "demand_kwh": 110,
            "solar_kwh": 5,
            "tariff_bdt_per_kwh": 8
          },
          {
            "hour": 7,
            "demand_kwh": 130,
            "solar_kwh": 20,
            "tariff_bdt_per_kwh": 10
          },
          {
            "hour": 8,
            "demand_kwh": 150,
            "solar_kwh": 50,
            "tariff_bdt_per_kwh": 12
          },
          {
            "hour": 9,
            "demand_kwh": 165,
            "solar_kwh": 90,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 10,
            "demand_kwh": 175,
            "solar_kwh": 130,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 11,
            "demand_kwh": 180,
            "solar_kwh": 160,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 12,
            "demand_kwh": 185,
            "solar_kwh": 180,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 13,
            "demand_kwh": 180,
            "solar_kwh": 170,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 14,
            "demand_kwh": 170,
            "solar_kwh": 140,
            "tariff_bdt_per_kwh": 13
          },
          {
            "hour": 15,
            "demand_kwh": 165,
            "solar_kwh": 90,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 16,
            "demand_kwh": 170,
            "solar_kwh": 45,
            "tariff_bdt_per_kwh": 18
          },
          {
            "hour": 17,
            "demand_kwh": 185,
            "solar_kwh": 10,
            "tariff_bdt_per_kwh": 22
          },
          {
            "hour": 18,
            "demand_kwh": 205,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 28
          },
          {
            "hour": 19,
            "demand_kwh": 215,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 30
          },
          {
            "hour": 20,
            "demand_kwh": 205,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 26
          },
          {
            "hour": 21,
            "demand_kwh": 175,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 18
          },
          {
            "hour": 22,
            "demand_kwh": 135,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 10
          },
          {
            "hour": 23,
            "demand_kwh": 105,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 7
          }
        ],
        "battery": {
          "capacity_kwh": 220,
          "initial_energy_kwh": 110,
          "minimum_energy_kwh": 40,
          "max_charge_kwh_per_hour": 50,
          "max_discharge_kwh_per_hour": 50
        }
      },
      "expected_output": {
        "scenario_id": "SAMPLE-01",
        "directive_interpretation": [
          {
            "note_index": 0,
            "applies": true,
            "directive_type": "solar_reduction",
            "structured_adjustment": {
              "hours": [
                12,
                13
              ],
              "factor": 0.25
            },
            "explanation": "Solar availability is reduced to 25% during the panel-cleaning window."
          },
          {
            "note_index": 1,
            "applies": false,
            "directive_type": "no_op",
            "structured_adjustment": null,
            "explanation": "This note does not affect today's 24-hour energy schedule."
          }
        ],
        "hourly_plan": [
          {
            "hour": 0,
            "grid_kwh": 90,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 110
          },
          {
            "hour": 1,
            "grid_kwh": 45,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 40,
            "battery_energy_after_kwh": 70
          },
          {
            "hour": 2,
            "grid_kwh": 130,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 120
          },
          {
            "hour": 3,
            "grid_kwh": 130,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 170
          },
          {
            "hour": 4,
            "grid_kwh": 135,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 5,
            "grid_kwh": 95,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 6,
            "grid_kwh": 105,
            "solar_used_kwh": 5,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 7,
            "grid_kwh": 110,
            "solar_used_kwh": 20,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 8,
            "grid_kwh": 100,
            "solar_used_kwh": 50,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 9,
            "grid_kwh": 75,
            "solar_used_kwh": 90,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 10,
            "grid_kwh": 0,
            "solar_used_kwh": 130,
            "battery_action": "discharge",
            "battery_kwh": 45,
            "battery_energy_after_kwh": 175
          },
          {
            "hour": 11,
            "grid_kwh": 0,
            "solar_used_kwh": 160,
            "battery_action": "discharge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 155
          },
          {
            "hour": 12,
            "grid_kwh": 90,
            "solar_used_kwh": 45,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 105
          },
          {
            "hour": 13,
            "grid_kwh": 152.5,
            "solar_used_kwh": 42.5,
            "battery_action": "charge",
            "battery_kwh": 15,
            "battery_energy_after_kwh": 120
          },
          {
            "hour": 14,
            "grid_kwh": 80,
            "solar_used_kwh": 140,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 170
          },
          {
            "hour": 15,
            "grid_kwh": 125,
            "solar_used_kwh": 90,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 16,
            "grid_kwh": 125,
            "solar_used_kwh": 45,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 17,
            "grid_kwh": 145,
            "solar_used_kwh": 10,
            "battery_action": "discharge",
            "battery_kwh": 30,
            "battery_energy_after_kwh": 190
          },
          {
            "hour": 18,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 140
          },
          {
            "hour": 19,
            "grid_kwh": 165,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 90
          },
          {
            "hour": 20,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 40
          },
          {
            "hour": 21,
            "grid_kwh": 175,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 40
          },
          {
            "hour": 22,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 60
          },
          {
            "hour": 23,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 110
          }
        ],
        "total_grid_kwh": 2692.5,
        "total_cost_bdt": 38365,
        "peak_grid_kwh": 175,
        "plan_summary": "Uses the reduced midday solar availability, ignores the unrelated note, and shifts battery energy toward higher-tariff hours while restoring the initial battery level."
      },
      "rationale": "Tests one relevant solar-reduction note plus one realistic distractor. The first note reduces usable solar to 25% for hours 12 and 13; the second must be no_op. The reference schedule optimizes against the reduced solar profile."
    },
    {
      "id": "SAMPLE-02",
      "label": "Battery charging maintenance",
      "input": {
        "scenario_id": "SAMPLE-02",
        "operator_notes": [
          "The battery charger will be isolated from 2 AM until 5 AM for electrical maintenance."
        ],
        "hours": [
          {
            "hour": 0,
            "demand_kwh": 100,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 1,
            "demand_kwh": 95,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 2,
            "demand_kwh": 90,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 4
          },
          {
            "hour": 3,
            "demand_kwh": 90,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 4
          },
          {
            "hour": 4,
            "demand_kwh": 95,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 4
          },
          {
            "hour": 5,
            "demand_kwh": 105,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 6,
            "demand_kwh": 120,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 7
          },
          {
            "hour": 7,
            "demand_kwh": 135,
            "solar_kwh": 10,
            "tariff_bdt_per_kwh": 9
          },
          {
            "hour": 8,
            "demand_kwh": 145,
            "solar_kwh": 30,
            "tariff_bdt_per_kwh": 11
          },
          {
            "hour": 9,
            "demand_kwh": 155,
            "solar_kwh": 55,
            "tariff_bdt_per_kwh": 13
          },
          {
            "hour": 10,
            "demand_kwh": 165,
            "solar_kwh": 80,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 11,
            "demand_kwh": 175,
            "solar_kwh": 100,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 12,
            "demand_kwh": 180,
            "solar_kwh": 110,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 13,
            "demand_kwh": 175,
            "solar_kwh": 105,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 14,
            "demand_kwh": 165,
            "solar_kwh": 85,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 15,
            "demand_kwh": 160,
            "solar_kwh": 60,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 16,
            "demand_kwh": 170,
            "solar_kwh": 30,
            "tariff_bdt_per_kwh": 19
          },
          {
            "hour": 17,
            "demand_kwh": 190,
            "solar_kwh": 10,
            "tariff_bdt_per_kwh": 24
          },
          {
            "hour": 18,
            "demand_kwh": 210,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 31
          },
          {
            "hour": 19,
            "demand_kwh": 220,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 33
          },
          {
            "hour": 20,
            "demand_kwh": 210,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 29
          },
          {
            "hour": 21,
            "demand_kwh": 180,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 20
          },
          {
            "hour": 22,
            "demand_kwh": 145,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 11
          },
          {
            "hour": 23,
            "demand_kwh": 115,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 7
          }
        ],
        "battery": {
          "capacity_kwh": 200,
          "initial_energy_kwh": 70,
          "minimum_energy_kwh": 30,
          "max_charge_kwh_per_hour": 55,
          "max_discharge_kwh_per_hour": 55
        }
      },
      "expected_output": {
        "scenario_id": "SAMPLE-02",
        "directive_interpretation": [
          {
            "note_index": 0,
            "applies": true,
            "directive_type": "no_charge_window",
            "structured_adjustment": {
              "hours": [
                2,
                3,
                4
              ]
            },
            "explanation": "Battery charging is unavailable during maintenance."
          }
        ],
        "hourly_plan": [
          {
            "hour": 0,
            "grid_kwh": 120,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 90
          },
          {
            "hour": 1,
            "grid_kwh": 150,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 145
          },
          {
            "hour": 2,
            "grid_kwh": 90,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 145
          },
          {
            "hour": 3,
            "grid_kwh": 90,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 145
          },
          {
            "hour": 4,
            "grid_kwh": 95,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 145
          },
          {
            "hour": 5,
            "grid_kwh": 160,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 6,
            "grid_kwh": 120,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 7,
            "grid_kwh": 125,
            "solar_used_kwh": 10,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 8,
            "grid_kwh": 115,
            "solar_used_kwh": 30,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 9,
            "grid_kwh": 100,
            "solar_used_kwh": 55,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 10,
            "grid_kwh": 85,
            "solar_used_kwh": 80,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 11,
            "grid_kwh": 20,
            "solar_used_kwh": 100,
            "battery_action": "discharge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 145
          },
          {
            "hour": 12,
            "grid_kwh": 15,
            "solar_used_kwh": 110,
            "battery_action": "discharge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 90
          },
          {
            "hour": 13,
            "grid_kwh": 70,
            "solar_used_kwh": 105,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 90
          },
          {
            "hour": 14,
            "grid_kwh": 135,
            "solar_used_kwh": 85,
            "battery_action": "charge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 145
          },
          {
            "hour": 15,
            "grid_kwh": 155,
            "solar_used_kwh": 60,
            "battery_action": "charge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 16,
            "grid_kwh": 140,
            "solar_used_kwh": 30,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 17,
            "grid_kwh": 175,
            "solar_used_kwh": 10,
            "battery_action": "discharge",
            "battery_kwh": 5,
            "battery_energy_after_kwh": 195
          },
          {
            "hour": 18,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 140
          },
          {
            "hour": 19,
            "grid_kwh": 165,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 85
          },
          {
            "hour": 20,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 30
          },
          {
            "hour": 21,
            "grid_kwh": 180,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 30
          },
          {
            "hour": 22,
            "grid_kwh": 145,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 30
          },
          {
            "hour": 23,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 40,
            "battery_energy_after_kwh": 70
          }
        ],
        "total_grid_kwh": 2915,
        "total_cost_bdt": 42885,
        "peak_grid_kwh": 180,
        "plan_summary": "Avoids charging during the maintenance window, charges in other economical hours, and discharges during expensive periods while preserving all battery limits."
      },
      "rationale": "Tests a hard no-charge maintenance window. Charging must be zero for hours 2, 3, and 4, so the optimizer must use other hours for any economically useful charging."
    },
    {
      "id": "SAMPLE-03",
      "label": "Emergency reserve as percentage",
      "input": {
        "scenario_id": "SAMPLE-03",
        "operator_notes": [
          "Keep at least 50% of the battery capacity stored in the battery from 6 PM until 9 PM for emergency operations."
        ],
        "hours": [
          {
            "hour": 0,
            "demand_kwh": 90,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 1,
            "demand_kwh": 85,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 2,
            "demand_kwh": 80,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 3,
            "demand_kwh": 80,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 4,
            "demand_kwh": 85,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 5,
            "demand_kwh": 95,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 6,
            "demand_kwh": 110,
            "solar_kwh": 5,
            "tariff_bdt_per_kwh": 8
          },
          {
            "hour": 7,
            "demand_kwh": 130,
            "solar_kwh": 20,
            "tariff_bdt_per_kwh": 10
          },
          {
            "hour": 8,
            "demand_kwh": 150,
            "solar_kwh": 50,
            "tariff_bdt_per_kwh": 12
          },
          {
            "hour": 9,
            "demand_kwh": 165,
            "solar_kwh": 90,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 10,
            "demand_kwh": 175,
            "solar_kwh": 130,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 11,
            "demand_kwh": 180,
            "solar_kwh": 160,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 12,
            "demand_kwh": 185,
            "solar_kwh": 180,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 13,
            "demand_kwh": 180,
            "solar_kwh": 170,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 14,
            "demand_kwh": 170,
            "solar_kwh": 140,
            "tariff_bdt_per_kwh": 13
          },
          {
            "hour": 15,
            "demand_kwh": 165,
            "solar_kwh": 90,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 16,
            "demand_kwh": 170,
            "solar_kwh": 45,
            "tariff_bdt_per_kwh": 18
          },
          {
            "hour": 17,
            "demand_kwh": 185,
            "solar_kwh": 10,
            "tariff_bdt_per_kwh": 22
          },
          {
            "hour": 18,
            "demand_kwh": 205,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 28
          },
          {
            "hour": 19,
            "demand_kwh": 215,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 30
          },
          {
            "hour": 20,
            "demand_kwh": 205,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 26
          },
          {
            "hour": 21,
            "demand_kwh": 175,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 18
          },
          {
            "hour": 22,
            "demand_kwh": 135,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 10
          },
          {
            "hour": 23,
            "demand_kwh": 105,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 7
          }
        ],
        "battery": {
          "capacity_kwh": 200,
          "initial_energy_kwh": 120,
          "minimum_energy_kwh": 40,
          "max_charge_kwh_per_hour": 50,
          "max_discharge_kwh_per_hour": 50
        }
      },
      "expected_output": {
        "scenario_id": "SAMPLE-03",
        "directive_interpretation": [
          {
            "note_index": 0,
            "applies": true,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {
              "hours": [
                18,
                19,
                20
              ],
              "minimum_energy_kwh": 100
            },
            "explanation": "Half of the 200 kWh battery is 100 kWh, which must remain available during the stated window."
          }
        ],
        "hourly_plan": [
          {
            "hour": 0,
            "grid_kwh": 70,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 100
          },
          {
            "hour": 1,
            "grid_kwh": 35,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 50
          },
          {
            "hour": 2,
            "grid_kwh": 130,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 100
          },
          {
            "hour": 3,
            "grid_kwh": 130,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 150
          },
          {
            "hour": 4,
            "grid_kwh": 135,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 5,
            "grid_kwh": 95,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 6,
            "grid_kwh": 105,
            "solar_used_kwh": 5,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 7,
            "grid_kwh": 110,
            "solar_used_kwh": 20,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 8,
            "grid_kwh": 100,
            "solar_used_kwh": 50,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 9,
            "grid_kwh": 75,
            "solar_used_kwh": 90,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 10,
            "grid_kwh": 0,
            "solar_used_kwh": 130,
            "battery_action": "discharge",
            "battery_kwh": 45,
            "battery_energy_after_kwh": 155
          },
          {
            "hour": 11,
            "grid_kwh": 0,
            "solar_used_kwh": 160,
            "battery_action": "discharge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 135
          },
          {
            "hour": 12,
            "grid_kwh": 0,
            "solar_used_kwh": 180,
            "battery_action": "discharge",
            "battery_kwh": 5,
            "battery_energy_after_kwh": 130
          },
          {
            "hour": 13,
            "grid_kwh": 10,
            "solar_used_kwh": 170,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 130
          },
          {
            "hour": 14,
            "grid_kwh": 80,
            "solar_used_kwh": 140,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 180
          },
          {
            "hour": 15,
            "grid_kwh": 95,
            "solar_used_kwh": 90,
            "battery_action": "charge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 16,
            "grid_kwh": 125,
            "solar_used_kwh": 45,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 17,
            "grid_kwh": 175,
            "solar_used_kwh": 10,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 200
          },
          {
            "hour": 18,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 150
          },
          {
            "hour": 19,
            "grid_kwh": 165,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 100
          },
          {
            "hour": 20,
            "grid_kwh": 205,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 100
          },
          {
            "hour": 21,
            "grid_kwh": 125,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 50
          },
          {
            "hour": 22,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 70
          },
          {
            "hour": 23,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 120
          }
        ],
        "total_grid_kwh": 2430,
        "total_cost_bdt": 35480,
        "peak_grid_kwh": 205,
        "plan_summary": "Maintains the 100 kWh emergency reserve during the evening window and optimizes the remaining battery flexibility around tariff peaks."
      },
      "rationale": "Tests relative-language interpretation. The 50% reserve must be converted from the 200 kWh battery capacity into a 100 kWh minimum reserve for hours 18, 19, and 20."
    },
    {
      "id": "SAMPLE-04",
      "label": "No-discharge protection test",
      "input": {
        "scenario_id": "SAMPLE-04",
        "operator_notes": [
          "For protection testing, the battery must not discharge from 6 PM until 8 PM."
        ],
        "hours": [
          {
            "hour": 0,
            "demand_kwh": 95,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 7
          },
          {
            "hour": 1,
            "demand_kwh": 90,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 2,
            "demand_kwh": 85,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 3,
            "demand_kwh": 85,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 4,
            "demand_kwh": 90,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 5,
            "demand_kwh": 100,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 6,
            "demand_kwh": 115,
            "solar_kwh": 5,
            "tariff_bdt_per_kwh": 8
          },
          {
            "hour": 7,
            "demand_kwh": 130,
            "solar_kwh": 15,
            "tariff_bdt_per_kwh": 10
          },
          {
            "hour": 8,
            "demand_kwh": 145,
            "solar_kwh": 40,
            "tariff_bdt_per_kwh": 12
          },
          {
            "hour": 9,
            "demand_kwh": 155,
            "solar_kwh": 75,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 10,
            "demand_kwh": 165,
            "solar_kwh": 110,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 11,
            "demand_kwh": 175,
            "solar_kwh": 145,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 12,
            "demand_kwh": 180,
            "solar_kwh": 165,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 13,
            "demand_kwh": 175,
            "solar_kwh": 155,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 14,
            "demand_kwh": 170,
            "solar_kwh": 125,
            "tariff_bdt_per_kwh": 13
          },
          {
            "hour": 15,
            "demand_kwh": 165,
            "solar_kwh": 80,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 16,
            "demand_kwh": 175,
            "solar_kwh": 35,
            "tariff_bdt_per_kwh": 17
          },
          {
            "hour": 17,
            "demand_kwh": 195,
            "solar_kwh": 5,
            "tariff_bdt_per_kwh": 21
          },
          {
            "hour": 18,
            "demand_kwh": 215,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 29
          },
          {
            "hour": 19,
            "demand_kwh": 225,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 32
          },
          {
            "hour": 20,
            "demand_kwh": 215,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 30
          },
          {
            "hour": 21,
            "demand_kwh": 185,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 20
          },
          {
            "hour": 22,
            "demand_kwh": 150,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 11
          },
          {
            "hour": 23,
            "demand_kwh": 120,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 8
          }
        ],
        "battery": {
          "capacity_kwh": 230,
          "initial_energy_kwh": 130,
          "minimum_energy_kwh": 40,
          "max_charge_kwh_per_hour": 55,
          "max_discharge_kwh_per_hour": 55
        }
      },
      "expected_output": {
        "scenario_id": "SAMPLE-04",
        "directive_interpretation": [
          {
            "note_index": 0,
            "applies": true,
            "directive_type": "no_discharge_window",
            "structured_adjustment": {
              "hours": [
                18,
                19
              ]
            },
            "explanation": "Battery discharge is disabled during the protection-test window."
          }
        ],
        "hourly_plan": [
          {
            "hour": 0,
            "grid_kwh": 40,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 75
          },
          {
            "hour": 1,
            "grid_kwh": 90,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 75
          },
          {
            "hour": 2,
            "grid_kwh": 85,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 75
          },
          {
            "hour": 3,
            "grid_kwh": 140,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 130
          },
          {
            "hour": 4,
            "grid_kwh": 145,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 185
          },
          {
            "hour": 5,
            "grid_kwh": 145,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 45,
            "battery_energy_after_kwh": 230
          },
          {
            "hour": 6,
            "grid_kwh": 110,
            "solar_used_kwh": 5,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 230
          },
          {
            "hour": 7,
            "grid_kwh": 115,
            "solar_used_kwh": 15,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 230
          },
          {
            "hour": 8,
            "grid_kwh": 105,
            "solar_used_kwh": 40,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 230
          },
          {
            "hour": 9,
            "grid_kwh": 80,
            "solar_used_kwh": 75,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 230
          },
          {
            "hour": 10,
            "grid_kwh": 0,
            "solar_used_kwh": 110,
            "battery_action": "discharge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 175
          },
          {
            "hour": 11,
            "grid_kwh": 0,
            "solar_used_kwh": 145,
            "battery_action": "discharge",
            "battery_kwh": 30,
            "battery_energy_after_kwh": 145
          },
          {
            "hour": 12,
            "grid_kwh": 0,
            "solar_used_kwh": 165,
            "battery_action": "discharge",
            "battery_kwh": 15,
            "battery_energy_after_kwh": 130
          },
          {
            "hour": 13,
            "grid_kwh": 20,
            "solar_used_kwh": 155,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 130
          },
          {
            "hour": 14,
            "grid_kwh": 100,
            "solar_used_kwh": 125,
            "battery_action": "charge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 185
          },
          {
            "hour": 15,
            "grid_kwh": 130,
            "solar_used_kwh": 80,
            "battery_action": "charge",
            "battery_kwh": 45,
            "battery_energy_after_kwh": 230
          },
          {
            "hour": 16,
            "grid_kwh": 115,
            "solar_used_kwh": 35,
            "battery_action": "discharge",
            "battery_kwh": 25,
            "battery_energy_after_kwh": 205
          },
          {
            "hour": 17,
            "grid_kwh": 135,
            "solar_used_kwh": 5,
            "battery_action": "discharge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 150
          },
          {
            "hour": 18,
            "grid_kwh": 215,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 150
          },
          {
            "hour": 19,
            "grid_kwh": 225,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 150
          },
          {
            "hour": 20,
            "grid_kwh": 160,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 95
          },
          {
            "hour": 21,
            "grid_kwh": 130,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 40
          },
          {
            "hour": 22,
            "grid_kwh": 185,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 35,
            "battery_energy_after_kwh": 75
          },
          {
            "hour": 23,
            "grid_kwh": 175,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 130
          }
        ],
        "total_grid_kwh": 2645,
        "total_cost_bdt": 40495,
        "peak_grid_kwh": 225,
        "plan_summary": "Keeps battery discharge at zero during protection testing and uses available battery flexibility outside that window to reduce grid cost."
      },
      "rationale": "Tests a hard no-discharge window during an expensive period. The schedule must keep discharge at zero for hours 18 and 19 even if discharging there would otherwise reduce cost."
    },
    {
      "id": "SAMPLE-05",
      "label": "Temporary feeder grid cap",
      "input": {
        "scenario_id": "SAMPLE-05",
        "operator_notes": [
          "From 6 PM until 9 PM, campus grid import must not exceed 155 kWh in any hour because the feeder is operating under a temporary limit."
        ],
        "hours": [
          {
            "hour": 0,
            "demand_kwh": 90,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 1,
            "demand_kwh": 85,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 2,
            "demand_kwh": 80,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 3,
            "demand_kwh": 80,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 4,
            "demand_kwh": 85,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 5,
            "demand_kwh": 95,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 6,
            "demand_kwh": 110,
            "solar_kwh": 5,
            "tariff_bdt_per_kwh": 8
          },
          {
            "hour": 7,
            "demand_kwh": 130,
            "solar_kwh": 20,
            "tariff_bdt_per_kwh": 10
          },
          {
            "hour": 8,
            "demand_kwh": 150,
            "solar_kwh": 50,
            "tariff_bdt_per_kwh": 12
          },
          {
            "hour": 9,
            "demand_kwh": 165,
            "solar_kwh": 90,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 10,
            "demand_kwh": 175,
            "solar_kwh": 130,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 11,
            "demand_kwh": 180,
            "solar_kwh": 160,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 12,
            "demand_kwh": 185,
            "solar_kwh": 180,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 13,
            "demand_kwh": 180,
            "solar_kwh": 170,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 14,
            "demand_kwh": 170,
            "solar_kwh": 140,
            "tariff_bdt_per_kwh": 13
          },
          {
            "hour": 15,
            "demand_kwh": 165,
            "solar_kwh": 90,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 16,
            "demand_kwh": 170,
            "solar_kwh": 45,
            "tariff_bdt_per_kwh": 18
          },
          {
            "hour": 17,
            "demand_kwh": 185,
            "solar_kwh": 10,
            "tariff_bdt_per_kwh": 22
          },
          {
            "hour": 18,
            "demand_kwh": 205,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 28
          },
          {
            "hour": 19,
            "demand_kwh": 215,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 30
          },
          {
            "hour": 20,
            "demand_kwh": 205,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 26
          },
          {
            "hour": 21,
            "demand_kwh": 175,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 18
          },
          {
            "hour": 22,
            "demand_kwh": 135,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 10
          },
          {
            "hour": 23,
            "demand_kwh": 105,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 7
          }
        ],
        "battery": {
          "capacity_kwh": 240,
          "initial_energy_kwh": 120,
          "minimum_energy_kwh": 30,
          "max_charge_kwh_per_hour": 60,
          "max_discharge_kwh_per_hour": 60
        }
      },
      "expected_output": {
        "scenario_id": "SAMPLE-05",
        "directive_interpretation": [
          {
            "note_index": 0,
            "applies": true,
            "directive_type": "max_grid_window",
            "structured_adjustment": {
              "hours": [
                18,
                19,
                20
              ],
              "max_grid_kwh": 155
            },
            "explanation": "Grid import is capped at 155 kWh for each hour in the feeder-restriction window."
          }
        ],
        "hourly_plan": [
          {
            "hour": 0,
            "grid_kwh": 90,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 120
          },
          {
            "hour": 1,
            "grid_kwh": 25,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 60
          },
          {
            "hour": 2,
            "grid_kwh": 140,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 120
          },
          {
            "hour": 3,
            "grid_kwh": 140,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 180
          },
          {
            "hour": 4,
            "grid_kwh": 145,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 5,
            "grid_kwh": 95,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 6,
            "grid_kwh": 105,
            "solar_used_kwh": 5,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 7,
            "grid_kwh": 110,
            "solar_used_kwh": 20,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 8,
            "grid_kwh": 100,
            "solar_used_kwh": 50,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 9,
            "grid_kwh": 75,
            "solar_used_kwh": 90,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 10,
            "grid_kwh": 0,
            "solar_used_kwh": 130,
            "battery_action": "discharge",
            "battery_kwh": 45,
            "battery_energy_after_kwh": 195
          },
          {
            "hour": 11,
            "grid_kwh": 0,
            "solar_used_kwh": 160,
            "battery_action": "discharge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 175
          },
          {
            "hour": 12,
            "grid_kwh": 0,
            "solar_used_kwh": 180,
            "battery_action": "discharge",
            "battery_kwh": 5,
            "battery_energy_after_kwh": 170
          },
          {
            "hour": 13,
            "grid_kwh": 20,
            "solar_used_kwh": 170,
            "battery_action": "charge",
            "battery_kwh": 10,
            "battery_energy_after_kwh": 180
          },
          {
            "hour": 14,
            "grid_kwh": 90,
            "solar_used_kwh": 140,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 15,
            "grid_kwh": 75,
            "solar_used_kwh": 90,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 16,
            "grid_kwh": 125,
            "solar_used_kwh": 45,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 17,
            "grid_kwh": 145,
            "solar_used_kwh": 10,
            "battery_action": "discharge",
            "battery_kwh": 30,
            "battery_energy_after_kwh": 210
          },
          {
            "hour": 18,
            "grid_kwh": 145,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 150
          },
          {
            "hour": 19,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 90
          },
          {
            "hour": 20,
            "grid_kwh": 145,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 30
          },
          {
            "hour": 21,
            "grid_kwh": 175,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 30
          },
          {
            "hour": 22,
            "grid_kwh": 165,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 30,
            "battery_energy_after_kwh": 60
          },
          {
            "hour": 23,
            "grid_kwh": 165,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 120
          }
        ],
        "total_grid_kwh": 2430,
        "total_cost_bdt": 33950,
        "peak_grid_kwh": 175,
        "plan_summary": "Respects the 155 kWh feeder import cap during the evening window by preparing sufficient battery energy in advance, then restores end-of-day battery neutrality."
      },
      "rationale": "Tests a hard grid-import cap. Grid usage must stay at or below 155 kWh in each of hours 18, 19, and 20, which requires the optimizer to prepare sufficient battery energy beforehand."
    },
    {
      "id": "SAMPLE-06",
      "label": "Multiple notes with distractor",
      "input": {
        "scenario_id": "SAMPLE-06",
        "operator_notes": [
          "Cloud cover during panel inspection will leave about half of the forecast solar output from 10 AM until noon.",
          "The charging circuit will be unavailable from 2 PM until 4 PM.",
          "The library is extending book-return hours next week."
        ],
        "hours": [
          {
            "hour": 0,
            "demand_kwh": 85,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 1,
            "demand_kwh": 80,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 2,
            "demand_kwh": 80,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 3,
            "demand_kwh": 80,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 4,
            "demand_kwh": 85,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 5,
            "demand_kwh": 95,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 7
          },
          {
            "hour": 6,
            "demand_kwh": 110,
            "solar_kwh": 5,
            "tariff_bdt_per_kwh": 8
          },
          {
            "hour": 7,
            "demand_kwh": 125,
            "solar_kwh": 20,
            "tariff_bdt_per_kwh": 9
          },
          {
            "hour": 8,
            "demand_kwh": 140,
            "solar_kwh": 55,
            "tariff_bdt_per_kwh": 11
          },
          {
            "hour": 9,
            "demand_kwh": 155,
            "solar_kwh": 100,
            "tariff_bdt_per_kwh": 13
          },
          {
            "hour": 10,
            "demand_kwh": 165,
            "solar_kwh": 150,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 11,
            "demand_kwh": 175,
            "solar_kwh": 190,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 12,
            "demand_kwh": 180,
            "solar_kwh": 210,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 13,
            "demand_kwh": 175,
            "solar_kwh": 200,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 14,
            "demand_kwh": 170,
            "solar_kwh": 160,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 15,
            "demand_kwh": 165,
            "solar_kwh": 100,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 16,
            "demand_kwh": 175,
            "solar_kwh": 50,
            "tariff_bdt_per_kwh": 18
          },
          {
            "hour": 17,
            "demand_kwh": 190,
            "solar_kwh": 15,
            "tariff_bdt_per_kwh": 22
          },
          {
            "hour": 18,
            "demand_kwh": 205,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 27
          },
          {
            "hour": 19,
            "demand_kwh": 215,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 29
          },
          {
            "hour": 20,
            "demand_kwh": 205,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 27
          },
          {
            "hour": 21,
            "demand_kwh": 175,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 18
          },
          {
            "hour": 22,
            "demand_kwh": 140,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 10
          },
          {
            "hour": 23,
            "demand_kwh": 110,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 7
          }
        ],
        "battery": {
          "capacity_kwh": 220,
          "initial_energy_kwh": 100,
          "minimum_energy_kwh": 35,
          "max_charge_kwh_per_hour": 50,
          "max_discharge_kwh_per_hour": 50
        }
      },
      "expected_output": {
        "scenario_id": "SAMPLE-06",
        "directive_interpretation": [
          {
            "note_index": 0,
            "applies": true,
            "directive_type": "solar_reduction",
            "structured_adjustment": {
              "hours": [
                10,
                11
              ],
              "factor": 0.5
            },
            "explanation": "Usable solar is reduced to 50% during the stated inspection window."
          },
          {
            "note_index": 1,
            "applies": true,
            "directive_type": "no_charge_window",
            "structured_adjustment": {
              "hours": [
                14,
                15
              ]
            },
            "explanation": "Battery charging is unavailable during the charging-circuit outage."
          },
          {
            "note_index": 2,
            "applies": false,
            "directive_type": "no_op",
            "structured_adjustment": null,
            "explanation": "This note does not affect today's energy schedule."
          }
        ],
        "hourly_plan": [
          {
            "hour": 0,
            "grid_kwh": 105,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 120
          },
          {
            "hour": 1,
            "grid_kwh": 130,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 170
          },
          {
            "hour": 2,
            "grid_kwh": 130,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 3,
            "grid_kwh": 80,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 4,
            "grid_kwh": 85,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 5,
            "grid_kwh": 95,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 6,
            "grid_kwh": 105,
            "solar_used_kwh": 5,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 7,
            "grid_kwh": 105,
            "solar_used_kwh": 20,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 8,
            "grid_kwh": 85,
            "solar_used_kwh": 55,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 9,
            "grid_kwh": 55,
            "solar_used_kwh": 100,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 10,
            "grid_kwh": 85,
            "solar_used_kwh": 75,
            "battery_action": "discharge",
            "battery_kwh": 5,
            "battery_energy_after_kwh": 215
          },
          {
            "hour": 11,
            "grid_kwh": 30,
            "solar_used_kwh": 95,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 165
          },
          {
            "hour": 12,
            "grid_kwh": 0,
            "solar_used_kwh": 210,
            "battery_action": "charge",
            "battery_kwh": 30,
            "battery_energy_after_kwh": 195
          },
          {
            "hour": 13,
            "grid_kwh": 0,
            "solar_used_kwh": 200,
            "battery_action": "charge",
            "battery_kwh": 25,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 14,
            "grid_kwh": 10,
            "solar_used_kwh": 160,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 15,
            "grid_kwh": 65,
            "solar_used_kwh": 100,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 16,
            "grid_kwh": 125,
            "solar_used_kwh": 50,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 17,
            "grid_kwh": 140,
            "solar_used_kwh": 15,
            "battery_action": "discharge",
            "battery_kwh": 35,
            "battery_energy_after_kwh": 185
          },
          {
            "hour": 18,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 135
          },
          {
            "hour": 19,
            "grid_kwh": 165,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 85
          },
          {
            "hour": 20,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 35
          },
          {
            "hour": 21,
            "grid_kwh": 175,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 35
          },
          {
            "hour": 22,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 15,
            "battery_energy_after_kwh": 50
          },
          {
            "hour": 23,
            "grid_kwh": 160,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 100
          }
        ],
        "total_grid_kwh": 2395,
        "total_cost_bdt": 34090,
        "peak_grid_kwh": 175,
        "plan_summary": "Applies both the 50% solar reduction and the no-charge maintenance window, ignores the unrelated library note, and optimizes the remaining feasible schedule."
      },
      "rationale": "Tests multiple notes in one request: a 50% solar reduction, a no-charge window, and an unrelated distractor. All three notes require interpretation entries, but only the first two affect optimization."
    },
    {
      "id": "SAMPLE-07",
      "label": "Reserve plus transformer cap",
      "input": {
        "scenario_id": "SAMPLE-07",
        "operator_notes": [
          "Keep at least 90 kWh in the battery from 6 PM until 10 PM for emergency services.",
          "The evening transformer limit is 180 kWh of grid import from 7 PM until 9 PM."
        ],
        "hours": [
          {
            "hour": 0,
            "demand_kwh": 100,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 1,
            "demand_kwh": 95,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 2,
            "demand_kwh": 90,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 3,
            "demand_kwh": 90,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 4,
            "demand_kwh": 95,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 5,
            "demand_kwh": 105,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 6,
            "demand_kwh": 120,
            "solar_kwh": 5,
            "tariff_bdt_per_kwh": 8
          },
          {
            "hour": 7,
            "demand_kwh": 135,
            "solar_kwh": 20,
            "tariff_bdt_per_kwh": 10
          },
          {
            "hour": 8,
            "demand_kwh": 150,
            "solar_kwh": 50,
            "tariff_bdt_per_kwh": 12
          },
          {
            "hour": 9,
            "demand_kwh": 165,
            "solar_kwh": 90,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 10,
            "demand_kwh": 175,
            "solar_kwh": 135,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 11,
            "demand_kwh": 185,
            "solar_kwh": 170,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 12,
            "demand_kwh": 190,
            "solar_kwh": 190,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 13,
            "demand_kwh": 185,
            "solar_kwh": 180,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 14,
            "demand_kwh": 175,
            "solar_kwh": 145,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 15,
            "demand_kwh": 170,
            "solar_kwh": 95,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 16,
            "demand_kwh": 180,
            "solar_kwh": 45,
            "tariff_bdt_per_kwh": 18
          },
          {
            "hour": 17,
            "demand_kwh": 195,
            "solar_kwh": 10,
            "tariff_bdt_per_kwh": 23
          },
          {
            "hour": 18,
            "demand_kwh": 210,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 29
          },
          {
            "hour": 19,
            "demand_kwh": 225,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 32
          },
          {
            "hour": 20,
            "demand_kwh": 215,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 30
          },
          {
            "hour": 21,
            "demand_kwh": 185,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 21
          },
          {
            "hour": 22,
            "demand_kwh": 145,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 11
          },
          {
            "hour": 23,
            "demand_kwh": 115,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 7
          }
        ],
        "battery": {
          "capacity_kwh": 250,
          "initial_energy_kwh": 150,
          "minimum_energy_kwh": 40,
          "max_charge_kwh_per_hour": 60,
          "max_discharge_kwh_per_hour": 60
        }
      },
      "expected_output": {
        "scenario_id": "SAMPLE-07",
        "directive_interpretation": [
          {
            "note_index": 0,
            "applies": true,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {
              "hours": [
                18,
                19,
                20,
                21
              ],
              "minimum_energy_kwh": 90
            },
            "explanation": "A 90 kWh emergency reserve is required for the full stated window."
          },
          {
            "note_index": 1,
            "applies": true,
            "directive_type": "max_grid_window",
            "structured_adjustment": {
              "hours": [
                19,
                20
              ],
              "max_grid_kwh": 180
            },
            "explanation": "Grid import is capped at 180 kWh in the transformer-limit window."
          }
        ],
        "hourly_plan": [
          {
            "hour": 0,
            "grid_kwh": 80,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 130
          },
          {
            "hour": 1,
            "grid_kwh": 35,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 70
          },
          {
            "hour": 2,
            "grid_kwh": 150,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 130
          },
          {
            "hour": 3,
            "grid_kwh": 150,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 190
          },
          {
            "hour": 4,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 250
          },
          {
            "hour": 5,
            "grid_kwh": 105,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 250
          },
          {
            "hour": 6,
            "grid_kwh": 115,
            "solar_used_kwh": 5,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 250
          },
          {
            "hour": 7,
            "grid_kwh": 115,
            "solar_used_kwh": 20,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 250
          },
          {
            "hour": 8,
            "grid_kwh": 100,
            "solar_used_kwh": 50,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 250
          },
          {
            "hour": 9,
            "grid_kwh": 75,
            "solar_used_kwh": 90,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 250
          },
          {
            "hour": 10,
            "grid_kwh": 0,
            "solar_used_kwh": 135,
            "battery_action": "discharge",
            "battery_kwh": 40,
            "battery_energy_after_kwh": 210
          },
          {
            "hour": 11,
            "grid_kwh": 0,
            "solar_used_kwh": 170,
            "battery_action": "discharge",
            "battery_kwh": 15,
            "battery_energy_after_kwh": 195
          },
          {
            "hour": 12,
            "grid_kwh": 0,
            "solar_used_kwh": 190,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 195
          },
          {
            "hour": 13,
            "grid_kwh": 0,
            "solar_used_kwh": 180,
            "battery_action": "discharge",
            "battery_kwh": 5,
            "battery_energy_after_kwh": 190
          },
          {
            "hour": 14,
            "grid_kwh": 90,
            "solar_used_kwh": 145,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 250
          },
          {
            "hour": 15,
            "grid_kwh": 75,
            "solar_used_kwh": 95,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 250
          },
          {
            "hour": 16,
            "grid_kwh": 135,
            "solar_used_kwh": 45,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 250
          },
          {
            "hour": 17,
            "grid_kwh": 185,
            "solar_used_kwh": 10,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 250
          },
          {
            "hour": 18,
            "grid_kwh": 170,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 40,
            "battery_energy_after_kwh": 210
          },
          {
            "hour": 19,
            "grid_kwh": 165,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 150
          },
          {
            "hour": 20,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 90
          },
          {
            "hour": 21,
            "grid_kwh": 185,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 90
          },
          {
            "hour": 22,
            "grid_kwh": 145,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 90
          },
          {
            "hour": 23,
            "grid_kwh": 175,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 150
          }
        ],
        "total_grid_kwh": 2560,
        "total_cost_bdt": 38550,
        "peak_grid_kwh": 185,
        "plan_summary": "Meets both the 90 kWh emergency reserve and the evening grid-import cap, using battery scheduling to satisfy the tighter combined operating conditions."
      },
      "rationale": "Tests two simultaneous hard directives: a 90 kWh battery reserve from 18:00 until 22:00 and a 180 kWh grid-import cap for hours 19 and 20. The schedule must satisfy both."
    },
    {
      "id": "SAMPLE-08",
      "label": "Separate charge/discharge outages",
      "input": {
        "scenario_id": "SAMPLE-08",
        "operator_notes": [
          "Battery charging is disabled from 11 AM until 1 PM while technicians inspect the charger.",
          "Do not discharge the battery from 5 PM until 7 PM during relay testing."
        ],
        "hours": [
          {
            "hour": 0,
            "demand_kwh": 90,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 1,
            "demand_kwh": 85,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 2,
            "demand_kwh": 80,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 3,
            "demand_kwh": 80,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 4,
            "demand_kwh": 85,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 5,
            "demand_kwh": 95,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 6,
            "demand_kwh": 110,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 8
          },
          {
            "hour": 7,
            "demand_kwh": 125,
            "solar_kwh": 15,
            "tariff_bdt_per_kwh": 10
          },
          {
            "hour": 8,
            "demand_kwh": 140,
            "solar_kwh": 40,
            "tariff_bdt_per_kwh": 12
          },
          {
            "hour": 9,
            "demand_kwh": 155,
            "solar_kwh": 80,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 10,
            "demand_kwh": 165,
            "solar_kwh": 120,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 11,
            "demand_kwh": 175,
            "solar_kwh": 155,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 12,
            "demand_kwh": 180,
            "solar_kwh": 175,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 13,
            "demand_kwh": 175,
            "solar_kwh": 165,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 14,
            "demand_kwh": 165,
            "solar_kwh": 130,
            "tariff_bdt_per_kwh": 13
          },
          {
            "hour": 15,
            "demand_kwh": 160,
            "solar_kwh": 85,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 16,
            "demand_kwh": 170,
            "solar_kwh": 40,
            "tariff_bdt_per_kwh": 18
          },
          {
            "hour": 17,
            "demand_kwh": 190,
            "solar_kwh": 10,
            "tariff_bdt_per_kwh": 24
          },
          {
            "hour": 18,
            "demand_kwh": 210,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 30
          },
          {
            "hour": 19,
            "demand_kwh": 220,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 31
          },
          {
            "hour": 20,
            "demand_kwh": 210,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 28
          },
          {
            "hour": 21,
            "demand_kwh": 180,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 19
          },
          {
            "hour": 22,
            "demand_kwh": 145,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 10
          },
          {
            "hour": 23,
            "demand_kwh": 115,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 7
          }
        ],
        "battery": {
          "capacity_kwh": 210,
          "initial_energy_kwh": 105,
          "minimum_energy_kwh": 35,
          "max_charge_kwh_per_hour": 50,
          "max_discharge_kwh_per_hour": 50
        }
      },
      "expected_output": {
        "scenario_id": "SAMPLE-08",
        "directive_interpretation": [
          {
            "note_index": 0,
            "applies": true,
            "directive_type": "no_charge_window",
            "structured_adjustment": {
              "hours": [
                11,
                12
              ]
            },
            "explanation": "Battery charging is disabled during charger inspection."
          },
          {
            "note_index": 1,
            "applies": true,
            "directive_type": "no_discharge_window",
            "structured_adjustment": {
              "hours": [
                17,
                18
              ]
            },
            "explanation": "Battery discharge is disabled during relay testing."
          }
        ],
        "hourly_plan": [
          {
            "hour": 0,
            "grid_kwh": 90,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 105
          },
          {
            "hour": 1,
            "grid_kwh": 40,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 45,
            "battery_energy_after_kwh": 60
          },
          {
            "hour": 2,
            "grid_kwh": 130,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 110
          },
          {
            "hour": 3,
            "grid_kwh": 130,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 160
          },
          {
            "hour": 4,
            "grid_kwh": 135,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 210
          },
          {
            "hour": 5,
            "grid_kwh": 95,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 210
          },
          {
            "hour": 6,
            "grid_kwh": 110,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 210
          },
          {
            "hour": 7,
            "grid_kwh": 110,
            "solar_used_kwh": 15,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 210
          },
          {
            "hour": 8,
            "grid_kwh": 100,
            "solar_used_kwh": 40,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 210
          },
          {
            "hour": 9,
            "grid_kwh": 75,
            "solar_used_kwh": 80,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 210
          },
          {
            "hour": 10,
            "grid_kwh": 0,
            "solar_used_kwh": 120,
            "battery_action": "discharge",
            "battery_kwh": 45,
            "battery_energy_after_kwh": 165
          },
          {
            "hour": 11,
            "grid_kwh": 0,
            "solar_used_kwh": 155,
            "battery_action": "discharge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 145
          },
          {
            "hour": 12,
            "grid_kwh": 0,
            "solar_used_kwh": 175,
            "battery_action": "discharge",
            "battery_kwh": 5,
            "battery_energy_after_kwh": 140
          },
          {
            "hour": 13,
            "grid_kwh": 10,
            "solar_used_kwh": 165,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 140
          },
          {
            "hour": 14,
            "grid_kwh": 85,
            "solar_used_kwh": 130,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 190
          },
          {
            "hour": 15,
            "grid_kwh": 95,
            "solar_used_kwh": 85,
            "battery_action": "charge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 210
          },
          {
            "hour": 16,
            "grid_kwh": 105,
            "solar_used_kwh": 40,
            "battery_action": "discharge",
            "battery_kwh": 25,
            "battery_energy_after_kwh": 185
          },
          {
            "hour": 17,
            "grid_kwh": 180,
            "solar_used_kwh": 10,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 185
          },
          {
            "hour": 18,
            "grid_kwh": 210,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 185
          },
          {
            "hour": 19,
            "grid_kwh": 170,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 135
          },
          {
            "hour": 20,
            "grid_kwh": 160,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 85
          },
          {
            "hour": 21,
            "grid_kwh": 130,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 35
          },
          {
            "hour": 22,
            "grid_kwh": 165,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 55
          },
          {
            "hour": 23,
            "grid_kwh": 165,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 105
          }
        ],
        "total_grid_kwh": 2490,
        "total_cost_bdt": 37665,
        "peak_grid_kwh": 210,
        "plan_summary": "Observes separate no-charge and no-discharge maintenance windows while still shifting battery energy to lower total grid cost."
      },
      "rationale": "Tests separate charging and discharging outages. Charging is prohibited for hours 11 and 12, while discharging is prohibited for hours 17 and 18."
    },
    {
      "id": "SAMPLE-09",
      "label": "Reduction wording normalization",
      "input": {
        "scenario_id": "SAMPLE-09",
        "operator_notes": [
          "Expect an 80% reduction in rooftop solar between 11 AM and 2 PM because of inverter work.",
          "The student affairs office will publish club notices tomorrow."
        ],
        "hours": [
          {
            "hour": 0,
            "demand_kwh": 90,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 1,
            "demand_kwh": 85,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 2,
            "demand_kwh": 80,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 3,
            "demand_kwh": 80,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 4,
            "demand_kwh": 85,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 5,
            "demand_kwh": 95,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 6,
            "demand_kwh": 105,
            "solar_kwh": 5,
            "tariff_bdt_per_kwh": 8
          },
          {
            "hour": 7,
            "demand_kwh": 120,
            "solar_kwh": 25,
            "tariff_bdt_per_kwh": 10
          },
          {
            "hour": 8,
            "demand_kwh": 135,
            "solar_kwh": 65,
            "tariff_bdt_per_kwh": 12
          },
          {
            "hour": 9,
            "demand_kwh": 150,
            "solar_kwh": 120,
            "tariff_bdt_per_kwh": 13
          },
          {
            "hour": 10,
            "demand_kwh": 165,
            "solar_kwh": 180,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 11,
            "demand_kwh": 175,
            "solar_kwh": 230,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 12,
            "demand_kwh": 180,
            "solar_kwh": 260,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 13,
            "demand_kwh": 175,
            "solar_kwh": 240,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 14,
            "demand_kwh": 165,
            "solar_kwh": 190,
            "tariff_bdt_per_kwh": 13
          },
          {
            "hour": 15,
            "demand_kwh": 160,
            "solar_kwh": 120,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 16,
            "demand_kwh": 170,
            "solar_kwh": 55,
            "tariff_bdt_per_kwh": 18
          },
          {
            "hour": 17,
            "demand_kwh": 185,
            "solar_kwh": 10,
            "tariff_bdt_per_kwh": 22
          },
          {
            "hour": 18,
            "demand_kwh": 200,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 27
          },
          {
            "hour": 19,
            "demand_kwh": 210,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 29
          },
          {
            "hour": 20,
            "demand_kwh": 200,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 26
          },
          {
            "hour": 21,
            "demand_kwh": 170,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 18
          },
          {
            "hour": 22,
            "demand_kwh": 135,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 10
          },
          {
            "hour": 23,
            "demand_kwh": 105,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 7
          }
        ],
        "battery": {
          "capacity_kwh": 240,
          "initial_energy_kwh": 120,
          "minimum_energy_kwh": 40,
          "max_charge_kwh_per_hour": 60,
          "max_discharge_kwh_per_hour": 60
        }
      },
      "expected_output": {
        "scenario_id": "SAMPLE-09",
        "directive_interpretation": [
          {
            "note_index": 0,
            "applies": true,
            "directive_type": "solar_reduction",
            "structured_adjustment": {
              "hours": [
                11,
                12,
                13
              ],
              "factor": 0.2
            },
            "explanation": "An 80% reduction leaves 20% usable solar during the stated hours."
          },
          {
            "note_index": 1,
            "applies": false,
            "directive_type": "no_op",
            "structured_adjustment": null,
            "explanation": "This note does not affect today's energy schedule."
          }
        ],
        "hourly_plan": [
          {
            "hour": 0,
            "grid_kwh": 90,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 120
          },
          {
            "hour": 1,
            "grid_kwh": 25,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 60
          },
          {
            "hour": 2,
            "grid_kwh": 140,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 120
          },
          {
            "hour": 3,
            "grid_kwh": 140,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 180
          },
          {
            "hour": 4,
            "grid_kwh": 145,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 5,
            "grid_kwh": 95,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 6,
            "grid_kwh": 100,
            "solar_used_kwh": 5,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 7,
            "grid_kwh": 95,
            "solar_used_kwh": 25,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 8,
            "grid_kwh": 70,
            "solar_used_kwh": 65,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 9,
            "grid_kwh": 15,
            "solar_used_kwh": 120,
            "battery_action": "discharge",
            "battery_kwh": 15,
            "battery_energy_after_kwh": 225
          },
          {
            "hour": 10,
            "grid_kwh": 0,
            "solar_used_kwh": 180,
            "battery_action": "charge",
            "battery_kwh": 15,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 11,
            "grid_kwh": 69,
            "solar_used_kwh": 46,
            "battery_action": "discharge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 180
          },
          {
            "hour": 12,
            "grid_kwh": 68,
            "solar_used_kwh": 52,
            "battery_action": "discharge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 120
          },
          {
            "hour": 13,
            "grid_kwh": 127,
            "solar_used_kwh": 48,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 120
          },
          {
            "hour": 14,
            "grid_kwh": 35,
            "solar_used_kwh": 190,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 180
          },
          {
            "hour": 15,
            "grid_kwh": 100,
            "solar_used_kwh": 120,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 16,
            "grid_kwh": 115,
            "solar_used_kwh": 55,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 17,
            "grid_kwh": 155,
            "solar_used_kwh": 10,
            "battery_action": "discharge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 220
          },
          {
            "hour": 18,
            "grid_kwh": 140,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 160
          },
          {
            "hour": 19,
            "grid_kwh": 150,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 100
          },
          {
            "hour": 20,
            "grid_kwh": 140,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 40
          },
          {
            "hour": 21,
            "grid_kwh": 170,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 40
          },
          {
            "hour": 22,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 60
          },
          {
            "hour": 23,
            "grid_kwh": 165,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 60,
            "battery_energy_after_kwh": 120
          }
        ],
        "total_grid_kwh": 2504,
        "total_cost_bdt": 34873,
        "peak_grid_kwh": 170,
        "plan_summary": "Correctly converts an 80% solar reduction into a 0.2 usable-solar factor, ignores the distractor note, and optimizes using the reduced solar profile."
      },
      "rationale": "Tests percentage normalization. An 80% solar reduction means only 20% remains usable, so factor = 0.2 for hours 11, 12, and 13. The second note is a distractor and must be no_op."
    },
    {
      "id": "SAMPLE-10",
      "label": "Multi-constraint evening operation",
      "input": {
        "scenario_id": "SAMPLE-10",
        "operator_notes": [
          "The data center requires at least 80 kWh to remain in the battery from 6 PM until 10 PM.",
          "Grid intake must stay at or below 190 kWh from 7 PM until 10 PM while the substation is constrained.",
          "A seminar room booking was moved to next week."
        ],
        "hours": [
          {
            "hour": 0,
            "demand_kwh": 105,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 7
          },
          {
            "hour": 1,
            "demand_kwh": 100,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 2,
            "demand_kwh": 95,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 3,
            "demand_kwh": 95,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 4,
            "demand_kwh": 100,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 5
          },
          {
            "hour": 5,
            "demand_kwh": 110,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 6
          },
          {
            "hour": 6,
            "demand_kwh": 125,
            "solar_kwh": 5,
            "tariff_bdt_per_kwh": 8
          },
          {
            "hour": 7,
            "demand_kwh": 140,
            "solar_kwh": 20,
            "tariff_bdt_per_kwh": 10
          },
          {
            "hour": 8,
            "demand_kwh": 155,
            "solar_kwh": 50,
            "tariff_bdt_per_kwh": 12
          },
          {
            "hour": 9,
            "demand_kwh": 170,
            "solar_kwh": 90,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 10,
            "demand_kwh": 180,
            "solar_kwh": 130,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 11,
            "demand_kwh": 190,
            "solar_kwh": 165,
            "tariff_bdt_per_kwh": 17
          },
          {
            "hour": 12,
            "demand_kwh": 195,
            "solar_kwh": 185,
            "tariff_bdt_per_kwh": 16
          },
          {
            "hour": 13,
            "demand_kwh": 190,
            "solar_kwh": 175,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 14,
            "demand_kwh": 180,
            "solar_kwh": 140,
            "tariff_bdt_per_kwh": 14
          },
          {
            "hour": 15,
            "demand_kwh": 175,
            "solar_kwh": 90,
            "tariff_bdt_per_kwh": 15
          },
          {
            "hour": 16,
            "demand_kwh": 185,
            "solar_kwh": 40,
            "tariff_bdt_per_kwh": 19
          },
          {
            "hour": 17,
            "demand_kwh": 200,
            "solar_kwh": 10,
            "tariff_bdt_per_kwh": 24
          },
          {
            "hour": 18,
            "demand_kwh": 215,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 30
          },
          {
            "hour": 19,
            "demand_kwh": 230,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 34
          },
          {
            "hour": 20,
            "demand_kwh": 220,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 31
          },
          {
            "hour": 21,
            "demand_kwh": 190,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 21
          },
          {
            "hour": 22,
            "demand_kwh": 150,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 11
          },
          {
            "hour": 23,
            "demand_kwh": 120,
            "solar_kwh": 0,
            "tariff_bdt_per_kwh": 8
          }
        ],
        "battery": {
          "capacity_kwh": 260,
          "initial_energy_kwh": 140,
          "minimum_energy_kwh": 40,
          "max_charge_kwh_per_hour": 65,
          "max_discharge_kwh_per_hour": 65
        }
      },
      "expected_output": {
        "scenario_id": "SAMPLE-10",
        "directive_interpretation": [
          {
            "note_index": 0,
            "applies": true,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {
              "hours": [
                18,
                19,
                20,
                21
              ],
              "minimum_energy_kwh": 80
            },
            "explanation": "An 80 kWh reserve is required during the data-center backup window."
          },
          {
            "note_index": 1,
            "applies": true,
            "directive_type": "max_grid_window",
            "structured_adjustment": {
              "hours": [
                19,
                20,
                21
              ],
              "max_grid_kwh": 190
            },
            "explanation": "Grid import is capped at 190 kWh during the substation constraint."
          },
          {
            "note_index": 2,
            "applies": false,
            "directive_type": "no_op",
            "structured_adjustment": null,
            "explanation": "This note does not affect today's energy schedule."
          }
        ],
        "hourly_plan": [
          {
            "hour": 0,
            "grid_kwh": 40,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 65,
            "battery_energy_after_kwh": 75
          },
          {
            "hour": 1,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 55,
            "battery_energy_after_kwh": 130
          },
          {
            "hour": 2,
            "grid_kwh": 95,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 130
          },
          {
            "hour": 3,
            "grid_kwh": 160,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 65,
            "battery_energy_after_kwh": 195
          },
          {
            "hour": 4,
            "grid_kwh": 165,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 65,
            "battery_energy_after_kwh": 260
          },
          {
            "hour": 5,
            "grid_kwh": 110,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 260
          },
          {
            "hour": 6,
            "grid_kwh": 120,
            "solar_used_kwh": 5,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 260
          },
          {
            "hour": 7,
            "grid_kwh": 120,
            "solar_used_kwh": 20,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 260
          },
          {
            "hour": 8,
            "grid_kwh": 105,
            "solar_used_kwh": 50,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 260
          },
          {
            "hour": 9,
            "grid_kwh": 80,
            "solar_used_kwh": 90,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 260
          },
          {
            "hour": 10,
            "grid_kwh": 0,
            "solar_used_kwh": 130,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 210
          },
          {
            "hour": 11,
            "grid_kwh": 0,
            "solar_used_kwh": 165,
            "battery_action": "discharge",
            "battery_kwh": 25,
            "battery_energy_after_kwh": 185
          },
          {
            "hour": 12,
            "grid_kwh": 0,
            "solar_used_kwh": 185,
            "battery_action": "discharge",
            "battery_kwh": 10,
            "battery_energy_after_kwh": 175
          },
          {
            "hour": 13,
            "grid_kwh": 15,
            "solar_used_kwh": 175,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 175
          },
          {
            "hour": 14,
            "grid_kwh": 105,
            "solar_used_kwh": 140,
            "battery_action": "charge",
            "battery_kwh": 65,
            "battery_energy_after_kwh": 240
          },
          {
            "hour": 15,
            "grid_kwh": 105,
            "solar_used_kwh": 90,
            "battery_action": "charge",
            "battery_kwh": 20,
            "battery_energy_after_kwh": 260
          },
          {
            "hour": 16,
            "grid_kwh": 145,
            "solar_used_kwh": 40,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 260
          },
          {
            "hour": 17,
            "grid_kwh": 190,
            "solar_used_kwh": 10,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 260
          },
          {
            "hour": 18,
            "grid_kwh": 165,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 50,
            "battery_energy_after_kwh": 210
          },
          {
            "hour": 19,
            "grid_kwh": 165,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 65,
            "battery_energy_after_kwh": 145
          },
          {
            "hour": 20,
            "grid_kwh": 155,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 65,
            "battery_energy_after_kwh": 80
          },
          {
            "hour": 21,
            "grid_kwh": 190,
            "solar_used_kwh": 0,
            "battery_action": "idle",
            "battery_kwh": 0,
            "battery_energy_after_kwh": 80
          },
          {
            "hour": 22,
            "grid_kwh": 145,
            "solar_used_kwh": 0,
            "battery_action": "discharge",
            "battery_kwh": 5,
            "battery_energy_after_kwh": 75
          },
          {
            "hour": 23,
            "grid_kwh": 185,
            "solar_used_kwh": 0,
            "battery_action": "charge",
            "battery_kwh": 65,
            "battery_energy_after_kwh": 140
          }
        ],
        "total_grid_kwh": 2715,
        "total_cost_bdt": 41620,
        "peak_grid_kwh": 190,
        "plan_summary": "Combines an evening battery-reserve requirement with a substation grid cap, ignores the unrelated seminar note, and returns a valid low-cost plan."
      },
      "rationale": "Tests a combined evening operating condition with an 80 kWh reserve, a 190 kWh grid-import cap, and one irrelevant note. The optimizer must satisfy the two hard directives while ignoring the distractor."
    }
  ]
}