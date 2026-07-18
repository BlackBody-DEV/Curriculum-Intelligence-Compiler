"""Validation for generated assessments and scope boundaries."""

from __future__ import annotations

from typing import Any

from .answer_calculators import calculate_answer
from .models import AssessmentGenerationError, REVIEW_STATUSES, VALIDATION_CONTRACT_VERSION


def validate_family_scope(family: dict[str, Any], blueprint: dict[str, Any]) -> None:
    if family["subject_code"] != blueprint["subject_code"]:
        raise AssessmentGenerationError("family subject outside blueprint")
    if family["topic_code"] not in blueprint["selected_topic_codes"]:
        raise AssessmentGenerationError("family topic outside blueprint")
    target = family["target_micro_skill_code"]
    if target not in blueprint["selected_micro_skill_codes"]:
        raise AssessmentGenerationError("family micro-skill outside blueprint")
    allowed = set(blueprint.get("prerequisite_policy", {}).get("allowed_prerequisite_skills", []))
    used = set(family.get("approved_prerequisite_skills", []))
    if not used <= allowed:
        raise AssessmentGenerationError("family uses unapproved prerequisite")
    downstream = set(blueprint.get("scope_policy", {}).get("forbidden_downstream_micro_skills", []))
    if downstream & set(family.get("supported_micro_skills", [])):
        raise AssessmentGenerationError("family introduces downstream skill")
    if family.get("approved_procedure_code") not in blueprint.get("generation_family_allocation", {}).get(family["generation_family_id"], {}).get("approved_procedure_codes", []):
        raise AssessmentGenerationError("procedure binding not approved by blueprint")
    allowed_types = set(blueprint.get("question_type_distribution", {}))
    if allowed_types and family["question_types"][0] not in allowed_types:
        raise AssessmentGenerationError("family question type outside blueprint")


def validate_question(question: dict[str, Any], family: dict[str, Any], blueprint: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if question["subject_code"] != blueprint["subject_code"]:
        errors.append("subject mismatch")
    if question["topic_code"] not in blueprint["selected_topic_codes"]:
        errors.append("topic outside blueprint")
    if question["micro_skill_code"] not in blueprint["selected_micro_skill_codes"]:
        errors.append("micro-skill outside blueprint")
    if question["procedure_code"] != family["approved_procedure_code"]:
        errors.append("procedure mismatch")
    if question["expected_answer"].get("unit") not in family["accepted_units"]:
        errors.append("unsupported unit")
    tolerance = question.get("tolerance", {})
    if not isinstance(tolerance, dict) or float(tolerance.get("absolute", -1)) < 0:
        errors.append("invalid tolerance")
    recomputed = calculate_answer(family["answer_calculator_id"], question["parameter_set"])
    if recomputed != question["expected_answer"]:
        errors.append("answer recomputation mismatch")
    prompt_lower = question["prompt"].lower()
    answer_text = str(question["expected_answer"].get("value")).lower()
    if answer_text and answer_text in prompt_lower:
        errors.append("prompt leaks answer")
    for exclusion in family.get("scope_exclusions", []):
        if exclusion.lower() in prompt_lower:
            errors.append(f"scope exclusion present: {exclusion}")
    return errors


def review_record(
    *,
    question_id: str,
    decision: str,
    locked: bool = False,
    reviewed_at: str | None = None,
    reviewer_note: str = "",
    math_content_edited: bool = False,
    replacement_question_id: str | None = None,
) -> dict[str, Any]:
    if decision not in REVIEW_STATUSES:
        raise AssessmentGenerationError("unsupported review decision")
    return {
        "question_id": question_id,
        "decision": decision,
        "locked": locked,
        "reviewed_at": reviewed_at,
        "reviewer_note": reviewer_note,
        "math_content_edited": math_content_edited,
        "validation_invalidated": bool(math_content_edited),
        "replacement_question_id": replacement_question_id,
    }


def validation_report(
    *,
    assessment: dict[str, Any],
    duplicate_report: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    return {
        "contract_version": VALIDATION_CONTRACT_VERSION,
        "assessment_id": assessment["assessment_id"],
        "validation_status": "pass" if not errors else "fail",
        "question_count": len(assessment.get("questions", [])),
        "duplicate_report": duplicate_report,
        "errors": errors,
        "non_live_boundary": assessment["non_live_boundary"],
    }
