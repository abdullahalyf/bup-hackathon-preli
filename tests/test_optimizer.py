from app.optimizer import optimize


def test_stub_uses_solar_then_grid():
    result = optimize(
        [{"hour": 0, "demand_kwh": 5, "solar_kwh": 2, "tariff_bdt_per_kwh": 10}],
        {"initial_energy_kwh": 3},
        [],
    )
    assert result["hourly_plan"][0]["grid_kwh"] == 3
    assert result["total_cost_bdt"] == 30
    assert result["status"] == "fallback"
