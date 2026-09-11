"""JSBSim (FGPiston) ground-truth mission generator.

Only imported when the `jsbsim` package is available. Kept thin: JSBSim owns the
flight dynamics and the FGPiston thermodynamics; we script a phase profile,
step the sim, and read the engine gauges back into the same row schema the
NumPy generator emits.

NOTE: a full JSBSim aircraft + turbo-piston config is bulky. If a suitable
aircraft model is not found on the JSBSim path, this raises and the caller
falls back to the NumPy generator — that fallback is expected on machines that
only `pip install jsbsim` without the aircraft data pack.
"""

from __future__ import annotations

from typing import Any

from ..config import EngineConfig, DEFAULT_ENGINE
from .degradation import DegradationSpec
from .numpy_mission import DEFAULT_PROFILE, Phase, generate_mission_numpy


def generate_mission_jsbsim(
    profile: list[Phase] | None = None,
    dt_s: float = 2.0,
    cfg: EngineConfig = DEFAULT_ENGINE,
    degradations_port: list[DegradationSpec] | None = None,
    degradations_stbd: list[DegradationSpec] | None = None,
    seed: int = 7,
    start_time: str = "2026-09-09T12:00:00",
    aircraft: str = "c172p",
) -> dict[str, Any]:
    try:
        import jsbsim
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"jsbsim not importable: {exc}")

    profile = profile or DEFAULT_PROFILE
    try:
        fdm = jsbsim.FGFDMExec(None)
        fdm.set_debug_level(0)
        if not fdm.load_model(aircraft):
            raise RuntimeError(f"could not load JSBSim aircraft '{aircraft}'")
    except Exception as exc:  # pragma: no cover - no aircraft data pack
        raise RuntimeError(
            f"JSBSim present but no usable aircraft model ({exc}); "
            "falling back to numpy generator"
        )

    # A single-engine GA model like c172p only gives us one FGPiston. We run it
    # once for the port engine and reuse the NumPy generator's scatter model for
    # per-cylinder / second-engine detail, since c172p exposes only bulk EGT/CHT.
    # For the hackathon this still gives a genuinely independent bulk thermo
    # source for the port engine's mean channels.
    dt = 1.0 / 60.0
    fdm.set_dt(dt)
    fdm["ic/h-sl-ft"] = profile[0].altitude_ft
    fdm["ic/vc-kts"] = max(profile[0].airspeed_kts, 1.0)
    fdm.run_ic()
    fdm["propulsion/engine[0]/set-running"] = 1

    bulk_rows: list[dict[str, float]] = []
    t_s = 0.0
    prev_alt = profile[0].altitude_ft
    for ph in profile:
        n_steps = max(1, int(round(ph.duration_h * 3600.0 / dt_s)))
        for k in range(n_steps):
            frac = (k + 1) / n_steps
            alt = prev_alt + (ph.altitude_ft - prev_alt) * frac
            fdm["ic/h-sl-ft"] = alt
            fdm["fcs/throttle-cmd-norm"] = ph.power_pct / 100.0
            for _ in range(int(dt_s / dt)):
                fdm.run()
            bulk_rows.append({
                "t_s": t_s,
                "egt_c": float(fdm["propulsion/engine[0]/egt-degF"] - 32) * 5 / 9,
                "cht_c": float(fdm["propulsion/engine[0]/cht-degF"] - 32) * 5 / 9,
                "map_kpa": float(fdm["propulsion/engine[0]/map-inhg"]) * 3.386389,
                "rpm": float(fdm["propulsion/engine[0]/engine-rpm"]),
            })
            t_s += dt_s
        prev_alt = ph.altitude_ft

    # Build the full two-engine schema with the NumPy generator, then overlay
    # JSBSim's bulk port-engine channels where we have them.
    base = generate_mission_numpy(
        profile, dt_s, cfg, degradations_port, degradations_stbd, seed, start_time
    )
    for row, bulk in zip(base["rows"], bulk_rows):
        e1 = row["engine1"]
        mean_egt = sum(e1["egt_cylinders"]) / len(e1["egt_cylinders"])
        mean_cht = sum(e1["cht_cylinders"]) / len(e1["cht_cylinders"])
        degt = bulk["egt_c"] - mean_egt
        dcht = bulk["cht_c"] - mean_cht
        e1["egt_cylinders"] = [round(x + degt, 1) for x in e1["egt_cylinders"]]
        e1["cht_cylinders"] = [round(x + dcht, 1) for x in e1["cht_cylinders"]]
        if bulk["map_kpa"] > 1:
            e1["manifold_pressure"] = round(bulk["map_kpa"], 2)
        if bulk["rpm"] > 1:
            e1["rpm"] = round(bulk["rpm"], 1)
    base["meta"]["generator"] = "jsbsim+numpy"
    base["meta"]["jsbsim_aircraft"] = aircraft
    return base
