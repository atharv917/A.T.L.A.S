"""Degradation injection — drift named parameters from a configurable onset.

This is the ground truth for validation: we KNOW volumetric_efficiency was
driven to 0.85 starting at t=4h, so we can check whether the estimator recovers
that value and how long it took to notice.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class DegradationSpec:
    parameter: str                       # e.g. "volumetric_efficiency"
    onset_h: float                       # hours into the mission it starts
    end_value: float                     # value it reaches by `full_h`
    full_h: float | None = None          # hours after onset to reach end_value
    shape: Literal["linear", "exp"] = "linear"
    start_value: float | None = None     # defaults to nominal at construction
    cylinder: int | None = None          # 1-indexed; None = whole engine
    egt_bias_c: float = 0.0              # extra: constant EGT offset on `cylinder`
    cht_bias_c: float = 0.0

    def value_at(self, t_h: float) -> float:
        if self.start_value is None:
            raise ValueError("start_value not resolved; call resolve() first")
        if t_h <= self.onset_h:
            return self.start_value
        full = self.full_h if self.full_h else 6.0
        frac = min(1.0, (t_h - self.onset_h) / max(full, 1e-6))
        if self.shape == "exp":
            frac = 1.0 - math.exp(-3.0 * frac)
        return self.start_value + (self.end_value - self.start_value) * frac

    def resolve(self, nominal: float) -> "DegradationSpec":
        if self.start_value is None:
            self.start_value = nominal
        return self


def apply_degradation(
    base_params: dict[str, float], specs: list[DegradationSpec], t_h: float
) -> dict[str, float]:
    """Return a copy of base_params with whole-engine specs applied at time t_h.

    Per-cylinder specs (cylinder is not None) are handled by the mission
    generator directly as EGT/CHT biases, not here.
    """
    out = dict(base_params)
    for s in specs:
        if s.cylinder is None and s.parameter in out:
            out[s.parameter] = s.value_at(t_h)
    return out
