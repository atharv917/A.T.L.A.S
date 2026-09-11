# uav-frontend — Operator Dashboard (SIH26054)

Dark, data-dense, instrument-panel digital-twin dashboard for the 8-minute
judge demo. React + Vite + Recharts. **Every value on screen is SIMULATED** and
the `DATA SOURCE: SIMULATED` badge is a structural part of every panel header
and the top bar — it cannot be dismissed.

## Run

Requires Node 18+ (not installed on the build machine — verify locally).

```bash
npm install
npm run dev            # http://localhost:5173, mock data, no backend needed
```

Against the real Java backend:

```bash
# backend on :8080, twin on :8000, then
VITE_USE_MOCK=false npm run dev          # proxies /api -> :8080 (see vite.config.js)
```

`npm run build` → static bundle in `dist/`.

## The 8 panels (demo click-order = file, = build order)

| # | Panel | File | The one thing it must do |
|---|---|---|---|
| 1 | Platform Overview | `components/OverviewTile.jsx` | two engines, regime, health; badge everywhere |
| 2 | Measured · Expected · Residual | `components/MeasuredExpectedResidualPanel.jsx` | show the physics **expectation** and the gap, not just the sensor |
| 3 | Estimated Parameters | `components/ParameterPanel.jsx` | physical params as bars with **nominal marker + ±σ** |
| 4 | Differential | `components/DifferentialPanel.jsx` | port↔stbd **and** cyl↔cyl → "it's cylinder N" |
| 5 | Anomaly & Diagnosis | `components/AnomalyPanel.jsx` | score flat → rises → crosses threshold; **lowest hypothesis always shown** |
| 6 | Component Health | `components/HealthPanel.jsx` | overall = **min**, labelled "limited by", never averaged |
| 7 | Remaining Useful Life | `components/RulPanel.jsx` | a **range** + P(fail mission), never a bare number |
| 8 | Mission Simulation | `components/MissionSimPanel.jsx` | **demo closer** — POST, two scenario cards, comparative ratio |

## Mock vs real — one switch

`src/api/dashboardApi.js` is the only file that knows. `USE_MOCK` defaults true
(`VITE_USE_MOCK=false` to flip). In mock mode it serves `src/mocks/dashboard.json`
with:

- live per-poll jitter on telemetry so the screen looks alive;
- a **scripted degradation ramp on engine 1**: over ~75 s the anomaly score
  climbs from ~1.1 and crosses the 3.0 threshold, the cyl-3 CHT residual grows,
  VE drifts down, combustion health falls, RUL shortens — so the whole story
  unfolds live on stage with no backend.

Switch engine to `UAV-ENG-002` to show a healthy engine for contrast.

## Real contract

`GET /api/v1/dashboard/{engineId}` → the shape in `src/mocks/dashboard.json`.
`POST /api/v1/engines/{engineId}/simulate` → `{ results:[…], comparativeRatio }`.
`useDashboard` polls every 2 s, keeps the last good payload on a failed poll
(banner: "feed stale"), and when the payload has no `twin` block it shows the
explicit **"TWIN UNAVAILABLE — showing raw telemetry only"** banner rather than
presenting stale twin numbers as live.

## Not built (by instruction)

No WebSocket/SSE, no auth, no router, no state library, no mobile layout, no 3D
engine render, no light theme.
