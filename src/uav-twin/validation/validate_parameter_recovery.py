"""Parameter-recovery validation — the single best piece of evidence.

Inject a known volumetric_efficiency degradation into a simulated mission at a
known time, run it through the live estimator, and print a markdown table of:
true value, estimated value at convergence, error %, detection latency (hours).

Run:  python -m validation.validate_parameter_recovery
"""

from __future__ import annotations

import argparse

import numpy as np

from app.config import DEFAULT_ENGINE, nominal_params
from app.estimator import ParameterEstimator
from app.mission_sim.degradation import DegradationSpec
from app.mission_sim.numpy_mission import Phase, generate_mission_numpy

CFG = DEFAULT_ENGINE


def run_case(true_value: float, onset_h: float, method: str,
             hours: float = 6.0, dt_s: float = 5.0) -> dict:
    nom = nominal_params(CFG)["volumetric_efficiency"]
    inj = DegradationSpec(
        parameter="volumetric_efficiency", onset_h=onset_h,
        end_value=true_value, full_h=1.5, shape="linear",
    )
    mission = generate_mission_numpy(
        [Phase("LOITER", hours, 22000, 58, 95)], dt_s=dt_s, cfg=CFG,
        degradations_port=[inj], seed=5,
    )
    est = ParameterEstimator(cfg=CFG, method=method, window=50)

    # detection is defined against the estimator's OWN healthy baseline, not the
    # absolute nominal: the two independent physics models carry a small constant
    # offset, so what we can honestly claim to detect is the *change*.
    healthy: list[float] = []
    detect_h = None
    baseline = baseline_sd = None
    est_series = []
    for row in mission["rows"]:
        e1 = row["engine1"]
        op = {"rpm": e1["rpm"],
              "throttle_position_pct": e1["throttle_position_pct"],
              "intake_air_temp_c": e1["intake_air_temp_c"]}
        amb = {"pressure_kpa": row["ambient_pressure_kpa"],
               "temp_c": row["ambient_temp_c"]}
        est.update(op, e1, amb, dt_s=dt_s)
        ve = est.parameters["volumetric_efficiency"]
        est_series.append(ve)
        t_h = row["t_s"] / 3600.0

        if t_h < onset_h - 0.1:
            healthy.append(ve)
        elif baseline is None and healthy:
            baseline = float(np.mean(healthy[-40:]))
            baseline_sd = float(np.std(healthy[-40:]) + 1e-4)
        elif (detect_h is None and baseline is not None
              and ve < baseline - max(3.0 * baseline_sd, 0.01)):
            detect_h = t_h - onset_h

    final = float(np.mean(est_series[-20:]))
    err_pct = 100.0 * abs(final - true_value) / true_value
    return {
        "true": true_value,
        "estimated": round(final, 4),
        "baseline": round(baseline, 4) if baseline is not None else None,
        "change_true": round(nom - true_value, 4),
        "change_est": round((baseline - final) if baseline else 0.0, 4),
        "error_pct": round(err_pct, 2),
        "latency_h": round(detect_h, 2) if detect_h is not None else None,
        "method": est.active_method,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", default="wls", choices=["wls", "ukf"])
    args = ap.parse_args()

    cases = [0.850, 0.820, 0.800, 0.780]
    rows = [run_case(v, onset_h=1.0, method=args.method) for v in cases]

    print(f"\n## Parameter recovery - volumetric_efficiency "
          f"(estimator: {rows[0]['method']}, data: SIMULATED)\n")
    print("| true VE | est VE | abs err % | true drop | est drop | detect latency (h) |")
    print("|-------:|------:|---------:|---------:|--------:|------------------:|")
    for r in rows:
        lat = "n/a" if r["latency_h"] is None else f"{r['latency_h']:.2f}"
        print(f"| {r['true']:.3f} | {r['estimated']:.3f} | {r['error_pct']:.2f} "
              f"| {r['change_true']:.3f} | {r['change_est']:.3f} | {lat} |")
    worst = max(r["error_pct"] for r in rows)
    worst_drop = max(abs(r["change_true"] - r["change_est"]) for r in rows)
    print(f"\nWorst-case absolute VE error : {worst:.2f}%  (demo pass: < 8%)")
    print(f"Worst-case error on the CHANGE: {worst_drop:.3f} VE  (demo pass: < 0.02)")
    print("The two physics implementations are independent, so a small constant "
          "offset\nin absolute VE is expected; the tracked *change* is what the "
          "estimator recovers.\n")


if __name__ == "__main__":
    main()
