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
