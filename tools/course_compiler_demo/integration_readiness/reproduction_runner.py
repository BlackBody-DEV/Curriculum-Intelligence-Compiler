"""Deterministic reproduction runner for frozen compiler release packages."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from tools.course_compiler_demo.integration_readiness.boundary_evidence import boundary_evidence
from tools.course_compiler_demo.integration_readiness.compare_reproduction import compare_runs
from tools.course_compiler_demo.integration_readiness.models import (
    COMPILER_ROOT,
    CONSUMER_ROOT,
    CONTRACT_ROOT,
    DETERMINISTIC_COMPARISON_FIELDS,
    FIXTURE_EXPECTATIONS,
    FIXTURE_ROOT,
    HARNESS_NAME,
    HARNESS_ROOT,
    HARNESS_VERSION,
    VALIDATOR_ROOT,
    VOLATILE_OBSERVABILITY_FIELDS,
    now_iso,
)
from tools.course_compiler_demo.reference_consumer.consume_release_package import consume_package
from tools.course_compiler_demo.reference_consumer.models import CONSUMER_NAME, CONSUMER_VERSION
from tools.course_compiler_demo.reference_consumer.package_reader import safe_package_root
from tools.course_compiler_demo.release_package.validate.models import VALIDATOR_NAME, VALIDATOR_VERSION
from tools.course_compiler_demo.release_package.validate.package_validator import validate_package


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _reject_path_text(path: Path | str) -> None:
    text = str(path)
    if "adaptive-platform" in text or "AxiomIQ_Alpha2.0" in text:
        raise ValueError("Path must not reference adaptive-platform.")
    if any(part == ".." for part in Path(path).parts):
        raise ValueError("Path must not contain parent traversal.")


def safe_output_dir(output: Path | str | None, package_root: Path | None = None) -> Path | None:
    if output is None:
        return None
    raw = Path(output)
    _reject_path_text(raw)
    resolved = raw.resolve()
    _reject_path_text(resolved)
    if not _inside(resolved, COMPILER_ROOT):
        raise ValueError("Output path must stay inside compiler repository.")
    for forbidden, message in [
        (package_root, "Output path must not overlap input package."),
        (FIXTURE_ROOT, "Output path must not overlap frozen fixture directories."),
        (CONTRACT_ROOT, "Output path must not overlap frozen contract paths."),
        (VALIDATOR_ROOT, "Output path must not overlap frozen validator paths."),
        (CONSUMER_ROOT, "Output path must not overlap frozen consumer paths."),
        (HARNESS_ROOT, "Output path must not overlap harness source paths."),
    ]:
        if forbidden and _inside(resolved, forbidden):
            raise ValueError(message)
    if resolved.exists() and resolved.is_symlink() and not _inside(resolved.resolve(), COMPILER_ROOT):
        raise ValueError("Output symlink must not escape compiler repository.")
    return resolved


def clean_source_state(ignore_lane_g: bool = False) -> str:
    try:
        status = subprocess.run(
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=COMPILER_ROOT,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
    except Exception:
        return "git_state_unavailable"
    if not status:
        return "clean_source_state"
    if ignore_lane_g:
        prefixes = (
            "tools/course_compiler_demo/integration_readiness/",
            "tests/course_compiler_demo/test_integration_readiness_reproduction.py",
            "reports/course_compiler_demo/integration_readiness/reproduction/",
            "docs/course_compiler_demo/integration_readiness/release_qa/",
        )
        current_lane_paths = {
            ".axiomiq/schemas/compiler_release_package_v1.schema.json",
            "docs/course_compiler_demo/internal_release/COMPILER_RELEASE_PACKAGE_EMITTER_v1.md",
            "reports/course_compiler_demo/internal_release/release_package_emitter_proof/VECTOR_COMPONENTS_2D_RELEASE_PACKAGE_V1.md",
            "reports/course_compiler_demo/internal_release/release_package_emitter_proof/vector_components_2d_release_manifest_v1.json",
            "reports/course_compiler_demo/internal_release/release_package_emitter_proof/vector_components_2d_release_package_v1.json",
            "reports/course_compiler_demo/internal_release/release_package_emitter_proof/vector_components_2d_release_validation_v1.json",
            "tests/course_compiler_demo/test_release_package_emitter.py",
            "tools/course_compiler_demo/emit_release_package.py",
            "tools/course_compiler_demo/package/__init__.py",
            "tools/course_compiler_demo/package/release_package_emitter.py",
        }
        paths = [line[3:] for line in status if len(line) > 3]
        if paths and all(path.startswith(prefixes) or path in current_lane_paths for path in paths):
            return "clean_source_state"
    return "dirty_source_state"


def capture_inventory(package_root: Path) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    artifact_digests: dict[str, str] = {}
    for path in sorted(package_root.rglob("*")):
        rel = path.relative_to(package_root).as_posix()
        if path.is_symlink():
            target = os.readlink(path)
            digest = f"symlink:{target}"
            size = 0
        elif path.is_file():
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            size = len(data)
        else:
            continue
        stat = path.lstat()
        files.append(
            {
                "relative_path": rel,
                "sha256": digest,
                "byte_size": size,
                "file_mode": oct(stat.st_mode & 0o777),
                "symlink_target": os.readlink(path) if path.is_symlink() else None,
            }
        )
        if path.is_file() and rel != "manifest.json":
            artifact_digests[rel] = digest
    manifest_path = package_root / "manifest.json"
    manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest() if manifest_path.is_file() else None
    payload = {
        "package_path": str(package_root),
        "file_count": len(files),
        "files": files,
        "manifest_digest": manifest_digest,
        "artifact_digests": artifact_digests,
    }
    payload["input_inventory_digest"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def _verdict_for(
    *,
    fixture_name: str | None,
    validator_verdicts: list[str],
    consumer_verdicts: list[str],
    plan_statuses: list[str],
    comparison: dict[str, Any],
    non_mutation: bool,
) -> tuple[str, list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    if not non_mutation:
        blockers.append("source package mutation detected")
    if comparison["unexpected_differences"]:
        blockers.extend(comparison["unexpected_differences"])
    if len(set(validator_verdicts)) != 1 or len(set(consumer_verdicts)) != 1 or len(set(plan_statuses)) != 1:
        blockers.append("repeat-run verdict drift")
    if fixture_name and fixture_name in FIXTURE_EXPECTATIONS:
        expected_validator, expected_consumer, expected_plan, expected_repro = FIXTURE_EXPECTATIONS[fixture_name]
        if validator_verdicts[0] != expected_validator:
            blockers.append("fixture validator verdict mismatch")
        if consumer_verdicts[0] != expected_consumer:
            blockers.append("fixture consumer verdict mismatch")
        if plan_statuses[0] != expected_plan:
            blockers.append("fixture plan status mismatch")
        if blockers:
            return "not_reproduced", blockers, warnings
        return expected_repro, blockers, warnings
    if blockers:
        return "not_reproduced", blockers, warnings
    if validator_verdicts[0] == "accept_with_warnings":
        return "reproduced_with_expected_warnings", blockers, warnings
    if validator_verdicts[0] == "reject":
        return "reproduced_expected_rejection", blockers, warnings
    return "reproduced", blockers, warnings


def reproduce_package(
    package_root: Path | str,
    *,
    mode: str = "existing_package_reproduction",
    repeat_count: int = 2,
    output_root: Path | None = None,
    require_clean: bool = True,
    fixture_name: str | None = None,
) -> dict[str, Any]:
    started = now_iso()
    if repeat_count < 2:
        return harness_error(package_root, mode, repeat_count, "repeat count must be at least two")
    try:
        package = safe_package_root(package_root)
        safe_output = safe_output_dir(output_root, package) if output_root else None
    except ValueError as exc:
        return harness_error(package_root, mode, repeat_count, str(exc))
    source_state = clean_source_state(ignore_lane_g=True)
    if require_clean and source_state != "clean_source_state":
        return harness_error(package, mode, repeat_count, "compiler worktree is not clean", source_state)

    before = capture_inventory(package)
    run_results = []
    files_read = [str(path) for path in sorted(package.rglob("*")) if path.is_file()]
    for index in range(1, repeat_count + 1):
        validator_result = validate_package(package)
        consumer_result, _plan, _enumeration, _references = consume_package(package)
        run_results.append(
            {
                "run_index": index,
                "validator_result": validator_result,
                "consumer_result": consumer_result,
                "input_inventory": capture_inventory(package),
            }
        )
    after = capture_inventory(package)
    non_mutation = before == after
    comparison = compare_runs(run_results)
    first_consumer = run_results[0]["consumer_result"]
    validator_verdicts = [run["validator_result"]["overall_verdict"] for run in run_results]
    consumer_verdicts = [run["consumer_result"]["consumer_verdict"] for run in run_results]
    plan_statuses = [run["consumer_result"]["dry_run_plan_status"] for run in run_results]
    repro_verdict, blockers, warnings = _verdict_for(
        fixture_name=fixture_name,
        validator_verdicts=validator_verdicts,
        consumer_verdicts=consumer_verdicts,
        plan_statuses=plan_statuses,
        comparison=comparison,
        non_mutation=non_mutation,
    )
    expected = FIXTURE_EXPECTATIONS.get(fixture_name or "", (None, None, None, None))
    evidence = boundary_evidence(
        allowed_output_root=safe_output,
        commands_executed=["python-interface:validate_package", "python-interface:consume_package"],
        files_read=files_read,
        files_written=[],
        environment_names=[],
    )
    evidence["source_package_modified"] = not non_mutation
    return {
        "harness_name": HARNESS_NAME,
        "harness_version": HARNESS_VERSION,
        "mode": mode,
        "input_type": "frozen_fixture" if fixture_name else "compiler_side_package",
        "package_path": str(package),
        "package_id": first_consumer.get("package_id"),
        "package_contract": first_consumer.get("package_contract"),
        "package_version": first_consumer.get("package_version"),
        "repeat_count": repeat_count,
        "input_inventory_digest": before["input_inventory_digest"],
        "input_artifact_digests": before["artifact_digests"],
        "validator_name": VALIDATOR_NAME,
        "validator_version": VALIDATOR_VERSION,
        "consumer_name": CONSUMER_NAME,
        "consumer_version": CONSUMER_VERSION,
        "run_results": run_results,
        "expected_validator_verdict": expected[0],
        "actual_validator_verdicts": validator_verdicts,
        "expected_consumer_verdict": expected[1],
        "actual_consumer_verdicts": consumer_verdicts,
        "expected_plan_status": expected[2],
        "actual_plan_statuses": plan_statuses,
        "deterministic_fields_compared": DETERMINISTIC_COMPARISON_FIELDS,
        "volatile_fields_excluded": VOLATILE_OBSERVABILITY_FIELDS,
        "manifest_digest_match": comparison["manifest_digest_match"],
        "artifact_digest_match": comparison["artifact_digest_match"],
        "artifact_order_match": comparison["artifact_order_match"],
        "dependency_order_match": comparison["dependency_order_match"],
        "reference_resolution_match": comparison["reference_resolution_match"],
        "error_order_match": comparison["error_order_match"],
        "warning_order_match": comparison["warning_order_match"],
        "package_non_mutation_confirmed": non_mutation,
        "boundary_evidence": evidence,
        "clean_state": source_state,
        "reproduction_verdict": repro_verdict,
        "blockers": blockers,
        "warnings": warnings,
        "reproduction_started_at": started,
        "reproduction_completed_at": now_iso(),
    }


def harness_error(package_root: Path | str, mode: str, repeat_count: int, message: str, source_state: str = "git_state_unavailable") -> dict[str, Any]:
    return {
        "harness_name": HARNESS_NAME,
        "harness_version": HARNESS_VERSION,
        "mode": mode,
        "input_type": "unknown",
        "package_path": str(package_root),
        "package_id": None,
        "package_contract": None,
        "package_version": None,
        "repeat_count": repeat_count,
        "input_inventory_digest": None,
        "input_artifact_digests": {},
        "validator_name": VALIDATOR_NAME,
        "validator_version": VALIDATOR_VERSION,
        "consumer_name": CONSUMER_NAME,
        "consumer_version": CONSUMER_VERSION,
        "run_results": [],
        "expected_validator_verdict": None,
        "actual_validator_verdicts": [],
        "expected_consumer_verdict": None,
        "actual_consumer_verdicts": [],
        "expected_plan_status": None,
        "actual_plan_statuses": [],
        "deterministic_fields_compared": DETERMINISTIC_COMPARISON_FIELDS,
        "volatile_fields_excluded": VOLATILE_OBSERVABILITY_FIELDS,
        "manifest_digest_match": False,
        "artifact_digest_match": False,
        "artifact_order_match": False,
        "dependency_order_match": False,
        "reference_resolution_match": False,
        "error_order_match": False,
        "warning_order_match": False,
        "package_non_mutation_confirmed": False,
        "boundary_evidence": boundary_evidence(allowed_output_root=None, commands_executed=[], files_read=[], files_written=[]),
        "clean_state": source_state,
        "reproduction_verdict": "harness_error",
        "blockers": [message],
        "warnings": [],
    }


def future_generated_package_reproduction(repeat_count: int = 2) -> dict[str, Any]:
    return {
        "harness_name": HARNESS_NAME,
        "harness_version": HARNESS_VERSION,
        "mode": "future_generated_package_reproduction",
        "generation_status": "unavailable_real_source_pipeline_pending",
        "real_source_generation_available": False,
        "real_source_blocker": "no approved real Statics source and generator output",
        "repeat_count": repeat_count,
        "boundary_evidence": boundary_evidence(allowed_output_root=None, commands_executed=[], files_read=[], files_written=[]),
        "reproduction_verdict": "generation_unavailable",
        "blockers": ["no approved real Statics source and generator output"],
        "warnings": ["REAL_SOURCE_REPRODUCTION_NOT_RUN", "COMPILER_INTEGRATION_READINESS_NOT_YET_CONFIRMED"],
    }


def fixture_matrix(repeat_count: int = 2, output_root: Path | None = None, require_clean: bool = True) -> dict[str, Any]:
    results = {}
    for fixture in FIXTURE_EXPECTATIONS:
        package = FIXTURE_ROOT / fixture
        out = output_root / fixture if output_root else None
        results[fixture] = reproduce_package(
            package,
            mode="fixture_reproduction",
            repeat_count=repeat_count,
            output_root=out,
            require_clean=require_clean,
            fixture_name=fixture,
        )
    verdicts = {name: item["reproduction_verdict"] for name, item in results.items()}
    ok = all(
        verdict in {"reproduced", "reproduced_with_expected_warnings", "reproduced_expected_rejection"}
        for verdict in verdicts.values()
    )
    evidence = boundary_evidence(
        allowed_output_root=output_root,
        commands_executed=["fixture_matrix"],
        files_read=[],
        files_written=[],
    )
    return {
        "harness_name": HARNESS_NAME,
        "harness_version": HARNESS_VERSION,
        "mode": "fixture_reproduction",
        "repeat_count": repeat_count,
        "fixture_results": results,
        "fixture_verdicts": verdicts,
        "matrix_status": "HARNESS_REPRODUCTION_CONFIRMED" if ok else "HARNESS_REPRODUCTION_NOT_CONFIRMED",
        "real_source_status": "REAL_SOURCE_REPRODUCTION_NOT_RUN",
        "integration_readiness_status": "COMPILER_INTEGRATION_READINESS_NOT_YET_CONFIRMED",
        "boundary_evidence": evidence,
        "reproduction_verdict": "reproduced" if ok else "not_reproduced",
        "blockers": [] if ok else ["fixture reproduction mismatch"],
    }
