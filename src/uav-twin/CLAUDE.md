# CLAUDE.md — uav-twin (Python Digital Twin Service)

## Project

SIH26054 (DRDO): AI-enabled real-time digital twin for aero piston engines in
MALE UAVs. This repo is the **Python twin core** — physics model, parameter
estimation, anomaly detection, health, RUL, mission simulation. **Deadline: 28
hours from now.** Ship something that runs over something elegant that doesn't.

A separate Spring Boot repo (`uav-backend`) handles persistence, REST API,
validation and orchestration. This service is called BY that backend over
REST/JSON. See "API Contract" below — that is the interface you must implement
exactly, because the backend team is building against it in parallel and it
will not change.

## Non-negotiable engineering facts (do not relitigate these)

- **No real engine, no dataset exists.** DRDO supplied none; no public
  run-to-failure dataset exists for any aero piston engine. Every number this
  service produces is a number about a simulator. Every response MUST include
  `"dataSource": "SIMULATED"`.
- **Engine class (assumed, must stay configurable):** turbocharged,
  liquid-cooled, compression-ignition, common-rail, FADEC-managed inline-4.
  Put engine-specific numbers (nominal VE, cooling factor, rated boost,
  rated altitude, cylinder count) in one config object, never hard-coded.
- **Two independent physics implementations, not one.** Generate ground-truth
  missions with JSBSim (`pip install jsbsim`, `FGPiston` engine model).
  Serve the live estimator with a SEPARATE pure-Python/NumPy reimplementation
  of the same relationships. If you use JSBSim on both sides, residuals are
  zero by construction and prove nothing — this is the single sharpest attack
  a judge will make and the two-implementation design is the defense.
- **Model capacity is not the bottleneck. Data is.** Do NOT reach for an
  LSTM, Transformer, or PINN for anything.
- **Health aggregates by MINIMUM, not mean.**
- **RUL is always a distribution with a tier label, never a bare number.**
- **Regime-conditioned everything.** Detect flight phase from RPM + airspeed +
  vertical speed, with hysteresis, before computing any residual or anomaly.

See the repo README.md for the implemented architecture and how it maps to
this contract.

## API Contract — implemented exactly as below

```
GET /health              -> 200 "ok"
POST /twin/step          -> see README "step response"
POST /twin/simulate      -> see README "simulate response"
```

If a field in an incoming request is missing or null, do not crash — degrade
gracefully. The backend must never be blocked by a twin failure.
