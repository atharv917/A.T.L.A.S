# CLAUDE.md — uav-frontend (React Dashboard)

## Project

SIH26054 (DRDO): digital twin dashboard for aero piston engines in MALE UAVs.
Operator-facing dashboard consumed by judges live during an 8-minute demo.
**Deadline: 28 hours from now.**

A working, honest, uncluttered dashboard beats a feature-complete one that
looks unfinished or breaks live.

## Do not wait for the real backend

Built against **mock data matching the exact JSON shape** the Java backend
returns. The switch lives in ONE place: `src/api/dashboardApi.js`
(`USE_MOCK`, default `true`, overridable with `VITE_USE_MOCK=false`). Flip it
and the same components fetch `/api/v1/dashboard/{engineId}` for real.

## The demo script this dashboard supports (panel order = build order)

1. Overview tile — two engines, current regime, all health green. **`DATA
   SOURCE: SIMULATED` badge visible on every panel, structurally, always.**
2. Measured / Expected / Residual panel — CHT channel, the "it's a twin" panel.
3. Parameter panel — estimated physical parameters with units + uncertainty,
   nominal marker.
4. Differential panel — **most important panel.** Port vs starboard for a
   channel, and all 4 cylinders' EGT for one engine.
5. Anomaly / diagnosis panel — score over time (flat, then rises across a
   threshold), ranked hypotheses, lowest one always shown.
6. Health panel — component bars, overall = MIN, "limited by: X".
7. RUL panel — a RANGE never a bare number, plus P(fail this mission).
8. Mission simulation panel — **the demo closer.** Two scenario cards, POST
   action.

See `README.md` for how each of the 8 lives in `src/components/`.

## Non-negotiable honesty elements

- `DATA SOURCE: SIMULATED` badge — `src/components/DataSourceBadge.jsx`, rendered
  by every `Panel` header, not removable by interaction.
- RUL never a bare number — `RulPanel` always renders the CI band + P(fail).
- Health overall never an average — `HealthPanel` shows `min` + `limited by`.
- Lowest-ranked diagnosis hypothesis always shown — `AnomalyPanel` maps the full
  list.
- Twin unreachable -> explicit "twin unavailable, raw telemetry only" state,
  never a silent freeze — handled in `useDashboard` + `App`.

## Stack

React + Vite, Recharts only, plain CSS (`src/index.css`, avionics dark theme),
2-second polling via `useDashboard`, no router, no state library. No
WebSocket/SSE, no auth, no mobile layout, no 3D.
