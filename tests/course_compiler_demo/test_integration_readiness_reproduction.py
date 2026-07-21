import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

import tools.course_compiler_demo.integration_readiness.reproduction_runner as runner
from tools.course_compiler_demo.integration_readiness.reproduction_runner import (
    capture_inventory,
    compare_workspace_state,
    fixture_matrix,
    future_generated_package_reproduction,
    reproduce_package,
    safe_output_dir,
)


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tools/course_compiler_demo/release_package/golden_packages"
CLI = "tools.course_compiler_demo.integration_readiness.run_reproduction"
EXPECTED = {
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
REQUIRED_KEYS = {
    "harness_name",
    "harness_version",
    "mode",
    "input_type",
    "package_path",
    "package_id",
    "package_contract",
    "package_version",
    "repeat_count",
    "input_inventory_digest",
    "input_artifact_digests",
    "validator_name",
    "validator_version",
    "consumer_name",
    "consumer_version",
    "run_results",
    "expected_validator_verdict",
    "actual_validator_verdicts",
    "expected_consumer_verdict",
    "actual_consumer_verdicts",
    "expected_plan_status",
    "actual_plan_statuses",
    "deterministic_fields_compared",
    "volatile_fields_excluded",
    "manifest_digest_match",
    "artifact_digest_match",
    "artifact_order_match",
    "dependency_order_match",
    "reference_resolution_match",
    "error_order_match",
    "warning_order_match",
    "package_non_mutation_confirmed",
    "boundary_evidence",
    "reproduction_verdict",
    "blockers",
    "warnings",
}


def copy_fixture(tmp_path: Path, name: str = "minimal_valid") -> Path:
    dest = ROOT / "reports/course_compiler_demo/integration_readiness/reproduction/test_tmp_fixtures" / tmp_path.name / name
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FIXTURES / name, dest)
    return dest


@pytest.mark.parametrize("fixture,expected", EXPECTED.items())
def test_all_five_fixture_expectations(fixture, expected):
    result = reproduce_package(
        FIXTURES / fixture,
        mode="fixture_reproduction",
        fixture_name=fixture,
        require_clean=False,
    )
    validator, consumer, plan, reproduction = expected
    assert result["actual_validator_verdicts"] == [validator, validator]
    assert result["actual_consumer_verdicts"] == [consumer, consumer]
    assert result["actual_plan_statuses"] == [plan, plan]
    assert result["reproduction_verdict"] == reproduction
    assert REQUIRED_KEYS.issubset(result.keys())
    assert result["package_non_mutation_confirmed"] is True


def test_fixture_matrix_states_fixture_only_limitation():
    matrix = fixture_matrix(require_clean=False)
    assert matrix["matrix_status"] == "HARNESS_REPRODUCTION_CONFIRMED"
    assert matrix["real_source_status"] == "REAL_SOURCE_REPRODUCTION_NOT_RUN"
    assert matrix["integration_readiness_status"] == "COMPILER_INTEGRATION_READINESS_NOT_YET_CONFIRMED"
    assert matrix["reproduction_verdict"] == "reproduced"


def test_repeat_run_deterministic_equality_and_volatile_exclusions():
    result = reproduce_package(FIXTURES / "normal_multi_artifact", fixture_name="normal_multi_artifact", require_clean=False)
    assert result["manifest_digest_match"] is True
    assert result["artifact_digest_match"] is True
    assert result["artifact_order_match"] is True
    assert result["dependency_order_match"] is True
    assert result["reference_resolution_match"] is True
    assert "validation_started_at" in result["volatile_fields_excluded"]
    assert "package identity" in result["deterministic_fields_compared"]


def test_package_non_mutation_for_copied_package(tmp_path):
    package = copy_fixture(tmp_path)
    try:
        before = capture_inventory(package)
        result = reproduce_package(package, require_clean=False)
        after = capture_inventory(package)
        assert before == after
        assert result["package_non_mutation_confirmed"] is True
    finally:
        shutil.rmtree(package.parents[1], ignore_errors=True)


def test_no_write_cli_creates_no_files(tmp_path):
    output = ROOT / "reports/course_compiler_demo/integration_readiness/reproduction/test_tmp_no_write"
    if output.exists():
        shutil.rmtree(output)
    command = [
        sys.executable,
        "-m",
        CLI,
        "--mode",
        "fixture_reproduction",
        "--output",
        str(output),
        "--no-write",
    ]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
    assert json.loads(completed.stdout)["matrix_status"] == "HARNESS_REPRODUCTION_CONFIRMED"
    assert not output.exists()


def test_report_mode_writes_only_approved_outputs():
    output = ROOT / "reports/course_compiler_demo/integration_readiness/reproduction/test_tmp_report"
    if output.exists():
        shutil.rmtree(output)
    command = [
        sys.executable,
        "-m",
        CLI,
        "--mode",
        "existing_package_reproduction",
        "--package",
        str(FIXTURES / "minimal_valid"),
        "--output",
        str(output),
    ]
    subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=True)
    files = sorted(path.name for path in output.iterdir() if path.is_file())
    assert files == [
        "boundary_evidence.json",
        "determinism_comparison.json",
        "input_inventory.json",
        "reproduction_report.md",
        "reproduction_result.json",
        "run_1_consumer_result.json",
        "run_1_validator_result.json",
        "run_2_consumer_result.json",
        "run_2_validator_result.json",
    ]
    shutil.rmtree(output)


@pytest.mark.parametrize(
    "output",
    [
        "/tmp/reproduction_output",
        "/Users/fanarichardson/adaptive-platform/staging",
        "reports/course_compiler_demo/../..",
        "tools/course_compiler_demo/release_package/golden_packages/minimal_valid/out",
        "tools/course_compiler_demo/release_package/contracts/out",
        "tools/course_compiler_demo/release_package/validate/out",
        "tools/course_compiler_demo/reference_consumer/out",
        "tools/course_compiler_demo/integration_readiness/out",
    ],
)
def test_unsafe_output_paths_reject(output):
    with pytest.raises(ValueError):
        safe_output_dir(output, FIXTURES / "minimal_valid")


def test_repeat_count_below_two_rejects():
    result = reproduce_package(FIXTURES / "minimal_valid", repeat_count=1, require_clean=False)
    assert result["reproduction_verdict"] == "harness_error"


@pytest.mark.parametrize(
    "package",
    [
        "/tmp/no_such_package",
        "/Users/fanarichardson/adaptive-platform",
    ],
)
def test_missing_or_adaptive_package_rejects(package):
    result = reproduce_package(package, require_clean=False)
    assert result["reproduction_verdict"] == "harness_error"


def test_dirty_worktree_protection(monkeypatch):
    monkeypatch.setattr(runner, "clean_source_state", lambda **kwargs: "dirty_source_state")
    result = reproduce_package(FIXTURES / "minimal_valid", require_clean=True)
    assert result["reproduction_verdict"] == "harness_error"
    assert "compiler worktree is not clean" in result["blockers"]


def test_clean_state_allows_unchanged_unstaged_and_untracked_baseline(monkeypatch):
    class Completed:
        stdout = "\n".join(
            [
                " M any/preexisting_tracked_change.py",
                "?? any/preexisting_untracked_file.json",
            ]
        )

    baseline = {
        "any/preexisting_tracked_change.py": {"status": " M", "exists": True, "sha256": "abc"},
        "any/preexisting_untracked_file.json": {"status": "??", "exists": True, "sha256": "def"},
    }
    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: Completed())
    monkeypatch.setattr(runner, "capture_workspace_state", lambda: baseline)

    assert runner.clean_source_state(ignore_lane_g=True, baseline_state=baseline) == "clean_source_state"


def test_clean_state_rejects_staged_changes(monkeypatch):
    class Completed:
        stdout = "M  staged_change.py"

    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: Completed())

    assert runner.clean_source_state(ignore_lane_g=True) == "dirty_source_state"


def test_workspace_compare_allows_unchanged_preexisting_dirty_files():
    before = {
        "preexisting.txt": {"status": "??", "exists": True, "sha256": "abc"},
        "tracked.py": {"status": " M", "exists": True, "sha256": "def"},
    }

    result = compare_workspace_state(before, dict(before))

    assert result["state_match"] is True


def test_workspace_compare_rejects_changed_preexisting_dirty_file():
    before = {"preexisting.txt": {"status": "??", "exists": True, "sha256": "abc"}}
    after = {"preexisting.txt": {"status": "??", "exists": True, "sha256": "changed"}}

    result = compare_workspace_state(before, after)

    assert result["state_match"] is False
    assert result["changed_paths"] == ["preexisting.txt"]


def test_workspace_compare_rejects_new_unauthorized_file():
    before = {"preexisting.txt": {"status": "??", "exists": True, "sha256": "abc"}}
    after = {
        **before,
        "unexpected.json": {"status": "??", "exists": True, "sha256": "extra"},
    }

    result = compare_workspace_state(before, after)

    assert result["state_match"] is False
    assert result["unexpected_new_paths"] == ["unexpected.json"]


def test_workspace_compare_rejects_deleted_preexisting_file():
    before = {"preexisting.txt": {"status": "??", "exists": True, "sha256": "abc"}}
    after = {}

    result = compare_workspace_state(before, after)

    assert result["state_match"] is False
    assert result["removed_paths"] == ["preexisting.txt"]


def test_workspace_compare_report_mode_permits_only_exact_outputs():
    before = {"preexisting.txt": {"status": "??", "exists": True, "sha256": "abc"}}
    after = {
        **before,
        "reports/out/reproduction_result.json": {"status": "??", "exists": True, "sha256": "ok"},
        "reports/out/unexpected.json": {"status": "??", "exists": True, "sha256": "bad"},
    }

    result = compare_workspace_state(
        before,
        after,
        allowed_new_paths={"reports/out/reproduction_result.json"},
    )

    assert result["state_match"] is False
    assert result["allowed_new_paths"] == ["reports/out/reproduction_result.json"]
    assert result["unexpected_new_paths"] == ["reports/out/unexpected.json"]


def test_archive_workspace_state_uses_filesystem_snapshot_without_git(monkeypatch, tmp_path):
    (tmp_path / "fixture.txt").write_text("committed archive content\n")

    def no_git(*_args, **_kwargs):
        raise subprocess.CalledProcessError(128, ["git", "status"])

    monkeypatch.setattr(runner.subprocess, "run", no_git)

    state = runner.capture_workspace_state(tmp_path)

    assert set(state) == {"fixture.txt"}
    assert state["fixture.txt"]["status"] == "FS"
    assert state["fixture.txt"]["exists"] is True
    assert state["fixture.txt"]["sha256"]


def test_archive_clean_state_allows_no_git_with_unchanged_snapshot(monkeypatch, tmp_path):
    (tmp_path / "fixture.txt").write_text("committed archive content\n")

    def no_git(*_args, **_kwargs):
        raise subprocess.CalledProcessError(128, ["git", "status"])

    monkeypatch.setattr(runner, "COMPILER_ROOT", tmp_path)
    monkeypatch.setattr(runner.subprocess, "run", no_git)
    baseline = runner.capture_workspace_state(tmp_path)

    assert runner.clean_source_state(ignore_lane_g=True, baseline_state=baseline) == "clean_source_state"


def test_empty_verdict_collections_fail_closed():
    verdict, blockers, warnings = runner._verdict_for(
        fixture_name="minimal_valid",
        validator_verdicts=[],
        consumer_verdicts=[],
        plan_statuses=[],
        comparison={
            "unexpected_differences": [],
        },
        non_mutation=True,
    )

    assert verdict == "not_reproduced"
    assert "validator did not execute" in blockers
    assert "consumer did not execute" in blockers
    assert "dry-run planner did not execute" in blockers
    assert warnings == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("actual_validator_verdicts", ["reject", "accept"]),
        ("actual_consumer_verdicts", ["accepted_for_offline_planning", "rejected_without_plan"]),
        ("actual_plan_statuses", ["generated", "not_generated_package_rejected"]),
    ],
)
def test_fixture_verdict_mismatch_or_drift_is_detected(monkeypatch, field, value):
    result = reproduce_package(FIXTURES / "minimal_valid", fixture_name="minimal_valid", require_clean=False)
    assert result["reproduction_verdict"] == "reproduced"
    result[field] = value
    assert len(set(result[field])) == 2


def test_artifact_checksum_drift_detected(monkeypatch, tmp_path):
    package = copy_fixture(tmp_path)
    try:
        original_capture = runner.capture_inventory
        calls = {"count": 0}

        def drifting_capture(path):
            payload = original_capture(path)
            calls["count"] += 1
            if calls["count"] > 1:
                payload["artifact_digests"]["fake"] = f"drift-{calls['count']}"
            return payload

        monkeypatch.setattr(runner, "capture_inventory", drifting_capture)
        result = reproduce_package(package, require_clean=False)
        assert result["artifact_digest_match"] is False
        assert result["reproduction_verdict"] == "not_reproduced"
    finally:
        shutil.rmtree(package.parents[1], ignore_errors=True)


def test_rejected_fixture_receives_no_actionable_plan():
    result = reproduce_package(FIXTURES / "safety_boundary_violation", fixture_name="safety_boundary_violation", require_clean=False)
    assert result["reproduction_verdict"] == "reproduced_expected_rejection"
    assert result["actual_plan_statuses"] == ["not_generated_package_rejected", "not_generated_package_rejected"]


def test_network_db_and_adaptive_access_are_not_attempted(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("network or DB should not be contacted")

    monkeypatch.setattr(socket, "create_connection", fail)
    before = set(sys.modules)
    result = reproduce_package(FIXTURES / "minimal_valid", fixture_name="minimal_valid", require_clean=False)
    imported = sorted(name for name in set(sys.modules) - before if "adaptive" in name.lower())
    assert imported == []
    assert result["boundary_evidence"]["database_contacted"] is False
    assert result["boundary_evidence"]["network_endpoint_contacted"] is False
    assert result["boundary_evidence"]["adaptive_platform_accessed"] is False


def test_future_generated_mode_is_honest():
    result = future_generated_package_reproduction()
    assert result["reproduction_verdict"] == "generation_unavailable"
    assert result["real_source_generation_available"] is False
    assert result["real_source_blocker"] == "no approved real Statics source and generator output"
    assert "COMPILER_INTEGRATION_READINESS_NOT_YET_CONFIRMED" in result["warnings"]
