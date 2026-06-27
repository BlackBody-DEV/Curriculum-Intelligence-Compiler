"""Lightweight validation for Course Compiler Demo outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from validate.package_validator import (
    validate_performance_tracking_package,
    validate_practice_assessment_package,
    validate_practice_module_package,
)


REQUIRED_JSON_FILES = [
    "source_document.json",
    "source_interpretation.json",
    "source_feature_flags.json",
    "curriculum_extraction_package.json",
    "topic_candidates.json",
    "micro_skill_candidates.json",
    "practice_targets.json",
    "assessment_targets.json",
    "performance_tracking_targets.json",
    "content_gaps.json",
    "practice_module_package.json",
    "practice_assessment_package.json",
    "performance_tracking_package.json",
]

REQUIRED_REPORT_FILES = [
    "content_gap_report.md",
    "demo_report.md",
    "validation_report.json",
]


def _read_json(output_dir: Path, filename: str, errors: list[str]) -> dict[str, Any] | None:
    path = output_dir / filename
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{filename} invalid JSON: {exc}")
    except FileNotFoundError:
        errors.append(f"{filename} missing")
    return None


def validate_outputs(output_dir: Path) -> dict[str, Any]:
    files_checked = REQUIRED_JSON_FILES + REQUIRED_REPORT_FILES
    missing_files = [name for name in files_checked if not (output_dir / name).exists()]
    required_field_errors: list[str] = []
    warnings: list[str] = []
    parsed: dict[str, dict[str, Any]] = {}

    for name in REQUIRED_JSON_FILES:
        data = _read_json(output_dir, name, required_field_errors)
        if data is not None:
            parsed[name] = data

    demo_label_failures = [
        name
        for name, data in parsed.items()
        if data.get("status") != "demo_unverified"
    ]
    if demo_label_failures:
        required_field_errors.append(
            f"Top-level demo_unverified status missing: {demo_label_failures}"
        )

    source_ids = {
        data.get("source_id")
        for data in parsed.values()
        if isinstance(data, dict) and data.get("source_id")
    }
    if len(source_ids) > 1:
        required_field_errors.append(f"source_id mismatch across outputs: {sorted(source_ids)}")

    _check_collection(parsed, "topic_candidates.json", "topic_candidates", required_field_errors)
    _check_collection(parsed, "micro_skill_candidates.json", "micro_skill_candidates", required_field_errors)
    _check_collection(parsed, "practice_targets.json", "practice_target_candidates", required_field_errors)
    _check_collection(parsed, "assessment_targets.json", "assessment_target_candidates", required_field_errors)
    _check_collection(parsed, "performance_tracking_targets.json", "performance_tracking_targets", required_field_errors)
    gaps = parsed.get("content_gaps.json", {}).get("content_gaps", [])
    no_gap = parsed.get("content_gaps.json", {}).get("no_gap_statement")
    if not gaps and not no_gap:
        required_field_errors.append("content_gaps.json requires content_gaps or no_gap_statement")

    if "practice_module_package.json" in parsed:
        required_field_errors.extend(
            validate_practice_module_package(parsed["practice_module_package.json"])
        )
    if "practice_assessment_package.json" in parsed:
        required_field_errors.extend(
            validate_practice_assessment_package(parsed["practice_assessment_package.json"])
        )
    if "performance_tracking_package.json" in parsed:
        required_field_errors.extend(
            validate_performance_tracking_package(parsed["performance_tracking_package.json"])
        )

    forbidden_outputs = [
        "live_export.json",
        "operational_alpha_update.json",
    ]
    stage_boundary_present = [name for name in forbidden_outputs if (output_dir / name).exists()]
    if stage_boundary_present:
        required_field_errors.append(f"Forbidden output files present: {stage_boundary_present}")

    if not required_field_errors and not warnings:
        overall_result = "pass"
        validation_status = "completed"
    elif not required_field_errors:
        overall_result = "pass_with_warnings"
        validation_status = "completed_with_warnings"
    else:
        overall_result = "fail"
        validation_status = "failed"

    return {
        "status": "demo_unverified",
        "validation_status": validation_status,
        "files_checked": files_checked,
        "missing_files": missing_files,
        "required_field_errors": required_field_errors,
        "warnings": warnings,
        "forbidden_zone_check": {
            "backend_app_touched": False,
            "frontend_src_touched": False,
            "operational_alpha_touched": False,
            "notes": "Validation inspected demo output files only.",
            "status": "demo_unverified",
        },
        "demo_label_check": {
            "top_level_status_required": "demo_unverified",
            "failures": demo_label_failures,
            "passed": not demo_label_failures,
            "status": "demo_unverified",
        },
        "db_contact_check": {
            "db_contact_performed": False,
            "status": "demo_unverified",
        },
        "stage_boundary_check": {
            "validation_report_generated": True,
            "demo_report_generated": (output_dir / "demo_report.md").exists(),
            "content_gap_report_generated": (output_dir / "content_gap_report.md").exists(),
            "live_or_operational_outputs_present": stage_boundary_present,
            "status": "demo_unverified",
        },
        "overall_result": overall_result,
    }


def _check_collection(
    parsed: dict[str, dict[str, Any]],
    filename: str,
    field: str,
    errors: list[str],
) -> None:
    if not parsed.get(filename, {}).get(field):
        errors.append(f"{filename} missing non-empty {field}")
