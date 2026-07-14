"""Generate non-operational dry-run integration plans."""

from __future__ import annotations

from typing import Any

from tools.course_compiler_demo.reference_consumer.models import (
    ARTIFACT_GROUPS,
    FUTURE_DESTINATION_CAPABILITIES,
    PROHIBITED_OPERATIONS,
)


def build_dry_run_plan(
    *,
    manifest: dict[str, Any],
    validator_result: dict[str, Any],
    dependency_order: list[str],
    classified_artifacts: list[dict[str, Any]],
    compatibility_warnings: list[str],
) -> dict[str, Any]:
    by_id = {item["artifact_id"]: item for item in classified_artifacts}
    groups: dict[str, list[str]] = {group: [] for group in ARTIFACT_GROUPS}
    groups.setdefault("non_importable_metadata", [])
    for artifact_id in dependency_order:
        artifact_type = by_id[artifact_id]["artifact_type"]
        placed = False
        for group, types in ARTIFACT_GROUPS.items():
            if artifact_type in types:
                groups[group].append(artifact_id)
                placed = True
                break
        if not placed:
            groups["non_importable_metadata"].append(artifact_id)

    plan_status = (
        "generated_with_warnings"
        if validator_result.get("overall_verdict") == "accept_with_warnings"
        else "generated"
    )
    return {
        "plan_id": f"DRY_RUN_PLAN_{manifest.get('package_id')}",
        "package_id": manifest.get("package_id"),
        "plan_status": plan_status,
        "package_contract": manifest.get("package_contract"),
        "package_version": manifest.get("package_version"),
        "source_validation_summary": {
            "validator_name": validator_result.get("validator_name"),
            "validator_version": validator_result.get("validator_version"),
            "validator_verdict": validator_result.get("overall_verdict"),
            "errors": len(validator_result.get("errors", [])),
            "warnings": len(validator_result.get("warnings", [])),
        },
        "artifact_processing_order": dependency_order,
        "artifact_groups": groups,
        "review_gates": [
            "human review required before protected integration review",
            "preserve review_pending and human_review_required state",
            "block canonical or student-visible activation",
        ],
        "known_gaps": manifest.get("known_gaps", []),
        "compatibility_warnings": compatibility_warnings,
        "required_future_destination_capabilities": FUTURE_DESTINATION_CAPABILITIES,
        "prohibited_operations": PROHIBITED_OPERATIONS,
        "rollback_expectations": [
            "future importer must provide transaction or rollback boundary",
            "this dry-run plan performs no destination writes",
        ],
        "boundary_statement": "Offline planning evidence only; no adaptive-platform, database, runtime, learner-state, canonical, or student-visible operation was performed.",
    }
