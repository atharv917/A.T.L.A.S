"""Generate a mission and POST it frame-by-frame at the running twin service.

Useful for driving the dashboard end-to-end without the Java backend:

    uvicorn app.main:app --port 8000      # terminal 1
    python -m validation.replay_mission --url http://localhost:8000 --speed 200

--speed is a time-compression factor (200 => 200x real time).
"""

from __future__ import annotations

import argparse
import time

import httpx

from app.config import DEFAULT_ENGINE
from app.mission_sim.degradation import DegradationSpec
from app.mission_sim.numpy_mission import generate_mission_numpy


def build_step_payload(row: dict, eng_key: str, engine_id: int,
                       paired_key: str | None, seq: int) -> dict:
    e = row[eng_key]
    payload = {
        "engineId": engine_id,
        "timestamp": row["timestamp"],
        "seq": seq,
        "cylinderCount": DEFAULT_ENGINE.cylinder_count,
        "engineType": "PISTON_CI_TURBO",
        "telemetry": {
            "rpm": e["rpm"], "manifold_pressure": e["manifold_pressure"],
            "throttle_position_pct": e["throttle_position_pct"],
            "fuel_flow": e["fuel_flow"], "oil_pressure": e["oil_pressure"],
            "oil_temperature": e["oil_temperature"],
            "coolant_temp_c": e["coolant_temp_c"],
            "intake_air_temp_c": e["intake_air_temp_c"],
            "fuel_rail_pressure_bar": e["fuel_rail_pressure_bar"],
            "egt_cylinders": e["egt_cylinders"],
            "cht_cylinders": e["cht_cylinders"],
            "vibration": e["vibration"], "battery_voltage": e["battery_voltage"],
        },
        "ambient": {
            "pressure_kpa": row["ambient_pressure_kpa"],
            "temp_c": row["ambient_temp_c"],
            "altitude_ft": row["altitude_ft"],
            "airspeed_kts": row["airspeed_kts"],
            "vertical_speed_fpm": row["vertical_speed_fpm"],
        },
    }
    if paired_key:
        p = row[paired_key]
        payload["paired"] = {
            "engineId": p["engineId"],
            "egt_cylinders": p["egt_cylinders"],
            "cht_cylinders": p["cht_cylinders"],
            "coolant_temp_c": p["coolant_temp_c"],
            "oil_pressure": p["oil_pressure"],
            "fuel_flow": p["fuel_flow"],
            "manifold_pressure": p["manifold_pressure"],
        }
    return payload


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--speed", type=float, default=300.0)
    ap.add_argument("--dt", type=float, default=5.0)
    ap.add_argument("--hours", type=float, default=10.0)
    ap.add_argument("--fault", default="injector_cyl3",
                    choices=["none", "ve_drift", "cooling", "injector_cyl3"])
    args = ap.parse_args()

    degr_port = []
    if args.fault == "ve_drift":
        degr_port = [DegradationSpec("volumetric_efficiency", 3.0, 0.83, 2.0)]
    elif args.fault == "cooling":
        degr_port = [DegradationSpec("cooling_factor", 3.0, 0.85, 2.0)]
    elif args.fault == "injector_cyl3":
        degr_port = [DegradationSpec("volumetric_efficiency", 999, 0.88, 1.0,
                                     cylinder=3, egt_bias_c=60.0, cht_bias_c=20.0,
                                     end_value=0.88)]
        degr_port[0].onset_h = 3.0
        degr_port[0].full_h = 3.0

    from app.mission_sim.numpy_mission import Phase
    mission = generate_mission_numpy(
        [Phase("LOITER", args.hours, 22000, 58, 95)],
        dt_s=args.dt, degradations_port=degr_port, seed=9,
    )
    print(f"replaying {len(mission['rows'])} frames -> {args.url} "
          f"(fault={args.fault})")

    with httpx.Client(timeout=10.0, base_url=args.url) as c:
        c.post("/twin/reset")
        for seq, row in enumerate(mission["rows"]):
            for eid, ekey, pkey in ((1, "engine1", "engine2"),
                                    (2, "engine2", "engine1")):
                body = build_step_payload(row, ekey, eid, pkey, seq)
                try:
                    c.post("/twin/step", json=body)
                except httpx.HTTPError as exc:
                    print("step error:", exc)
            if seq % 20 == 0:
                st = c.get("/twin/state/1").json()
                print(f"t={row['t_s']/3600:5.2f}h regime={st.get('regime'):8} "
                      f"VE={st['parameters']['volumetric_efficiency']:.3f} "
                      f"damage={st['valveDamage']:.4f}")
            time.sleep(args.dt / max(args.speed, 1e-6))


if __name__ == "__main__":
    main()
