"""HTTP entry point for the GridWise service.

Production-grade layer over the interpreter and optimizer packages.
Owns request validation, error normalisation, CORS, the per-request log,
the interpreter/optimizer timeouts, and the public response shape.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.interpreter import interpret_notes
from app.optimizer import optimize
from app.schemas import OptimizeRequest

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


# --------------------------------------------------------- helpers / builders

def _safe_no_op_entry(index: int) -> dict:
    """A directive entry that opts out of the schedule without changing it."""
    return {
        "note_index": index,
        "applies": False,
        "directive_type": "no_op",
        "structured_adjustment": None,
        "explanation": "interpreter unavailable; treated as no-op",
    }


def _build_response(
    scenario_id: str,
    interpretation: list[dict],
    optimizer_result: dict,
) -> dict:
    """Assemble the public response with the exact key order from the contract."""
    applied = [entry for entry in interpretation if entry.get("applies")]
    types = ", ".join(dict.fromkeys(
        str(entry.get("directive_type", "no_op")) for entry in applied
    )) or "none"
    total_cost = float(optimizer_result.get("total_cost_bdt", 0.0))
    summary = f"Applied directives: {types}; total cost: {total_cost:.6f} BDT."
    return {
        "scenario_id": scenario_id,
        "directive_interpretation": interpretation,
        "hourly_plan": optimizer_result.get("hourly_plan", []),
        "total_grid_kwh": float(optimizer_result.get("total_grid_kwh", 0.0)),
        "total_cost_bdt": total_cost,
        "peak_grid_kwh": float(optimizer_result.get("peak_grid_kwh", 0.0)),
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
async def optimize_energy(payload: OptimizeRequest, request: Request):
    started = time.perf_counter()
    # Deterministic order: 0..23 ascending.
    hours_sorted = sorted(payload.hours, key=lambda item: item.hour)
    hours = [hour.model_dump() for hour in hours_sorted]
    battery = payload.battery.model_dump()

    # ---- Interpret ---------------------------------------------------------
    # interpret_notes() is contracted to never raise, but we still guard it
    # with a hard timeout so an LLM stall cannot blow our total budget.
    interpretation: list[dict] = []
    try:
        interpretation = await asyncio.wait_for(
            asyncio.to_thread(interpret_notes, payload.operator_notes, battery),
            timeout=INTERPRETER_TIMEOUT_S,
        )
        # Defensive: if the interpreter returned the wrong shape, fall back
        # to safe no-ops rather than 500ing the whole request.
        if not isinstance(interpretation, list) or len(interpretation) != len(payload.operator_notes):
            interpretation = [_safe_no_op_entry(i) for i in range(len(payload.operator_notes))]
    except (asyncio.TimeoutError, Exception):  # noqa: BLE001 - intentional safety net
        logger.warning(
            "interpret_notes failed/timeout; substituting no-ops (notes=%d)",
            len(payload.operator_notes),
        )
        interpretation = [_safe_no_op_entry(i) for i in range(len(payload.operator_notes))]

    applied = [entry for entry in interpretation if entry.get("applies")]

    # ---- Optimise ----------------------------------------------------------
    # optimize() is contracted to never raise; if it does, that's a 500
    # because it means the schedule is undefined.
    try:
        result = optimize(hours, battery, applied)
    except Exception:  # noqa: BLE001
        logger.exception("optimizer raised")
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "request scenario_id=%s notes=%d types=%s latency_ms=%d status=500",
            payload.scenario_id,
            len(payload.operator_notes),
            "none",
            latency_ms,
        )
        return JSONResponse(status_code=500, content={"error": "internal error"})

    # Guard against an optimizer that ran slow enough to blow the budget.
    if (time.perf_counter() - started) > TOTAL_REQUEST_BUDGET_S:
        logger.warning("optimizer exceeded total request budget")
        return JSONResponse(status_code=500, content={"error": "internal error"})

    response = _build_response(payload.scenario_id, interpretation, result)

    # ---- Log ---------------------------------------------------------------
    directive_types = sorted({str(e.get("directive_type", "no_op")) for e in applied})
    latency_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "request scenario_id=%s notes=%d types=%s latency_ms=%d",
        payload.scenario_id,
        len(payload.operator_notes),
        directive_types,
        latency_ms,
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
