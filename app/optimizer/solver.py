"""Safe baseline: serve demand from solar, then grid; keep battery idle."""


def build_limits(hours: list[dict], battery: dict, directives: list[dict]) -> dict:
    """Build per-hour effective limits from hours, battery params, and directives."""
    hours_by_h = {entry["hour"]: entry for entry in hours}
    num_hours = max(24, max(hours_by_h.keys(), default=23) + 1)

    base_min_energy = float(battery.get("minimum_energy_kwh", 0.0))
    base_max_charge = float(battery.get("max_charge_kwh_per_hour", 0.0))
    base_max_discharge = float(battery.get("max_discharge_kwh_per_hour", 0.0))

    eff_solar = [
        float(hours_by_h[h]["solar_kwh"]) if h in hours_by_h else 0.0
        for h in range(num_hours)
    ]
    min_energy = [base_min_energy] * num_hours
    max_charge = [base_max_charge] * num_hours
    max_discharge = [base_max_discharge] * num_hours
    max_grid = [None] * num_hours

    for d in directives or []:
        if not d.get("applies", True):
            continue
        dtype = d.get("directive_type")
        if dtype == "no_op":
            continue
        adj = d.get("structured_adjustment")
        if not adj:
            continue
        target_hours = adj.get("hours", [])

        if dtype == "solar_reduction":
            factor = float(adj.get("factor", 1.0))
            for h in target_hours:
                if 0 <= h < num_hours:
                    eff_solar[h] *= factor
        elif dtype == "minimum_battery_reserve":
            req_min = float(adj.get("minimum_energy_kwh", 0.0))
            for h in target_hours:
                if 0 <= h < num_hours:
                    min_energy[h] = max(min_energy[h], req_min)
        elif dtype == "no_charge_window":
            for h in target_hours:
                if 0 <= h < num_hours:
                    max_charge[h] = 0.0
        elif dtype == "no_discharge_window":
            for h in target_hours:
                if 0 <= h < num_hours:
                    max_discharge[h] = 0.0
        elif dtype == "max_grid_window":
            req_cap = float(adj.get("max_grid_kwh", 0.0))
            for h in target_hours:
                if 0 <= h < num_hours:
                    if max_grid[h] is None:
                        max_grid[h] = req_cap
                    else:
                        max_grid[h] = min(max_grid[h], req_cap)

    return {
        "eff_solar": eff_solar,
        "min_energy": min_energy,
        "max_charge": max_charge,
        "max_discharge": max_discharge,
        "max_grid": max_grid,
    }


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

