import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.course_compiler_demo.package.release_package_emitter import (
    ReleasePackageEmitterError,
    emit_release_package,
    semantic_digest,
)


ROOT = Path(__file__).resolve().parents[2]
VECTOR_SEED = ROOT / "reports/course_compiler_demo/internal_release/vector_components_2d_seed_packet/vector_components_2d_seed_packet.json"
CLI = ROOT / "tools/course_compiler_demo/emit_release_package.py"


def load_json(path: Path):
    return json.loads(path.read_text())


def vector_payload():
    return load_json(VECTOR_SEED)


def synthetic_payload():
    return {
        "subject_code": "PHYSICS",
        "topic_code": "kinematics",
        "subtopic_code": "constant_acceleration",
        "selected_micro_skill_code": "velocity_from_acceleration",
        "source_artifacts": [{"path": "synthetic/physics_seed.json"}],
        "source_provenance": {"source_id": "SYNTH_PHYSICS_001", "method": "test_fixture"},
        "rights_summary": {"rights_status": "synthetic_fixture"},
        "review_state": {"human_review_required": True, "review_status": "review_pending"},
        "procedure_candidates": [
            {
                "candidate_id": "PROC_PHYSICS_001",
                "subject_code": "PHYSICS",
                "topic_code": "kinematics",
                "micro_skill_code": "velocity_from_acceleration",
                "steps": ["Identify acceleration.", "Multiply by elapsed time."],
            }
        ],
        "question_candidates": [
            {
                "candidate_id": "Q_PHYSICS_001",
                "subject_code": "PHYSICS",
                "topic_code": "kinematics",
                "micro_skill_code": "velocity_from_acceleration",
                "procedure_id": "PROC_PHYSICS_001",
                "prompt": "A cart starts from rest and accelerates at 2 m/s^2 for 3 s. Find final velocity.",
            }
        ],
        "generation_family_candidates": [
            {
                "family_id": "GF_PHYSICS_001",
                "subject_code": "PHYSICS",
                "topic_code": "kinematics",
                "micro_skill_code": "velocity_from_acceleration",
                "procedure_id": "PROC_PHYSICS_001",
                "question_ids": ["Q_PHYSICS_001"],
            }
        ],
        "practice_module_package": {
            "package_id": "PM_PHYSICS_001",
            "selected_micro_skill_code": "velocity_from_acceleration",
            "question_ids": ["Q_PHYSICS_001"],
            "procedure_ids": ["PROC_PHYSICS_001"],
        },
        "practice_assessment_package": {
            "package_id": "PA_PHYSICS_001",
            "selected_micro_skill_code": "velocity_from_acceleration",
            "question_ids": ["Q_PHYSICS_001"],
        },
        "performance_tracking_package": {
            "package_id": "PERF_PHYSICS_001",
            "selected_micro_skill_code": "velocity_from_acceleration",
            "tracked_question_ids": ["Q_PHYSICS_001"],
        },
        "content_gaps": [],
        "known_limitations": ["Synthetic test fixture only."],
    }


def emit(payload, tmp_path, package_id="TEST_PACKAGE_001"):
    return emit_release_package(source_payload=payload, output_dir=tmp_path, package_id=package_id)


def test_valid_vector_components_seed_emits_package(tmp_path):
    result = emit(vector_payload(), tmp_path, "STATICS_VECTOR_COMPONENTS_2D_INTERNAL_V1")
    package = load_json(result.package_path)
    assert package["selected_micro_skill_code"] == "vector_components_2d"
    assert package["package_status"] == "compiler_non_live_review_pending"
    assert package["integration_boundary"]["eligible_for_alpha_import"] is False
    assert package["integration_boundary"]["adaptive_platform_write_performed"] is False


def test_valid_synthetic_second_subject_emits_package(tmp_path):
    result = emit(synthetic_payload(), tmp_path, "PHYSICS_VELOCITY_INTERNAL_V1")
    package = load_json(result.package_path)
    assert package["subject_code"] == "PHYSICS"
    assert package["selected_micro_skill_code"] == "velocity_from_acceleration"


def test_identical_input_produces_identical_semantic_digest(tmp_path):
    one = emit(vector_payload(), tmp_path / "one", "STATICS_VECTOR_COMPONENTS_2D_INTERNAL_V1")
    two = emit(vector_payload(), tmp_path / "two", "STATICS_VECTOR_COMPONENTS_2D_INTERNAL_V1")
    assert one.semantic_digest == two.semantic_digest
    assert semantic_digest(load_json(one.package_path)) == semantic_digest(load_json(two.package_path))


def test_manifest_checksums_match_generated_files(tmp_path):
    result = emit(vector_payload(), tmp_path, "STATICS_VECTOR_COMPONENTS_2D_INTERNAL_V1")
    manifest = load_json(result.manifest_path)
    for filename, expected in manifest["generated_file_sha256"].items():
        data = (tmp_path / filename).read_bytes()
        import hashlib

        assert hashlib.sha256(data).hexdigest() == expected
    assert manifest["validation_status"] == "pass"
    assert result.manifest_path.name in manifest["generated_file_paths"]


def test_required_package_fields_are_present(tmp_path):
    result = emit(vector_payload(), tmp_path)
    package = load_json(result.package_path)
    required = {
        "package_id",
        "package_version",
        "package_status",
        "created_at",
        "emitter_version",
        "subject_code",
        "selected_micro_skill_code",
        "procedure_candidates",
        "question_candidates",
        "practice_module_package",
        "practice_assessment_package",
        "performance_tracking_package",
        "integration_boundary",
    }
    assert required.issubset(package)


def test_package_remains_non_live_and_review_pending(tmp_path):
    result = emit(vector_payload(), tmp_path)
    boundary = load_json(result.package_path)["integration_boundary"]
    assert all(
        boundary[key] is False
        for key in [
            "live_eligible",
            "eligible_for_alpha_import",
            "canonical_approved",
            "db_read_performed",
            "db_write_performed",
            "adaptive_platform_write_performed",
            "student_visible_publish_performed",
            "deployment_performed",
        ]
    )
    assert boundary["human_review_required"] is True


@pytest.mark.parametrize(
    "mutator",
    [
        lambda p: p.update(procedure_candidates=[]),
        lambda p: p.update(question_candidates=[]),
        lambda p: p.pop("practice_module_package"),
        lambda p: p.pop("practice_assessment_package"),
        lambda p: p.pop("performance_tracking_package"),
    ],
)
def test_required_components_fail(mutator, tmp_path):
    payload = synthetic_payload()
    mutator(payload)
    with pytest.raises(ReleasePackageEmitterError):
        emit(payload, tmp_path)
    assert not any(tmp_path.iterdir()) if tmp_path.exists() else True


def test_duplicate_ids_fail(tmp_path):
    payload = synthetic_payload()
    payload["procedure_candidates"].append(dict(payload["procedure_candidates"][0]))
    with pytest.raises(ReleasePackageEmitterError):
        emit(payload, tmp_path)


def test_broken_question_to_procedure_reference_fails(tmp_path):
    payload = synthetic_payload()
    payload["question_candidates"][0]["procedure_id"] = "NOPE"
    with pytest.raises(ReleasePackageEmitterError):
        emit(payload, tmp_path)


def test_inconsistent_micro_skill_linkage_fails(tmp_path):
    payload = synthetic_payload()
    payload["question_candidates"][0]["micro_skill_code"] = "other_skill"
    with pytest.raises(ReleasePackageEmitterError):
        emit(payload, tmp_path)


def test_broken_practice_module_question_reference_fails(tmp_path):
    payload = synthetic_payload()
    payload["practice_module_package"]["question_ids"] = ["NO_SUCH_QUESTION"]
    with pytest.raises(ReleasePackageEmitterError):
        emit(payload, tmp_path)


def test_broken_practice_module_procedure_reference_fails(tmp_path):
    payload = synthetic_payload()
    payload["practice_module_package"]["procedure_ids"] = ["NO_SUCH_PROCEDURE"]
    with pytest.raises(ReleasePackageEmitterError):
        emit(payload, tmp_path)


def test_broken_assessment_question_reference_fails(tmp_path):
    payload = synthetic_payload()
    payload["practice_assessment_package"]["question_ids"] = ["NO_SUCH_QUESTION"]
    with pytest.raises(ReleasePackageEmitterError):
        emit(payload, tmp_path)


def test_broken_performance_tracking_question_reference_fails(tmp_path):
    payload = synthetic_payload()
    payload["performance_tracking_package"]["tracked_question_ids"] = ["NO_SUCH_QUESTION"]
    with pytest.raises(ReleasePackageEmitterError):
        emit(payload, tmp_path)


def test_missing_provenance_or_rights_fails(tmp_path):
    payload = synthetic_payload()
    payload.pop("source_provenance")
    with pytest.raises(ReleasePackageEmitterError):
        emit(payload, tmp_path / "a")
    payload = synthetic_payload()
    payload.pop("rights_summary")
    with pytest.raises(ReleasePackageEmitterError):
        emit(payload, tmp_path / "b")


@pytest.mark.parametrize(
    "field",
    [
        "source_artifacts",
        "review_state",
        "generation_family_candidates",
        "content_gaps",
        "known_limitations",
    ],
)
def test_schema_required_top_level_fields_fail_when_missing(field, tmp_path):
    payload = synthetic_payload()
    payload.pop(field)
    with pytest.raises(ReleasePackageEmitterError):
        emit(payload, tmp_path)


def test_unauthorized_canonical_live_status_fails(tmp_path):
    payload = synthetic_payload()
    payload["live_deployable"] = True
    with pytest.raises(ReleasePackageEmitterError):
        emit(payload, tmp_path)


@pytest.mark.parametrize(
    "component,field",
    [
        ("practice_module_package", "live_eligible"),
        ("practice_assessment_package", "canonical_approved"),
        ("performance_tracking_package", "eligible_for_alpha_import"),
    ],
)
def test_nested_unauthorized_live_or_canonical_status_fails(component, field, tmp_path):
    payload = synthetic_payload()
    payload[component][field] = True
    with pytest.raises(ReleasePackageEmitterError):
        emit(payload, tmp_path)


def test_output_inside_adaptive_platform_is_rejected():
    with pytest.raises(ReleasePackageEmitterError):
        emit_release_package(
            source_payload=vector_payload(),
            output_dir=Path("/Users/fanarichardson/adaptive-platform/tmp"),
            package_id="BAD_OUTPUT",
        )


def test_cli_exits_nonzero_on_invalid_input(tmp_path):
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}\n")
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--input",
            str(invalid),
            "--package-id",
            "BAD",
            "--output",
            str(tmp_path / "out"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert completed.returncode != 0


def test_cli_emits_four_expected_proof_files_for_valid_input(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--input",
            str(VECTOR_SEED),
            "--package-id",
            "STATICS_VECTOR_COMPONENTS_2D_INTERNAL_V1",
            "--output",
            str(tmp_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "DOCS_COMPILER_RELEASE_PACKAGE_EMITTED" in completed.stdout
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "VECTOR_COMPONENTS_2D_RELEASE_PACKAGE_V1.md",
        "vector_components_2d_release_manifest_v1.json",
        "vector_components_2d_release_package_v1.json",
        "vector_components_2d_release_validation_v1.json",
    ]
