"""POST /twin/simulate — Monte-Carlo forward run of the physics model.

This is the demo closer. It proves the "digital twin" claim: from an engine's
CURRENT estimated parameters (with their uncertainty), roll the physics model
forward over a hypothetical mission profile many times, sampling parameter
values and degradation-rate noise, and count how often accumulated damage stays
below the failure threshold before the mission ends.

Reports, per variant (`as_planned`, `derated_85pct`):
  - pComplete: fraction of Monte-Carlo runs that finish without exceeding the
    damage threshold on any tracked component
  - damageConsumed: median additional damage accumulated over the mission

A dashboard cannot do this — it needs a forward model of state evolution.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from . import DATA_SOURCE
from .config import EngineConfig, DEFAULT_ENGINE, nominal_params, PARAM_NAMES
from .physics import expected_state, isa_from_altitude
from .rul import _metal_temp_c

_VARIANT_POWER_SCALE = {
    "as_planned": 1.0,
    "derated_85pct": 0.85,
    "derated_90pct": 0.90,
    "derated_75pct": 0.75,
}


def simulate_mission(
    mission_profile: list[dict[str, Any]],
    current_params: dict[str, float],
    param_sigma: dict[str, float] | None = None,
    damage_so_far: float = 0.0,
    variants: list[str] | None = None,
    cfg: EngineConfig = DEFAULT_ENGINE,
    n_mc: int = 300,
    damage_threshold: float = 1.0,
    seed: int = 2026,
) -> dict[str, Any]:
    variants = variants or ["as_planned", "derated_85pct"]
    sigma = param_sigma or {k: 0.01 for k in PARAM_NAMES}
    nom = nominal_params(cfg)
    rng = np.random.default_rng(seed)

    results = []
    for variant in variants:
        pscale = _VARIANT_POWER_SCALE.get(variant, 1.0)
        completed = 0
        end_damage = []

        for _ in range(n_mc):
            # sample a plausible current parameter vector from the estimate
            p = {}
            for k in PARAM_NAMES:
                v = float(current_params.get(k, nom[k]))
                s = float(sigma.get(k, 0.01))
                p[k] = float(np.clip(rng.normal(v, max(s, 1e-3)), 0.5, 1.05))
            # a slow continued-drift rate on the limiting parameter
            drift_rate = abs(rng.normal(0.0, 0.004))  # per hour

            dmg = damage_so_far
            failed = False
            for seg in mission_profile:
                dur_h = float(seg.get("duration_h", seg.get("duration_hours", 1.0)))
                alt = float(seg.get("altitude_ft", 20000.0))
                power = float(seg.get("power_pct", 55.0)) / 100.0 * pscale
                amb_p, amb_t = isa_from_altitude(alt)
                rpm = cfg.idle_rpm + (cfg.max_rpm - cfg.idle_rpm) * (0.25 + 0.75 * power)

                # integrate damage over the segment in <=0.5h sub-steps
                steps = max(1, int(math.ceil(dur_h / 0.5)))
                sub = dur_h / steps
                for _s in range(steps):
                    pp = dict(p)
                    pp["volumetric_efficiency"] = max(
                        0.5, pp["volumetric_efficiency"] - drift_rate * sub
                    )
                    op = {"rpm": rpm, "throttle_position_pct": power * 100.0}
                    exp = expected_state(op, pp, {"pressure_kpa": amb_p,
                                                  "temp_c": amb_t}, cfg)
                    egt_hot = max(exp["egt_c"])
                    cht_hot = max(exp["cht_c"])
                    tk = _metal_temp_c(egt_hot, cht_hot, cfg) + 273.15
                    rate = cfg.valve_arrhenius_A * math.exp(
                        -cfg.valve_activation_energy_J_per_mol
                        / (cfg.gas_constant_R * tk)
                    )
                    dmg += rate * sub
                    if dmg >= damage_threshold:
                        failed = True
                        break
                if failed:
                    break

            if not failed:
                completed += 1
            end_damage.append(min(dmg, 1.5) - damage_so_far)

        results.append({
            "variant": variant,
            "label": _VARIANT_LABEL.get(variant, variant),
            "pComplete": round(completed / n_mc, 3),
            "damageConsumed": {
                "exhaust_valve_hottest": round(float(np.median(end_damage)), 4)
            },
        })

    ratio = None
    if len(results) >= 2:
        d0 = results[0]["damageConsumed"]["exhaust_valve_hottest"] or 1e-6
        d1 = results[1]["damageConsumed"]["exhaust_valve_hottest"] or 1e-6
        ratio = round(max(d0, d1) / max(min(d0, d1), 1e-6), 2)

    return {
        "results": results,
        "comparativeRatio": ratio,
        "dataSource": DATA_SOURCE,
    }


_VARIANT_LABEL = {
    "as_planned": "As Planned",
    "derated_85pct": "De-rated 85%",
    "derated_90pct": "De-rated 90%",
    "derated_75pct": "De-rated 75%",
}
