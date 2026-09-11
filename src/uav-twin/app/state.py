"""Per-engine twin state + the /twin/step pipeline.

Holds one RegimeTracker, ParameterEstimator, AnomalyDetector and RulEngine per
engineId, in process memory (the brief says one FastAPI process is correct at
this data volume). `TwinRegistry.step()` runs the whole pipeline for one
incoming telemetry frame and returns the API-contract response dict.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from . import DATA_SOURCE
from .anomaly import AnomalyDetector
from .config import EngineConfig, DEFAULT_ENGINE
from .diagnosis import rank_hypotheses
from .differential import cylinder_spread, engine_delta
from .estimator import ParameterEstimator
from .health import component_health
from .physics import expected_state
from .regime import RegimeTracker
from .residuals import compute_residuals, flatten_residual_vector
from .rul import RulEngine


@dataclass
class EngineTwin:
    engine_id: int
    cfg: EngineConfig = DEFAULT_ENGINE
    estimator_method: str = "wls"
    regime: RegimeTracker = field(init=False)
    estimator: ParameterEstimator = field(init=False)
    anomaly: AnomalyDetector = field(init=False)
    rul: RulEngine = field(init=False)
    _last_ts: float | None = field(default=None, repr=False)
    _steps: int = 0

    def __post_init__(self) -> None:
        self.regime = RegimeTracker(cfg=self.cfg)
        self.estimator = ParameterEstimator(cfg=self.cfg, method=self.estimator_method)
        # residual vector = 2*n_cyl (cht+egt) + 3 scalars kept in flatten order
        self.anomaly = AnomalyDetector(dim=2 * self.cfg.cylinder_count + 3)
        self.rul = RulEngine(cfg=self.cfg)

    # ------------------------------------------------------------------
    def step(self, payload: dict[str, Any]) -> dict[str, Any]:
        cfg = self.cfg
        tel: dict[str, Any] = dict(payload.get("telemetry") or {})
        amb: dict[str, Any] = dict(payload.get("ambient") or {})
        paired = payload.get("paired")

        dt_s = 1.0
        ts = _epoch(payload.get("timestamp"))
        if ts is not None and self._last_ts is not None:
            dt_s = float(np.clip(ts - self._last_ts, 0.05, 30.0))
        if ts is not None:
            self._last_ts = ts
        self._steps += 1

        op = {
            "rpm": tel.get("rpm", cfg.idle_rpm),
            "throttle_position_pct": tel.get("throttle_position_pct", 25.0),
            "intake_air_temp_c": tel.get("intake_air_temp_c"),
        }

        # 1. regime (hysteresis)
        regime = self.regime.update(
            float(tel.get("rpm", cfg.idle_rpm)),
            float(amb.get("airspeed_kts", 0.0)),
            float(amb.get("vertical_speed_fpm", amb.get("vertical_speed", 0.0)) or 0.0),
        )

        # 2. parameter estimate
        self.estimator.update(op, tel, amb, dt_s)
        params = self.estimator.parameters
        sigma = self.estimator.parameter_sigma

        # 3. expected + residuals (against the INDEPENDENT physics model)
        exp = expected_state(op, params, amb, cfg)
        residuals = compute_residuals(tel, exp)
        rvec = flatten_residual_vector(residuals)

        # 4. differential features
        spread = cylinder_spread(tel)
        delta = engine_delta(tel, paired)

        # 5. anomaly (Mahalanobis + CUSUM persistence gate)
        an = self.anomaly.update(rvec)

        # 6. diagnosis
        diag = rank_hypotheses(residuals, spread, delta, params, sigma)
        top = diag["hypotheses"][0] if diag["hypotheses"] else {}

        # 7. health (from parameters, min-aggregated). Fold a per-cylinder
        #    combustion penalty when one cylinder's EGT is a clear outlier.
        cyl_penalty = 0.0
        margin = float(spread.get("egt_outlier_margin", 0.0))
        if margin > 15.0 and an["fired"]:
            cyl_penalty = float(np.clip((margin - 15.0) / 60.0, 0.0, 0.4))
        health = component_health(params, sigma, cfg, cyl_penalty)

        # 8. RUL (3 tiers). Accumulate valve damage on the hottest cylinder.
        egt_cyls = tel.get("egt_cylinders") or [cfg.egt_base_c]
        cht_cyls = tel.get("cht_cylinders") or [cfg.cht_soak_c]
        hot_idx = int(np.argmax(egt_cyls))
        egt_hot = float(egt_cyls[hot_idx])
        cht_hot = float(cht_cyls[min(hot_idx, len(cht_cyls) - 1)])
        self.rul.accumulate(egt_hot, cht_hot, dt_s)
        self.rul.observe_health(health["overall"])
        p_fail = _p_fail_mission(health["overall"], an["score"], an["fired"])
        hot_cyl = spread.get("hottest_cylinder", hot_idx + 1)
        comp_label = f"{health['limited_by']}_cyl{hot_cyl}" if cyl_penalty > 0 \
            else health["limited_by"]
        rul = self.rul.report(egt_hot, cht_hot, health["overall"], comp_label, p_fail)

        return {
            "engineId": self.engine_id,
            "regime": regime,
            "expected": {
                "cht_c": [round(x, 2) for x in exp["cht_c"]],
                "egt_c": [round(x, 2) for x in exp["egt_c"]],
                "coolant_temp_c": round(exp["coolant_temp_c"], 2),
                "oil_temperature_c": round(exp["oil_temperature_c"], 2),
                "oil_press_kpa": round(exp["oil_press_kpa"], 1),
                "manifold_pressure_kpa": round(exp["manifold_pressure_kpa"], 2),
            },
            "residual": residuals,
            "parameters": params,
            "parameterSigma": sigma,
            "estimatorMethod": self.estimator.active_method,
            "engineDelta": delta,
            "cylinderSpread": spread,
            "anomalyScore": an["score"],
            "anomalyFired": an["fired"],
            "anomalyHistory": self._anomaly_history(),
            "confidence": self.estimator.confidence,
            "health": {
                "overall": health["overall"],
                "limited_by": health["limited_by"],
                "cooling": health["components"]["cooling"]["index"],
                "combustion": health["components"]["combustion"]["index"],
                "induction": health["components"]["induction"]["index"],
                "lubrication": health["components"]["lubrication"]["index"],
                "components": health["components"],
            },
            "rul": {
                "tier": rul["tier"],
                "component": rul["component"],
                "median_hours": rul["median_hours"],
                "p05_hours": rul["p05_hours"],
                "p95_hours": rul["p95_hours"],
                "p_fail_mission": rul["p_fail_mission"],
                "assumptions": rul["assumptions"],
                "all_tiers": rul["all_tiers"],
            },
            "diagnosis": diag,
            "dataSource": DATA_SOURCE,
        }

    def _anomaly_history(self, k: int = 12) -> list[dict[str, Any]]:
        hist = self.anomaly.history(k)
        out = []
        n = len(hist)
        for i, s in enumerate(hist):
            out.append({"t": f"-{(n - 1 - i) * 10}m" if i < n - 1 else "0h",
                        "score": s})
        return out


class TwinRegistry:
    """Thread-safe map of engineId -> EngineTwin."""

    def __init__(self, cfg: EngineConfig = DEFAULT_ENGINE,
                 estimator_method: str = "wls") -> None:
        self._cfg = cfg
        self._method = estimator_method
        self._twins: dict[int, EngineTwin] = {}
        self._lock = threading.Lock()

    def get(self, engine_id: int, cylinder_count: int | None = None) -> EngineTwin:
        with self._lock:
            t = self._twins.get(engine_id)
            if t is None:
                cfg = self._cfg
                if cylinder_count and cylinder_count != cfg.cylinder_count:
                    from dataclasses import replace
                    cfg = replace(cfg, cylinder_count=cylinder_count)
                t = EngineTwin(engine_id=engine_id, cfg=cfg,
                               estimator_method=self._method)
                self._twins[engine_id] = t
            return t

    def step(self, payload: dict[str, Any]) -> dict[str, Any]:
        eid = int(payload.get("engineId", 1))
        twin = self.get(eid, payload.get("cylinderCount"))
        return twin.step(payload)

    def snapshot(self, engine_id: int) -> EngineTwin | None:
        return self._twins.get(engine_id)


def _epoch(ts: Any) -> float | None:
    if ts is None:
        return None
    try:
        from datetime import datetime

        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def _p_fail_mission(overall_health: float, anomaly_score: float,
                    fired: bool) -> float:
    """Crude but monotone: worse health + a fired anomaly -> higher P(fail)."""
    base = np.clip((0.85 - overall_health) * 0.18, 0.0, 0.3)
    an_term = np.clip((anomaly_score - 2.0) * 0.02, 0.0, 0.15) if fired else 0.0
    return float(np.clip(base + an_term + 0.005, 0.001, 0.95))
