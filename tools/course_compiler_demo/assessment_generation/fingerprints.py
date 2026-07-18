"""Deterministic exact and structural fingerprints."""

from __future__ import annotations

from typing import Any

from .models import sha256_payload


def exact_fingerprint(question: dict[str, Any]) -> str:
    return sha256_payload(
        {
            "prompt": " ".join(question["prompt"].lower().split()),
            "parameter_set": question["parameter_set"],
            "expected_answer": question["expected_answer"],
            "diagram_specification": question.get("diagram_specification"),
        }
    )


def structural_fingerprint(question: dict[str, Any], family: dict[str, Any]) -> str:
    fields = family.get("structural_signature_fields", [])
    params = question["parameter_set"]
    return sha256_payload(
        {
            "generation_family_id": question["generation_family_id"],
            "reasoning_sequence": family.get("reasoning_sequence", []),
            "difficulty": question["difficulty"],
            "question_type": question["question_type"],
            "fields": {field: params.get(field) for field in fields},
        }
    )
