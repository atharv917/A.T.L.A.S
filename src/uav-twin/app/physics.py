"""Pure-Python / NumPy reimplementation of FGPiston-style engine relationships.

WHY this exists separately from the JSBSim mission generator: if the same code
produces both the "measured" mission and the "expected" values, every residual
is identically zero and proves nothing. The mission generator (mission_sim/)
is the ground truth; this module is an INDEPENDENT model of the same physics,
written from the same first principles but not sharing an implementation. Small
structural differences here vs. JSBSim are expected and are exactly what the
residual is supposed to capture once a real fault is injected on top.

Everything in here is stateless and unit-tested. Thermal states are modelled as
first-order lags toward a power-dependent steady state; callers that want the
transient integrate `thermal_step()` themselves, callers that want the estimator
target use `expected_state()` which returns the steady-state values.
"""

from __future__ import annotations

import math
from typing import Any

from .config import EngineConfig, DEFAULT_ENGINE

# International Standard Atmosphere, troposphere only (good to ~36 kft).
_ISA_T0_K = 288.15
_ISA_P0_KPA = 101.325
_ISA_LAPSE_K_PER_M = 0.0065
_ISA_G = 9.80665
_ISA_R = 287.05
_FT_TO_M = 0.3048


def isa_density(pressure_kpa: float, temp_c: float) -> float:
    """Air density [kg/m^3] from static pressure and temperature (ideal gas)."""
    t_k = max(temp_c + 273.15, 150.0)
    return (pressure_kpa * 1000.0) / (_ISA_R * t_k)


def isa_from_altitude(altitude_ft: float) -> tuple[float, float]:
    """(pressure_kpa, temp_c) at a pressure altitude, ISA troposphere."""
    h = max(altitude_ft, 0.0) * _FT_TO_M
    t_k = _ISA_T0_K - _ISA_LAPSE_K_PER_M * h
    p = _ISA_P0_KPA * (t_k / _ISA_T0_K) ** (_ISA_G / (_ISA_R * _ISA_LAPSE_K_PER_M))
    return p, t_k - 273.15


def manifold_pressure(
    throttle_frac: float,
    ambient_pressure_kpa: float,
    ambient_temp_c: float,
    boost_capability: float,
    cfg: EngineConfig = DEFAULT_ENGINE,
) -> float:
    """Intake manifold absolute pressure [kPa].

    Turbo holds rated boost ratio up to the critical altitude, then falls off
    with ambient pressure. `boost_capability` in [0,1] scales the achievable
    pressure ratio — a degraded compressor / leaking wastegate drives it down
    and that shows up as low MAP for a commanded throttle.
    """
    throttle_frac = _clip(throttle_frac, 0.05, 1.0)
    boost_capability = _clip(boost_capability, 0.3, 1.05)

    crit_p, _ = isa_from_altitude(cfg.rated_altitude_ft)
    # available pressure ratio: full at/below critical altitude, decaying above
    if ambient_pressure_kpa >= crit_p:
        pr_available = cfg.rated_boost_ratio
    else:
        pr_available = 1.0 + (cfg.rated_boost_ratio - 1.0) * (
            ambient_pressure_kpa / crit_p
        )
    pr = 1.0 + (pr_available - 1.0) * boost_capability
    map_full = ambient_pressure_kpa * pr
    # throttle plate: quadratic-ish blend between ambient and boosted
    return ambient_pressure_kpa + (map_full - ambient_pressure_kpa) * throttle_frac**1.3


def air_mass_flow(
    rpm: float,
    map_kpa: float,
    intake_air_temp_c: float,
    volumetric_efficiency: float,
    cfg: EngineConfig = DEFAULT_ENGINE,
) -> float:
    """Trapped air mass flow [g/s] via the speed-density relation."""
    rho = isa_density(map_kpa, intake_air_temp_c)
    disp_m3 = cfg.displacement_l * 1e-3
    # 4-stroke: one intake event per cylinder every 2 revs
    breaths_per_s = (rpm / 60.0) / 2.0
    ve = _clip(volumetric_efficiency, 0.4, 1.05)
    return rho * disp_m3 * breaths_per_s * ve * 1000.0


def power_fraction(
    rpm: float,
    map_kpa: float,
    ambient_pressure_kpa: float,
    volumetric_efficiency: float,
    cfg: EngineConfig = DEFAULT_ENGINE,
) -> float:
    """Normalised shaft power in [0,1] relative to rated.

    Proportional to air mass flow (fuel follows air under FADEC lambda control)
    times a mild speed term. Rated point is defined as max_rpm at sea-level
    rated boost with nominal VE.
    """
    mdot = air_mass_flow(rpm, map_kpa, 40.0, volumetric_efficiency, cfg)
    rated_map = manifold_pressure(1.0, _ISA_P0_KPA, 15.0, 1.0, cfg)
    rated_mdot = air_mass_flow(cfg.max_rpm, rated_map, 40.0,
                               cfg.nominal_volumetric_efficiency, cfg)
    speed_term = 0.85 + 0.15 * (rpm / cfg.max_rpm)
    return _clip((mdot / rated_mdot) * speed_term, 0.0, 1.15)


def expected_state(
    operating_point: dict[str, Any],
    params: dict[str, float],
    ambient: dict[str, Any],
    cfg: EngineConfig = DEFAULT_ENGINE,
) -> dict[str, Any]:
    """Steady-state expected sensor values for one operating point.

    operating_point: rpm, throttle_position_pct, intake_air_temp_c (optional),
                     per-cylinder fuel trims (optional list `fuel_trim`)
    params:          volumetric_efficiency, cooling_factor, boost_capability,
                     oil_system_health  (missing keys fall back to nominal)
    ambient:         pressure_kpa, temp_c   (altitude_ft accepted as a fallback)

    Returns a dict keyed the way the API contract expects: cht_c (list),
    egt_c (list), coolant_temp_c, oil_temperature_c, oil_press_kpa,
    manifold_pressure_kpa, power_fraction.
    """
    p = _with_nominal(params, cfg)
    n = cfg.cylinder_count

    rpm = float(operating_point.get("rpm", cfg.idle_rpm))
    throttle_frac = float(operating_point.get("throttle_position_pct", 25.0)) / 100.0

    amb_p = ambient.get("pressure_kpa")
    amb_t = ambient.get("temp_c")
    if amb_p is None or amb_t is None:
        alt = float(ambient.get("altitude_ft", 0.0))
        isa_p, isa_t = isa_from_altitude(alt)
        amb_p = amb_p if amb_p is not None else isa_p
        amb_t = amb_t if amb_t is not None else isa_t
    amb_p = float(amb_p)
    amb_t = float(amb_t)

    iat = operating_point.get("intake_air_temp_c")
    if iat is None:
        # compressor heating minus intercooler recovery
        map_guess = manifold_pressure(throttle_frac, amb_p, amb_t,
                                      p["boost_capability"], cfg)
        comp_rise = 45.0 * (map_guess / max(amb_p, 1.0) - 1.0)
        iat = amb_t + comp_rise * (1.0 - cfg.intercooler_effectiveness)
    iat = float(iat)

    map_kpa = manifold_pressure(throttle_frac, amb_p, amb_t,
                                p["boost_capability"], cfg)
    pf = power_fraction(rpm, map_kpa, amb_p, p["volumetric_efficiency"], cfg)

    # --- steady-state thermal targets (shared, untuned mapping) -------
    from .thermo import steady_targets

    tgt = steady_targets(pf, amb_t, p, cfg, rpm=rpm)
    cht_list = [tgt["cht_c"]] * n

    # --- exhaust gas temperature per cylinder ----------------------
    fuel_trim = operating_point.get("fuel_trim") or [0.0] * n
    fuel_trim = (list(fuel_trim) + [0.0] * n)[:n]
    egt_list = [tgt["egt_c"] + cfg.egt_mixture_gain_c * t for t in fuel_trim]

    coolant_ss = tgt["coolant_temp_c"]
    oil_temp_ss = tgt["oil_temperature_c"]

    # --- oil pressure -------------------------------------------
    oil_health = _clip(p["oil_system_health"], 0.4, 1.05)
    oil_press = (
        cfg.oil_press_idle_kpa
        + (cfg.oil_press_rated_kpa - cfg.oil_press_idle_kpa) * (rpm / cfg.max_rpm)
    ) * (0.5 + 0.5 * oil_health)

    return {
        "power_fraction": pf,
        "manifold_pressure_kpa": map_kpa,
        "intake_air_temp_c": iat,
        "cht_c": cht_list,
        "egt_c": egt_list,
        "coolant_temp_c": coolant_ss,
        "oil_temperature_c": oil_temp_ss,
        "oil_press_kpa": oil_press,
    }


def thermal_step(prev_c: float, target_c: float, dt_s: float, tau_s: float) -> float:
    """One first-order lag integration step toward a steady-state target.

    Used by the mission simulator and by anyone who wants the transient rather
    than the steady state that `expected_state` returns.
    """
    if tau_s <= 0:
        return target_c
    alpha = 1.0 - math.exp(-max(dt_s, 0.0) / tau_s)
    return prev_c + alpha * (target_c - prev_c)


# --------------------------------------------------------------------------
def _clip(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def _with_nominal(params: dict[str, float], cfg: EngineConfig) -> dict[str, float]:
    from .config import nominal_params

    base = nominal_params(cfg)
    if params:
        for k, v in params.items():
            if v is not None and k in base:
                base[k] = float(v)
    return base
