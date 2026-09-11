"""Parameter-recovery test: the property that proves this is a state estimator
and not a chart. Generate a healthy-then-degraded mission, feed it through the
estimator, and check it converges near the injected value."""

import numpy as np

from app.config import DEFAULT_ENGINE, nominal_params
from app.estimator import ParameterEstimator
from app.mission_sim.numpy_mission import generate_mission_numpy, Phase
from app.mission_sim.degradation import DegradationSpec

CFG = DEFAULT_ENGINE


def _steady_profile(hours: float) -> list[Phase]:
    return [Phase("LOITER", hours, 22000, 58, 95)]


def test_estimator_recovers_injected_ve():
    inj = DegradationSpec(parameter="volumetric_efficiency", onset_h=1.0,
                          end_value=0.82, full_h=1.5, shape="linear")
    mission = generate_mission_numpy(
        _steady_profile(4.0), dt_s=5.0, cfg=CFG,
        degradations_port=[inj], seed=3,
    )
    est = ParameterEstimator(cfg=CFG, method="wls", window=50)
    for row in mission["rows"]:
        e1 = row["engine1"]
        op = {"rpm": e1["rpm"], "throttle_position_pct": e1["throttle_position_pct"],
              "intake_air_temp_c": e1["intake_air_temp_c"]}
        amb = {"pressure_kpa": row["ambient_pressure_kpa"],
               "temp_c": row["ambient_temp_c"],
               "airspeed_kts": row["airspeed_kts"]}
        est.update(op, e1, amb, dt_s=5.0)

    ve = est.parameters["volumetric_efficiency"]
    # recovered within 6% of the injected 0.82 (independent-physics bias budget)
    assert abs(ve - 0.82) < 0.06, f"VE estimate {ve} did not converge to 0.82"
    assert est.parameters["volumetric_efficiency"] < nominal_params(CFG)["volumetric_efficiency"]


def test_estimator_stays_near_nominal_on_healthy_mission():
    mission = generate_mission_numpy(_steady_profile(3.0), dt_s=5.0, cfg=CFG, seed=11)
    est = ParameterEstimator(cfg=CFG, method="wls", window=50)
    for row in mission["rows"]:
        e1 = row["engine1"]
        op = {"rpm": e1["rpm"], "throttle_position_pct": e1["throttle_position_pct"],
              "intake_air_temp_c": e1["intake_air_temp_c"]}
        amb = {"pressure_kpa": row["ambient_pressure_kpa"],
               "temp_c": row["ambient_temp_c"]}
        est.update(op, e1, amb, dt_s=5.0)
    nom = nominal_params(CFG)
    for k in ("volumetric_efficiency", "cooling_factor"):
        assert abs(est.parameters[k] - nom[k]) < 0.08, f"{k} drifted while healthy"


def test_confidence_in_unit_interval():
    est = ParameterEstimator(cfg=CFG, method="wls")
    assert 0.0 <= est.confidence <= 1.0
