"""Stable constants for the compiler integration reproduction harness."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


HARNESS_NAME = "compiler_integration_reproduction_harness"
HARNESS_VERSION = "1.0.0"
COMPILER_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = COMPILER_ROOT / "tools/course_compiler_demo/release_package/golden_packages"
CONTRACT_ROOT = COMPILER_ROOT / "tools/course_compiler_demo/release_package/contracts"
VALIDATOR_ROOT = COMPILER_ROOT / "tools/course_compiler_demo/release_package/validate"
CONSUMER_ROOT = COMPILER_ROOT / "tools/course_compiler_demo/reference_consumer"
HARNESS_ROOT = COMPILER_ROOT / "tools/course_compiler_demo/integration_readiness"

FIXTURE_EXPECTATIONS = {
    "minimal_valid": ("accept", "accepted_for_offline_planning", "generated", "reproduced"),
    "normal_multi_artifact": ("accept", "accepted_for_offline_planning", "generated", "reproduced"),
    "known_nonblocking_gaps": (
        "accept_with_warnings",
        "accepted_for_offline_planning_with_warnings",
        "generated_with_warnings",
        "reproduced_with_expected_warnings",
    ),
    "deliberately_invalid": (
        "reject",
        "rejected_without_plan",
        "not_generated_package_rejected",
        "reproduced_expected_rejection",
    ),
    "safety_boundary_violation": (
        "reject",
        "rejected_without_plan",
        "not_generated_package_rejected",
        "reproduced_expected_rejection",
    ),
}

DETERMINISTIC_COMPARISON_FIELDS = [
    "package identity",
    "contract and version",
    "validator and consumer verdicts",
    "artifact inventory and type counts",
    "reference-resolution sets",
    "dependency ordering",
    "artifact classifications",
    "known gaps",
    "errors, warnings, and rule IDs",
    "manifest and artifact checksums",
    "dry-run plan status",
    "prohibited-operation declarations",
    "boundary booleans",
]

VOLATILE_OBSERVABILITY_FIELDS = [
    "validation_started_at",
    "validation_completed_at",
    "consumption_started_at",
    "consumption_completed_at",
    "reproduction_started_at",
    "reproduction_completed_at",
    "package_path",
]


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"
