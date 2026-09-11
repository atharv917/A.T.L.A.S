// The ONE place mock vs. real is decided. Every component imports from here and
// never knows which it got.
//
//   USE_MOCK = true  (default)  -> served from src/mocks/dashboard.json, with a
//                                  little live jitter + a scripted anomaly ramp
//                                  so the demo moves without a backend.
//   USE_MOCK = false            -> GET  /api/v1/dashboard/{engineId}
//                                  POST /api/v1/engines/{engineId}/simulate
//
// Flip with VITE_USE_MOCK=false at build/dev time, or edit the default below.

import mockData from '../mocks/dashboard.json';

export const USE_MOCK =
  (import.meta.env.VITE_USE_MOCK ?? 'true').toString() !== 'false';

export const ENGINE_IDS = [1, 2];
const API_BASE = '/api/v1';

// ---------------------------------------------------------------------------
// real backend
// ---------------------------------------------------------------------------
async function fetchDashboardReal(engineId) {
  const res = await fetch(`${API_BASE}/dashboard/${engineId}`, {
    headers: { Accept: 'application/json' },
  });
  if (!res.ok) throw new Error(`dashboard ${engineId}: HTTP ${res.status}`);
  return normalize(await res.json());
}

async function simulateMissionReal(engineId, missionProfile, variants) {
  const res = await fetch(`${API_BASE}/engines/${engineId}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ engineId, missionProfile, variants }),
  });
  if (!res.ok) throw new Error(`simulate ${engineId}: HTTP ${res.status}`);
  return res.json();
}

// The backend may name things slightly differently as it evolves; keep a single
// tolerant normalizer so components can rely on the mock's shape.
function normalize(d) {
  if (d && d.twin && !d.twin.anomalyThreshold) d.twin.anomalyThreshold = 3.0;
  if (d && d.twinAvailable === undefined) d.twinAvailable = !!d.twin;
  return d;
}

// ---------------------------------------------------------------------------
// mock — stateful so the demo is not a frozen snapshot
// ---------------------------------------------------------------------------
const t0 = Date.now();
const RAMP_SECONDS = 75; // anomaly on engine 1 crosses threshold at ~this mark

function jitter(base, amp) {
  return +(base + (Math.random() - 0.5) * 2 * amp).toFixed(2);
}

function mockDashboard(engineId) {
  const src = mockData[String(engineId)];
  if (!src) throw new Error(`no mock for engine ${engineId}`);
  const d = structuredClone(src);
  const elapsed = (Date.now() - t0) / 1000;

  // live telemetry jitter
  const tel = d.telemetry;
  tel.timestamp = new Date().toISOString().slice(0, 19);
  tel.rpm = Math.round(jitter(tel.rpm, 8));
  tel.coolantTempC = jitter(tel.coolantTempC, 0.6);
  tel.oilTemperature = jitter(tel.oilTemperature, 0.6);
  tel.oilPressure = Math.round(jitter(tel.oilPressure, 4));
  tel.egtCylinders = tel.egtCylinders.map((v) => Math.round(jitter(v, 3)));
  tel.chtCylinders = tel.chtCylinders.map((v) => Math.round(jitter(v, 2)));

  if (engineId === 1 && d.twin) {
    // scripted degradation ramp: anomaly score and the cyl-3 residual grow,
    // health/RUL follow, so the story unfolds live on stage.
    const p = Math.min(1, elapsed / RAMP_SECONDS);
    const score = 1.1 + p * 2.4 + (Math.random() - 0.5) * 0.15;
    d.twin.anomalyScore = +score.toFixed(2);
    d.twin.residual.cht_c[2] = +(12 + p * 26 + (Math.random() - 0.5) * 2).toFixed(1);
    d.twin.cylinderSpread.egt_spread = +(18 + p * 34).toFixed(1);
    d.twin.parameters.volumetric_efficiency.value = +(0.88 - p * 0.03).toFixed(3);
    d.health.components.combustion.index = +(0.94 - p * 0.2).toFixed(3);
    d.health.overall = Math.min(
      ...Object.values(d.health.components).map((c) => c.index)
    );
    d.health.limitedBy = Object.entries(d.health.components).sort(
      (a, b) => a[1].index - b[1].index
    )[0][0];
    d.rul.medianHours = Math.round(140 - p * 60);
    d.rul.p05Hours = Math.round(d.rul.medianHours * 0.55);
    d.rul.p95Hours = Math.round(d.rul.medianHours * 1.7);
    d.rul.pFailMission = +(0.01 + p * 0.03).toFixed(3);

    const hist = d.twin.anomalyHistory;
    hist.push({ t: '0h', score: d.twin.anomalyScore });
    if (hist.length > 1) hist[hist.length - 2].t = `-${Math.round((hist.length - 1) * 0.4)}m`;
    if (hist.length > 14) hist.shift();
  }
  return normalize(d);
}

function mockSimulate(engineId) {
  const src = mockData[String(engineId)];
  const base = structuredClone(src.missionSim);
  // tiny variation so re-running "Simulate" visibly recomputes
  base.results = base.results.map((r) => ({
    ...r,
    pComplete: +Math.min(0.999, r.pComplete + (Math.random() - 0.5) * 0.01).toFixed(3),
    damageConsumed: +(r.damageConsumed * (0.95 + Math.random() * 0.1)).toFixed(3),
  }));
  const d0 = base.results[0].damageConsumed || 1e-6;
  const d1 = base.results[1].damageConsumed || 1e-6;
  base.comparativeRatio = +(Math.max(d0, d1) / Math.max(Math.min(d0, d1), 1e-6)).toFixed(2);
  base.dataSource = 'SIMULATED';
  return base;
}

// ---------------------------------------------------------------------------
// public surface
// ---------------------------------------------------------------------------
export async function getDashboard(engineId) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 120)); // feel like a network call
    return mockDashboard(engineId);
  }
  return fetchDashboardReal(engineId);
}

export async function simulateMission(engineId, missionProfile, variants) {
  if (USE_MOCK) {
    await new Promise((r) => setTimeout(r, 400));
    return mockSimulate(engineId);
  }
  return simulateMissionReal(engineId, missionProfile, variants);
}

export const DEFAULT_MISSION_PROFILE = [
  { phase: 'loiter', altitude_ft: 22000, power_pct: 58, duration_h: 12 },
  { phase: 'descent', altitude_ft: 5000, power_pct: 30, duration_h: 0.5 },
];
