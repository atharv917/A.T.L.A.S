"""Residual generation: measured - expected, per channel.

Kept deliberately tiny. The only non-obvious choice is that CHT/EGT residuals
are returned per-cylinder (a list) because the whole localization story depends
on one cylinder's residual diverging while its siblings stay near zero.
"""

from __future__ import annotations

from typing import Any


def _pairwise_diff(measured: list[float], expected: list[float]) -> list[float]:
    n = min(len(measured), len(expected))
    return [round(float(measured[i]) - float(expected[i]), 3) for i in range(n)]


def compute_residuals(
    telemetry: dict[str, Any], expected: dict[str, Any]
) -> dict[str, Any]:
    """Build the residual dict in the shape the API contract expects."""
    res: dict[str, Any] = {}

    if "cht_cylinders" in telemetry and "cht_c" in expected:
        res["cht_c"] = _pairwise_diff(telemetry["cht_cylinders"], expected["cht_c"])
    if "egt_cylinders" in telemetry and "egt_c" in expected:
        res["egt_c"] = _pairwise_diff(telemetry["egt_cylinders"], expected["egt_c"])

    scalar_map = {
        "coolant_temp_c": "coolant_temp_c",
        "oil_temperature": "oil_temperature_c",
        "oil_pressure": "oil_press_kpa",
        "manifold_pressure": "manifold_pressure_kpa",
    }
    for tkey, ekey in scalar_map.items():
        if telemetry.get(tkey) is not None and expected.get(ekey) is not None:
            out_key = "oil_press_kpa" if tkey == "oil_pressure" else ekey
            res[out_key] = round(float(telemetry[tkey]) - float(expected[ekey]), 3)

    return res


def flatten_residual_vector(residuals: dict[str, Any]) -> list[float]:
    """Flatten to a 1-D vector for the anomaly detector, deterministic order."""
    vec: list[float] = []
    for key in ("cht_c", "egt_c"):
        if key in residuals:
            vec.extend(float(x) for x in residuals[key])
    for key in ("coolant_temp_c", "oil_temperature_c", "oil_press_kpa",
                "manifold_pressure_kpa"):
        if key in residuals and not isinstance(residuals[key], list):
            vec.append(float(residuals[key]))
    return vec
