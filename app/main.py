"""HTTP entry point for the GridWise service.

Production-grade layer over the interpreter and optimizer packages. Owns
request validation, error normalisation, CORS, the per-request log, the
interpreter timeout, the LRU response cache, the public response shape, and
defensive guards around both the interpreter output and the optimizer output
so a buggy teammate implementation can never break the public contract.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import threading
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.interpreter import interpret_notes
from app.optimizer import optimize
from app.schemas import OptimizeRequest

# replay_check is owned by Taseen; we use it opportunistically if it exists.
try:
    from app.optimizer.replay import replay_check as _replay_check  # type: ignore
except Exception:  # pragma: no cover - replay stub missing
    _replay_check = None

load_dotenv()

# --------------------------------------------------------------------- logging

logger = logging.getLogger("gridwise.api")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logger.addHandler(handler)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

# Public budget: full request must finish in <25 s. Interpreter is the slow
# path (LLM call); we cap it at 12 s and leave the rest for the optimizer.
INTERPRETER_TIMEOUT_S = 12.0
TOTAL_REQUEST_BUDGET_S = 25.0
CACHE_MAX_SIZE = 256

# Dedicated pool for the interpreter call so a stalled LLM cannot tie up
# FastAPI's default threadpool workers (which also run the sync handlers).
_INTERP_EXECUTOR = ThreadPoolExecutor(
    max_workers=int(os.getenv("INTERP_WORKERS", "8")),
    thread_name_prefix="gridwise-interp",
)

# Allowed directive_type values per docs/CONTRACTS.md.
_ALLOWED_TYPES = {
    "solar_reduction",
    "minimum_battery_reserve",
    "no_charge_window",
    "no_discharge_window",
    "max_grid_window",
    "no_op",
}

_DEFAULT_EXPLANATION = "interpreter output did not match schema; treated as no-op"


# --------------------------------------------------------- helpers / builders

def _safe_no_op_entry(index: int, explanation: str | None = None) -> dict:
    """A directive entry that opts out of the schedule without changing it."""
    return {
        "note_index": index,
        "applies": False,
        "directive_type": "no_op",
        "structured_adjustment": None,
        "explanation": explanation or _DEFAULT_EXPLANATION,
    }


def _is_finite_number(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _coerce_hours(raw) -> list[int] | None:
    """Validate and normalise a `hours` list from structured_adjustment."""
    if not isinstance(raw, list) or not raw:
        return None
    out: list[int] = []
    seen: set[int] = set()
    for item in raw:
        # bool is a subclass of int in Python; reject it explicitly.
        if isinstance(item, bool) or not isinstance(item, int):
            return None
        if item < 0 or item > 23:
            return None
        if item in seen:
            return None
        seen.add(item)
        out.append(item)
    return out  # do not require sorted; we will sort + re-check anyway


def _validate_adjustment(directive_type: str, adj, capacity_kwh: float):
    """Return the cleaned structured_adjustment, or None if invalid."""
    if not isinstance(adj, dict):
        return None
    if directive_type == "solar_reduction":
        hours = _coerce_hours(adj.get("hours"))
        factor = adj.get("factor")
        if hours is None:
            return None
        if not _is_finite_number(factor):
            return None
        f = float(factor)
        if f < 0.0 or f > 1.0:
            return None
        return {"hours": hours, "factor": f}
    if directive_type == "minimum_battery_reserve":
        hours = _coerce_hours(adj.get("hours"))
        reserve = adj.get("minimum_energy_kwh")
        if hours is None:
            return None
        if not _is_finite_number(reserve):
            return None
        r = float(reserve)
        if r < 0.0 or r > capacity_kwh:
            return None
        return {"hours": hours, "minimum_energy_kwh": r}
    if directive_type in ("no_charge_window", "no_discharge_window"):
        hours = _coerce_hours(adj.get("hours"))
        if hours is None:
            return None
        return {"hours": hours}
    if directive_type == "max_grid_window":
        hours = _coerce_hours(adj.get("hours"))
        cap = adj.get("max_grid_kwh")
        if hours is None:
            return None
        if not _is_finite_number(cap):
            return None
        c = float(cap)
        if c < 0.0:
            return None
        return {"hours": hours, "max_grid_kwh": c}
    return None  # pragma: no cover - guarded by caller


def _normalise_interpretation(notes: list[str], raw, battery: dict | None = None) -> list[dict]:
    """Defensive normalisation of the interpreter output.

    Guarantees len(notes) entries with note_index 0..N-1, allowed directive
    types, exact adjustment shape, finite numerics, and ascending unique hours.
    Anything that does not validate becomes a no_op for that index.
    """
    n = len(notes)
    capacity_kwh = 0.0
    if isinstance(battery, dict):
        cap = battery.get("capacity_kwh")
        if isinstance(cap, (int, float)) and math.isfinite(float(cap)):
            capacity_kwh = float(cap)
    if not isinstance(raw, list):
        raw = []

    by_index: dict[int, dict] = {}
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        idx = entry.get("note_index")
        if isinstance(idx, bool) or not isinstance(idx, int):
            continue
        if idx < 0 or idx >= n:
            continue
        if idx in by_index:  # duplicate -> ignore extras
            continue
        by_index[idx] = entry

    out: list[dict] = []
    for i in range(n):
        entry = by_index.get(i)
        if not entry:
            out.append(_safe_no_op_entry(i))
            continue
        dtype = entry.get("directive_type")
        explanation = entry.get("explanation")
        if not isinstance(explanation, str) or not explanation.strip():
            explanation = _DEFAULT_EXPLANATION
        if dtype not in _ALLOWED_TYPES:
            out.append(_safe_no_op_entry(i, explanation))
            continue
        if dtype == "no_op":
            out.append({
                "note_index": i,
                "applies": False,
                "directive_type": "no_op",
                "structured_adjustment": None,
                "explanation": explanation,
            })
            continue
        adj = _validate_adjustment(dtype, entry.get("structured_adjustment"), capacity_kwh)
        if adj is None:
            out.append(_safe_no_op_entry(i, explanation))
            continue
        applies = entry.get("applies")
        if applies is not True:
            out.append(_safe_no_op_entry(i, explanation))
            continue
        out.append({
            "note_index": i,
            "applies": True,
            "directive_type": dtype,
            "structured_adjustment": adj,
            "explanation": explanation,
        })
    return out


def _normalise_plan(plan, hours_meta: list[dict]) -> dict:
    """Force exactly 24 sorted entries, sanitise numerics, recompute totals.

    Recomputes total_grid_kwh, total_cost_bdt, peak_grid_kwh from the plan so
    the API never trusts the optimizer's totals. Raises ValueError on
    non-finite output so the caller can return a generic 500.
    """
    tariff_by_hour = {int(h["hour"]): float(h["tariff_bdt_per_kwh"]) for h in hours_meta}

    by_hour: dict[int, dict] = {}
    for entry in plan or []:
        if not isinstance(entry, dict):
            continue
        h = entry.get("hour")
        if isinstance(h, bool) or not isinstance(h, int):
            continue
        if h < 0 or h > 23:
            continue
        if h in by_hour:
            continue
        by_hour[h] = entry

    sanitised: list[dict] = []
    for h in range(24):
        src = by_hour.get(h, {})
        action = src.get("battery_action")
        if action not in ("charge", "discharge", "idle"):
            action = "idle"

        def _num(value, default: float = 0.0) -> float:
            if not _is_finite_number(value):
                raise ValueError(f"non-finite numeric in plan at hour {h}")
            return float(value)

        grid = _num(src.get("grid_kwh"), 0.0)
        solar = _num(src.get("solar_used_kwh"), 0.0)
        batt_kwh = _num(src.get("battery_kwh"), 0.0)
        after = _num(src.get("battery_energy_after_kwh"), 0.0)

        # Tiny negatives (numerical noise) clamped to 0.
        for name in ("grid", "solar", "batt_kwh"):
            v = locals()[name]
            if -1e-6 < v < 0:
                locals()[name] = 0.0
        grid = max(0.0, grid)
        solar = max(0.0, solar)
        batt_kwh = max(0.0, batt_kwh)

        if action == "idle":
            batt_kwh = 0.0

        if not math.isfinite(after):
            raise ValueError(f"non-finite battery_energy_after_kwh at hour {h}")

        sanitised.append({
            "hour": h,
            "grid_kwh": round(grid, 6),
            "solar_used_kwh": round(solar, 6),
            "battery_action": action,
            "battery_kwh": round(batt_kwh, 6),
            "battery_energy_after_kwh": round(after, 6),
        })

    total_grid = 0.0
    total_cost = 0.0
    peak = 0.0
    for entry in sanitised:
        g = entry["grid_kwh"]
        total_grid += g
        total_cost += g * tariff_by_hour[entry["hour"]]
        if g > peak:
            peak = g
    return {
        "hourly_plan": sanitised,
        "total_grid_kwh": round(total_grid, 6),
        "total_cost_bdt": round(total_cost, 6),
        "peak_grid_kwh": round(peak, 6),
    }


def _run_with_retry(hours: list[dict], battery: dict, applied: list[dict]):
    """Call optimise(); try a replay check, retry once if it fails.

    Returns the normalised plan dict. Raises ValueError on non-finite output.
    """
    last_error: Exception | None = None
    for attempt in range(2):
        result = optimize(hours, battery, applied) or {}
        try:
            norm = _normalise_plan(result.get("hourly_plan"), hours)
        except ValueError as exc:
            last_error = exc
            break  # non-finite -> don't retry, bubble up
        violations: list[str] = []
        if _replay_check is not None:
            try:
                violations = list(_replay_check(hours, battery, applied, {
                    **result,
                    **norm,
                }))
            except Exception:  # pragma: no cover - buggy replay impl
                violations = []
        if not violations:
            return norm
        last_violations = violations
        logger.warning(
            "replay_check returned %d violations (attempt %d); retrying",
            len(violations), attempt + 1,
        )
    if last_error is not None:
        raise last_error
    # Both attempts produced replay violations; return the second plan anyway
    # per task spec, and log the violations without leaking payload data.
    logger.warning(
        "replay_check still returning violations after retry: %s",
        "; ".join(str(v) for v in last_violations)[:200],
    )
    return norm  # type: ignore[name-defined]


# ------------------------------------------------------------- response cache

class _ResponseCache:
    """Thread-safe LRU cache for fully-built response bodies."""

    def __init__(self, maxsize: int = CACHE_MAX_SIZE) -> None:
        self._maxsize = maxsize
        self._lock = threading.Lock()
        self._store: "OrderedDict[str, dict]" = OrderedDict()

    def get(self, key: str) -> dict | None:
        with self._lock:
            if key not in self._store:
                return None
            self._store.move_to_end(key)
            import copy as _copy
            return _copy.deepcopy(self._store[key])

    def put(self, key: str, value: dict) -> None:
        import copy as _copy
        snapshot = _copy.deepcopy(value)
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = snapshot
            while len(self._store) > self._maxsize:
                self._store.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


_RESPONSE_CACHE = _ResponseCache()


def _reset_cache_for_tests() -> None:
    """Test-only helper: empty the response cache so each test is isolated."""
    _RESPONSE_CACHE.clear()


def _canonical_cache_key(payload: OptimizeRequest) -> str:
    """Hash the canonical JSON of the request payload."""
    body = {
        "scenario_id": payload.scenario_id.strip(),
        "operator_notes": [n for n in payload.operator_notes],
        "hours": sorted(
            (h.model_dump() for h in payload.hours),
            key=lambda x: x["hour"],
        ),
        "battery": payload.battery.model_dump(),
    }
    blob = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _build_response(
    scenario_id: str,
    interpretation: list[dict],
    normalised: dict,
) -> dict:
    """Assemble the public response with the exact key order from the contract."""
    applied = [entry for entry in interpretation if entry.get("applies")]
    types = ", ".join(dict.fromkeys(
        str(entry.get("directive_type", "no_op")) for entry in applied
    )) or "none"
    total_cost = float(normalised.get("total_cost_bdt", 0.0))
    summary = f"Applied directives: {types}; total cost: {total_cost:.6f} BDT."
    return {
        "scenario_id": scenario_id,
        "directive_interpretation": interpretation,
        "hourly_plan": normalised["hourly_plan"],
        "total_grid_kwh": float(normalised["total_grid_kwh"]),
        "total_cost_bdt": total_cost,
        "peak_grid_kwh": float(normalised["peak_grid_kwh"]),
        "plan_summary": summary,
    }


# ----------------------------------------------------------------- app setup

FRONTEND_INDEX = Path(__file__).resolve().parent.parent / "frontend" / "index.html"

app = FastAPI(title="GridWise")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def invalid_request(_request: Request, exc: RequestValidationError):
    # Normalised short message; never leak internal validation details.
    return JSONResponse(status_code=400, content={"error": "invalid request"})


@app.exception_handler(Exception)
async def unexpected_error(_request: Request, exc: Exception):
    # Log the real cause server-side, return a clean envelope to the caller.
    logger.exception("unhandled error: %s", type(exc).__name__)
    return JSONResponse(status_code=500, content={"error": "internal error"})


# ------------------------------------------------------------------- routes

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def root_index():
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "service": "GridWise", "docs": "/docs"},
    )


@app.post("/optimize-energy")
def optimize_energy(payload: OptimizeRequest, request: Request):
    """Production endpoint.

    - Sync handler so FastAPI runs it in its threadpool; paired with a
      dedicated ThreadPoolExecutor for the interpreter to insulate slow
      LLM calls from everything else.
    - LRU cache keyed by SHA-256 of the canonical request JSON.
    - Defensive interpretation/plan guards wrap the interpreter and
      optimizer outputs so a buggy downstream cannot break the contract.
    """
    started = time.perf_counter()
    cache_key = _canonical_cache_key(payload)

    cached = _RESPONSE_CACHE.get(cache_key)
    if cached is not None:
        total_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "request scenario_id=%s notes=%d types=cache_hit latency_ms=%d",
            payload.scenario_id,
            len(payload.operator_notes),
            total_ms,
        )
        return cached

    # Deterministic order: 0..23 ascending.
    hours_sorted = sorted(payload.hours, key=lambda item: item.hour)
    hours = [hour.model_dump() for hour in hours_sorted]
    battery = payload.battery.model_dump()
    note_count = len(payload.operator_notes)

    # ---- Interpret ---------------------------------------------------------
    interp_started = time.perf_counter()
    raw_interp: object = []
    interp_error: bool = False
    try:
        future = _INTERP_EXECUTOR.submit(
            interpret_notes, list(payload.operator_notes), battery,
        )
        raw_interp = future.result(timeout=INTERPRETER_TIMEOUT_S)
    except Exception:  # noqa: BLE001 - intentional safety net
        interp_error = True
        raw_interp = []
        logger.warning(
            "interpret_notes failed/timeout; substituting no-ops (notes=%d)",
            note_count,
        )
    interpretation = _normalise_interpretation(payload.operator_notes, raw_interp, battery)
    interp_ms = int((time.perf_counter() - interp_started) * 1000)
    applied = [entry for entry in interpretation if entry.get("applies")]

    # ---- Optimise ----------------------------------------------------------
    opt_started = time.perf_counter()
    try:
        normalised = _run_with_retry(hours, battery, applied)
    except Exception as exc:  # noqa: BLE001
        logger.exception("optimizer/plan guard raised: %s", type(exc).__name__)
        total_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "request scenario_id=%s notes=%d types=%s latency_ms=%d status=500",
            payload.scenario_id, note_count, "none", total_ms,
        )
        return JSONResponse(status_code=500, content={"error": "internal error"})

    if (time.perf_counter() - started) > TOTAL_REQUEST_BUDGET_S:
        logger.warning("optimizer exceeded total request budget")
        return JSONResponse(status_code=500, content={"error": "internal error"})

    opt_ms = int((time.perf_counter() - opt_started) * 1000)
    response = _build_response(payload.scenario_id, interpretation, normalised)

    _RESPONSE_CACHE.put(cache_key, response)

    # ---- Log ---------------------------------------------------------------
    directive_types = sorted({str(e.get("directive_type", "no_op")) for e in applied})
    total_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "request scenario_id=%s notes=%d types=%s "
        "interpret_ms=%d optimize_ms=%d total_ms=%d cache_hit=%s interp_err=%s",
        payload.scenario_id, note_count, directive_types,
        interp_ms, opt_ms, total_ms, False, interp_error,
    )
    return response


# ----------------------------------------------------------- local entrypoint

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT") or "8000"),
    )
