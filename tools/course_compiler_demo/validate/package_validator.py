"""Minimal package validation helpers for demo artifacts."""

from __future__ import annotations

from typing import Any


def validate_demo_package(package: dict[str, Any], required_fields: list[str]) -> None:
    missing = [field for field in required_fields if field not in package]
    if missing:
        raise ValueError(f"Package missing required fields: {missing}")
    if package.get("status") != "demo_unverified":
        raise ValueError("Package must use status demo_unverified.")


def validate_practice_module_package(package: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "package_id",
        "status",
        "source_context",
        "target_curriculum",
        "practice_sequence",
        "difficulty_plan",
        "readiness_condition",
        "performance_metrics",
    ]
    errors.extend(_missing_fields(package, required, "practice_module_package"))
    if package.get("status") != "demo_unverified":
        errors.append("practice_module_package status must be demo_unverified")
    curriculum = package.get("target_curriculum", {})
    if not curriculum.get("topics"):
        errors.append("practice_module_package target_curriculum topics missing")
    if not curriculum.get("micro_skills"):
        errors.append("practice_module_package target_curriculum micro_skills missing")
    if not package.get("content_gaps") and not package.get("limitations"):
        errors.append("practice_module_package requires content_gaps or limitations")
    return errors


def validate_practice_assessment_package(package: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "package_id",
        "status",
        "source_context",
        "target_goal",
        "covered_curriculum",
        "assessment_blueprint",
        "assessment_items",
        "scoring_policy",
        "weakness_detection_rules",
        "recommended_next_actions",
    ]
    errors.extend(_missing_fields(package, required, "practice_assessment_package"))
    if package.get("status") != "demo_unverified":
        errors.append("practice_assessment_package status must be demo_unverified")
    curriculum = package.get("covered_curriculum", {})
    if not curriculum.get("topics"):
        errors.append("practice_assessment_package covered_curriculum topics missing")
    if not curriculum.get("micro_skills"):
        errors.append("practice_assessment_package covered_curriculum micro_skills missing")
    return errors


def validate_performance_tracking_package(package: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = [
        "package_id",
        "status",
        "source_context",
        "tracked_curriculum",
        "linked_packages",
        "attempt_record_schema",
        "metric_definitions",
        "readiness_model",
        "weakness_detection_model",
        "recommended_next_action_model",
        "computed_demo_results",
    ]
    errors.extend(_missing_fields(package, required, "performance_tracking_package"))
    if package.get("status") != "demo_unverified":
        errors.append("performance_tracking_package status must be demo_unverified")
    curriculum = package.get("tracked_curriculum", {})
    if not curriculum.get("topics"):
        errors.append("performance_tracking_package tracked_curriculum topics missing")
    if not curriculum.get("micro_skills"):
        errors.append("performance_tracking_package tracked_curriculum micro_skills missing")
    linked = package.get("linked_packages", {})
    if "PM_DEMO_001" not in linked.get("practice_module_package_ids", []):
        errors.append("performance_tracking_package missing PM_DEMO_001 link")
    if "PA_DEMO_001" not in linked.get("practice_assessment_package_ids", []):
        errors.append("performance_tracking_package missing PA_DEMO_001 link")
    return errors


def _missing_fields(package: dict[str, Any], fields: list[str], label: str) -> list[str]:
    return [f"{label} missing {field}" for field in fields if field not in package]
