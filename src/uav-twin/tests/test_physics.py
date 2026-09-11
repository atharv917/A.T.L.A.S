"""Physics model sanity + monotonicity properties (no real data to check against,
so we assert directional relationships the model must obey)."""

import math

from app.config import DEFAULT_ENGINE, nominal_params
from app.physics import (
    expected_state, isa_from_altitude, isa_density, manifold_pressure,
    power_fraction, thermal_step,
)

CFG = DEFAULT_ENGINE
NOM = nominal_params(CFG)


def _op(rpm=2400, thr=60):
    return {"rpm": rpm, "throttle_position_pct": thr}


def _amb(p=46.5, t=-18.0):
    return {"pressure_kpa": p, "temp_c": t}


def test_isa_altitude_monotonic():
    p0, t0 = isa_from_altitude(0)
    p1, t1 = isa_from_altitude(20000)
    assert p0 > p1 > 0
    assert t0 > t1
    assert math.isclose(p0, 101.325, rel_tol=1e-3)


def test_density_drops_with_altitude():
    p_lo, t_lo = isa_from_altitude(0)
    p_hi, t_hi = isa_from_altitude(25000)
    assert isa_density(p_lo, t_lo) > isa_density(p_hi, t_hi)


def test_manifold_pressure_increases_with_throttle():
    low = manifold_pressure(0.2, 46.5, -18, 1.0, CFG)
    high = manifold_pressure(0.95, 46.5, -18, 1.0, CFG)
    assert high > low > 0


def test_boost_capability_reduces_map():
    healthy = manifold_pressure(0.9, 46.5, -18, 1.0, CFG)
    degraded = manifold_pressure(0.9, 46.5, -18, 0.7, CFG)
    assert degraded < healthy


def test_power_fraction_bounded_and_monotonic_in_rpm():
    lo = power_fraction(1400, 90, 46.5, NOM["volumetric_efficiency"], CFG)
    hi = power_fraction(2600, 150, 46.5, NOM["volumetric_efficiency"], CFG)
    assert 0.0 <= lo < hi <= 1.15


def test_expected_state_keys_and_cylinder_count():
    out = expected_state(_op(), NOM, _amb(), CFG)
    for k in ("cht_c", "egt_c", "coolant_temp_c", "oil_temperature_c",
              "oil_press_kpa", "manifold_pressure_kpa", "power_fraction"):
        assert k in out
    assert len(out["cht_c"]) == CFG.cylinder_count
    assert len(out["egt_c"]) == CFG.cylinder_count


def test_lower_cooling_factor_raises_cht():
    hot = expected_state(_op(), {**NOM, "cooling_factor": 0.8}, _amb(), CFG)
    base = expected_state(_op(), NOM, _amb(), CFG)
    assert hot["cht_c"][0] > base["cht_c"][0]


def test_lower_ve_lowers_power_and_cht():
    low_ve = expected_state(_op(), {**NOM, "volumetric_efficiency": 0.80},
                            _amb(), CFG)
    base = expected_state(_op(), NOM, _amb(), CFG)
    assert low_ve["power_fraction"] < base["power_fraction"]


def test_fuel_trim_biases_only_that_cylinder():
    op = _op()
    op["fuel_trim"] = [0.0, 0.0, 1.0, 0.0]
    out = expected_state(op, NOM, _amb(), CFG)
    egt = out["egt_c"]
    assert egt[2] > egt[0]
    assert abs(egt[0] - egt[1]) < 1e-6 and abs(egt[0] - egt[3]) < 1e-6


def test_thermal_step_converges_to_target():
    v = 20.0
    for _ in range(2000):
        v = thermal_step(v, 180.0, 1.0, 45.0)
    assert abs(v - 180.0) < 0.5


def test_missing_ambient_falls_back_to_altitude():
    out = expected_state(_op(), NOM, {"altitude_ft": 22000}, CFG)
    assert out["manifold_pressure_kpa"] > 0
