"""Load and validate deterministic generation-family definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .answer_calculators import ANSWER_CALCULATORS
from .models import FAMILY_CONTRACT_VERSION, AssessmentGenerationError, load_json
from .prompt_builders import PROMPT_BUILDERS
from .solution_builders import SOLUTION_BUILDERS


REQUIRED_FAMILY_FIELDS = {
    "generation_family_id",
    "contract_version",
    "family_version",
    "subject_code",
    "topic_code",
    "subtopic_code",
    "supported_micro_skills",
    "target_micro_skill_code",
    "approved_procedure_code",
    "approved_prerequisite_skills",
    "question_types",
    "answer_adapter_type",
    "parameter_schema",
    "parameter_constraints",
    "difficulty_profiles",
    "scenario_templates",
    "prompt_builder_id",
    "answer_calculator_id",
    "solution_builder_id",
    "accepted_units",
    "grading_type",
    "tolerance",
    "reasoning_sequence",
    "structural_signature_fields",
    "scope_inclusions",
    "scope_exclusions",
    "known_failure_modes",
    "rights_boundary",
    "question_origin",
    "human_review_required",
    "enabled",
}


def load_family(path: Path | str) -> dict[str, Any]:
    family = load_json(Path(path))
    validate_family(family)
    return family


def validate_family(family: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_FAMILY_FIELDS - set(family))
    if missing:
        raise AssessmentGenerationError(f"family missing fields: {missing}")
    if family["contract_version"] != FAMILY_CONTRACT_VERSION:
        raise AssessmentGenerationError("unknown family contract version")
    if family.get("enabled") is not True:
        raise AssessmentGenerationError("generation family is disabled")
    if family["prompt_builder_id"] not in PROMPT_BUILDERS:
        raise AssessmentGenerationError("unknown prompt builder ID")
    if family["answer_calculator_id"] not in ANSWER_CALCULATORS:
        raise AssessmentGenerationError("unknown answer calculator ID")
    if family["solution_builder_id"] not in SOLUTION_BUILDERS:
        raise AssessmentGenerationError("unknown solution builder ID")
    if "family_type" not in family:
        raise AssessmentGenerationError("family missing family_type")
    if family.get("human_review_required") is not True:
        raise AssessmentGenerationError("family must require human review")
    boundary = family.get("rights_boundary", {})
    if boundary.get("student_visible") is not False or boundary.get("canonical_approved") is not False:
        raise AssessmentGenerationError("unsafe family rights boundary")
    if not family.get("scenario_templates"):
        raise AssessmentGenerationError("family requires scenario templates")
    if any("/" in str(value) or "." in str(value) for key, value in family.items() if key.endswith("_builder_id") or key.endswith("_calculator_id")):
        raise AssessmentGenerationError("family IDs must be registry keys, not code paths")
