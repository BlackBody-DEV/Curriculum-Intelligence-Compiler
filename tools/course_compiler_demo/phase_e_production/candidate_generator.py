"""Blind candidate generation for Phase E golden replay."""

from __future__ import annotations

from typing import Any

from .common import resultant_magnitude_from_text
from .family_adapters import vector_components_from_primitive

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
    "benchmark_prompt_present": False,
    "benchmark_answer_present": False,
    "benchmark_solution_present": False,
    "benchmark_correct_option_present": False,
    "benchmark_answer_parameters_present": False,
    "sealed_benchmark_access": False,
}


def validate_generation_packet(packet: dict[str, Any]) -> None:
    certifications = packet.get("blind_boundary_certification", {})
    for key, expected in REQUIRED_CERTIFICATIONS.items():
        if certifications.get(key) is not expected:
            raise ValueError(f"generation packet failed blind certification: {key}")
    present = _find_prohibited_fields(packet)
    if present:
        raise ValueError(f"generation packet contains prohibited benchmark fields: {present}")


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


def generate_candidate(packet: dict[str, Any]) -> dict[str, Any]:
    validate_generation_packet(packet)
    row = packet["manifest_row"]
    ordinal = int(row["ordinal"])
    answer_type = row["answer_type"]
    primitive_text = str(row.get("primitive_input_data", ""))
    prompt = (
        f"For Phase E row {ordinal}, use the signed procedure "
        f"{row['procedure_id']} with these text-only givens: {primitive_text} "
        f"Follow generation family {row['generation_family']} and report only the declared terminal answer."
    )
    if answer_type == "multiple_choice":
        options = [
            {"option_id": "A", "content": "Complete inventory follows the declared procedure."},
            {"option_id": "B", "content": "Inventory omits one declared reaction component."},
            {"option_id": "C", "content": "Inventory uses an unsupported sign convention."},
            {"option_id": "D", "content": "Inventory requires undeclared geometry."},
        ]
        answer = {"type": "multiple_choice", "correct_option_id": "A"}
    elif answer_type == "numeric_pair":
        options = []
        answer = vector_components_from_primitive(primitive_text)
    else:
        value = resultant_magnitude_from_text(prompt)
        options = []
        answer = {"type": "numeric", "value": value, "unit": "N"}
    return {
        "candidate_schema_version": "PHASE_E_CANDIDATE_v0_1",
        "status_labels": {
            "noncanonical": True,
            "human_review_required": True,
            "student_visible": False,
            "eligible_for_alpha_import": False,
            "shadow_mode": True,
        },
        "manifest_identity": {
            "manifest_uuid": row["manifest_uuid"],
            "ordinal": ordinal,
            "family_identifier": row["family_identifier"],
            "destination_canonical_path": row["destination_canonical_path"],
        },
        "procedure_id": row["procedure_id"],
        "question_type": row["question_type"],
        "answer_type": answer_type,
        "prompt": prompt,
        "options": options,
        "expected_answer_proposal": answer,
        "generation_source": "candidate_generator",
    }
