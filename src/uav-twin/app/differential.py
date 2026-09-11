"""Differential features — the cheapest and strongest diagnostic signal.

Two comparisons, neither of which needs a model:

  engine-to-engine: both engines on the platform fly through the SAME ambient
    air at the same instant. If port CHT is 15 C above starboard CHT, that
    difference cannot be the weather — it is the engine.

  cylinder-to-cylinder: all 4 cylinders of one engine share the same coolant,
    oil and intake. If cylinder 3's EGT sits 40 C above the mean of 1/2/4,
    that cannot be a whole-engine or environmental effect — it is cylinder 3.

Together they localize a fault to (which engine, which cylinder) before any
parameter estimate or anomaly score is computed.
"""

from __future__ import annotations

from statistics import fmean
from typing import Any


def engine_delta(
    telemetry: dict[str, Any], paired: dict[str, Any] | None
) -> dict[str, float]:
    """Mean CHT / EGT / other-scalar difference: this engine minus the other."""
    if not paired:
        return {}
    out: dict[str, float] = {}

    for name, key in (("cht_mean_diff", "cht_cylinders"),
                      ("egt_mean_diff", "egt_cylinders")):
        a, b = telemetry.get(key), paired.get(key)
        if a and b:
            out[name] = round(fmean(a) - fmean(b), 3)

    for name, key in (("coolant_diff", "coolant_temp_c"),
                      ("oil_press_diff", "oil_pressure"),
                      ("fuel_flow_diff", "fuel_flow"),
                      ("map_diff", "manifold_pressure")):
        a, b = telemetry.get(key), paired.get(key)
        if a is not None and b is not None:
            out[name] = round(float(a) - float(b), 3)
    return out


def cylinder_spread(telemetry: dict[str, Any]) -> dict[str, Any]:
    """Per-engine spread of the 4 cylinders + which one is the outlier.

    `hottest_cylinder` is 1-indexed to match how an operator numbers cylinders.
    `egt_outlier_margin` is the hottest cylinder minus the mean of the rest —
    that is the number the diagnosis stage thresholds on.
    """
    out: dict[str, Any] = {}
    egt = telemetry.get("egt_cylinders")
    cht = telemetry.get("cht_cylinders")

    if egt:
        out["egt_spread"] = round(max(egt) - min(egt), 3)
        hot = max(range(len(egt)), key=lambda i: egt[i])
        rest = [egt[i] for i in range(len(egt)) if i != hot]
        out["hottest_cylinder"] = hot + 1
        out["egt_outlier_margin"] = round(egt[hot] - (fmean(rest) if rest else egt[hot]), 3)
    if cht:
        out["cht_spread"] = round(max(cht) - min(cht), 3)
        hot_c = max(range(len(cht)), key=lambda i: cht[i])
        rest_c = [cht[i] for i in range(len(cht)) if i != hot_c]
        out["cht_outlier_margin"] = round(
            cht[hot_c] - (fmean(rest_c) if rest_c else cht[hot_c]), 3
        )
        out.setdefault("hottest_cylinder", hot_c + 1)
    return out
