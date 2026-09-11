"""NumPy ground-truth mission generator.

DELIBERATELY NOT app/physics.py. Same physical relationships, different
implementation: this one integrates thermal transients explicitly with its own
time constants, uses a different MAP/altitude formulation (exponential lapse vs
the estimator's power-law ISA), a different VE curve (rpm-dependent parabola vs
the estimator's flat VE), and adds correlated sensor noise. When both engines
are healthy the residual against app/physics.expected_state is therefore small
but NON-ZERO — which is the honest picture. Injected faults then push one
channel's residual well outside that healthy band.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from ..config import EngineConfig, DEFAULT_ENGINE, nominal_params
from .degradation import DegradationSpec, apply_degradation

_FT_TO_M = 0.3048


@dataclass
class Phase:
    name: str
    duration_h: float
    altitude_ft: float
    power_pct: float
    airspeed_kts: float


DEFAULT_PROFILE = [
    Phase("START", 0.02, 0, 12, 0),
    Phase("TAXI", 0.05, 0, 18, 15),
    Phase("TAKEOFF", 0.03, 500, 98, 60),
    Phase("CLIMB", 0.6, 22000, 85, 90),
    Phase("LOITER", 6.0, 22000, 55, 95),
    Phase("CRUISE", 2.0, 20000, 68, 120),
    Phase("LOITER", 4.0, 21000, 52, 92),
    Phase("DESCENT", 0.5, 3000, 28, 110),
    Phase("TAXI", 0.05, 0, 16, 12),
]


def _ambient(alt_ft: float) -> tuple[float, float]:
    """Exponential-ish atmosphere — intentionally not the estimator's ISA law."""
    h = max(alt_ft, 0.0) * _FT_TO_M
    p = 101.325 * math.exp(-h / 8100.0)
    t = 15.0 - 0.00198 * alt_ft
    return p, t


def _ve_curve(rpm: float, cfg: EngineConfig, ve_param: float) -> float:
    """rpm-dependent VE: peak near 0.75*max_rpm, tails off either side."""
    x = rpm / cfg.max_rpm
    shape = 1.0 - 1.1 * (x - 0.78) ** 2
    return ve_param * max(0.6, shape)


def generate_mission_numpy(
    profile: list[Phase] | None = None,
    dt_s: float = 2.0,
    cfg: EngineConfig = DEFAULT_ENGINE,
    degradations_port: list[DegradationSpec] | None = None,
    degradations_stbd: list[DegradationSpec] | None = None,
    seed: int = 7,
    start_time: str = "2026-09-09T12:00:00",
) -> dict[str, Any]:
    """Return {'rows': [...], 'meta': {...}} — one row per timestep, both engines.

    Each row:
      t_s, timestamp, phase, altitude_ft, airspeed_kts, vertical_speed_fpm,
      ambient_pressure_kpa, ambient_temp_c,
      engine1{...telemetry...}, engine2{...telemetry...}
    """
    profile = profile or DEFAULT_PROFILE
    rng = np.random.default_rng(seed)
    nom = nominal_params(cfg)
    n_cyl = cfg.cylinder_count

    deg_p = [d.resolve(nom.get(d.parameter, 1.0)) for d in (degradations_port or [])]
    deg_s = [d.resolve(nom.get(d.parameter, 1.0)) for d in (degradations_stbd or [])]

    from datetime import datetime, timedelta
    t0 = datetime.fromisoformat(start_time)

    # per-engine thermal state (transient integration)
    st = {
        1: {"cht": [cfg.cht_soak_c] * n_cyl, "egt": [cfg.egt_base_c] * n_cyl,
            "cool": cfg.coolant_soak_c, "oil": cfg.oil_temp_soak_c},
        2: {"cht": [cfg.cht_soak_c] * n_cyl, "egt": [cfg.egt_base_c] * n_cyl,
            "cool": cfg.coolant_soak_c, "oil": cfg.oil_temp_soak_c},
    }

    rows: list[dict[str, Any]] = []
    t_s = 0.0
    prev_alt = profile[0].altitude_ft

    for ph in profile:
        n_steps = max(1, int(round(ph.duration_h * 3600.0 / dt_s)))
        for k in range(n_steps):
            frac = (k + 1) / n_steps
            alt = prev_alt + (ph.altitude_ft - prev_alt) * frac
            vs_fpm = (ph.altitude_ft - prev_alt) / max(ph.duration_h, 1e-3) / 60.0
            amb_p, amb_t = _ambient(alt)
            t_h = t_s / 3600.0

            # engine command: same power target, tiny asymmetry so the two
            # engines are not bit-identical even when healthy
            row: dict[str, Any] = {
                "t_s": round(t_s, 1),
                "timestamp": (t0 + timedelta(seconds=t_s)).isoformat(),
                "phase": ph.name,
                "altitude_ft": round(alt, 1),
                "airspeed_kts": round(ph.airspeed_kts + rng.normal(0, 1.2), 2),
                "vertical_speed_fpm": round(vs_fpm, 1),
                "ambient_pressure_kpa": round(amb_p, 3),
                "ambient_temp_c": round(amb_t, 3),
            }
            for eng_id, degs, trim_asym in ((1, deg_p, 0.0), (2, deg_s, 0.6)):
                p = apply_degradation(nom, degs, t_h)
                cyl_bias_egt = np.zeros(n_cyl)
                cyl_bias_cht = np.zeros(n_cyl)
                for d in degs:
                    if d.cylinder is not None:
                        w = d.value_at(t_h)  # 0..1 progress reused as scale
                        prog = 0.0 if t_h <= d.onset_h else min(
                            1.0, (t_h - d.onset_h) / max(d.full_h or 6.0, 1e-6))
                        cyl_bias_egt[d.cylinder - 1] += d.egt_bias_c * prog
                        cyl_bias_cht[d.cylinder - 1] += d.cht_bias_c * prog
                row[f"engine{eng_id}"] = _engine_frame(
                    eng_id, ph, alt, amb_p, amb_t, p, st[eng_id], dt_s, cfg,
                    rng, cyl_bias_egt, cyl_bias_cht, trim_asym,
                )
            rows.append(row)
            t_s += dt_s
        prev_alt = ph.altitude_ft

    return {
        "rows": rows,
        "meta": {
            "dt_s": dt_s, "cylinder_count": n_cyl, "dataSource": "SIMULATED",
            "generator": "numpy", "n_rows": len(rows),
            "degradations_port": [d.__dict__ for d in deg_p],
            "degradations_stbd": [d.__dict__ for d in deg_s],
        },
    }


def _engine_frame(eng_id, ph, alt, amb_p, amb_t, p, state, dt_s, cfg, rng,
                  cyl_bias_egt, cyl_bias_cht, trim_asym) -> dict[str, Any]:
    from ..physics import power_fraction as _phys_pf
    from ..thermo import steady_targets

    n_cyl = cfg.cylinder_count
    power = ph.power_pct / 100.0
    rpm = cfg.idle_rpm + (cfg.max_rpm - cfg.idle_rpm) * (0.25 + 0.75 * power)
    rpm += rng.normal(0, 6) + trim_asym

    # MAP: turbo holds boost until an exponential critical-altitude rolloff
    # (independent formulation from the estimator's power-law model)
    crit_p, _ = _ambient(cfg.rated_altitude_ft)
    pr = 1.0 + (cfg.rated_boost_ratio - 1.0) * min(1.0, amb_p / crit_p) * p["boost_capability"]
    map_kpa = amb_p * (1.0 + (pr - 1.0) * power ** 1.25)

    # power fraction: rpm-dependent VE curve (mission) fed through the shared
    # speed-density power relation. VE degradation shows up here and propagates
    # into every thermal channel via steady_targets.
    ve_eff = _ve_curve(rpm, cfg, p["volumetric_efficiency"])
    pf = float(np.clip(_phys_pf(rpm, map_kpa, amb_p, ve_eff, cfg), 0.02, 1.2))

    tgt = steady_targets(pf, amb_t, p, cfg, rpm=rpm)
    # per-engine build tolerance (fixed, ~0.4%) + a small structural RPM term the
    # estimator's model does NOT have -> healthy residual is non-white but small
    # enough that it biases the VE estimate by only a couple of percent.
    build_tol = 1.0 + 0.004 * math.sin(eng_id * 2.3)
    rpm_term = 0.004 * (rpm - 2200.0)
    cht_target = tgt["cht_c"] * build_tol + rpm_term
    egt_target = tgt["egt_c"] * build_tol + 1.7 * rpm_term
    cool_target = tgt["coolant_temp_c"] * build_tol
    oil_target = tgt["oil_temperature_c"] * build_tol

    # explicit first-order transient integration (own time constants)
    a_cht = 1 - math.exp(-dt_s / 50.0)
    a_egt = 1 - math.exp(-dt_s / 8.0)
    a_cool = 1 - math.exp(-dt_s / 55.0)
    a_oil = 1 - math.exp(-dt_s / 130.0)

    cht = []
    egt = []
    for i in range(n_cyl):
        # natural per-cylinder scatter (flow distribution), fixed per engine
        scatter_c = 3.0 * math.sin(eng_id * 1.7 + i * 2.0)
        scatter_e = 6.0 * math.sin(eng_id * 0.9 + i * 1.3)
        ct = cht_target + scatter_c + cyl_bias_cht[i]
        et = egt_target + scatter_e + cyl_bias_egt[i]
        state["cht"][i] += a_cht * (ct - state["cht"][i])
        state["egt"][i] += a_egt * (et - state["egt"][i])
        cht.append(state["cht"][i] + rng.normal(0, 1.1))
        egt.append(state["egt"][i] + rng.normal(0, 2.4))

    state["cool"] += a_cool * (cool_target - state["cool"])
    state["oil"] += a_oil * (oil_target - state["oil"])

    oil_press = (cfg.oil_press_idle_kpa +
                 (cfg.oil_press_rated_kpa - cfg.oil_press_idle_kpa) * (rpm / cfg.max_rpm)
                 ) * (0.5 + 0.5 * p["oil_system_health"]) + rng.normal(0, 3)
    fuel_flow = 6.0 + 30.0 * pf + rng.normal(0, 0.3)
    iat = amb_t + 42.0 * (map_kpa / max(amb_p, 1.0) - 1.0) * (1 - cfg.intercooler_effectiveness)

    return {
        "engineId": eng_id,
        "rpm": round(float(rpm), 1),
        "manifold_pressure": round(float(map_kpa), 2),
        "throttle_position_pct": round(float(ph.power_pct + rng.normal(0, 0.5)), 1),
        "fuel_flow": round(float(fuel_flow), 2),
        "oil_pressure": round(float(oil_press), 1),
        "oil_temperature": round(float(state["oil"] + rng.normal(0, 0.6)), 2),
        "coolant_temp_c": round(float(state["cool"] + rng.normal(0, 0.6)), 2),
        "intake_air_temp_c": round(float(iat + rng.normal(0, 0.8)), 2),
        "fuel_rail_pressure_bar": round(float(1650 + rng.normal(0, 8)), 1),
        "egt_cylinders": [round(float(x), 1) for x in egt],
        "cht_cylinders": [round(float(x), 1) for x in cht],
        "vibration": round(float(1.8 + 0.6 * pf + rng.normal(0, 0.15)), 3),
        "battery_voltage": round(float(24.5 + rng.normal(0, 0.1)), 2),
        "power_fraction_true": round(float(pf), 4),
    }
