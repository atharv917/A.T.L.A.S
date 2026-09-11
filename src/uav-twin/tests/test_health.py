from app.config import DEFAULT_ENGINE, nominal_params
from app.health import component_health

CFG = DEFAULT_ENGINE
NOM = nominal_params(CFG)


def test_all_nominal_is_full_health():
    h = component_health(NOM, cfg=CFG)
    assert h["overall"] > 0.98
    assert h["components"]["combustion"]["index"] > 0.98


def test_overall_is_minimum_not_mean():
    params = dict(NOM)
    params["oil_system_health"] = 0.6  # drag one component down
    h = component_health(params, cfg=CFG)
    # min-aggregation: overall must equal the lubrication index, not an average
    assert h["limited_by"] == "lubrication"
    assert abs(h["overall"] - h["components"]["lubrication"]["index"]) < 1e-9
    assert h["overall"] < 0.8  # a mean would sit ~0.9 and hide this


def test_floor_fraction_clamps_to_zero():
    params = dict(NOM)
    params["cooling_factor"] = NOM["cooling_factor"] * 0.4  # below the floor
    h = component_health(params, cfg=CFG)
    assert h["components"]["cooling"]["index"] == 0.0
    assert h["overall"] == 0.0
    assert h["limited_by"] == "cooling"


def test_cylinder_penalty_lowers_combustion_only():
    base = component_health(NOM, cfg=CFG)
    pen = component_health(NOM, cfg=CFG, combustion_cyl_penalty=0.3)
    assert pen["components"]["combustion"]["index"] < base["components"]["combustion"]["index"]
    assert pen["components"]["cooling"]["index"] == base["components"]["cooling"]["index"]


def test_confidence_tracks_sigma():
    tight = component_health(NOM, {k: 0.002 for k in NOM}, CFG)
    loose = component_health(NOM, {k: 0.05 for k in NOM}, CFG)
    assert tight["components"]["combustion"]["confidence"] > loose["components"]["combustion"]["confidence"]
