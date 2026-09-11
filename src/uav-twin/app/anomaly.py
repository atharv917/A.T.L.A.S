"""Anomaly detection: Mahalanobis distance over the residual vector, gated by
CUSUM persistence.

WHY not alert on a single sample: no piston engine degrades in one second. A
lone large residual is sensor noise or a transient. We accumulate a one-sided
CUSUM of (distance - slack); the anomaly only "fires" once that accumulation
crosses a decision interval, i.e. the deviation has persisted. The reported
`anomalyScore` is the Mahalanobis distance (in sigma-equivalent units) so the
frontend can plot it rising smoothly; `fired` is the gated boolean.

The covariance is learned online from residuals seen while healthy (the first
`warmup` samples, and thereafter only samples where CUSUM is quiet), so the
baseline is regime-appropriate without needing a labelled training set.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np


@dataclass
class AnomalyDetector:
    dim: int
    warmup: int = 60
    # slack sits ABOVE the ~1.0 mean of the healthy normalized distance so
    # ordinary noise never accumulates; only a sustained elevated distance does.
    cusum_slack_k: float = 1.6
    cusum_threshold_h: float = 4.0   # decision interval
    # no SINGLE sample may push CUSUM by more than this — forces persistence,
    # so one huge spike (sensor glitch) can never trip the gate on its own.
    cusum_step_cap: float = 1.5
    _n: int = field(default=0, repr=False)
    _mean: np.ndarray = field(default=None, repr=False)
    _M2: np.ndarray = field(default=None, repr=False)
    _cov: np.ndarray = field(default=None, repr=False)
    _cusum: float = field(default=0.0, repr=False)
    _hist: deque = field(default_factory=lambda: deque(maxlen=512), repr=False)

    def __post_init__(self) -> None:
        d = max(int(self.dim), 1)
        self.dim = d
        self._mean = np.zeros(d)
        self._M2 = np.zeros((d, d))
        self._cov = np.eye(d)

    def update(self, residual_vec: list[float]) -> dict:
        r = np.asarray(residual_vec, float)
        if r.size != self.dim:  # channel set changed — pad / truncate
            r = np.resize(r, self.dim)
        r = np.nan_to_num(r, nan=0.0)

        dist = self._mahalanobis(r)

        # CUSUM one-sided accumulation, with a per-sample increment cap
        inc = dist - self.cusum_slack_k
        inc = min(inc, self.cusum_step_cap)
        self._cusum = max(0.0, self._cusum + inc)
        fired = self._cusum > self.cusum_threshold_h

        # update the healthy-covariance model only while things look calm.
        # during warmup we always absorb; after that, only quiet samples.
        if self._n < self.warmup or (not fired and dist < 2.5):
            self._absorb(r)

        self._hist.append(dist)
        return {
            "score": round(float(dist), 3),
            "cusum": round(float(self._cusum), 3),
            "fired": bool(fired),
            "threshold": self.cusum_threshold_h,
            "samples": self._n,
        }

    def history(self, k: int = 24) -> list[float]:
        h = list(self._hist)[-k:]
        return [round(x, 3) for x in h]

    def reset_cusum(self) -> None:
        self._cusum = 0.0

    # -- internals -------------------------------------------------
    def _absorb(self, r: np.ndarray) -> None:
        self._n += 1
        delta = r - self._mean
        self._mean += delta / self._n
        self._M2 += np.outer(delta, r - self._mean)
        if self._n >= 8:
            cov = self._M2 / (self._n - 1)
            cov += np.eye(self.dim) * 1e-3  # regularize
            self._cov = cov

    def _mahalanobis(self, r: np.ndarray) -> float:
        try:
            inv = np.linalg.pinv(self._cov)
            d2 = float(r @ inv @ r)
            return float(np.sqrt(max(d2, 0.0)) / np.sqrt(self.dim))
        except np.linalg.LinAlgError:
            return float(np.linalg.norm(r) / np.sqrt(self.dim))
