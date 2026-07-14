import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

import tools.course_compiler_demo.reference_consumer.consume_release_package as consumer_module
from tools.course_compiler_demo.reference_consumer.consume_release_package import (
    consume_package,
    safe_output_dir,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tools/course_compiler_demo/release_package/golden_packages"
CLI = "tools.course_compiler_demo.reference_consumer.consume_release_package"
EXPECTED = {
    "minimal_valid": ("accept", "accepted_for_offline_planning", "generated"),
    "normal_multi_artifact": ("accept", "accepted_for_offline_planning", "generated"),
    "known_nonblocking_gaps": (
        "accept_with_warnings",
        "accepted_for_offline_planning_with_warnings",
        "generated_with_warnings",
    ),
    "deliberately_invalid": ("reject", "rejected_without_plan", "not_generated_package_rejected"),
    "safety_boundary_violation": ("reject", "rejected_without_plan", "not_generated_package_rejected"),
}
REQUIRED_RESULT_KEYS = {
    "consumer_name",
    "consumer_version",
    "package_path",
    "package_id",
    "package_contract",
    "package_version",
    "validator_name",
    "validator_version",
    "validator_verdict",
    "consumer_verdict",
    "consumption_started_at",
    "consumption_completed_at",
    "manifest_loaded",
    "artifact_count",
    "artifact_type_counts",
    "declared_artifacts",
    "resolved_references",
    "unresolved_references",
    "dependency_order",
    "importable_artifacts",
    "review_only_artifacts",
    "non_importable_artifacts",
    "compatibility_warnings",
    "known_gaps",
    "dry_run_plan_status",
    "boundary_evidence",
    "errors",
    "warnings",
}


def load_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def package_hashes(package: Path) -> dict[str, bytes]:
    return {
        path.relative_to(package).as_posix(): path.read_bytes()
        for path in sorted(package.rglob("*"))
        if path.is_file()
    }


def copy_fixture(tmp_path: Path, name: str = "minimal_valid") -> Path:
    dest = (
        ROOT
        / "reports/course_compiler_demo/integration_readiness/reference_consumer/test_tmp_fixtures"
        / tmp_path.name
        / name
    )
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIXTURES / name, dest)
    return dest


@pytest.mark.parametrize("fixture,expected", EXPECTED.items())
def test_all_required_fixture_verdicts(fixture, expected):
    result, plan, enumeration, references = consume_package(FIXTURES / fixture)
    validator, verdict, plan_status = expected
    assert result["validator_verdict"] == validator
    assert result["consumer_verdict"] == verdict
    assert result["dry_run_plan_status"] == plan_status
    assert REQUIRED_RESULT_KEYS.issubset(result.keys())
    assert isinstance(enumeration["artifacts"], list)
    assert isinstance(references["resolved"], list)
    if verdict == "rejected_without_plan":
        assert plan is None
    else:
        assert plan is not None


def test_valid_fixture_references_resolve_and_orders_are_stable():
    first, plan, _, _ = consume_package(FIXTURES / "normal_multi_artifact")
    second, second_plan, _, _ = consume_package(FIXTURES / "normal_multi_artifact")
    assert first["unresolved_references"] == []
    assert first["declared_artifacts"] == second["declared_artifacts"]
    assert first["dependency_order"] == second["dependency_order"]
    assert first["errors"] == second["errors"]
    assert first["warnings"] == second["warnings"]
    assert plan["artifact_processing_order"] == second_plan["artifact_processing_order"]
    assert first["dependency_order"].index("PROC_RESULTANT_001") < first["dependency_order"].index("Q_RESULTANT_001")


def test_package_files_remain_unchanged_after_consumption():
    package = FIXTURES / "normal_multi_artifact"
    before = package_hashes(package)
    consume_package(package)
    after = package_hashes(package)
    assert before == after


def test_no_write_cli_creates_no_files(tmp_path):
    output = tmp_path / "not_created"
    command = [
        sys.executable,
        "-m",
        CLI,
        "--package",
        str(FIXTURES / "minimal_valid"),
        "--output",
        str(output),
        "--no-write",
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
    assert json.loads(completed.stdout)["consumer_verdict"] == "accepted_for_offline_planning"
    assert not output.exists()


def test_report_mode_writes_only_allowed_outputs(tmp_path):
    output = ROOT / "reports/course_compiler_demo/integration_readiness/reference_consumer/test_tmp_report_mode"
    if output.exists():
        shutil.rmtree(output)
    command = [
        sys.executable,
        "-m",
        CLI,
        "--package",
        str(FIXTURES / "minimal_valid"),
        "--output",
        str(output),
    ]
    subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
    files = sorted(path.name for path in output.iterdir() if path.is_file())
    assert files == [
        "artifact_enumeration.json",
        "consumer_report.md",
        "consumer_result.json",
        "dry_run_import_plan.json",
        "reference_resolution.json",
    ]
    shutil.rmtree(output)


@pytest.mark.parametrize(
    "output",
    [
        "/tmp/reference_consumer_out",
        "/Users/fanarichardson/adaptive-platform/staging",
        "reports/course_compiler_demo/../..",
        "tools/course_compiler_demo/release_package/golden_packages/minimal_valid/out",
        "tools/course_compiler_demo/release_package/validate/out",
    ],
)
def test_unsafe_output_paths_are_rejected(output):
    with pytest.raises(ValueError):
        safe_output_dir(output, FIXTURES / "minimal_valid")


@pytest.mark.parametrize(
    "package",
    [
        "/tmp/no_such_package",
        "/Users/fanarichardson/adaptive-platform/AxiomIQ_Alpha2.0_Content_Repository",
        "tools/course_compiler_demo/release_package/golden_packages/../minimal_valid",
    ],
)
def test_unsafe_or_missing_package_paths_reject(package):
    result, plan, _, _ = consume_package(package)
    assert result["consumer_verdict"] == "consumer_error"
    assert plan is None


def test_validator_reject_receives_no_actionable_plan():
    result, plan, _, _ = consume_package(FIXTURES / "deliberately_invalid")
    assert result["consumer_verdict"] == "rejected_without_plan"
    assert result["dry_run_plan_status"] == "not_generated_package_rejected"
    assert plan is None


def test_validator_error_stops_before_plan(monkeypatch):
    monkeypatch.setattr(
        consumer_module,
        "validate_package",
        lambda _: {"overall_verdict": "validator_error", "errors": [{"message": "boom"}]},
    )
    result, plan, _, _ = consume_package(FIXTURES / "minimal_valid")
    assert result["consumer_verdict"] == "consumer_error"
    assert result["dry_run_plan_status"] == "not_generated_consumer_error"
    assert plan is None


def test_missing_manifest_after_validation_handoff(monkeypatch, tmp_path):
    package = copy_fixture(tmp_path)
    try:
        (package / "manifest.json").unlink()
        monkeypatch.setattr(
            consumer_module,
            "validate_package",
            lambda _: {"overall_verdict": "accept", "errors": [], "warnings": []},
        )
        result, plan, _, _ = consume_package(package)
        assert result["consumer_verdict"] == "consumer_error"
        assert plan is None
    finally:
        shutil.rmtree(package.parents[1], ignore_errors=True)


def test_unresolved_internal_reference_after_validation_handoff(monkeypatch, tmp_path):
    package = copy_fixture(tmp_path)
    try:
        manifest = load_json(package / "manifest.json")
        manifest["procedure_artifact_ids"].append("MISSING_PROC")
        write_json(package / "manifest.json", manifest)
        monkeypatch.setattr(
            consumer_module,
            "validate_package",
            lambda _: {"overall_verdict": "accept", "errors": [], "warnings": []},
        )
        result, plan, _, _ = consume_package(package)
        assert result["consumer_verdict"] == "accepted_for_offline_planning"
        assert any(ref["status"] == "unresolved" for ref in result["unresolved_references"])
        assert plan is not None
    finally:
        shutil.rmtree(package.parents[1], ignore_errors=True)


def test_dependency_cycle_after_validation_handoff_rejects_plan(monkeypatch, tmp_path):
    package = copy_fixture(tmp_path)
    try:
        manifest = load_json(package / "manifest.json")
        manifest["artifact_inventory"][0]["depends_on_artifact_ids"] = [manifest["artifact_inventory"][1]["artifact_id"]]
        manifest["artifact_inventory"][1]["depends_on_artifact_ids"] = [manifest["artifact_inventory"][0]["artifact_id"]]
        write_json(package / "manifest.json", manifest)
        monkeypatch.setattr(
            consumer_module,
            "validate_package",
            lambda _: {"overall_verdict": "accept", "errors": [], "warnings": []},
        )
        result, plan, _, _ = consume_package(package)
        assert result["consumer_verdict"] == "rejected_without_plan"
        assert result["dry_run_plan_status"] == "not_generated_package_rejected"
        assert plan is None
    finally:
        shutil.rmtree(package.parents[1], ignore_errors=True)


def test_artifact_enumeration_mismatch_is_rejected_by_validator(tmp_path):
    package = copy_fixture(tmp_path)
    try:
        (package / "artifacts/extra.json").write_text("{}\n")
        result, plan, _, _ = consume_package(package)
        assert result["validator_verdict"] == "reject"
        assert result["consumer_verdict"] == "rejected_without_plan"
        assert plan is None
    finally:
        shutil.rmtree(package.parents[1], ignore_errors=True)


def test_unsafe_symlink_is_rejected_by_validator(tmp_path):
    package = copy_fixture(tmp_path)
    try:
        target = Path("/tmp/reference_consumer_escape.json")
        link = package / "artifacts/procedures/procedure_candidate_vector_components.json"
        link.unlink()
        link.symlink_to(target)
        result, plan, _, _ = consume_package(package)
        assert result["validator_verdict"] == "reject"
        assert plan is None
    finally:
        shutil.rmtree(package.parents[1], ignore_errors=True)


def test_database_and_network_are_not_attempted(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network/database should not be contacted")

    monkeypatch.setattr(socket, "create_connection", fail)
    result, _, _, _ = consume_package(FIXTURES / "minimal_valid")
    assert result["boundary_evidence"]["database_contacted"] is False
    assert result["boundary_evidence"]["network_endpoint_contacted"] is False


def test_adaptive_platform_modules_are_not_imported():
    before = set(sys.modules)
    result, _, _, _ = consume_package(FIXTURES / "minimal_valid")
    after = set(sys.modules)
    imported = sorted(name for name in after - before if "adaptive" in name.lower())
    assert imported == []
    assert result["boundary_evidence"]["adaptive_platform_accessed"] is False


def test_no_adaptive_platform_path_is_accessed():
    result, plan, _, _ = consume_package("/Users/fanarichardson/adaptive-platform")
    assert result["consumer_verdict"] == "consumer_error"
    assert plan is None
    assert result["boundary_evidence"]["adaptive_platform_accessed"] is False
