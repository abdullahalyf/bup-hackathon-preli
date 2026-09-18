"""Highs LP optimizer with relaxation chain and safe fallback."""

from typing import Any
import numpy as np
from scipy.optimize import linprog


def build_limits(
    hours: list[dict],
    battery: dict,
    directives: list[dict],
    *,
    allow_max_grid: bool = True,
    allow_reserve: bool = True,
    allow_no_discharge: bool = True,
    allow_no_charge: bool = True,
) -> dict:
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
        elif dtype == "minimum_battery_reserve" and allow_reserve:
            req_min = float(adj.get("minimum_energy_kwh", 0.0))
            for h in target_hours:
                if 0 <= h < num_hours:
                    min_energy[h] = max(min_energy[h], req_min)
        elif dtype == "no_charge_window" and allow_no_charge:
            for h in target_hours:
                if 0 <= h < num_hours:
                    max_charge[h] = 0.0
        elif dtype == "no_discharge_window" and allow_no_discharge:
            for h in target_hours:
                if 0 <= h < num_hours:
                    max_discharge[h] = 0.0
        elif dtype == "max_grid_window" and allow_max_grid:
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


def _fallback_plan(hours: list[dict], battery: dict) -> dict:
    """Safe baseline: serve demand from solar, then grid; keep battery idle."""
    initial = float(battery.get("initial_energy_kwh", 0.0))
    plan = []
    total_cost = 0.0
    sorted_hours = sorted(hours, key=lambda x: x.get("hour", 0))
    for entry in sorted_hours:
        solar_used = min(float(entry.get("solar_kwh", 0.0)), float(entry.get("demand_kwh", 0.0)))
        grid = float(entry.get("demand_kwh", 0.0)) - solar_used
        tariff = float(entry.get("tariff_bdt_per_kwh", 0.0))
        plan.append(
            {
                "hour": entry.get("hour", 0),
                "grid_kwh": round(grid, 6),
                "solar_used_kwh": round(solar_used, 6),
                "battery_action": "idle",
                "battery_kwh": 0.0,
                "battery_energy_after_kwh": round(initial, 6),
            }
        )
        total_cost += grid * tariff
    return {
        "hourly_plan": plan,
        "total_grid_kwh": round(sum(entry["grid_kwh"] for entry in plan), 6),
        "total_cost_bdt": round(total_cost, 6),
        "peak_grid_kwh": round(max((entry["grid_kwh"] for entry in plan), default=0.0), 6),
        "status": "fallback",
    }


def _solve_lp_attempt(
    sorted_hours: list[dict],
    battery: dict,
    directives: list[dict],
    status_label: str,
    allow_max_grid: bool,
    allow_reserve: bool,
    allow_no_discharge: bool,
    allow_no_charge: bool,
) -> dict | None:
    try:
        limits = build_limits(
            sorted_hours,
            battery,
            directives,
            allow_max_grid=allow_max_grid,
            allow_reserve=allow_reserve,
            allow_no_discharge=allow_no_discharge,
            allow_no_charge=allow_no_charge,
        )

        eff_solar = limits["eff_solar"]
        min_energy = limits["min_energy"]
        max_charge = limits["max_charge"]
        max_discharge = limits["max_discharge"]
        max_grid = limits["max_grid"]

        capacity = float(battery["capacity_kwh"])
        initial = float(battery["initial_energy_kwh"])

        # Check basic consistency of bounds
        for h in range(24):
            if min_energy[h] > capacity + 1e-9:
                return None

        n_vars = 120
        c_obj = np.zeros(n_vars)
        bounds = []

        for h in range(24):
            tariff = float(sorted_hours[h]["tariff_bdt_per_kwh"])
            idx = 5 * h
            c_obj[idx + 0] = tariff
            c_obj[idx + 1] = 0.0
            c_obj[idx + 2] = 1e-6
            c_obj[idx + 3] = 1e-6
            c_obj[idx + 4] = 0.0

            bounds.append((0.0, max_grid[h]))
            bounds.append((0.0, max(0.0, eff_solar[h])))
            bounds.append((0.0, max(0.0, max_charge[h])))
            bounds.append((0.0, max(0.0, max_discharge[h])))
            bounds.append((min_energy[h], capacity))

        A_eq = []
        b_eq = []

        # 1) Power balance: g_h + s_h + d_h - c_h = demand_h
        for h in range(24):
            row = np.zeros(n_vars)
            idx = 5 * h
            row[idx + 0] = 1.0
            row[idx + 1] = 1.0
            row[idx + 2] = -1.0
            row[idx + 3] = 1.0
            A_eq.append(row)
            b_eq.append(float(sorted_hours[h]["demand_kwh"]))

        # 2) Battery balance: E_h - E_{h-1} - c_h + d_h = 0 (E_{-1} = initial)
        for h in range(24):
            row = np.zeros(n_vars)
            idx = 5 * h
            row[idx + 4] = 1.0
            row[idx + 2] = -1.0
            row[idx + 3] = 1.0
            if h > 0:
                row[5 * (h - 1) + 4] = -1.0
                b_eq.append(0.0)
            else:
                b_eq.append(initial)
            A_eq.append(row)

        # 3) End neutrality: E_23 = initial
        row = np.zeros(n_vars)
        row[5 * 23 + 4] = 1.0
        A_eq.append(row)
        b_eq.append(initial)

        res = linprog(
            c=c_obj,
            A_eq=np.array(A_eq),
            b_eq=np.array(b_eq),
            bounds=bounds,
            method="highs",
        )

        if not res.success:
            return None

        # Post-processing as required by Technical spec
        plan = []
        curr_E = initial
        total_cost = 0.0

        for h in range(24):
            idx = 5 * h
            s_val = float(res.x[idx + 1])
            c_val = float(res.x[idx + 2])
            d_val = float(res.x[idx + 3])

            net = c_val - d_val
            if net > 1e-7:
                action = "charge"
                c_post = round(net, 6)
                d_post = 0.0
                b_kwh = c_post
            elif net < -1e-7:
                action = "discharge"
                c_post = 0.0
                d_post = round(-net, 6)
                b_kwh = d_post
            else:
                action = "idle"
                c_post = 0.0
                d_post = 0.0
                b_kwh = 0.0

            s_post = round(min(max(0.0, s_val), eff_solar[h]), 6)
            curr_E = round(curr_E + c_post - d_post, 6)

            demand = float(sorted_hours[h]["demand_kwh"])
            grid = round(demand + c_post - d_post - s_post, 6)
            if grid < 0:
                s_post = round(max(0.0, s_post + grid), 6)
                grid = 0.0

            plan.append(
                {
                    "hour": sorted_hours[h]["hour"],
                    "grid_kwh": grid,
                    "solar_used_kwh": s_post,
                    "battery_action": action,
                    "battery_kwh": b_kwh,
                    "battery_energy_after_kwh": curr_E,
                }
            )
            total_cost += grid * float(sorted_hours[h]["tariff_bdt_per_kwh"])

        return {
            "hourly_plan": plan,
            "total_grid_kwh": round(sum(entry["grid_kwh"] for entry in plan), 6),
            "total_cost_bdt": round(total_cost, 6),
            "peak_grid_kwh": round(max((entry["grid_kwh"] for entry in plan), default=0.0), 6),
            "status": status_label,
        }
    except Exception:
        return None


def optimize(hours: list[dict], battery: dict, directives: list[dict]) -> dict:
    """Optimize 24-hour battery and grid schedule with relaxation and fallback."""
    try:
        required_battery_keys = [
            "capacity_kwh",
            "initial_energy_kwh",
            "minimum_energy_kwh",
            "max_charge_kwh_per_hour",
            "max_discharge_kwh_per_hour",
        ]
        if not hours or not battery or len(hours) != 24:
            return _fallback_plan(hours, battery)

        if not all(k in battery for k in required_battery_keys):
            return _fallback_plan(hours, battery)

        sorted_hours = sorted(hours, key=lambda x: x["hour"])

        # Order of relaxation on infeasibility:
        # max-grid -> reserve -> no-discharge -> no-charge
        attempts = [
            ("optimal", True, True, True, True),
            ("relaxed", False, True, True, True),
            ("relaxed", False, False, True, True),
            ("relaxed", False, False, False, True),
            ("relaxed", False, False, False, False),
        ]

        for status_label, allow_mg, allow_res, allow_nd, allow_nc in attempts:
            sol = _solve_lp_attempt(
                sorted_hours=sorted_hours,
                battery=battery,
                directives=directives,
                status_label=status_label,
                allow_max_grid=allow_mg,
                allow_reserve=allow_res,
                allow_no_discharge=allow_nd,
                allow_no_charge=allow_nc,
            )
            if sol is not None:
                return sol

        return _fallback_plan(sorted_hours, battery)
    except Exception:
        return _fallback_plan(hours, battery)


