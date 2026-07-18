"""Fixed prompt builders for approved assessment generation families."""

from __future__ import annotations

from typing import Any

from .models import AssessmentGenerationError


def newtons_second_law_1d_prompt(params: dict[str, Any], scenario: dict[str, Any]) -> str:
    body = scenario["object"]
    direction = "to the right" if float(params["net_force_n"]) >= 0 else "to the left"
    target = params["target_variable"]
    if target == "acceleration":
        return (
            f"{body} has mass {params['mass_kg']} kg and a net horizontal force of "
            f"{abs(params['net_force_n'])} N {direction}. What is its acceleration?"
        )
    if target == "net_force":
        adir = "to the right" if float(params["acceleration_mps2"]) >= 0 else "to the left"
        return (
            f"{body} has mass {params['mass_kg']} kg and accelerates at "
            f"{abs(params['acceleration_mps2'])} m/s^2 {adir}. What net force acts on it?"
        )
    if target == "mass":
        return (
            f"{body} has a net horizontal force of {abs(params['net_force_n'])} N {direction} "
            f"and acceleration {abs(params['acceleration_mps2'])} m/s^2 in the same direction. "
            "What is its mass?"
        )
    raise AssessmentGenerationError(f"unsupported target variable: {target}")


def vector_components_2d_prompt(params: dict[str, Any], scenario: dict[str, Any]) -> str:
    quadrant = params["quadrant_label"]
    if quadrant == "Quadrant I":
        reference = "above the positive x-axis"
    elif quadrant == "Quadrant II":
        reference = "above the negative x-axis"
    elif quadrant == "Quadrant III":
        reference = "below the negative x-axis"
    elif quadrant == "Quadrant IV":
        reference = "below the positive x-axis"
    else:
        raise AssessmentGenerationError(f"unsupported quadrant label: {quadrant}")
    return (
        f"{scenario['object']} experiences a {params['magnitude']} N force at "
        f"{params['angle_degrees']} degrees {reference} in {quadrant}. "
        "Find the signed x- and y-components of the force."
    )


PROMPT_BUILDERS = {
    "newtons_second_law_1d_prompt_v1": newtons_second_law_1d_prompt,
    "vector_components_2d_prompt_v1": vector_components_2d_prompt,
}


def build_prompt(builder_id: str, params: dict[str, Any], scenario: dict[str, Any]) -> str:
    builder = PROMPT_BUILDERS.get(builder_id)
    if builder is None:
        raise AssessmentGenerationError(f"unknown prompt builder: {builder_id}")
    return builder(params, scenario)
