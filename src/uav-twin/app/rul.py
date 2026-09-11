"""Remaining Useful Life — three tiers, most-conservative reported, all shown.

None of these need run-to-failure data:

  Tier 1  Arrhenius exhaust-valve recession. dD/dt = A * exp(-Ea/(R*T_metal)).
          T_metal is estimated from EGT and CHT. Damage accumulates to 1.0 =
          failure. The failure model is physical, not fitted to failures.

  Tier 2  Fit a linear trend to the health-index history and extrapolate to a
          declared threshold (default 0.5). Needs history, not failure data.

  Tier 3  Time since anomaly onset + current rate of change of the health
          index. Makes NO life claim — it only says "at this rate you reach
          the threshold in X hours". Always available; built first.

Every tier returns median / p05 / p95 hours (a distribution, never a bare
number) plus the assumptions that produced it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .config import EngineConfig, DEFAULT_ENGINE


def _metal_temp_c(egt_c: float, cht_c: float, cfg: EngineConfig) -> float:
    return 0.5 * egt_c + 0.5 * cht_c + cfg.valve_metal_offset_c


def tier1_arrhenius(
    egt_hot_c: float,
    cht_hot_c: float,
    damage_so_far: float,
    cfg: EngineConfig = DEFAULT_ENGINE,
    temp_sigma_c: float = 15.0,
    mc: int = 400,
) -> dict[str, Any]:
    """Hours until exhaust-valve damage reaches 1.0 at the current thermal state.

    Monte-Carlo over metal-temperature uncertainty (the dominant unknown) to get
    the distribution rather than a point value.
    """
    t_metal = _metal_temp_c(egt_hot_c, cht_hot_c, cfg)
    rng = np.random.default_rng(12345)
    samples = []
    for _ in range(mc):
        tk = t_metal + rng.normal(0.0, temp_sigma_c) + 273.15
        rate = cfg.valve_arrhenius_A * math.exp(
            -cfg.valve_activation_energy_J_per_mol / (cfg.gas_constant_R * tk)
        )
        rate = max(rate, 1e-9)
        remaining = max(0.0, 1.0 - damage_so_far)
        samples.append(remaining / rate)
    s = np.sort(samples)
    return {
        "tier": 1,
        "component": "exhaust_valve",
        "median_hours": round(float(np.median(s)), 1),
        "p05_hours": round(float(s[int(0.05 * len(s))]), 1),
        "p95_hours": round(float(s[int(0.95 * len(s)) - 1]), 1),
        "assumptions": {
            "model": "arrhenius_valve_recession",
            "t_metal_c": round(t_metal, 1),
            "t_metal_sigma_c": temp_sigma_c,
            "damage_so_far": round(damage_so_far, 4),
        },
    }


def tier2_trend(
    health_history: list[tuple[float, float]],
    threshold: float = 0.5,
    cfg: EngineConfig = DEFAULT_ENGINE,
) -> dict[str, Any] | None:
    """Linear fit of health index vs. hours, extrapolated to `threshold`.

    health_history: list of (hours_ago<=0 or absolute hours, health_index).
    Returns None if there is not enough history or the trend is flat/improving.
    """
    if len(health_history) < 4:
        return None
    t = np.array([h for h, _ in health_history], float)
    y = np.array([v for _, v in health_history], float)
    t = t - t.min()
    A = np.vstack([t, np.ones_like(t)]).T
    (slope, intercept), res, *_ = np.linalg.lstsq(A, y, rcond=None)
    if slope >= -1e-5:
        return None  # not degrading
    cur = intercept + slope * t.max()
    hours_to_thr = (threshold - cur) / slope
    if hours_to_thr <= 0:
        hours_to_thr = 0.0
    # uncertainty from fit residual std propagated to the crossing time
    resid_std = float(np.sqrt(res[0] / len(t))) if res.size else 0.02
    dslope = max(abs(slope) * 0.25, resid_std / max(t.max(), 1e-6))
    lo = (threshold - cur) / (slope - dslope)
    hi = (threshold - cur) / (slope + dslope) if (slope + dslope) < 0 else hours_to_thr * 3
    p05, p95 = sorted([max(0.0, lo), max(0.0, hi)])
    return {
        "tier": 2,
        "component": "health_trend",
        "median_hours": round(float(hours_to_thr), 1),
        "p05_hours": round(float(p05), 1),
        "p95_hours": round(float(p95), 1),
        "assumptions": {
            "model": "linear_health_extrapolation",
            "threshold": threshold,
            "slope_per_hour": round(float(slope), 6),
            "current_health": round(float(cur), 3),
        },
    }


def tier3_onset(
    hours_since_onset: float,
    health_rate_per_hour: float,
    current_health: float,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """No life claim. 'At the current rate you hit the threshold in X hours.'"""
    rate = min(health_rate_per_hour, -1e-6) if health_rate_per_hour < 0 else -1e-6
    hours = max(0.0, (threshold - current_health) / rate)
    return {
        "tier": 3,
        "component": "anomaly_onset",
        "median_hours": round(float(hours), 1),
        "p05_hours": round(float(hours * 0.4), 1),
        "p95_hours": round(float(hours * 2.5), 1),
        "assumptions": {
            "model": "onset_rate_projection",
            "hours_since_onset": round(hours_since_onset, 2),
            "health_rate_per_hour": round(health_rate_per_hour, 6),
            "no_physical_life_claim": True,
        },
    }


@dataclass
class RulEngine:
    """Accumulates valve damage over the mission and produces the 3-tier RUL."""

    cfg: EngineConfig = DEFAULT_ENGINE
    threshold_health: float = 0.5
    damage: float = 0.0
    _health_hist: list = field(default_factory=list, repr=False)
    _elapsed_h: float = 0.0
    _onset_h: float | None = None

    def accumulate(self, egt_hot_c: float, cht_hot_c: float, dt_s: float) -> None:
        t_metal_k = _metal_temp_c(egt_hot_c, cht_hot_c, self.cfg) + 273.15
        rate = self.cfg.valve_arrhenius_A * math.exp(
            -self.cfg.valve_activation_energy_J_per_mol
            / (self.cfg.gas_constant_R * t_metal_k)
        )
        self.damage = min(1.0, self.damage + rate * (dt_s / 3600.0))
        self._elapsed_h += dt_s / 3600.0

    def observe_health(self, overall_health: float) -> None:
        self._health_hist.append((self._elapsed_h, overall_health))
        if len(self._health_hist) > 4000:
            self._health_hist = self._health_hist[-4000:]
        if self._onset_h is None and overall_health < 0.9:
            self._onset_h = self._elapsed_h

    def report(
        self,
        egt_hot_c: float,
        cht_hot_c: float,
        overall_health: float,
        component_label: str,
        p_fail_mission: float,
    ) -> dict[str, Any]:
        t1 = tier1_arrhenius(egt_hot_c, cht_hot_c, self.damage, self.cfg)
        t2 = tier2_trend(self._health_hist, self.threshold_health, self.cfg)

        rate = 0.0
        if len(self._health_hist) >= 2:
            (h0, v0), (h1, v1) = self._health_hist[0], self._health_hist[-1]
            if h1 > h0:
                rate = (v1 - v0) / (h1 - h0)
        t3 = tier3_onset(
            (self._elapsed_h - self._onset_h) if self._onset_h is not None else 0.0,
            rate, overall_health, self.threshold_health,
        )

        tiers = [t for t in (t1, t2, t3) if t is not None]
        reported = min(tiers, key=lambda t: t["median_hours"])
        return {
            "tier": reported["tier"],
            "component": component_label,
            "median_hours": reported["median_hours"],
            "p05_hours": reported["p05_hours"],
            "p95_hours": reported["p95_hours"],
            "p_fail_mission": round(float(p_fail_mission), 4),
            "assumptions": reported["assumptions"],
            "all_tiers": tiers,
        }
