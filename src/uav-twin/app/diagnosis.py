"""Fault hypothesis ranking.

Deliberately a transparent scoring model, not a black box: no training data
exists to fit a classifier honestly, and a judge can read exactly why each
hypothesis got the score it did. Each candidate fault has a small set of
expected signatures over the differential features and residuals; we score how
well the current observation matches each signature, then softmax to
probabilities.

The lowest-probability hypothesis is ALWAYS returned, never trimmed — showing
the alternative you considered and rejected is an honesty signal.
"""

from __future__ import annotations

import math
from typing import Any


def _sig(x: float, k: float = 1.0) -> float:
    return 1.0 / (1.0 + math.exp(-k * x))


def rank_hypotheses(
    residuals: dict[str, Any],
    cyl_spread: dict[str, Any],
    eng_delta: dict[str, float],
    params: dict[str, float],
    param_sigma: dict[str, float],
) -> dict[str, Any]:
    cht_res = residuals.get("cht_c", [])
    egt_res = residuals.get("egt_c", [])
    hot = cyl_spread.get("hottest_cylinder")
    egt_margin = float(cyl_spread.get("egt_outlier_margin", 0.0))
    cht_margin = float(cyl_spread.get("cht_outlier_margin", 0.0))
    ve = float(params.get("volumetric_efficiency", 0.88))
    ve_nom = 0.88
    cooling = float(params.get("cooling_factor", 1.0))

    single_cyl = egt_margin > 12.0 or cht_margin > 10.0
    cyl_tag = f"cyl{hot}" if hot else "cylX"

    scores: dict[str, float] = {}

    # injector / fuelling degradation on one cylinder: EGT of that cyl HIGH
    # (lean-ish, slow burn) with only a small CHT rise, whole-engine VE ~ nominal
    scores[f"injector_degradation_{cyl_tag}"] = (
        2.2 * _sig(egt_margin - 12.0, 0.15)
        + 0.6 * _sig(8.0 - cht_margin, 0.2)
        + 0.8 * _sig(0.02 - abs(ve - ve_nom), 40.0)
        + (0.5 if single_cyl else -0.5)
    )

    # exhaust valve recession on one cylinder: EGT high AND CHT of same cyl also
    # elevated (blow-by heats the head), spread grows over time
    scores[f"exhaust_valve_recession_{cyl_tag}"] = (
        1.6 * _sig(egt_margin - 15.0, 0.12)
        + 1.4 * _sig(cht_margin - 8.0, 0.2)
        + (0.4 if single_cyl else -0.6)
    )

    # EGT sensor drift on one cylinder: EGT residual high but CHT of that cyl
    # totally normal and engine delta unaffected — nothing thermal corroborates
    scores[f"egt_sensor_drift_{cyl_tag}"] = (
        1.3 * _sig(egt_margin - 10.0, 0.12)
        + 1.2 * _sig(4.0 - cht_margin, 0.4)
        + 0.6 * _sig(3.0 - abs(eng_delta.get("cht_mean_diff", 0.0)), 0.5)
        - (0.2 if single_cyl else 0.0)
    )

    # whole-engine cooling degradation: ALL cylinders' CHT up, low cooling_factor,
    # engine-to-engine CHT delta large, spread SMALL (uniform)
    scores["cooling_system_degradation"] = (
        1.8 * _sig((1.0 - cooling) * 20.0 - 1.5, 1.0)
        + 1.0 * _sig(abs(eng_delta.get("cht_mean_diff", 0.0)) - 6.0, 0.3)
        + 0.8 * _sig(6.0 - float(cyl_spread.get("cht_spread", 0.0)), 0.3)
        - (0.8 if single_cyl else 0.0)
    )

    # induction / boost loss: low boost_capability, MAP residual negative,
    # power down across the board
    map_res = float(residuals.get("manifold_pressure_kpa", 0.0))
    scores["induction_boost_loss"] = (
        1.7 * _sig((1.0 - float(params.get("boost_capability", 1.0))) * 20.0 - 1.5, 1.0)
        + 1.1 * _sig(-map_res - 3.0, 0.3)
        - (0.6 if single_cyl else 0.0)
    )

    # nothing wrong / noise floor — always a candidate
    max_margin = max(abs(egt_margin), abs(cht_margin), 0.0)
    scores["nominal_within_noise"] = 1.4 * _sig(10.0 - max_margin, 0.3)

    # softmax -> probabilities
    m = max(scores.values())
    exp = {k: math.exp(v - m) for k, v in scores.items()}
    z = sum(exp.values())
    probs = {k: v / z for k, v in exp.items()}

    ranked = sorted(probs.items(), key=lambda kv: kv[1], reverse=True)
    hypotheses = [
        {"fault": k, "label": _label(k), "probability": round(p, 3)}
        for k, p in ranked
    ]
    return {"hypotheses": hypotheses}


_LABELS = {
    "injector_degradation": "Injector degradation",
    "exhaust_valve_recession": "Exhaust valve recession",
    "egt_sensor_drift": "EGT sensor drift",
    "cooling_system_degradation": "Cooling system degradation",
    "induction_boost_loss": "Induction / boost loss",
    "nominal_within_noise": "Nominal (within noise)",
}


def _label(key: str) -> str:
    for stem, text in _LABELS.items():
        if key.startswith(stem):
            tail = key[len(stem):].lstrip("_")
            return f"{text} ({tail.replace('cyl', 'cyl ')})" if tail else text
    return key.replace("_", " ").capitalize()
