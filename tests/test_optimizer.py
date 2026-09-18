from app.optimizer import optimize
from app.optimizer.solver import build_limits


def test_stub_uses_solar_then_grid():
    result = optimize(
        [{"hour": 0, "demand_kwh": 5, "solar_kwh": 2, "tariff_bdt_per_kwh": 10}],
        {"initial_energy_kwh": 3},
        [],
    )
    assert result["hourly_plan"][0]["grid_kwh"] == 3
    assert result["total_cost_bdt"] == 30
    assert result["status"] == "fallback"


def _sample_hours(solar_val=4.0):
    return [
        {"hour": h, "demand_kwh": 5.0, "solar_kwh": solar_val, "tariff_bdt_per_kwh": 8.0}
        for h in range(24)
    ]


def _sample_battery():
    return {
        "capacity_kwh": 10.0,
        "initial_energy_kwh": 5.0,
        "minimum_energy_kwh": 2.0,
        "max_charge_kwh_per_hour": 3.0,
        "max_discharge_kwh_per_hour": 3.0,
    }


def test_build_limits_baseline():
    hours = _sample_hours(4.0)
    battery = _sample_battery()
    limits = build_limits(hours, battery, [])
    assert limits["eff_solar"] == [4.0] * 24
    assert limits["min_energy"] == [2.0] * 24
    assert limits["max_charge"] == [3.0] * 24
    assert limits["max_discharge"] == [3.0] * 24
    assert limits["max_grid"] == [None] * 24


def test_build_limits_solar_reduction():
    hours = _sample_hours(4.0)
    battery = _sample_battery()
    directives = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [13, 14], "factor": 0.5},
        }
    ]
    limits = build_limits(hours, battery, directives)
    assert limits["eff_solar"][13] == 2.0
    assert limits["eff_solar"][14] == 2.0
    assert limits["eff_solar"][12] == 4.0


def test_build_limits_minimum_battery_reserve():
    hours = _sample_hours(4.0)
    battery = _sample_battery()
    directives = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {"hours": [10, 11], "minimum_energy_kwh": 4.5},
        }
    ]
    limits = build_limits(hours, battery, directives)
    assert limits["min_energy"][10] == 4.5
    assert limits["min_energy"][11] == 4.5
    assert limits["min_energy"][9] == 2.0


def test_build_limits_no_charge_window():
    hours = _sample_hours(4.0)
    battery = _sample_battery()
    directives = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [1, 2]},
        }
    ]
    limits = build_limits(hours, battery, directives)
    assert limits["max_charge"][1] == 0.0
    assert limits["max_charge"][2] == 0.0
    assert limits["max_charge"][3] == 3.0


def test_build_limits_no_discharge_window():
    hours = _sample_hours(4.0)
    battery = _sample_battery()
    directives = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "no_discharge_window",
            "structured_adjustment": {"hours": [18, 19]},
        }
    ]
    limits = build_limits(hours, battery, directives)
    assert limits["max_discharge"][18] == 0.0
    assert limits["max_discharge"][19] == 0.0
    assert limits["max_discharge"][20] == 3.0


def test_build_limits_max_grid_window():
    hours = _sample_hours(4.0)
    battery = _sample_battery()
    directives = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "max_grid_window",
            "structured_adjustment": {"hours": [12, 13], "max_grid_kwh": 1.5},
        }
    ]
    limits = build_limits(hours, battery, directives)
    assert limits["max_grid"][12] == 1.5
    assert limits["max_grid"][13] == 1.5
    assert limits["max_grid"][11] is None


def test_build_limits_no_op():
    hours = _sample_hours(4.0)
    battery = _sample_battery()
    directives = [
        {
            "note_index": 0,
            "applies": False,
            "directive_type": "no_op",
            "structured_adjustment": None,
        }
    ]
    limits = build_limits(hours, battery, directives)
    assert limits["eff_solar"] == [4.0] * 24
    assert limits["min_energy"] == [2.0] * 24


def test_build_limits_overlaps():
    hours = _sample_hours(10.0)
    battery = _sample_battery()  # base min_energy = 2.0
    directives = [
        # Solar reduction overlap: 10 * 0.5 * 0.5 = 2.5
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [12], "factor": 0.5},
        },
        {
            "note_index": 1,
            "applies": True,
            "directive_type": "solar_reduction",
            "structured_adjustment": {"hours": [12], "factor": 0.5},
        },
        # Reserve floor overlap: max(2.0, 4.0, 7.0) = 7.0
        {
            "note_index": 2,
            "applies": True,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {"hours": [14], "minimum_energy_kwh": 4.0},
        },
        {
            "note_index": 3,
            "applies": True,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {"hours": [14], "minimum_energy_kwh": 7.0},
        },
        # Grid cap overlap: min(5.0, 2.0) = 2.0
        {
            "note_index": 4,
            "applies": True,
            "directive_type": "max_grid_window",
            "structured_adjustment": {"hours": [15], "max_grid_kwh": 5.0},
        },
        {
            "note_index": 5,
            "applies": True,
            "directive_type": "max_grid_window",
            "structured_adjustment": {"hours": [15], "max_grid_kwh": 2.0},
        },
        # No charge union: [1, 2] and [2, 3] -> [1, 2, 3]
        {
            "note_index": 6,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [1, 2]},
        },
        {
            "note_index": 7,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [2, 3]},
        },
    ]
    limits = build_limits(hours, battery, directives)
    assert limits["eff_solar"][12] == 2.5
    assert limits["min_energy"][14] == 7.0
    assert limits["max_grid"][15] == 2.0
    assert limits["max_charge"][1] == 0.0
    assert limits["max_charge"][2] == 0.0
    assert limits["max_charge"][3] == 0.0
    assert limits["max_charge"][4] == 3.0


def test_all_public_samples():
    import json
    from pathlib import Path

    data_path = Path(__file__).parent.parent / "data" / "public_samples.json"
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data["cases"]) == 10
    for case in data["cases"]:
        inp = case["input"]
        exp = case["expected_output"]
        hours = inp["hours"]
        battery = inp["battery"]
        directives = [
            d for d in exp["directive_interpretation"] if d.get("applies") is True
        ]
        res = optimize(hours, battery, directives)
        assert res["status"] == "optimal"
        assert abs(res["total_cost_bdt"] - exp["total_cost_bdt"]) <= 0.01
        assert abs(res["total_grid_kwh"] - exp["total_grid_kwh"]) <= 0.01
        assert abs(res["peak_grid_kwh"] - exp["peak_grid_kwh"]) <= 0.01


def test_replay_check_all_public_samples():
    import json
    from pathlib import Path
    from app.optimizer.replay import replay_check

    data_path = Path(__file__).parent.parent / "data" / "public_samples.json"
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for case in data["cases"]:
        inp = case["input"]
        exp = case["expected_output"]
        directives = [
            d for d in exp["directive_interpretation"] if d.get("applies") is True
        ]
        # Replay expected reference
        violations_exp = replay_check(inp["hours"], inp["battery"], directives, exp)
        assert violations_exp == [], f"{case['id']} expected output failed replay: {violations_exp}"

        # Replay our optimizer output
        res = optimize(inp["hours"], inp["battery"], directives)
        violations_opt = replay_check(inp["hours"], inp["battery"], directives, res)
        assert violations_opt == [], f"{case['id']} optimizer output failed replay: {violations_opt}"


def _get_base_valid_case():
    import json
    from pathlib import Path
    data_path = Path(__file__).parent.parent / "data" / "public_samples.json"
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    case0 = data["cases"][0]
    import copy
    return copy.deepcopy(case0["input"]), copy.deepcopy(case0["expected_output"])


def test_replay_check_bad_balance():
    import copy
    from app.optimizer.replay import replay_check

    inp, exp = _get_base_valid_case()
    directives = [d for d in exp["directive_interpretation"] if d.get("applies")]
    broken = copy.deepcopy(exp)
    broken["hourly_plan"][0]["grid_kwh"] += 15.0

    violations = replay_check(inp["hours"], inp["battery"], directives, broken)
    assert any("energy balance violated" in v for v in violations)


def test_replay_check_violated_no_charge():
    import copy
    from app.optimizer.replay import replay_check

    inp, exp = _get_base_valid_case()
    directives = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "no_charge_window",
            "structured_adjustment": {"hours": [5]},
        }
    ]
    broken = copy.deepcopy(exp)
    broken["hourly_plan"][5]["battery_action"] = "charge"
    broken["hourly_plan"][5]["battery_kwh"] = 10.0

    violations = replay_check(inp["hours"], inp["battery"], directives, broken)
    assert any("charge amount" in v and "exceeds max charge limit" in v for v in violations)


def test_replay_check_wrong_final_energy():
    import copy
    from app.optimizer.replay import replay_check

    inp, exp = _get_base_valid_case()
    directives = [d for d in exp["directive_interpretation"] if d.get("applies")]
    broken = copy.deepcopy(exp)
    broken["hourly_plan"][23]["battery_energy_after_kwh"] += 20.0

    violations = replay_check(inp["hours"], inp["battery"], directives, broken)
    assert any("End-of-day battery energy" in v for v in violations)


def test_replay_check_wrong_totals():
    import copy
    from app.optimizer.replay import replay_check

    inp, exp = _get_base_valid_case()
    directives = [d for d in exp["directive_interpretation"] if d.get("applies")]
    broken = copy.deepcopy(exp)
    broken["total_cost_bdt"] += 100.0
    broken["total_grid_kwh"] += 50.0

    violations = replay_check(inp["hours"], inp["battery"], directives, broken)
    assert any("Reported total_cost_bdt" in v for v in violations)
    assert any("Reported total_grid_kwh" in v for v in violations)


def test_zero_tariff():
    from app.optimizer.replay import replay_check
    inp, _ = _get_base_valid_case()
    hours = [dict(h, tariff_bdt_per_kwh=0.0) for h in inp["hours"]]
    battery = inp["battery"]
    res = optimize(hours, battery, [])
    assert res["status"] == "optimal"
    assert res["total_cost_bdt"] == 0.0
    assert replay_check(hours, battery, res["applied_directives"], res) == []


def test_zero_solar():
    from app.optimizer.replay import replay_check
    inp, _ = _get_base_valid_case()
    hours = [dict(h, solar_kwh=0.0) for h in inp["hours"]]
    battery = inp["battery"]
    res = optimize(hours, battery, [])
    assert res["status"] == "optimal"
    assert all(e["solar_used_kwh"] == 0.0 for e in res["hourly_plan"])
    assert replay_check(hours, battery, res["applied_directives"], res) == []


def test_huge_solar():
    from app.optimizer.replay import replay_check
    inp, _ = _get_base_valid_case()
    hours = [dict(h, solar_kwh=10000.0) for h in inp["hours"]]
    battery = inp["battery"]
    res = optimize(hours, battery, [])
    assert res["status"] == "optimal"
    assert res["total_grid_kwh"] == 0.0
    assert res["total_cost_bdt"] == 0.0
    assert replay_check(hours, battery, res["applied_directives"], res) == []


def test_initial_equals_capacity():
    from app.optimizer.replay import replay_check
    inp, _ = _get_base_valid_case()
    battery = dict(inp["battery"], initial_energy_kwh=inp["battery"]["capacity_kwh"])
    res = optimize(inp["hours"], battery, [])
    assert res["status"] == "optimal"
    assert replay_check(inp["hours"], battery, res["applied_directives"], res) == []


def test_minimum_equals_initial():
    from app.optimizer.replay import replay_check
    inp, _ = _get_base_valid_case()
    battery = dict(inp["battery"], minimum_energy_kwh=inp["battery"]["initial_energy_kwh"])
    res = optimize(inp["hours"], battery, [])
    assert res["status"] == "optimal"
    assert replay_check(inp["hours"], battery, res["applied_directives"], res) == []


def test_reserve_above_capacity_relaxation():
    from app.optimizer.replay import replay_check
    inp, _ = _get_base_valid_case()
    battery = inp["battery"]
    # Directive demands reserve greater than capacity
    excessive_reserve = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "minimum_battery_reserve",
            "structured_adjustment": {"hours": [12], "minimum_energy_kwh": battery["capacity_kwh"] + 100},
        }
    ]
    res = optimize(inp["hours"], battery, excessive_reserve)
    assert res["status"] == "relaxed"
    assert replay_check(inp["hours"], battery, res["applied_directives"], res) == []


def test_conflicting_directives_relaxation():
    from app.optimizer.replay import replay_check
    inp, _ = _get_base_valid_case()
    battery = inp["battery"]
    # Force hour 0 to have 0 solar, 0 grid, 0 discharge when demand > 0 -> infeasible
    hours = [dict(h) for h in inp["hours"]]
    hours[0]["solar_kwh"] = 0.0
    hours[0]["demand_kwh"] = 50.0
    conflicting = [
        {
            "note_index": 0,
            "applies": True,
            "directive_type": "max_grid_window",
            "structured_adjustment": {"hours": [0], "max_grid_kwh": 0.0},
        },
        {
            "note_index": 1,
            "applies": True,
            "directive_type": "no_discharge_window",
            "structured_adjustment": {"hours": [0]},
        },
    ]
    res = optimize(hours, battery, conflicting)
    assert res["status"] == "relaxed"
    assert replay_check(hours, battery, res["applied_directives"], res) == []


def test_optimize_never_raises_on_corrupt_input():
    # Corrupt / missing inputs must never raise and return a valid schema dict
    for bad_h, bad_b, bad_d in [
        (None, None, None),
        ([], {}, []),
        ([{"hour": 0}], {}, []),
        ([{"hour": h} for h in range(24)], {"initial_energy_kwh": 50}, []),
        (
            [{"hour": h, "demand_kwh": 10, "solar_kwh": 0, "tariff_bdt_per_kwh": 5} for h in range(24)],
            {"capacity_kwh": 50, "initial_energy_kwh": 100, "minimum_energy_kwh": 10, "max_charge_kwh_per_hour": 10, "max_discharge_kwh_per_hour": 10},
            [],
        ),
    ]:
        res = optimize(bad_h, bad_b, bad_d)
        assert isinstance(res, dict)
        assert "hourly_plan" in res
        assert "total_cost_bdt" in res
        assert "total_grid_kwh" in res
        assert "peak_grid_kwh" in res
        assert "status" in res


def test_solve_time_under_200ms():
    import time
    import json
    from pathlib import Path

    data_path = Path(__file__).parent.parent / "data" / "public_samples.json"
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for case in data["cases"]:
        inp = case["input"]
        exp = case["expected_output"]
        directives = [d for d in exp["directive_interpretation"] if d.get("applies")]
        t0 = time.perf_counter()
        res = optimize(inp["hours"], inp["battery"], directives)
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.20, f"Case {case['id']} took {elapsed:.4f}s > 0.20s"
        assert res["status"] == "optimal"
