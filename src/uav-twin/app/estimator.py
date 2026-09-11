"""Parameter estimation.

The API needs named, unit-bearing physical parameters with uncertainty:
volumetric_efficiency, cooling_factor, boost_capability, oil_system_health.

Two estimators, selected at construction:

  "wls"  (default) — windowed non-linear least squares. Fit the parameter
         vector that best explains the last N samples of measured sensors
         through `physics.expected_state`. Robust, small, always converges to
         *something*, and the sigma comes straight from the Gauss-Newton
         covariance (J^T J)^-1 * s^2. This is the "fall back to windowed
         least-squares" option from the brief, promoted to primary because a
         28-hour demo cannot afford a filter that might not converge live.

  "ukf"  — filterpy UnscentedKalmanFilter over
         [T_cht, T_coolant, T_oil, VE, cooling_factor, boost_capability,
          oil_health]. Process noise on the 4 parameter states is set MUCH
         smaller than on the 3 thermal states: that asymmetry is the whole
         point — it forces the filter to explain fast wiggles with thermal
         dynamics and reserve the slow parameter states for genuine drift.
         Falls back to "wls" automatically if filterpy is missing or the
         filter goes non-finite.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np

try:  # scipy is a hard dep, but keep the import defensive
    from scipy.optimize import least_squares as _scipy_lsq
except Exception:  # pragma: no cover
    _scipy_lsq = None

from .config import EngineConfig, DEFAULT_ENGINE, PARAM_NAMES, nominal_params
from .physics import expected_state

_PARAM_BOUNDS = {
    "volumetric_efficiency": (0.55, 1.02),
    "cooling_factor": (0.55, 1.10),
    "boost_capability": (0.55, 1.05),
    "oil_system_health": (0.55, 1.05),
}


def _predict_vector(params: dict[str, float], sample: dict[str, Any],
                    cfg: EngineConfig) -> np.ndarray:
    exp = expected_state(sample["operating_point"], params, sample["ambient"], cfg)
    parts = [np.asarray(exp["cht_c"], float),
             np.asarray(exp["egt_c"], float),
             np.array([exp["coolant_temp_c"], exp["oil_temperature_c"],
                       exp["oil_press_kpa"], exp["manifold_pressure_kpa"]], float)]
    return np.concatenate(parts)


def _measure_vector(sample: dict[str, Any], n_cyl: int) -> np.ndarray:
    t = sample["telemetry"]
    cht = np.asarray((t.get("cht_cylinders") or [np.nan] * n_cyl)[:n_cyl], float)
    egt = np.asarray((t.get("egt_cylinders") or [np.nan] * n_cyl)[:n_cyl], float)
    scal = np.array([
        _f(t.get("coolant_temp_c")), _f(t.get("oil_temperature")),
        _f(t.get("oil_pressure")), _f(t.get("manifold_pressure")),
    ], float)
    return np.concatenate([cht, egt, scal])


def _f(x: Any) -> float:
    return float(x) if x is not None else np.nan


# channel weights: temps in C, oil pressure in kPa. Down-weight the noisier /
# larger-magnitude channels so no single channel dominates the fit.
def _weights(n_cyl: int) -> np.ndarray:
    return np.concatenate([
        np.full(n_cyl, 1.0),      # CHT
        np.full(n_cyl, 0.6),      # EGT (noisier, bigger numbers)
        np.array([1.0, 0.8, 0.15, 0.3]),  # coolant, oil T, oil P(kPa), MAP(kPa)
    ])


@dataclass
class ParameterEstimator:
    cfg: EngineConfig = DEFAULT_ENGINE
    method: str = "wls"
    window: int = 40
    _buf: deque = field(default_factory=lambda: deque(maxlen=256), repr=False)
    _params: dict[str, float] = field(default_factory=dict, repr=False)
    _sigma: dict[str, float] = field(default_factory=dict, repr=False)
    _ukf: Any = field(default=None, repr=False)
    _active_method: str = field(default="wls", repr=False)

    def __post_init__(self) -> None:
        self._params = nominal_params(self.cfg)
        self._sigma = {k: 0.02 for k in PARAM_NAMES}
        self._buf = deque(maxlen=max(64, self.window * 4))
        self._active_method = "wls"
        if self.method == "ukf":
            self._try_init_ukf()

    # -- public ------------------------------------------------------
    def update(self, operating_point: dict[str, Any], telemetry: dict[str, Any],
               ambient: dict[str, Any], dt_s: float = 1.0) -> None:
        self._buf.append({"operating_point": operating_point,
                          "telemetry": telemetry, "ambient": ambient})
        if self._active_method == "ukf":
            ok = self._ukf_step(dt_s)
            if not ok:
                self._active_method = "wls"  # permanent fallback for this engine
        if self._active_method == "wls" and len(self._buf) >= max(6, self.window // 4):
            self._wls_fit()

    @property
    def parameters(self) -> dict[str, float]:
        return {k: round(v, 4) for k, v in self._params.items()}

    @property
    def parameter_sigma(self) -> dict[str, float]:
        return {k: round(v, 4) for k, v in self._sigma.items()}

    @property
    def active_method(self) -> str:
        return self._active_method

    @property
    def confidence(self) -> float:
        """0..1 — shrinks as the largest relative sigma grows, grows with data."""
        rel = max(self._sigma[k] / max(abs(self._params[k]), 1e-6)
                  for k in PARAM_NAMES)
        data_term = min(len(self._buf) / self.window, 1.0)
        return round(float(np.clip((1.0 - 6.0 * rel) * data_term, 0.05, 0.98)), 3)

    # -- windowed least squares -----------------------------------
    def _wls_fit(self) -> None:
        samples = list(self._buf)[-self.window:]
        n_cyl = self.cfg.cylinder_count
        w = _weights(n_cyl)

        # stack only channels present in every sample
        meas = []
        keep = None
        for s in samples:
            m = _measure_vector(s, n_cyl)
            mask = np.isfinite(m)
            keep = mask if keep is None else (keep & mask)
            meas.append(m)
        if keep is None or keep.sum() < 4:
            return
        meas_arr = np.array([m[keep] for m in meas])
        w_keep = w[keep]

        p0 = np.array([self._params[k] for k in PARAM_NAMES])
        lo = np.array([_PARAM_BOUNDS[k][0] for k in PARAM_NAMES])
        hi = np.array([_PARAM_BOUNDS[k][1] for k in PARAM_NAMES])
        p0 = np.clip(p0, lo + 1e-4, hi - 1e-4)

        def resid(pv: np.ndarray) -> np.ndarray:
            pd = dict(zip(PARAM_NAMES, pv))
            rows = []
            for i, s in enumerate(samples):
                pred = _predict_vector(pd, s, self.cfg)[keep]
                rows.append((meas_arr[i] - pred) * w_keep)
            return np.concatenate(rows)

        if _scipy_lsq is not None:
            sol = _scipy_lsq(resid, p0, bounds=(lo, hi), method="trf",
                             max_nfev=60, xtol=1e-8, ftol=1e-8)
            pv, J, r = sol.x, sol.jac, sol.fun
        else:  # tiny hand-rolled Gauss-Newton if scipy is unavailable
            pv = p0.copy()
            for _ in range(8):
                r = resid(pv)
                J = _numeric_jac(resid, pv)
                step, *_ = np.linalg.lstsq(J, -r, rcond=None)
                pv = np.clip(pv + 0.7 * step, lo, hi)
            r = resid(pv)
            J = _numeric_jac(resid, pv)

        # Gauss-Newton covariance: (J^T J)^-1 * residual variance
        dof = max(len(r) - len(pv), 1)
        s2 = float(r @ r) / dof
        try:
            cov = np.linalg.inv(J.T @ J) * s2
            sig = np.sqrt(np.clip(np.diag(cov), 1e-8, None))
        except np.linalg.LinAlgError:
            sig = np.full(len(pv), 0.05)

        # light smoothing so the demo trace doesn't jitter sample-to-sample
        a = 0.35
        for i, k in enumerate(PARAM_NAMES):
            self._params[k] = (1 - a) * self._params[k] + a * float(pv[i])
            self._sigma[k] = float(np.clip(sig[i], 0.001, 0.2))

    # -- UKF ----------------------------------------------------
    def _try_init_ukf(self) -> None:
        try:
            from filterpy.kalman import (
                UnscentedKalmanFilter, MerweScaledSigmaPoints,
            )
        except Exception:
            self._active_method = "wls"
            return
        n = 7  # T_cht, T_cool, T_oil, VE, cool_f, boost, oil_h
        pts = MerweScaledSigmaPoints(n, alpha=1e-3, beta=2.0, kappa=0.0)
        ukf = UnscentedKalmanFilter(dim_x=n, dim_z=6, dt=1.0,
                                    fx=self._ukf_fx, hx=self._ukf_hx, points=pts)
        nm = nominal_params(self.cfg)
        ukf.x = np.array([160.0, 85.0, 90.0, nm["volumetric_efficiency"],
                          nm["cooling_factor"], nm["boost_capability"],
                          nm["oil_system_health"]])
        ukf.P = np.diag([25.0, 16.0, 16.0, 4e-3, 4e-3, 4e-3, 4e-3])
        # asymmetric process noise: thermal states are free to move, parameter
        # states are nearly frozen so only sustained evidence shifts them.
        ukf.Q = np.diag([2.0, 1.0, 1.0, 2e-7, 2e-7, 3e-7, 1e-7])
        ukf.R = np.diag([9.0, 9.0, 9.0, 9.0, 400.0, 25.0])
        self._ukf = ukf
        self._active_method = "ukf"

    def _ukf_fx(self, x: np.ndarray, dt: float) -> np.ndarray:
        return x.copy()  # random-walk model; dynamics enter via hx + Q

    def _ukf_hx(self, x: np.ndarray) -> np.ndarray:
        s = self._buf[-1]
        pd = {"volumetric_efficiency": x[3], "cooling_factor": x[4],
              "boost_capability": x[5], "oil_system_health": x[6]}
        exp = expected_state(s["operating_point"], pd, s["ambient"], self.cfg)
        return np.array([
            float(np.mean(exp["cht_c"])), exp["coolant_temp_c"],
            exp["oil_temperature_c"], float(np.mean(exp["egt_c"])),
            exp["oil_press_kpa"], exp["manifold_pressure_kpa"],
        ])

    def _ukf_step(self, dt_s: float) -> bool:
        s = self._buf[-1]
        t = s["telemetry"]
        try:
            z = np.array([
                float(np.mean(t["cht_cylinders"])), float(t["coolant_temp_c"]),
                float(t["oil_temperature"]), float(np.mean(t["egt_cylinders"])),
                float(t["oil_pressure"]), float(t["manifold_pressure"]),
            ])
        except (KeyError, TypeError):
            return True  # missing channels this step — skip, stay on UKF
        try:
            self._ukf.predict(dt=max(dt_s, 1e-3))
            self._ukf.update(z)
        except Exception:
            return False
        x, P = self._ukf.x, np.diag(self._ukf.P)
        if not (np.all(np.isfinite(x)) and np.all(np.isfinite(P))):
            return False
        for i, k in enumerate(PARAM_NAMES):
            lo, hi = _PARAM_BOUNDS[k]
            self._params[k] = float(np.clip(x[3 + i], lo, hi))
            self._sigma[k] = float(np.clip(np.sqrt(max(P[3 + i], 1e-8)), 1e-3, 0.2))
        return True


def _numeric_jac(fn, x: np.ndarray, eps: float = 1e-5) -> np.ndarray:
    f0 = fn(x)
    J = np.zeros((len(f0), len(x)))
    for j in range(len(x)):
        dx = x.copy()
        dx[j] += eps
        J[:, j] = (fn(dx) - f0) / eps
    return J
