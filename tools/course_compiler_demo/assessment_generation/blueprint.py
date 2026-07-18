"""Assessment blueprint validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import ASSESSMENT_TYPES, BLUEPRINT_STATUSES, CONTRACT_VERSION, DIFFICULTIES, AssessmentGenerationError, load_json


def load_blueprint(path: Path | str) -> dict[str, Any]:
    blueprint = load_json(Path(path))
    validate_blueprint(blueprint)
    return blueprint


def validate_blueprint(blueprint: dict[str, Any]) -> None:
    required = {
        "assessment_id",
        "contract_version",
        "title",
        "assessment_type",
        "subject_code",
        "course_profile",
        "selected_topic_codes",
        "selected_micro_skill_codes",
        "question_count",
        "difficulty_distribution",
        "question_type_distribution",
        "generation_family_allocation",
        "prerequisite_policy",
        "scaffolding_policy",
        "solution_policy",
        "answer_key_policy",
        "uniqueness_policy",
        "rights_boundary",
        "random_seed",
        "status",
    }
    missing = sorted(required - set(blueprint))
    if missing:
        raise AssessmentGenerationError(f"blueprint missing fields: {missing}")
    if blueprint["contract_version"] != CONTRACT_VERSION:
        raise AssessmentGenerationError("unknown blueprint contract version")
    if blueprint["assessment_type"] not in ASSESSMENT_TYPES:
        raise AssessmentGenerationError("unsupported assessment type")
    if blueprint["status"] not in BLUEPRINT_STATUSES:
        raise AssessmentGenerationError("unsupported blueprint status")
    if blueprint["status"] != "generation_ready":
        raise AssessmentGenerationError("blueprint is not generation_ready")
    if int(blueprint["question_count"]) <= 0:
        raise AssessmentGenerationError("question_count must be positive")
    if not blueprint.get("selected_topic_codes"):
        raise AssessmentGenerationError("blueprint requires selected topics")
    if not blueprint.get("selected_micro_skill_codes"):
        raise AssessmentGenerationError("blueprint requires selected micro-skills")
    difficulty_keys = set(blueprint["difficulty_distribution"])
    allowed_difficulty_keys = DIFFICULTIES - {"mixed"}
    unknown_difficulties = sorted(difficulty_keys - allowed_difficulty_keys)
    if unknown_difficulties:
        raise AssessmentGenerationError(f"unsupported difficulty distribution keys: {unknown_difficulties}")
    dist_total = sum(int(value) for value in blueprint["difficulty_distribution"].values())
    if dist_total != int(blueprint["question_count"]):
        raise AssessmentGenerationError("difficulty distribution must equal question_count")
    question_type_total = sum(int(value) for value in blueprint["question_type_distribution"].values())
    if question_type_total != int(blueprint["question_count"]):
        raise AssessmentGenerationError("question type distribution must equal question_count")
    boundary = blueprint.get("rights_boundary", {})
    for key in ["eligible_for_alpha_import", "canonical_approved", "student_visible"]:
        if boundary.get(key) is not False:
            raise AssessmentGenerationError(f"unsafe blueprint boundary: {key}")
    if boundary.get("human_review_required") is not True:
        raise AssessmentGenerationError("blueprint must require human review")
