"""Stable constants and helpers for the offline reference consumer."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


CONSUMER_NAME = "compiler_offline_reference_consumer"
CONSUMER_VERSION = "1.0.0"
COMPILER_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = COMPILER_ROOT / "tools/course_compiler_demo/release_package/golden_packages"
FROZEN_CONTRACT_ROOT = COMPILER_ROOT / "tools/course_compiler_demo/release_package/contracts"
FROZEN_VALIDATOR_ROOT = COMPILER_ROOT / "tools/course_compiler_demo/release_package/validate"

ACCEPTED_VALIDATOR_VERDICTS = {"accept", "accept_with_warnings"}
REJECTED_PLAN = "not_generated_package_rejected"
CONSUMER_ERROR_PLAN = "not_generated_consumer_error"

BOUNDARY_EVIDENCE = {
    "adaptive_platform_accessed": False,
    "adaptive_platform_modified": False,
    "adaptive_platform_git_activity": False,
    "database_contacted": False,
    "network_endpoint_contacted": False,
    "runtime_route_called": False,
    "learner_state_modified": False,
    "canonical_promotion_performed": False,
    "student_visible_output_created": False,
    "package_modified": False,
}

PROHIBITED_OPERATIONS = [
    "no adaptive-platform write performed",
    "no database write performed",
    "no migration performed",
    "no runtime route called",
    "no learner state modified",
    "no canonical promotion performed",
    "no student-visible publication performed",
]

FUTURE_DESTINATION_CAPABILITIES = [
    "candidate-record intake",
    "identifier mapping",
    "review-state preservation",
    "non-live staging isolation",
    "transaction or rollback boundary",
    "artifact-reference validation",
]

ARTIFACT_GROUPS = {
    "source_and_provenance": {"source_metadata", "source_interpretation"},
    "curriculum_identity": {"curriculum_extraction"},
    "procedure_candidates": {"procedure_candidate"},
    "question_candidates": {"question_candidate"},
    "generation_family_candidates": {"generation_family_candidate"},
    "signal_mappings": {"signal_mapping"},
    "performance_tracking_targets": {"performance_tracking_target"},
    "review_records": {"review_record"},
    "validation_evidence": {"validation_report"},
    "assets": {"asset_reference"},
    "known_gaps": {"known_gap_report"},
}


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(payload: Any) -> str:
    import json

    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
