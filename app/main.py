"""HTTP entry point for the GridWise prototype."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.interpreter import interpret_notes
from app.optimizer import optimize
from app.schemas import OptimizeRequest

load_dotenv()
app = FastAPI(title="GridWise")


@app.exception_handler(RequestValidationError)
async def invalid_request(_request: Request, _exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "invalid request"})


@app.exception_handler(Exception)
async def unexpected_error(_request: Request, _exc: Exception):
    return JSONResponse(status_code=500, content={"error": "internal error"})


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/optimize-energy")
def optimize_energy(payload: OptimizeRequest):
    hours = [hour.model_dump() for hour in sorted(payload.hours, key=lambda item: item.hour)]
    battery = payload.battery.model_dump()
    interpretation = interpret_notes(payload.operator_notes, battery)
    applied = [entry for entry in interpretation if entry["applies"]]
    result = optimize(hours, battery, applied)
    types = ", ".join(dict.fromkeys(entry["directive_type"] for entry in applied)) or "none"
    summary = f"Applied directives: {types}; total cost: {result['total_cost_bdt']:.6f} BDT."
    return {
        "scenario_id": payload.scenario_id,
        "directive_interpretation": interpretation,
        "hourly_plan": result["hourly_plan"],
        "total_grid_kwh": result["total_grid_kwh"],
        "total_cost_bdt": result["total_cost_bdt"],
        "peak_grid_kwh": result["peak_grid_kwh"],
        "plan_summary": summary,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT") or "8000"))
