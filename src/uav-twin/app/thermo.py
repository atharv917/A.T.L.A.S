"""Shared steady-state thermodynamic mapping: (power fraction, ambient, params)
-> steady sensor targets.

This is the ONE relationship the estimator physics (app/physics.py) and the
ground-truth mission generator (app/mission_sim/) are allowed to share, because
it is textbook and untuned: given how much power the engine is making and how
cold the air is, these are the equilibrium temperatures and pressures. Sharing
it keeps healthy residuals near zero so that an injected fault — not a modelling
offset — is what moves a residual.

Everything that makes the two sides genuinely independent lives elsewhere:
  * how `power_fraction` itself is computed (speed-density vs throttle-MAP+VE curve)
  * the atmosphere model (power-law ISA vs exponential)
  * transient integration (mission) vs steady state (estimator)
  * a structural RPM term the mission adds and the estimator does not
  * sensor noise, per-engine build tolerance
"""

from __future__ import annotations

from typing import Any

from .config import EngineConfig, DEFAULT_ENGINE


def steady_targets(
    power_fraction: float,
    ambient_temp_c: float,
    params: dict[str, float],
    cfg: EngineConfig = DEFAULT_ENGINE,
    rpm: float | None = None,
) -> dict[str, Any]:
    """Return steady-state {cht_c, egt_c, coolant_temp_c, oil_temperature_c}.

    `params` must already contain volumetric_efficiency, cooling_factor,
    boost_capability, oil_system_health (callers pass nominal-filled dicts).
    `rpm` is unused here by design — it is where the mission generator adds an
    independent structural term.
    """
    pf = _clip(power_fraction, 0.0, 1.2)
    cooling = _clip(params.get("cooling_factor", cfg.nominal_cooling_factor), 0.4, 1.1)
    oil_h = _clip(params.get("oil_system_health", cfg.nominal_oil_system_health),
                  0.4, 1.05)

    cht = (cfg.cht_soak_c
           + cfg.cht_ambient_gain_c * ambient_temp_c
           + cfg.cht_power_gain_c * pf / cooling)
    egt = cfg.egt_base_c + cfg.egt_power_gain_c * pf + 0.6 * ambient_temp_c
    coolant = (cfg.coolant_soak_c
               + 0.8 * ambient_temp_c
               + cfg.coolant_temp_power_gain_c * pf / cooling)
    oil_t = (cfg.oil_temp_soak_c
             + 0.7 * ambient_temp_c
             + cfg.oil_temp_power_gain_c * pf / (0.6 + 0.4 * oil_h))

    return {
        "cht_c": cht,
        "egt_c": egt,
        "coolant_temp_c": coolant,
        "oil_temperature_c": oil_t,
    }


def _clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x
