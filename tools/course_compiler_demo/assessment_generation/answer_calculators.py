"""Fixed answer calculators for approved assessment generation families."""

from __future__ import annotations

import math
from typing import Any

from .models import AssessmentGenerationError


def _round(value: float) -> float:
    return round(float(value), 6)


def newtons_second_law_1d_answer(params: dict[str, Any]) -> dict[str, Any]:
    target = params["target_variable"]
    mass = float(params["mass_kg"])
    force = float(params["net_force_n"])
    acceleration = float(params["acceleration_mps2"])
    if mass <= 0:
        raise AssessmentGenerationError("mass must be positive")
    if target == "acceleration":
        return {"value": _round(force / mass), "unit": "m/s^2"}
    if target == "net_force":
        return {"value": _round(mass * acceleration), "unit": "N"}
    if target == "mass":
        if acceleration == 0:
            raise AssessmentGenerationError("acceleration cannot be zero when solving mass")
        return {"value": _round(force / acceleration), "unit": "kg"}
    raise AssessmentGenerationError(f"unsupported target variable: {target}")


def vector_components_2d_answer(params: dict[str, Any]) -> dict[str, Any]:
    magnitude = float(params["magnitude"])
    angle = math.radians(float(params["angle_degrees"]))
    sx = int(params["x_sign"])
    sy = int(params["y_sign"])
    fx = sx * magnitude * math.cos(angle)
    fy = sy * magnitude * math.sin(angle)
    return {"value": {"Fx": _round(fx), "Fy": _round(fy)}, "unit": "N"}


ANSWER_CALCULATORS = {
    "newtons_second_law_1d_answer_v1": newtons_second_law_1d_answer,
    "vector_components_2d_answer_v1": vector_components_2d_answer,
}


def calculate_answer(calculator_id: str, params: dict[str, Any]) -> dict[str, Any]:
    calculator = ANSWER_CALCULATORS.get(calculator_id)
    if calculator is None:
        raise AssessmentGenerationError(f"unknown answer calculator: {calculator_id}")
    return calculator(params)
