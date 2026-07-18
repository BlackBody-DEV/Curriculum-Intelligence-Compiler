"""Shared constants and small helpers for assessment generation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "assessment_generation_contract_v1"
FAMILY_CONTRACT_VERSION = "assessment_generation_family_v1"
QUESTION_CONTRACT_VERSION = "generated_question_v1"
ASSESSMENT_CONTRACT_VERSION = "generated_assessment_v1"
VALIDATION_CONTRACT_VERSION = "assessment_validation_report_v1"
REVIEW_CONTRACT_VERSION = "assessment_review_decisions_v1"

ASSESSMENT_TYPES = {
    "practice_set",
    "homework_set",
    "quiz",
    "mastery_check",
    "exam_section",
    "custom_assessment",
}
BLUEPRINT_STATUSES = {
    "draft",
    "validated",
    "generation_ready",
    "generated",
    "review_pending",
    "review_complete",
}
DIFFICULTIES = {"foundational", "standard", "advanced", "mixed"}
REVIEW_STATUSES = {"pending", "accepted", "rejected", "needs_revision", "regenerate"}

NON_LIVE_BOUNDARY = {
    "status": "compiler_non_live_review_pending",
    "eligible_for_alpha_import": False,
    "canonical_approved": False,
    "student_visible": False,
    "human_review_required": True,
}


class AssessmentGenerationError(ValueError):
    """Raised when deterministic generation cannot proceed safely."""


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def pretty_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def sha256_payload(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pretty_json(payload), encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AssessmentGenerationError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise AssessmentGenerationError(f"expected JSON object: {path}")
    return payload
