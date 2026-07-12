#!/usr/bin/env python3
"""Validate docs-only compiler task contracts.

This checker is intentionally small and local. It validates contract shape and
docs-only safety constraints, but it does not execute contract actions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL_FIELDS = {
    "task_id",
    "repository",
    "risk_class",
    "baseline",
    "policy_refs",
    "allowed_paths",
    "actions",
    "source_snapshot",
    "safety_flags",
    "report",
}

REQUIRED_BASELINE_FIELDS = {"mode", "expected_head", "branch"}
REQUIRED_SOURCE_SNAPSHOT_FIELDS = {"snapshot_id", "source_type", "live_alpha_access"}
REQUIRED_REPORT_FIELDS = {"required", "format", "recommended_next_task"}

REQUIRED_SAFETY_FLAGS = {
    "allow_alpha_write",
    "allow_adaptive_platform_write",
    "allow_database_contact",
    "allow_canonical_promotion",
    "allow_student_visible_output",
    "allow_live_deployable_output",
    "allow_ocr",
    "allow_parser_implementation",
    "allow_dependency_addition",
    "allow_mvp_tag_move",
}

ALLOWED_ACTIONS = {
    "create_or_update_files",
    "validate",
    "commit",
    "push",
    "audit",
    "closeout",
}

ALLOWED_PATH_PREFIXES = (
    "docs/course_compiler_demo/",
    "reports/course_compiler_demo/",
    ".axiomiq/policies/",
    ".axiomiq/schemas/",
    ".axiomiq/task_contracts/",
)

ALLOWED_PATH_SUFFIXES = (".md", ".yaml", ".json")


class ContractValidationError(Exception):
    """Raised when a contract fails docs-only validation."""


def _expect_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractValidationError(f"{label} must be an object")
    return value


def _expect_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ContractValidationError(f"{label} must be a non-empty list")
    if not all(isinstance(item, str) and item for item in value):
        raise ContractValidationError(f"{label} must contain only non-empty strings")
    return value


def _check_required_fields(data: dict[str, Any]) -> None:
    missing = REQUIRED_TOP_LEVEL_FIELDS - data.keys()
    if missing:
        raise ContractValidationError(f"missing required top-level fields: {sorted(missing)}")

    baseline = _expect_mapping(data["baseline"], "baseline")
    missing_baseline = REQUIRED_BASELINE_FIELDS - baseline.keys()
    if missing_baseline:
        raise ContractValidationError(f"missing baseline fields: {sorted(missing_baseline)}")

    source_snapshot = _expect_mapping(data["source_snapshot"], "source_snapshot")
    missing_source = REQUIRED_SOURCE_SNAPSHOT_FIELDS - source_snapshot.keys()
    if missing_source:
        raise ContractValidationError(f"missing source_snapshot fields: {sorted(missing_source)}")

    report = _expect_mapping(data["report"], "report")
    missing_report = REQUIRED_REPORT_FIELDS - report.keys()
    if missing_report:
        raise ContractValidationError(f"missing report fields: {sorted(missing_report)}")

    safety_flags = _expect_mapping(data["safety_flags"], "safety_flags")
    missing_flags = REQUIRED_SAFETY_FLAGS - safety_flags.keys()
    if missing_flags:
        raise ContractValidationError(f"missing safety flags: {sorted(missing_flags)}")


def _check_docs_only_identity(data: dict[str, Any]) -> None:
    if data.get("repository") != "Curriculum-Intelligence-Compiler":
        raise ContractValidationError("repository must be Curriculum-Intelligence-Compiler")
    if data.get("risk_class") != "docs_only":
        raise ContractValidationError("risk_class must be docs_only")

    policy_refs = _expect_string_list(data.get("policy_refs"), "policy_refs")
    if "compiler_non_live_v1" not in policy_refs:
        raise ContractValidationError("policy_refs must include compiler_non_live_v1")

    source_snapshot = _expect_mapping(data.get("source_snapshot"), "source_snapshot")
    if source_snapshot.get("live_alpha_access") != "forbidden":
        raise ContractValidationError("source_snapshot.live_alpha_access must be forbidden")


def _check_safety_flags(data: dict[str, Any]) -> None:
    safety_flags = _expect_mapping(data.get("safety_flags"), "safety_flags")
    for flag in sorted(REQUIRED_SAFETY_FLAGS):
        if safety_flags.get(flag) is not False:
            raise ContractValidationError(f"{flag} must be false")


def _check_allowed_paths(data: dict[str, Any]) -> None:
    allowed_paths = _expect_string_list(data.get("allowed_paths"), "allowed_paths")
    for path in allowed_paths:
        if path.startswith("/") or ".." in Path(path).parts:
            raise ContractValidationError(f"allowed path is not repository-relative and safe: {path}")
        if not path.startswith(ALLOWED_PATH_PREFIXES):
            raise ContractValidationError(f"allowed path outside docs-only compiler scope: {path}")
        if not path.endswith(ALLOWED_PATH_SUFFIXES):
            raise ContractValidationError(f"allowed path must be md, yaml, or json: {path}")


def _check_actions(data: dict[str, Any]) -> None:
    actions = set(_expect_string_list(data.get("actions"), "actions"))
    unexpected = actions - ALLOWED_ACTIONS
    if unexpected:
        raise ContractValidationError(f"actions are not docs-only safe: {sorted(unexpected)}")

    if "validate" not in actions:
        raise ContractValidationError("actions must include validate")


def _check_report(data: dict[str, Any]) -> None:
    report = _expect_mapping(data.get("report"), "report")
    if report.get("required") is not True:
        raise ContractValidationError("report.required must be true")
    if report.get("format") not in {
        "codex_task_report",
        "codex_commit_report",
        "codex_push_report",
        "codex_readiness_audit_report",
    }:
        raise ContractValidationError("report.format is not supported")
    if not isinstance(report.get("recommended_next_task"), str) or not report["recommended_next_task"]:
        raise ContractValidationError("report.recommended_next_task must be a non-empty string")


def load_contract(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ContractValidationError(f"invalid JSON: {exc}") from exc
    except OSError as exc:
        raise ContractValidationError(f"unable to read contract: {exc}") from exc

    return _expect_mapping(data, "contract")


def validate_contract(path: Path) -> list[str]:
    data = load_contract(path)
    _check_required_fields(data)
    _check_docs_only_identity(data)
    _check_safety_flags(data)
    _check_allowed_paths(data)
    _check_actions(data)
    _check_report(data)
    return [
        "valid JSON",
        "required fields present",
        "docs_only risk class",
        "compiler_non_live_v1 policy ref",
        "live Alpha access forbidden",
        "safety flags false",
        "allowed paths docs-only scoped",
        "actions docs-only safe",
        "report model present",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a docs-only compiler task contract.")
    parser.add_argument("contract", type=Path, help="Path to the docs-only contract JSON file.")
    args = parser.parse_args(argv)

    try:
        checks = validate_contract(args.contract)
    except ContractValidationError as exc:
        print(f"DOCS_ONLY_CONTRACT_INVALID: {exc}", file=sys.stderr)
        return 1

    print("DOCS_ONLY_CONTRACT_VALID")
    for check in checks:
        print(f"- {check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
