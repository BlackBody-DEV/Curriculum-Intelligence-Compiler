"""CLI and Python interface for the offline compiler package consumer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.course_compiler_demo.reference_consumer.artifact_classifier import classify_artifact
from tools.course_compiler_demo.reference_consumer.dry_run_planner import build_dry_run_plan
from tools.course_compiler_demo.reference_consumer.models import (
    ACCEPTED_VALIDATOR_VERDICTS,
    BOUNDARY_EVIDENCE,
    COMPILER_ROOT,
    CONSUMER_ERROR_PLAN,
    CONSUMER_NAME,
    CONSUMER_VERSION,
    REJECTED_PLAN,
    canonical_json,
    now_iso,
)
from tools.course_compiler_demo.reference_consumer.package_reader import (
    load_artifact_payload,
    load_manifest,
    safe_output_dir,
    safe_package_root,
)
from tools.course_compiler_demo.reference_consumer.reference_resolver import (
    dependency_order,
    resolve_references,
)
from tools.course_compiler_demo.release_package.manifest.integrity import sha256_file
from tools.course_compiler_demo.release_package.validate.package_validator import validate_package
from tools.course_compiler_demo.release_package.validate.models import (
    VALIDATOR_NAME,
    VALIDATOR_VERSION,
)


ALLOWED_OUTPUT_FILES = {
    "consumer_result.json",
    "consumer_report.md",
    "dry_run_import_plan.json",
    "artifact_enumeration.json",
    "reference_resolution.json",
}


def _base_result(package_path: Path | str, started_at: str) -> dict[str, Any]:
    return {
        "consumer_name": CONSUMER_NAME,
        "consumer_version": CONSUMER_VERSION,
        "package_path": str(package_path),
        "package_id": None,
        "package_contract": None,
        "package_version": None,
        "validator_name": VALIDATOR_NAME,
        "validator_version": VALIDATOR_VERSION,
        "validator_verdict": "not_run",
        "consumer_verdict": "consumer_error",
        "consumption_started_at": started_at,
        "consumption_completed_at": now_iso(),
        "manifest_loaded": False,
        "artifact_count": 0,
        "artifact_type_counts": {},
        "declared_artifacts": [],
        "resolved_references": [],
        "unresolved_references": [],
        "dependency_order": [],
        "importable_artifacts": [],
        "review_only_artifacts": [],
        "non_importable_artifacts": [],
        "compatibility_warnings": [],
        "known_gaps": [],
        "dry_run_plan_status": CONSUMER_ERROR_PLAN,
        "boundary_evidence": dict(BOUNDARY_EVIDENCE),
        "errors": [],
        "warnings": [],
    }


def _error_result(package_path: Path | str, started_at: str, message: str) -> dict[str, Any]:
    result = _base_result(package_path, started_at)
    result["errors"] = [{"rule_id": "CONSUMER_INPUT", "message": message}]
    result["consumption_completed_at"] = now_iso()
    return result


def _artifact_counts(artifacts: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for artifact in artifacts:
        kind = artifact.get("artifact_type", "unknown")
        counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))


def _resolution_status(artifact_id: str, unresolved: list[dict[str, Any]]) -> str:
    return "unresolved" if any(item["origin"] == artifact_id for item in unresolved) else "resolved"


def _compatibility_warnings(manifest: dict[str, Any], validator_result: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if manifest.get("known_gaps"):
        warnings.append("known non-blocking content gaps")
    if not manifest.get("asset_artifact_ids"):
        warnings.append("optional assets absent")
    if manifest.get("review_status") == "human_review_required":
        warnings.append("human review outstanding")
    if manifest.get("promotion_recommendation") == "hold_for_human_review":
        warnings.append("promotion recommendation on hold")
    known_types = {
        "source_metadata",
        "source_interpretation",
        "curriculum_extraction",
        "procedure_candidate",
        "question_candidate",
        "generation_family_candidate",
        "signal_mapping",
        "performance_tracking_target",
        "review_record",
        "validation_report",
        "asset_reference",
        "known_gap_report",
    }
    unsupported = sorted(
        {
            item.get("artifact_type")
            for item in manifest.get("artifact_inventory", [])
            if item.get("artifact_type") not in known_types
        }
    )
    if unsupported:
        warnings.append(f"unsupported optional artifact types: {', '.join(unsupported)}")
    if validator_result.get("warnings"):
        warnings.append("validator warnings preserved")
    warnings.append("future destination mapping required")
    return sorted(set(warnings))


def _enumerate_artifacts(
    package_root: Path,
    manifest: dict[str, Any],
    unresolved: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for descriptor in sorted(manifest.get("artifact_inventory", []), key=lambda item: item.get("artifact_id", "")):
        path = package_root / str(descriptor.get("relative_path", ""))
        classification, reason = classify_artifact(descriptor)
        checksum_verified = path.is_file() and descriptor.get("sha256") == sha256_file(path)
        byte_size_verified = path.is_file() and descriptor.get("byte_size") == len(path.read_bytes())
        artifacts.append(
            {
                "artifact_id": descriptor.get("artifact_id"),
                "artifact_type": descriptor.get("artifact_type"),
                "relative_path": descriptor.get("relative_path"),
                "status": descriptor.get("status"),
                "required": descriptor.get("required"),
                "source_reference_ids": sorted(descriptor.get("source_reference_ids", [])),
                "depends_on_artifact_ids": sorted(descriptor.get("depends_on_artifact_ids", [])),
                "checksum_verified": checksum_verified,
                "byte_size_verified": byte_size_verified,
                "reference_resolution_status": _resolution_status(descriptor.get("artifact_id", ""), unresolved),
                "consumer_classification": classification,
                "classification_reason": reason,
            }
        )
    return artifacts


def consume_package(package_root: Path | str) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any], dict[str, Any]]:
    started_at = now_iso()
    try:
        safe_package = safe_package_root(package_root)
    except ValueError as exc:
        return _error_result(package_root, started_at, str(exc)), None, {"artifacts": []}, {"resolved": [], "unresolved": []}

    result = _base_result(safe_package, started_at)
    validator_result = validate_package(safe_package)
    result["validator_verdict"] = validator_result.get("overall_verdict", "validator_error")
    result["warnings"] = list(validator_result.get("warnings", []))
    result["errors"] = list(validator_result.get("errors", []))

    if result["validator_verdict"] not in ACCEPTED_VALIDATOR_VERDICTS:
        result.update(
            {
                "package_id": validator_result.get("package_id"),
                "package_contract": validator_result.get("package_contract"),
                "package_version": validator_result.get("package_version"),
                "consumer_verdict": "consumer_error"
                if result["validator_verdict"] == "validator_error"
                else "rejected_without_plan",
                "dry_run_plan_status": CONSUMER_ERROR_PLAN
                if result["validator_verdict"] == "validator_error"
                else REJECTED_PLAN,
                "consumption_completed_at": now_iso(),
            }
        )
        return result, None, {"artifacts": []}, {"resolved": [], "unresolved": []}

    try:
        manifest = load_manifest(safe_package)
    except Exception as exc:
        result["errors"].append({"rule_id": "MANIFEST_LOAD", "message": str(exc)})
        result["consumer_verdict"] = "consumer_error"
        result["dry_run_plan_status"] = CONSUMER_ERROR_PLAN
        result["consumption_completed_at"] = now_iso()
        return result, None, {"artifacts": []}, {"resolved": [], "unresolved": []}

    payloads = {
        item["artifact_id"]: load_artifact_payload(safe_package, item)
        for item in manifest.get("artifact_inventory", [])
    }
    resolved, unresolved = resolve_references(manifest, payloads)
    order, has_cycle = dependency_order(manifest)
    artifacts = _enumerate_artifacts(safe_package, manifest, unresolved)
    warnings = _compatibility_warnings(manifest, validator_result)
    dry_run_plan = None
    if has_cycle:
        result["errors"].append({"rule_id": "DEPENDENCY_ORDER", "message": "Dependency cycle detected."})
        result["consumer_verdict"] = "rejected_without_plan"
        result["dry_run_plan_status"] = REJECTED_PLAN
    else:
        dry_run_plan = build_dry_run_plan(
            manifest=manifest,
            validator_result=validator_result,
            dependency_order=order,
            classified_artifacts=artifacts,
            compatibility_warnings=warnings,
        )
        result["consumer_verdict"] = (
            "accepted_for_offline_planning_with_warnings"
            if result["validator_verdict"] == "accept_with_warnings"
            else "accepted_for_offline_planning"
        )
        result["dry_run_plan_status"] = dry_run_plan["plan_status"]

    importable = [
        item["artifact_id"]
        for item in artifacts
        if item["consumer_classification"] == "future_integration_candidate"
    ]
    review_only = [
        item["artifact_id"]
        for item in artifacts
        if item["consumer_classification"] in {"review_record", "validation_evidence", "known_gap_record"}
    ]
    non_importable = [
        item["artifact_id"]
        for item in artifacts
        if item["artifact_id"] not in set(importable + review_only)
    ]
    result.update(
        {
            "package_id": manifest.get("package_id"),
            "package_contract": manifest.get("package_contract"),
            "package_version": manifest.get("package_version"),
            "manifest_loaded": True,
            "artifact_count": len(artifacts),
            "artifact_type_counts": _artifact_counts(artifacts),
            "declared_artifacts": artifacts,
            "resolved_references": resolved,
            "unresolved_references": unresolved,
            "dependency_order": order if not has_cycle else [],
            "importable_artifacts": sorted(importable),
            "review_only_artifacts": sorted(review_only),
            "non_importable_artifacts": sorted(non_importable),
            "compatibility_warnings": warnings,
            "known_gaps": manifest.get("known_gaps", []),
            "consumption_completed_at": now_iso(),
        }
    )
    enumeration = {"package_id": result["package_id"], "artifacts": artifacts}
    references = {"package_id": result["package_id"], "resolved": resolved, "unresolved": unresolved}
    return result, dry_run_plan, enumeration, references


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Consume a portable compiler release package offline.")
    parser.add_argument("--package", required=True, help="Package root containing manifest.json")
    parser.add_argument("--output", help="Compiler-owned output directory")
    parser.add_argument("--no-write", action="store_true", help="Print JSON result and write no files")
    return parser.parse_args()


def _report_markdown(result: dict[str, Any], plan: dict[str, Any] | None) -> str:
    lines = [
        f"# {CONSUMER_NAME} Report",
        "",
        f"- package_id: {result.get('package_id')}",
        f"- validator_verdict: {result.get('validator_verdict')}",
        f"- consumer_verdict: {result.get('consumer_verdict')}",
        f"- dry_run_plan_status: {result.get('dry_run_plan_status')}",
        f"- artifact_count: {result.get('artifact_count')}",
        "",
    ]
    if result.get("consumer_verdict") == "rejected_without_plan":
        lines.extend([
            "fixture-only rejection evidence",
            "no dry-run integration plan authorized",
            "",
        ])
    if result.get("compatibility_warnings"):
        lines.extend(["## Compatibility Warnings", ""])
        lines.extend(f"- {warning}" for warning in result["compatibility_warnings"])
        lines.append("")
    if plan:
        lines.extend(["## Boundary Statement", "", plan["boundary_statement"], ""])
    return "\n".join(lines)


def write_reports(
    output_dir: Path,
    result: dict[str, Any],
    plan: dict[str, Any] | None,
    enumeration: dict[str, Any],
    references: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "consumer_result.json": result,
        "artifact_enumeration.json": enumeration,
        "reference_resolution.json": references,
    }
    if plan is not None:
        files["dry_run_import_plan.json"] = plan
    elif result.get("consumer_verdict") == "rejected_without_plan":
        files["dry_run_import_plan.json"] = {"plan_status": REJECTED_PLAN}
    for name, payload in files.items():
        if name not in ALLOWED_OUTPUT_FILES:
            raise ValueError(f"Unexpected output file requested: {name}")
        (output_dir / name).write_text(canonical_json(payload))
    (output_dir / "consumer_report.md").write_text(_report_markdown(result, plan))


def main() -> int:
    args = parse_args()
    result, plan, enumeration, references = consume_package(args.package)
    if args.no_write:
        print(canonical_json(result), end="")
        return 0 if result["consumer_verdict"].startswith("accepted_for_offline_planning") else 1

    try:
        package = safe_package_root(args.package)
        output = safe_output_dir(args.output, package)
    except ValueError as exc:
        error = _error_result(args.package, now_iso(), str(exc))
        print(canonical_json(error), end="")
        return 2
    if output is None:
        print(canonical_json(result), end="")
        return 0 if result["consumer_verdict"].startswith("accepted_for_offline_planning") else 1
    write_reports(output, result, plan, enumeration, references)
    print(canonical_json(result), end="")
    return 0 if result["consumer_verdict"].startswith("accepted_for_offline_planning") else 1


if __name__ == "__main__":
    raise SystemExit(main())
