"""FastAPI entrypoint for the uav-twin service.

    uvicorn app.main:app --reload --port 8000

Routes (exactly the backend team's contract):
    GET  /health          -> "ok"
    POST /twin/step       -> full twin state for one telemetry frame
    POST /twin/simulate   -> Monte-Carlo mission reliability comparison

Extra convenience routes (not required by the contract, handy for the demo):
    GET  /twin/state/{engineId}   -> last computed snapshot summary
    POST /twin/reset              -> clear all in-memory twins
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from . import DATA_SOURCE, __version__
from .config import DEFAULT_ENGINE
from .schemas import TwinSimulateRequest, TwinStepRequest
from .simulate import simulate_mission
from .state import TwinRegistry

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("uav-twin")

ESTIMATOR_METHOD = os.getenv("TWIN_ESTIMATOR", "wls")  # "wls" | "ukf"

app = FastAPI(title="uav-twin", version=__version__,
              description="SIH26054 digital twin core — all data SIMULATED")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

registry = TwinRegistry(cfg=DEFAULT_ENGINE, estimator_method=ESTIMATOR_METHOD)


@app.get("/health", response_class=PlainTextResponse)
def health() -> str:
    return "ok"


@app.get("/")
def root() -> dict:
    return {
        "service": "uav-twin",
        "version": __version__,
        "dataSource": DATA_SOURCE,
        "estimator": ESTIMATOR_METHOD,
        "endpoints": ["/health", "/twin/step", "/twin/simulate",
                      "/twin/state/{engineId}", "/twin/reset"],
    }


@app.post("/twin/step")
async def twin_step(req: TwinStepRequest, request: Request):
    """Run the full pipeline for one telemetry frame.

    Never raises to the caller: on any internal error we return a minimal,
    contract-shaped body with dataSource so the backend can persist and move on.
    """
    payload = req.model_dump()
    try:
        return registry.step(payload)
    except Exception as exc:  # pragma: no cover - defensive
        log.exception("twin/step failed for engine %s", payload.get("engineId"))
        return JSONResponse(
            status_code=200,
            content={
                "engineId": payload.get("engineId", 1),
                "regime": "UNKNOWN",
                "expected": {}, "residual": {}, "parameters": {},
                "parameterSigma": {}, "engineDelta": {}, "cylinderSpread": {},
                "anomalyScore": 0.0, "anomalyFired": False, "confidence": 0.0,
                "health": {"overall": 1.0, "limited_by": "unknown"},
                "rul": {"tier": 3, "median_hours": 0, "p05_hours": 0,
                        "p95_hours": 0, "p_fail_mission": 0.0, "assumptions": {}},
                "diagnosis": {"hypotheses": []},
                "error": str(exc),
                "dataSource": DATA_SOURCE,
            },
        )


@app.post("/twin/simulate")
async def twin_simulate(req: TwinSimulateRequest):
    payload = req.model_dump()
    twin = registry.snapshot(int(payload.get("engineId", 1)))
    if twin is not None:
        params = twin.estimator.parameters
        sigma = twin.estimator.parameter_sigma
        damage = twin.rul.damage
    else:  # no step() seen yet — simulate from nominal
        from .config import nominal_params

        params = nominal_params(DEFAULT_ENGINE)
        sigma = {k: 0.01 for k in params}
        damage = 0.0

    profile = payload.get("missionProfile") or [
        {"phase": "loiter", "altitude_ft": 22000, "power_pct": 58, "duration_h": 12},
        {"phase": "descent", "altitude_ft": 5000, "power_pct": 30, "duration_h": 0.5},
    ]
    try:
        return simulate_mission(
            profile, params, sigma, damage_so_far=damage,
            variants=payload.get("variants"), cfg=DEFAULT_ENGINE,
        )
    except Exception as exc:  # pragma: no cover
        log.exception("twin/simulate failed")
        return JSONResponse(status_code=200, content={
            "results": [], "comparativeRatio": None,
            "error": str(exc), "dataSource": DATA_SOURCE,
        })


@app.get("/twin/state/{engine_id}")
def twin_state(engine_id: int):
    twin = registry.snapshot(engine_id)
    if twin is None:
        return JSONResponse(status_code=404, content={"error": "no such engine",
                                                      "dataSource": DATA_SOURCE})
    return {
        "engineId": engine_id,
        "steps": twin._steps,
        "regime": twin.regime.current,
        "parameters": twin.estimator.parameters,
        "parameterSigma": twin.estimator.parameter_sigma,
        "estimatorMethod": twin.estimator.active_method,
        "valveDamage": round(twin.rul.damage, 5),
        "dataSource": DATA_SOURCE,
    }


@app.post("/twin/reset")
def twin_reset():
    global registry
    registry = TwinRegistry(cfg=DEFAULT_ENGINE, estimator_method=ESTIMATOR_METHOD)
    return {"reset": True, "dataSource": DATA_SOURCE}
