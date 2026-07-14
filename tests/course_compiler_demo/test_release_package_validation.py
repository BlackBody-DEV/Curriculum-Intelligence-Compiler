import json
import shutil
import sqlite3
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from tools.course_compiler_demo.release_package.validate.package_validator import validate_package
from tools.course_compiler_demo.release_package.validate.validate_release_package import safe_output_dir


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tools/course_compiler_demo/release_package/golden_packages"
CLI = "tools.course_compiler_demo.release_package.validate.validate_release_package"
EXPECTED_VERDICTS = {
    "minimal_valid": "accept",
    "normal_multi_artifact": "accept",
    "known_nonblocking_gaps": "accept_with_warnings",
    "deliberately_invalid": "reject",
    "safety_boundary_violation": "reject",
}
REQUIRED_RESULT_KEYS = {
    "validator_name",
    "validator_version",
    "package_path",
    "package_id",
    "package_contract",
    "package_version",
    "validation_started_at",
    "validation_completed_at",
    "overall_verdict",
    "schema_status",
    "manifest_status",
    "artifact_inventory_status",
    "identifier_status",
    "reference_integrity_status",
    "provenance_status",
    "procedure_question_linkage_status",
    "generation_family_linkage_status",
    "signal_policy_status",
    "review_state_status",
    "rights_status",
    "safety_boundary_status",
    "integrity_status",
    "determinism_status",
    "known_gap_status",
    "errors",
    "warnings",
    "rule_results",
    "artifact_results",
    "boundary_evidence",
}


def copy_fixture(tmp_path: Path, name: str = "minimal_valid") -> Path:
    dest = tmp_path / name
    shutil.copytree(FIXTURES / name, dest)
    return dest


def load_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def manifest_path(package: Path) -> Path:
    return package / "manifest.json"


def mutate_manifest(package: Path, mutator):
    path = manifest_path(package)
    data = load_json(path)
    mutator(data)
    write_json(path, data)


def first_artifact(data, artifact_type):
    return next(item for item in data["artifact_inventory"] if item["artifact_type"] == artifact_type)


@pytest.mark.parametrize("fixture,expected", EXPECTED_VERDICTS.items())
def test_all_five_required_fixture_verdicts(fixture, expected):
    assert validate_package(FIXTURES / fixture)["overall_verdict"] == expected


def test_stable_structured_result_shape_and_rule_order():
    result = validate_package(FIXTURES / "minimal_valid")
    assert REQUIRED_RESULT_KEYS.issubset(result.keys())
    rule_ids = [item["rule_id"] for item in result["rule_results"]]
    assert rule_ids == sorted(rule_ids, key=rule_ids.index)
    assert rule_ids[0] == "CONTRACT_VERSION"
    assert result["errors"] == []
    assert result["warnings"] == []


def test_errors_and_warnings_are_ordered_deterministically():
    first = validate_package(FIXTURES / "safety_boundary_violation")
    second = validate_package(FIXTURES / "safety_boundary_violation")
    assert first["errors"] == second["errors"]
    assert first["warnings"] == second["warnings"]


def test_validation_does_not_mutate_fixture():
    package = FIXTURES / "minimal_valid"
    before = {path: path.read_bytes() for path in package.rglob("*") if path.is_file()}
    validate_package(package)
    after = {path: path.read_bytes() for path in package.rglob("*") if path.is_file()}
    assert before == after


def test_no_write_cli_creates_no_files(tmp_path):
    output = tmp_path / "out"
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
    assert json.loads(completed.stdout)["overall_verdict"] == "accept"
    assert not output.exists()


def test_report_mode_writes_only_two_allowed_files(tmp_path):
    output = ROOT / "reports/course_compiler_demo/integration_readiness/validation/test_tmp_report_mode"
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
    assert files == ["validation_report.md", "validation_result.json"]
    shutil.rmtree(output)


@pytest.mark.parametrize(
    "output",
    [
        "/tmp/outside_compiler_validation",
        "reports/course_compiler_demo/../..",
        "tools/course_compiler_demo/release_package/golden_packages/minimal_valid/output",
    ],
)
def test_unsafe_output_paths_are_rejected(output):
    with pytest.raises(ValueError):
        safe_output_dir(output, FIXTURES / "minimal_valid")


def test_missing_manifest_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    manifest_path(package).unlink()
    assert validate_package(package)["overall_verdict"] == "reject"


def test_malformed_json_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    manifest_path(package).write_text("{not-json")
    assert validate_package(package)["overall_verdict"] == "reject"


def test_unsupported_contract_version_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    mutate_manifest(package, lambda data: data.update(package_contract_semver="2.0.0"))
    assert validate_package(package)["overall_verdict"] == "reject"


def test_missing_required_artifact_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    (package / "artifacts/procedures/procedure_candidate_vector_components.json").unlink()
    result = validate_package(package)
    assert result["overall_verdict"] == "reject"
    assert any(issue["rule_id"] == "ARTIFACT_INVENTORY" for issue in result["errors"])


def test_undeclared_extra_artifact_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    extra = package / "artifacts/extra.json"
    extra.write_text("{}\n")
    assert validate_package(package)["overall_verdict"] == "reject"


def test_duplicate_artifact_id_rejects(tmp_path):
    package = copy_fixture(tmp_path)

    def duplicate(data):
        data["artifact_inventory"][1]["artifact_id"] = data["artifact_inventory"][0]["artifact_id"]

    mutate_manifest(package, duplicate)
    assert validate_package(package)["overall_verdict"] == "reject"


def test_duplicate_procedure_id_rejects(tmp_path):
    package = copy_fixture(tmp_path, "normal_multi_artifact")
    first = package / "artifacts/procedures/procedure_candidate_vector_components.json"
    second = package / "artifacts/procedures/procedure_candidate_resultant.json"
    payload = load_json(second)
    payload["candidate_id"] = load_json(first)["candidate_id"]
    write_json(second, payload)
    assert validate_package(package)["overall_verdict"] == "reject"


def test_broken_dependency_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    mutate_manifest(package, lambda data: data["artifact_inventory"][0]["depends_on_artifact_ids"].append("NO_SUCH_ARTIFACT"))
    assert validate_package(package)["overall_verdict"] == "reject"


def test_orphan_question_rejects(tmp_path):
    package = copy_fixture(tmp_path)

    def orphan(data):
        data["micro_skill_codes"] = []
        first_artifact(data, "question_candidate")["depends_on_artifact_ids"] = []

    mutate_manifest(package, orphan)
    assert validate_package(package)["overall_verdict"] == "reject"


def test_orphan_generation_family_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    gf_path = package / "artifacts/generation_families/generation_family_vector_components.json"
    payload = load_json(gf_path)
    payload["variable_parameters"] = []
    write_json(gf_path, payload)
    assert validate_package(package)["overall_verdict"] == "reject"


def test_unknown_signal_category_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    signal_path = package / "artifacts/signals/signal_mapping_vector_components.json"
    payload = load_json(signal_path)
    payload["signals"].append("mystery_runtime_signal")
    write_json(signal_path, payload)
    assert validate_package(package)["overall_verdict"] == "reject"


def test_missing_provenance_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    mutate_manifest(package, lambda data: first_artifact(data, "procedure_candidate").update(source_reference_ids=[]))
    assert validate_package(package)["overall_verdict"] == "reject"


def test_unsafe_rights_state_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    mutate_manifest(package, lambda data: data["source_references"][0].update(rights_status="unknown_restricted"))
    assert validate_package(package)["overall_verdict"] == "reject"


@pytest.mark.parametrize(
    "mutator",
    [
        lambda data: data.update(content_status="canonical_approved"),
        lambda data: data["safety_boundary"].update(student_visible=True),
        lambda data: data["safety_boundary"].update(database_contact_required=True),
        lambda data: data["compatibility_metadata"].update(path="/Users/fanarichardson/adaptive-platform/example"),
    ],
)
def test_safety_claims_reject(tmp_path, mutator):
    package = copy_fixture(tmp_path)
    mutate_manifest(package, mutator)
    assert validate_package(package)["overall_verdict"] == "reject"


def test_absolute_path_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    mutate_manifest(package, lambda data: first_artifact(data, "procedure_candidate").update(relative_path="/absolute/path.json"))
    assert validate_package(package)["overall_verdict"] == "reject"


def test_parent_traversal_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    mutate_manifest(package, lambda data: first_artifact(data, "procedure_candidate").update(relative_path="../escape.json"))
    assert validate_package(package)["overall_verdict"] == "reject"


def test_symlink_escape_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text("{}\n")
    link = package / "artifacts/procedures/escape_link.json"
    link.unlink(missing_ok=True)
    link.symlink_to(outside)

    def set_link(data):
        item = first_artifact(data, "procedure_candidate")
        item["relative_path"] = "artifacts/procedures/escape_link.json"

    mutate_manifest(package, set_link)
    assert validate_package(package)["overall_verdict"] == "reject"


def test_checksum_mismatch_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    mutate_manifest(package, lambda data: first_artifact(data, "procedure_candidate").update(sha256="0" * 64))
    assert validate_package(package)["overall_verdict"] == "reject"


def test_byte_size_mismatch_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    mutate_manifest(package, lambda data: first_artifact(data, "procedure_candidate").update(byte_size=1))
    assert validate_package(package)["overall_verdict"] == "reject"


def test_manifest_integrity_mismatch_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    mutate_manifest(package, lambda data: data["integrity"].update(package_manifest_sha256="1" * 64))
    assert validate_package(package)["overall_verdict"] == "reject"


def test_dependency_cycle_rejects(tmp_path):
    package = copy_fixture(tmp_path, "normal_multi_artifact")

    def cycle(data):
        proc = next(item for item in data["artifact_inventory"] if item["artifact_id"] == "PROC_RESULTANT_001")
        q = next(item for item in data["artifact_inventory"] if item["artifact_id"] == "Q_RESULTANT_001")
        proc["depends_on_artifact_ids"] = ["Q_RESULTANT_001"]
        q["depends_on_artifact_ids"] = ["PROC_RESULTANT_001"]

    mutate_manifest(package, cycle)
    assert validate_package(package)["overall_verdict"] == "reject"


def test_undeclared_nonblocking_gap_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    mutate_manifest(
        package,
        lambda data: data.update(
            known_gaps=[{"gap_id": "GAP_UNDECLARED", "severity": "nonblocking"}],
            promotion_recommendation="eligible_for_protected_integration_review",
        ),
    )
    assert validate_package(package)["overall_verdict"] == "reject"


def test_blocking_gap_mislabeled_nonblocking_rejects(tmp_path):
    package = copy_fixture(tmp_path)
    mutate_manifest(
        package,
        lambda data: data.update(
            known_gaps=[{"gap_id": "GAP_SAFETY", "severity": "nonblocking", "gap_class": "blocking_safety"}],
            promotion_recommendation="hold_for_human_review",
        ),
    )
    assert validate_package(package)["overall_verdict"] == "reject"


def test_validator_imports_no_adaptive_platform_module():
    loaded = set(sys.modules)
    validate_package(FIXTURES / "minimal_valid")
    new_modules = set(sys.modules) - loaded
    assert not any("adaptive" in name or "backend" in name or "frontend" in name for name in new_modules)


def test_validator_opens_no_database_or_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("network or database access attempted")

    monkeypatch.setattr(sqlite3, "connect", fail)
    monkeypatch.setattr(socket, "create_connection", fail)
    validate_package(FIXTURES / "minimal_valid")
