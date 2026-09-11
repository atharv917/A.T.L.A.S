"""Component health indices, derived from ESTIMATED PARAMETERS (not the anomaly
score) and aggregated by MINIMUM.

Each parameter maps to a 0..1 index: 1.0 at nominal, 0.0 once it has fallen to
`health_floor_fraction` of nominal (default 0.55). Linear in between, clamped.

Overall health is the MINIMUM of the component indices, never the mean. An
engine with lubrication 0.35 and everything else 1.0 reports overall 0.35,
limited_by="lubrication" — averaging would report 0.87 and bury the problem.
"""

from __future__ import annotations

from typing import Any

from .config import EngineConfig, DEFAULT_ENGINE, nominal_params

# which estimated parameter drives which named component
_COMPONENT_PARAM = {
    "cooling": "cooling_factor",
    "combustion": "volumetric_efficiency",
    "induction": "boost_capability",
    "lubrication": "oil_system_health",
}


def _index(value: float, nominal: float, floor_frac: float) -> float:
    floor = nominal * floor_frac
    if nominal <= floor:
        return 1.0
    idx = (value - floor) / (nominal - floor)
    return float(max(0.0, min(1.0, idx)))


def component_health(
    params: dict[str, float],
    param_sigma: dict[str, float] | None = None,
    cfg: EngineConfig = DEFAULT_ENGINE,
    combustion_cyl_penalty: float = 0.0,
) -> dict[str, Any]:
    """Return {overall, limited_by, components:{name:{index,confidence}}}.

    `combustion_cyl_penalty` (0..1) lets the caller fold in a per-cylinder
    combustion problem that the whole-engine VE estimate would otherwise miss
    (e.g. cylinder 3 EGT outlier). It is subtracted from the combustion index.
    """
    nom = nominal_params(cfg)
    sig = param_sigma or {}
    comps: dict[str, Any] = {}

    for comp, pkey in _COMPONENT_PARAM.items():
        val = float(params.get(pkey, nom[pkey]))
        idx = _index(val, nom[pkey], cfg.health_floor_fraction)
        if comp == "combustion":
            idx = max(0.0, idx - combustion_cyl_penalty)
        # confidence: tighter sigma -> higher confidence
        s = float(sig.get(pkey, 0.03))
        conf = float(max(0.05, min(0.98, 1.0 - 12.0 * s)))
        comps[comp] = {"index": round(idx, 3), "confidence": round(conf, 3)}

    limiting = min(comps, key=lambda c: comps[c]["index"])
    overall = comps[limiting]["index"]
    return {
        "overall": round(overall, 3),
        "limited_by": limiting,
        "components": comps,
    }
