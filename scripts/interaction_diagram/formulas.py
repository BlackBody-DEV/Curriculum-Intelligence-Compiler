"""Allowlisted typed formula implementations for interaction specs.

Free-form expressions are forbidden. Only these formula_id values may compute
dependent state.
"""

from __future__ import annotations

import math
from typing import Mapping


class FormulaError(ValueError):
    pass


def _require_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FormulaError(f"{name} must be numeric")
    return float(value)


def cartesian_fx_from_magnitude_angle_deg(
    values: Mapping[str, float], inputs: Mapping[str, object]
) -> float:
    magnitude = _require_number("magnitude", values[str(inputs["magnitude"])])
    angle = _require_number("angle_deg", values[str(inputs["angle_deg"])])
    return magnitude * math.cos(math.radians(angle))


def cartesian_fy_from_magnitude_angle_deg(
    values: Mapping[str, float], inputs: Mapping[str, object]
) -> float:
    magnitude = _require_number("magnitude", values[str(inputs["magnitude"])])
    angle = _require_number("angle_deg", values[str(inputs["angle_deg"])])
    return magnitude * math.sin(math.radians(angle))


def sum_selected(values: Mapping[str, float], inputs: Mapping[str, object]) -> float:
    selected = inputs.get("terms")
    if not isinstance(selected, list) or not selected:
        raise FormulaError("sum_selected requires non-empty terms list")
    total = 0.0
    for term in selected:
        total += _require_number(str(term), values[str(term)])
    return total


def resultant_magnitude_from_rx_ry(
    values: Mapping[str, float], inputs: Mapping[str, object]
) -> float:
    rx = _require_number("rx", values[str(inputs["rx"])])
    ry = _require_number("ry", values[str(inputs["ry"])])
    return math.hypot(rx, ry)


def resultant_direction_deg_from_rx_ry(
    values: Mapping[str, float], inputs: Mapping[str, object]
) -> float:
    rx = _require_number("rx", values[str(inputs["rx"])])
    ry = _require_number("ry", values[str(inputs["ry"])])
    if rx == 0.0 and ry == 0.0:
        raise FormulaError("resultant direction undefined for zero vector")
    angle = math.degrees(math.atan2(ry, rx))
    if angle < 0:
        angle += 360.0
    return angle


FORMULA_REGISTRY = {
    "cartesian_fx_from_magnitude_angle_deg": cartesian_fx_from_magnitude_angle_deg,
    "cartesian_fy_from_magnitude_angle_deg": cartesian_fy_from_magnitude_angle_deg,
    "sum_selected": sum_selected,
    "resultant_magnitude_from_rx_ry": resultant_magnitude_from_rx_ry,
    "resultant_direction_deg_from_rx_ry": resultant_direction_deg_from_rx_ry,
}


def evaluate_formula(
    formula_id: str, values: Mapping[str, float], inputs: Mapping[str, object]
) -> float:
    try:
        fn = FORMULA_REGISTRY[formula_id]
    except KeyError as exc:
        raise FormulaError(f"unsupported formula_id: {formula_id}") from exc
    return fn(values, inputs)
