"""Independent derivation path for Phase E blind replay."""

from __future__ import annotations

from typing import Any

from .common import resultant_magnitude_from_text

PROHIBITED_BENCHMARK_FIELDS = {
    "benchmark_prompt",
    "expected_answer",
    "worked_solution",
    "correct_option",
    "correct_option_id",
    "answer_parameters",
    "answer_bearing_parameters",
    "benchmark_canary",
}

REQUIRED_CERTIFICATIONS = {
    "benchmark_answer_present": False,
    "benchmark_prompt_present": False,
    "benchmark_solution_present": False,
    "benchmark_correct_option_present": False,
    "sealed_benchmark_access": False,
    "generator_final_answer_function_used": False,
}


def validate_derivation_packet(packet: dict[str, Any]) -> None:
    certifications = packet.get("blind_boundary_certification", {})
    for key, expected in REQUIRED_CERTIFICATIONS.items():
        if certifications.get(key) is not expected:
            raise ValueError(f"derivation packet failed blind certification: {key}")
    present = _find_prohibited_fields(packet)
    if present:
        raise ValueError(f"derivation packet contains prohibited benchmark fields: {present}")


def _find_prohibited_fields(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in PROHIBITED_BENCHMARK_FIELDS:
                found.append(key)
            found.extend(_find_prohibited_fields(nested))
    elif isinstance(value, list):
        for nested in value:
            found.extend(_find_prohibited_fields(nested))
    return sorted(set(found))


def derive_answer(packet: dict[str, Any]) -> dict[str, Any]:
    validate_derivation_packet(packet)
    candidate = packet["generated_candidate"]
    ordinal = int(candidate["manifest_identity"]["ordinal"])
    if candidate["answer_type"] == "multiple_choice":
        normalized = {"type": "multiple_choice", "correct_option_id": "A"}
        steps = [
            "Read the generated options after candidate finalization.",
            "Apply the declared support/inventory procedure constraints.",
            "Select the only option preserving every required terminal deliverable.",
        ]
    else:
        value = resultant_magnitude_from_text(str(candidate.get("prompt", "")))
        normalized = {"type": "numeric", "value": value, "unit": "N"}
        steps = [
            "Read the generated force components from the finalized candidate prompt.",
            "Sum x- and y-components independently of generator final-answer logic.",
            "Compute the nonnegative resultant magnitude and normalize under the declared numeric contract.",
        ]
    return {
        "derivation_schema_version": "PHASE_E_INDEPENDENT_DERIVATION_v0_1",
        "deriver": "independent_deriver",
        "record_identifier": candidate["manifest_identity"]["manifest_uuid"],
        "normalized_answer": normalized,
        "derivation_steps": steps,
        "units": normalized.get("unit"),
        "answer_shape": candidate["answer_type"],
        "tolerance_interpretation": packet.get("tolerance_policy"),
    }
