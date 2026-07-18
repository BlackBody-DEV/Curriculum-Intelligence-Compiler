"""Fixed solution builders for approved assessment generation families."""

from __future__ import annotations

from typing import Any

from .models import AssessmentGenerationError


def newtons_second_law_1d_solution(params: dict[str, Any], answer: dict[str, Any]) -> list[str]:
    target = params["target_variable"]
    if target == "acceleration":
        return [
            "Use F_net = m a.",
            "Solve for acceleration with a = F_net / m.",
            f"Substitute a = {params['net_force_n']} / {params['mass_kg']} = {answer['value']} {answer['unit']}.",
        ]
    if target == "net_force":
        return [
            "Use F_net = m a.",
            "Multiply mass by acceleration.",
            f"F_net = {params['mass_kg']} * {params['acceleration_mps2']} = {answer['value']} {answer['unit']}.",
        ]
    if target == "mass":
        return [
            "Use F_net = m a.",
            "Solve for mass with m = F_net / a.",
            f"m = {params['net_force_n']} / {params['acceleration_mps2']} = {answer['value']} {answer['unit']}.",
        ]
    raise AssessmentGenerationError(f"unsupported target variable: {target}")


def vector_components_2d_solution(params: dict[str, Any], answer: dict[str, Any]) -> list[str]:
    return [
        "Resolve the force using cosine for the x-component and sine for the y-component.",
        f"Apply the stated quadrant signs: x_sign = {params['x_sign']}, y_sign = {params['y_sign']}.",
        f"Fx = {answer['value']['Fx']} {answer['unit']}; Fy = {answer['value']['Fy']} {answer['unit']}.",
    ]


SOLUTION_BUILDERS = {
    "newtons_second_law_1d_solution_v1": newtons_second_law_1d_solution,
    "vector_components_2d_solution_v1": vector_components_2d_solution,
}


def build_solution(builder_id: str, params: dict[str, Any], answer: dict[str, Any]) -> list[str]:
    builder = SOLUTION_BUILDERS.get(builder_id)
    if builder is None:
        raise AssessmentGenerationError(f"unknown solution builder: {builder_id}")
    return builder(params, answer)
