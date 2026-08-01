import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools.course_compiler_demo.answer_engines.registry import ENABLED_ENGINE_TYPES
from tools.course_compiler_demo.production_readiness import (
    ADAPTIVE_MAIN_BASELINE,
    COMPILER_BASELINE,
    ProductionReadinessError,
    build_import_package,
    classify_import_error,
    deployment_gate,
    reopen_rehearsal,
    run_synthetic_student_flow,
    validate_import_package,
)


ROOT = Path(__file__).resolve().parents[2]
REPORT_ROOT = ROOT / "reports/course_compiler_demo/production_readiness"


def question(index=1, revision="v1"):
    qid = f"public-question-{index:03d}"
    return {
        "source_question_id": qid,
        "source_revision": revision,
        "proposed_identity": f"proposed-{qid}",
        "proposed_revision_id": f"proposed-{qid}-{revision}",
        "subject_code": "PUBLIC_MATHEMATICS",
        "course_id": "PUBLIC_PRE_ALGEBRA",
        "topic_code": "PUBLIC_ARITHMETIC",
        "subtopic_code": "PUBLIC_ADDITION",
        "micro_skill_code": "ADD_INTEGERS",
        "procedure_id": "addition-v1",
        "generation_family": "public-contract-arithmetic",
        "prompt": f"Compute {index} + 1.",
        "answer_engine": "numeric_scalar",
        "answer_contract": {"absolute_tolerance": 0.0, "relative_tolerance": 0.0},
        "expected_answer": index + 1,
        "explanation": "Add one.",
        "difficulty_level": 1,
        "use_case": "practice",
        "diagram_required": False,
        "image_ref": None,
        "lineage": [{"stage": "synthetic-public-contract", "source_question_id": qid, "source_revision": revision}],
        "provenance": {"type": "SYNTHETIC_PUBLIC_CONTRACT", "private": False, "protected": False},
    }


def package(*questions):
    return build_import_package("readiness-test", questions or (question(),))


def test_import_package_is_deterministic_complete_and_non_executable():
    first = build_import_package("ordered", [question(2), question(1)])
    second = build_import_package("ordered", [question(1), question(2)])
    assert first == second
    assert first["compiler_commit"] == COMPILER_BASELINE
    assert first["target"]["baseline"] == ADAPTIVE_MAIN_BASELINE
    assert first["capability_handshake"]["compiler_capabilities"] == list(ENABLED_ENGINE_TYPES)
    assert first["capability_handshake"]["silent_fallback_allowed"] is False
    assert first["transaction_contract"]["activation_is_separate_transaction"] is True
    assert validate_import_package(first) == {
        "status": "PASS", "would_write": False, "question_count": 2,
        "assessment_count": 0, "package_sha256": first["package_sha256"],
    }
    assert all(q["serving_eligible"] is q["is_active"] is q["student_visible"] is False for q in first["questions"])


def test_machine_readable_schema_accepts_package_and_rejects_authority_escalation():
    schema = json.loads((ROOT / "schemas/course_compiler_demo/student_activation_import_package_v1.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validator.validate(package(question()))
    escalated = package(question())
    escalated["safety"]["student_visibility_authorized"] = True
    assert list(validator.iter_errors(escalated))


def test_identity_revision_checksum_and_assessment_links_fail_closed():
    q = question()
    duplicate = copy.deepcopy(q)
    duplicate["proposed_identity"] = "other-proposed-id"
    duplicate["proposed_revision_id"] = "other-proposed-revision"
    with pytest.raises(ProductionReadinessError, match="duplicate or conflicting"):
        build_import_package("duplicate", [q, duplicate])

    forged = package(q)
    forged["questions"][0]["prompt"] = "forged"
    with pytest.raises(ProductionReadinessError, match="checksum"):
        validate_import_package(forged)

    with pytest.raises(ProductionReadinessError, match="outside"):
        build_import_package("bad-assessment", [q], assessments=[{
            "assessment_id": "diagnostic-1",
            "question_references": [["missing", "v1"]],
            "is_active": False,
            "student_visible": False,
        }])


def test_capability_and_lineage_are_mandatory_without_fallback():
    unsupported = question()
    unsupported["answer_engine"] = "unknown_engine"
    with pytest.raises(ProductionReadinessError, match="not an enabled"):
        package(unsupported)
    broken = question()
    broken["lineage"][-1]["source_revision"] = "wrong"
    with pytest.raises(ProductionReadinessError, match="terminate"):
        package(broken)


def test_retry_policy_is_bounded_and_unknown_errors_fail_closed():
    assert classify_import_error("E_TIMEOUT", 1) == {"classification": "TRANSIENT", "retry": True, "next_attempt": 2}
    assert classify_import_error("E_TIMEOUT", 4) == {"classification": "TRANSIENT", "retry": False, "next_attempt": None}
    assert classify_import_error("E_CHECKSUM_MISMATCH", 1)["retry"] is False
    assert classify_import_error("E_UNRECOGNIZED", 1) == {"classification": "UNKNOWN_FAIL_CLOSED", "retry": False, "next_attempt": None}


def test_deployment_gate_enumerates_every_protected_blocker():
    result = deployment_gate({
        "adaptive_commit": ADAPTIVE_MAIN_BASELINE,
        "environment": "production",
        "feature_flag_initially_disabled": True,
    }, package(question()))
    assert result["status"] == "BLOCKED"
    assert set(result["blockers"]) == {
        "database_reachable", "migrations_verified", "canonical_promotion_approved",
        "adaptive_write_approved", "student_visibility_approved", "rollback_rehearsed",
        "capability_parity_verified", "identity_ownership_tests_passed",
    }
    assert result["database_write_performed"] is result["student_visibility_changed"] is False


def test_synthetic_end_to_end_student_flow_and_restart_reopen(tmp_path):
    proof = run_synthetic_student_flow("student-flow", output_root=tmp_path)
    assert proof["status"] == "PASS" and len(proof["events"]) == 10
    assert proof["idempotency"]["pass"] and proof["conflict_rejected"]
    assert proof["ownership"]["forged_identity_rejected"]
    assert proof["retrieval"] == {"question_found": True, "student_visible_system_changed": False}
    assert proof["grading"] == {"correct_answer_passed": True, "incorrect_answer_failed": True}
    assert proof["rollback"] == {"question_unavailable": True, "attempt_history_retained": True}
    assert reopen_rehearsal("student-flow", output_root=tmp_path)["reopened"] is True


def test_restart_reopen_detects_tampering(tmp_path):
    run_synthetic_student_flow("tamper", output_root=tmp_path)
    path = tmp_path / "tamper" / "student_flow_proof.json"
    value = json.loads(path.read_text())
    value["status"] = "FORGED"
    path.write_text(json.dumps(value))
    with pytest.raises(ProductionReadinessError, match="integrity check failed"):
        reopen_rehearsal("tamper", output_root=tmp_path)


def test_durable_census_and_authorization_packet_match_observed_boundaries():
    census = json.loads((REPORT_ROOT / "production_gap_census_v1.json").read_text())
    packet = json.loads((REPORT_ROOT / "protected_authorization_packet_v1.json").read_text())
    path = census["critical_path"]
    assert [step["stage"] for step in path] == [
        "source_intake", "curriculum_synthesis", "validated_question_bank",
        "canonical_staging", "beta_import", "student_retrieval",
        "answer_submission", "grading_result",
    ]
    assert census["compiler_baseline"] == COMPILER_BASELINE
    assert packet["repositories"]["compiler"]["baseline"] == COMPILER_BASELINE
    assert packet["repositories"]["adaptive_platform"]["main_baseline"] == ADAPTIVE_MAIN_BASELINE
    assert packet["requested_authority"]["database_write"] is True
    assert packet["current_authority"]["database_write"] is False
    assert packet["activation_sequence"][0]["feature_flag"] == "disabled"
    assert packet["rollback"][0] == "disable student serving before any compensating data operation"


def test_human_report_and_json_evidence_do_not_drift():
    census = json.loads((REPORT_ROOT / "production_gap_census_v1.json").read_text())
    report = (REPORT_ROOT / "STUDENT_FACING_COMPILER_PRODUCTION_READINESS_REPORT.md").read_text()
    for expected in (
        COMPILER_BASELINE, ADAPTIVE_MAIN_BASELINE, "33 course packs",
        "14 answer capabilities", "1,275 validated questions", "27 diagnostic assessments",
        "Three protected execution waves", "student_visible=false",
    ):
        assert expected in report
    assert report.count("production activation blocker") >= 1
    assert census["housekeeping_recommendations"] == []
