"""Independent judge-style plan validator with 0.01 tolerance."""

import math
from app.optimizer.solver import build_limits


def replay_check(
    hours: list[dict],
    battery: dict,
    directives: list[dict],
    response: dict,
) -> list[str]:
    """Validate plan against physics, directives, battery limits, and totals."""
    violations: list[str] = []

    if not isinstance(response, dict):
        return ["Response must be a dictionary."]

    plan = response.get("hourly_plan")
    if not isinstance(plan, list):
        return ["Response missing 'hourly_plan' list."]

    if len(plan) != 24:
        violations.append(f"Expected 24 hourly plan entries, got {len(plan)}.")
        return violations

    plan_hours = [entry.get("hour") for entry in plan]
    if sorted(plan_hours) != list(range(24)):
        violations.append(
            f"Plan hours must contain exactly hours 0 through 23, got {plan_hours}."
        )
        return violations

    sorted_plan = sorted(plan, key=lambda x: x["hour"])
    hours_by_h = {entry["hour"]: entry for entry in hours}
    if set(hours_by_h.keys()) != set(range(24)):
        violations.append("Input hours must contain exactly hours 0 through 23.")
        return violations

    limits = build_limits(hours, battery, directives)
    eff_solar = limits["eff_solar"]
    min_energy = limits["min_energy"]
    max_charge = limits["max_charge"]
    max_discharge = limits["max_discharge"]
    max_grid = limits["max_grid"]

    capacity = float(battery.get("capacity_kwh", 0.0))
    initial = float(battery.get("initial_energy_kwh", 0.0))

    prev_energy = initial
    tol = 0.01

    for h in range(24):
        entry = sorted_plan[h]
        hour_in = hours_by_h[h]
        demand = float(hour_in.get("demand_kwh", 0.0))

        # Check finite numbers
        for field in [
            "grid_kwh",
            "solar_used_kwh",
            "battery_kwh",
            "battery_energy_after_kwh",
        ]:
            val = entry.get(field)
            if val is None or not isinstance(val, (int, float)) or not math.isfinite(val):
                violations.append(
                    f"Hour {h}: '{field}' must be a finite number, got {val}."
                )

        grid = float(entry.get("grid_kwh", 0.0))
        solar_used = float(entry.get("solar_used_kwh", 0.0))
        b_kwh = float(entry.get("battery_kwh", 0.0))
        e_after = float(entry.get("battery_energy_after_kwh", 0.0))
        action = entry.get("battery_action")

        # Non-negative checks
        if grid < -tol:
            violations.append(f"Hour {h}: grid_kwh must be non-negative, got {grid}.")
        if solar_used < -tol:
            violations.append(
                f"Hour {h}: solar_used_kwh must be non-negative, got {solar_used}."
            )
        if b_kwh < -tol:
            violations.append(f"Hour {h}: battery_kwh must be non-negative, got {b_kwh}.")

        # Action check
        if action not in ("charge", "discharge", "idle"):
            violations.append(
                f"Hour {h}: battery_action must be 'charge', 'discharge', or 'idle', got '{action}'."
            )
        elif action == "idle" and b_kwh > tol:
            violations.append(
                f"Hour {h}: battery_action is 'idle' but battery_kwh is {b_kwh} > 0."
            )

        # Rate limits
        if action == "charge" and b_kwh > max_charge[h] + tol:
            violations.append(
                f"Hour {h}: charge amount {b_kwh} exceeds max charge limit {max_charge[h]}."
            )
        if action == "discharge" and b_kwh > max_discharge[h] + tol:
            violations.append(
                f"Hour {h}: discharge amount {b_kwh} exceeds max discharge limit {max_discharge[h]}."
            )

        # Solar limit
        if solar_used > eff_solar[h] + tol:
            violations.append(
                f"Hour {h}: solar_used {solar_used} exceeds effective solar {eff_solar[h]}."
            )

        # Stored energy transition
        c_val = b_kwh if action == "charge" else 0.0
        d_val = b_kwh if action == "discharge" else 0.0
        expected_e_after = prev_energy + c_val - d_val
        if abs(e_after - expected_e_after) > tol:
            violations.append(
                f"Hour {h}: battery energy after {e_after} does not match expected transition {expected_e_after}."
            )

        # Capacity & minimum reserve
        if e_after > capacity + tol:
            violations.append(
                f"Hour {h}: battery energy {e_after} exceeds capacity {capacity}."
            )
        if e_after < min_energy[h] - tol:
            violations.append(
                f"Hour {h}: battery energy {e_after} is below minimum reserve {min_energy[h]}."
            )

        # Energy balance
        # grid + solar_used + discharge = demand + charge
        supply = grid + solar_used + d_val
        consumption = demand + c_val
        if abs(supply - consumption) > tol:
            violations.append(
                f"Hour {h}: energy balance violated: supply {supply} != consumption {consumption}."
            )

        # Max grid directive check
        if max_grid[h] is not None and grid > max_grid[h] + tol:
            violations.append(
                f"Hour {h}: grid {grid} exceeds max grid limit {max_grid[h]}."
            )

        prev_energy = e_after

    # End neutrality
    if abs(prev_energy - initial) > tol:
        violations.append(
            f"End-of-day battery energy {prev_energy} does not match initial energy {initial}."
        )

    # Totals check
    if "total_grid_kwh" in response:
        calc_total_grid = sum(float(e.get("grid_kwh", 0.0)) for e in sorted_plan)
        rep_total_grid = float(response.get("total_grid_kwh", 0.0))
        if abs(rep_total_grid - calc_total_grid) > tol:
            violations.append(
                f"Reported total_grid_kwh {rep_total_grid} != calculated {calc_total_grid}."
            )

    if "total_cost_bdt" in response:
        calc_total_cost = sum(
            float(e.get("grid_kwh", 0.0))
            * float(hours_by_h[e["hour"]].get("tariff_bdt_per_kwh", 0.0))
            for e in sorted_plan
        )
        rep_total_cost = float(response.get("total_cost_bdt", 0.0))
        if abs(rep_total_cost - calc_total_cost) > tol:
            violations.append(
                f"Reported total_cost_bdt {rep_total_cost} != calculated {calc_total_cost}."
            )

    if "peak_grid_kwh" in response:
        calc_peak_grid = max(
            (float(e.get("grid_kwh", 0.0)) for e in sorted_plan), default=0.0
        )
        rep_peak_grid = float(response.get("peak_grid_kwh", 0.0))
        if abs(rep_peak_grid - calc_peak_grid) > tol:
            violations.append(
                f"Reported peak_grid_kwh {rep_peak_grid} != calculated {calc_peak_grid}."
            )

    return violations
