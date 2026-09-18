"""Safe baseline: serve demand from solar, then grid; keep battery idle."""


def optimize(hours: list[dict], battery: dict, directives: list[dict]) -> dict:
    initial = battery["initial_energy_kwh"]
    plan = []
    total_cost = 0.0
    for entry in hours:
        solar_used = min(entry["solar_kwh"], entry["demand_kwh"])
        grid = entry["demand_kwh"] - solar_used
        plan.append(
            {
                "hour": entry["hour"],
                "grid_kwh": grid,
                "solar_used_kwh": solar_used,
                "battery_action": "idle",
                "battery_kwh": 0.0,
                "battery_energy_after_kwh": initial,
            }
        )
        total_cost += grid * entry["tariff_bdt_per_kwh"]
    return {
        "hourly_plan": plan,
        "total_grid_kwh": sum(entry["grid_kwh"] for entry in plan),
        "total_cost_bdt": total_cost,
        "peak_grid_kwh": max((entry["grid_kwh"] for entry in plan), default=0.0),
        "status": "fallback",
    }
