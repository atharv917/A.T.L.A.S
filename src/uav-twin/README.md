# uav-twin — Python Digital Twin Core (SIH26054)

AI-enabled real-time digital twin for a turbocharged, liquid-cooled,
compression-ignition inline-4 aero piston engine in a MALE UAV.

> **Every number this service produces is a number about a simulator.**
> There is no real engine and no run-to-failure dataset. Every response
> carries `"dataSource": "SIMULATED"`.

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows;  source .venv/bin/activate on *nix
pip install -r requirements.txt

pytest -q                         # 34 tests, ~10s
uvicorn app.main:app --reload --port 8000
```

Drive the dashboard end-to-end without the Java backend:

```bash
uvicorn app.main:app --port 8000                                  # terminal 1
python -m validation.replay_mission --url http://localhost:8000 --speed 300 --fault injector_cyl3
```

Produce the headline evidence table:

```bash
python -m validation.validate_parameter_recovery
```

## How the code maps to the contract

| Pipeline stage | Module | Notes |
|---|---|---|
| Config (all engine constants) | `app/config.py` | `EngineConfig` dataclass; nothing engine-specific is hard-coded elsewhere |
| Pure physics (estimator side) | `app/physics.py` | stateless `expected_state()`, NumPy speed-density + turbo MAP |
| Shared steady thermal map | `app/thermo.py` | the one untuned relationship both sides share (see below) |
| Ground-truth mission | `app/mission_sim/` | JSBSim `FGPiston` when installed, else independent NumPy generator |
| Degradation injection | `app/mission_sim/degradation.py` | drift a named parameter linearly/exponentially from an onset time |
| Regime detection | `app/regime.py` | 8 phases from RPM + airspeed + vertical speed, **persistence hysteresis** |
| Residuals | `app/residuals.py` | `measured - expected`, per cylinder |
| Differential features | `app/differential.py` | engine↔engine delta, cylinder↔cylinder spread — no model needed |
| Parameter estimation | `app/estimator.py` | windowed non-linear least squares (default) or UKF (`TWIN_ESTIMATOR=ukf`) |
| Anomaly detection | `app/anomaly.py` | Mahalanobis distance + **CUSUM persistence gate** with per-sample step cap |
| Health indices | `app/health.py` | per-parameter 0–1 index, **overall = min(components)**, `limited_by` |
| RUL (3 tiers) | `app/rul.py` | Arrhenius valve life / health-trend extrapolation / onset-rate projection |
| Mission simulation | `app/simulate.py` | Monte-Carlo forward run from current estimated parameters |
| FastAPI app | `app/main.py` | `/health`, `/twin/step`, `/twin/simulate` (+ `/twin/state/{id}`, `/twin/reset`) |

### The two-implementation defense

A judge's sharpest attack: *"if the same physics generates the data and the
expectation, every residual is zero by construction."* The defense:

* the **ground-truth mission** (`app/mission_sim/`) and the **estimator model**
  (`app/physics.py`) are separate implementations;
* they deliberately differ in: `power_fraction` derivation, atmosphere model
  (exponential vs power-law ISA), transient integration vs steady state, an
  extra structural RPM term in the mission, sensor noise, per-engine build
  tolerance;
* they share exactly **one** relationship — `app/thermo.py`, the equilibrium
  temperature map given power fraction and ambient — because it is textbook and
  untuned. Sharing it keeps the *healthy* residual small so that an injected
  fault, not a modelling offset, is what moves a residual.

Consequence, measured by `validation/validate_parameter_recovery.py`: the two
models carry a ~3% constant offset in absolute VE, but the estimator recovers
the **change** in VE to within 0.001 with 0.15–0.55 h detection latency.

## API

### `GET /health` → `200 "ok"`

### `POST /twin/step`

Request (fields may be null / missing — the service degrades, never 500s):

```jsonc
{
  "engineId": 1, "timestamp": "2026-09-09T14:32:00", "seq": 1042,
  "cylinderCount": 4, "engineType": "PISTON_CI_TURBO",
  "telemetry": { "rpm": 2450, "manifold_pressure": 89.2, "throttle_position_pct": 58,
    "fuel_flow": 32.5, "oil_pressure": 412, "oil_temperature": 92,
    "coolant_temp_c": 88, "intake_air_temp_c": 45, "fuel_rail_pressure_bar": 1650,
    "egt_cylinders": [615,618,649,620], "cht_cylinders": [178,176,196,177],
    "vibration": 2.1, "battery_voltage": 24.5 },
  "ambient": { "pressure_kpa": 46.5, "temp_c": -18.2, "altitude_ft": 22000, "airspeed_kts": 95 },
  "paired": { "engineId": 2, "egt_cylinders": [610,605,612,608],
    "cht_cylinders": [174,173,175,172], "coolant_temp_c": 86, "oil_pressure": 408,
    "fuel_flow": 31.9, "manifold_pressure": 88.7 }
}
```

Response (`step response`):

```jsonc
{
  "engineId": 1, "regime": "LOITER",
  "expected": { "cht_c": [...4], "egt_c": [...4], "coolant_temp_c": ...,
                "oil_temperature_c": ..., "oil_press_kpa": ..., "manifold_pressure_kpa": ... },
  "residual": { "cht_c": [1.2,0.8,31.4,1.1], "egt_c": [...4], "coolant_temp_c": ...,
                "oil_temperature_c": ..., "oil_press_kpa": ... },
  "parameters":      { "volumetric_efficiency":0.862, "cooling_factor":0.91,
                       "boost_capability":0.97, "oil_system_health":0.96 },
  "parameterSigma":  { "volumetric_efficiency":0.004, ... },
  "estimatorMethod": "wls",
  "engineDelta":     { "cht_mean_diff":3.1, "egt_mean_diff":14.2, ... },
  "cylinderSpread":  { "egt_spread":38.0, "cht_spread":22.0, "hottest_cylinder":3,
                       "egt_outlier_margin":29.4, "cht_outlier_margin":18.9 },
  "anomalyScore": 2.6, "anomalyFired": false,
  "anomalyHistory": [ {"t":"-110m","score":1.1}, ... {"t":"0h","score":2.6} ],
  "confidence": 0.82,
  "health": { "overall":0.78, "limited_by":"combustion",
              "cooling":0.91, "combustion":0.78, "induction":0.97, "lubrication":0.96,
              "components": { "cooling":{"index":0.91,"confidence":0.82}, ... } },
  "rul": { "tier":1, "component":"combustion_cyl3",
           "median_hours":96, "p05_hours":51, "p95_hours":158,
           "p_fail_mission":0.024, "assumptions":{...},
           "all_tiers":[ {...tier1}, {...tier3} ] },
  "diagnosis": { "hypotheses": [
      {"fault":"injector_degradation_cyl3","label":"Injector degradation (cyl 3)","probability":0.61},
      {"fault":"exhaust_valve_recession_cyl3","label":"Exhaust valve recession (cyl 3)","probability":0.27},
      {"fault":"egt_sensor_drift_cyl3","label":"EGT sensor drift (cyl 3)","probability":0.09},
      ... every remaining hypothesis, lowest kept ] },
  "dataSource": "SIMULATED"
}
```

### `POST /twin/simulate` (`simulate response`)

```jsonc
// request
{ "engineId": 1,
  "missionProfile": [
    {"phase":"loiter","altitude_ft":22000,"power_pct":58,"duration_h":12},
    {"phase":"descent","altitude_ft":5000,"power_pct":30,"duration_h":0.5} ],
  "variants": ["as_planned","derated_85pct"] }        // optional, defaults to both

// response
{ "results": [
    {"variant":"as_planned","label":"As Planned","pComplete":0.971,
     "damageConsumed":{"exhaust_valve_hottest":0.031}},
    {"variant":"derated_85pct","label":"De-rated 85%","pComplete":0.989,
     "damageConsumed":{"exhaust_valve_hottest":0.019}} ],
  "comparativeRatio": 1.63,
  "dataSource": "SIMULATED" }
```

`/twin/simulate` uses the engine's **current estimated parameters** (from the
last `/twin/step` for that `engineId`) as the Monte-Carlo starting point; if no
step has been seen it simulates from nominal.

## Estimator choice

`wls` (windowed non-linear least squares) is the default because a 28-hour demo
cannot risk a filter that might not converge on stage. Set `TWIN_ESTIMATOR=ukf`
to use the UnscentedKalmanFilter instead — it auto-falls-back to `wls` per
engine if `filterpy` is missing or the filter goes non-finite. Both report the
same 4 named parameters with sigma.

## Not built (out of scope, by instruction)

No LSTM/Transformer/PINN. No Kafka/microservices/K8s. No vibration signal
processing (no accelerometer data exists — `vibration` is accepted and ignored).
No CAN/ARINC parsing. No auth (the Spring backend owns that). No validation
against a real engine — there is none; validation is by parameter recovery on
injected faults and residual behaviour on healthy simulated data.
