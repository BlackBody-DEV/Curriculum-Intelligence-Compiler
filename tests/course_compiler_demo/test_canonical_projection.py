import hashlib
import json
from pathlib import Path

import pytest

from tools.course_compiler_demo.beta_export import build_beta_export
from tools.course_compiler_demo.canonical_projection import (
    ProjectionPlanningError,
    projection_mode,
    reopen_projection_run,
    run_projection,
)
from tools.course_compiler_demo.dashboard.controller import DashboardController
from tools.course_compiler_demo.dashboard.run_storage import DashboardStorage
from tools.course_compiler_demo.universal_core import ValidatedQuestionReferenceV1


def reference(index: int, revision: str = "r1") -> ValidatedQuestionReferenceV1:
    return ValidatedQuestionReferenceV1(
        f"question-{index}", revision, f"procedure-{index}", "family-1", "answer-1", f"validation-{index}-{revision}",
        source_evidence=({
            "evidence_id": f"evidence-{index}", "source_type": "SYNTHETIC_PUBLIC_CONTRACT",
            "source_identity": f"public-contract-{index}", "source_hash": "a" * 64,
        },),
        curriculum_mapping={"course_id": "course-1", "unit_id": "unit-1", "topic_id": "topic-1"},
        difficulty="DEVELOPING", grading_contract={"method": "EXACT"},
        failure_signals=({"code": "WRONG"},), assessment_identity="diagnostic-1",
        assessment_role="DIAGNOSTIC", provenance={"provider": "synthetic-public-contract", "validated": True},
        version_data={"question_type": "NUMERIC", "estimated_minutes": 2},
    )


def candidate(question: ValidatedQuestionReferenceV1, *, prior: str | None = None) -> dict:
    payload = question.to_json().encode()
    return {
        "source_system": "curriculum-compiler-production-bank",
        "source_identity": question.question_id,
        "source_revision": question.question_revision,
        "content_sha256": hashlib.sha256(payload).hexdigest(),
        "preparation_id": f"preparation-{question.question_id}-{question.question_revision}",
        "prior_proposed_revision_id": prior,
        "source_lineage": [{"stage": "validated-question-bank", "question_id": question.question_id}],
        "review_action": "ACCEPT_FOR_PROMOTION_REVIEW",
        "eligible": True,
    }


def beta(questions):
    return build_beta_export("beta-export-1", "curriculum-1", questions).to_dict()


def assessments(questions):
    return [{"assessment_id": "diagnostic-1", "question_references": [q.to_dict() for q in questions]}]


def test_deterministic_projection_staging_rollback_and_restart(tmp_path):
    questions = [reference(2), reference(1)]
    first = run_projection(
        "projection-a", [candidate(q) for q in questions], beta(questions), assessments(questions),
        projection_root=tmp_path / "a",
    )
    second = run_projection(
        "projection-b", reversed([candidate(q) for q in questions]), beta(questions), assessments(questions),
        projection_root=tmp_path / "b",
    )
    assert first["records"] == second["records"]
    assert [item["source_identity"] for item in first["records"]] == ["question-1", "question-2"]
    assert first["counts"] == {"records": 2, "creates": 2, "revisions": 0, "idempotent_noops": 0,
                               "assessments": 1, "beta_references": 2}
    run_dir = tmp_path / "a" / "projection-a"
    rollback = json.loads((run_dir / "rollback_plan.json").read_text())
    assert rollback["complete"] is True and len(rollback["steps"]) == 2
    assert rollback["database_instructions"] == [] and rollback["canonical_store_instructions"] == []
    assert json.loads((run_dir / "beta_import_stage.json").read_text())["status"] == "VALIDATED_NOT_IMPORTED"
    reopened = reopen_projection_run("projection-a", projection_root=tmp_path / "a")
    assert reopened["reopened"] is True and reopened["manifest"] == first["manifest"]


def test_idempotent_reprojection_and_revision_lineage(tmp_path):
    old = reference(1)
    initial = run_projection("initial", [candidate(old)], beta([old]), assessments([old]), projection_root=tmp_path)
    prior = initial["records"]
    noop = run_projection(
        "noop", [candidate(old)], beta([old]), assessments([old]), projection_root=tmp_path,
        previous_records=prior,
    )
    assert noop["records"][0]["operation"] == "REPROJECT_NOOP"
    assert noop["records"][0]["proposed_revision_id"] == prior[0]["proposed_revision_id"]
    assert noop["counts"]["idempotent_noops"] == 1

    updated = reference(1, "r2")
    revised = run_projection(
        "revision", [candidate(updated, prior=prior[0]["proposed_revision_id"])], beta([updated]),
        assessments([updated]), projection_root=tmp_path, previous_records=prior,
    )
    record = revised["records"][0]
    assert record["operation"] == "STAGE_REVISION"
    assert record["proposed_identity"] == prior[0]["proposed_identity"]
    assert record["parent_proposed_revision_id"] == prior[0]["proposed_revision_id"]
    assert record["proposed_revision_id"] != prior[0]["proposed_revision_id"]
    assert record["lineage"][0]["stage"] == "validated-question-bank"


def test_duplicates_conflicts_and_invalid_links_fail_closed(tmp_path):
    question = reference(1)
    item = candidate(question)
    with pytest.raises(ProjectionPlanningError, match="duplicate projection candidate"):
        run_projection("duplicate", [item, item], beta([question]), assessments([question]), projection_root=tmp_path)
    revision = reference(1, "r2")
    with pytest.raises(ProjectionPlanningError, match="duplicate projection candidate"):
        run_projection(
            "multi-revision", [item, candidate(revision)], beta([question]), assessments([question]),
            projection_root=tmp_path,
        )

    initial = run_projection("initial", [item], beta([question]), assessments([question]), projection_root=tmp_path)
    conflicted = dict(item, content_sha256="f" * 64)
    with pytest.raises(ProjectionPlanningError, match="content changed"):
        run_projection("conflict", [conflicted], beta([question]), assessments([question]),
                       projection_root=tmp_path, previous_records=initial["records"])

    forged = [dict(initial["records"][0], proposed_revision_id="proposed-revision-forged")]
    with pytest.raises(ProjectionPlanningError, match="revision fails deterministic integrity"):
        run_projection("forged-prior", [item], beta([question]), assessments([question]),
                       projection_root=tmp_path, previous_records=forged)

    with pytest.raises(ProjectionPlanningError, match="no exact projection candidate revision"):
        run_projection("revision-mismatch", [item], beta([revision]), assessments([revision]), projection_root=tmp_path)

    unrelated = reference(2)
    with pytest.raises(ProjectionPlanningError, match="no exact projection candidate revision"):
        run_projection("bad-beta", [item], beta([question, unrelated]), assessments([question]), projection_root=tmp_path)
    with pytest.raises(ProjectionPlanningError, match="outside the validated Beta package"):
        run_projection("bad-assessment", [item], beta([question]), assessments([unrelated]), projection_root=tmp_path)


def test_reopen_detects_artifact_tampering(tmp_path):
    question = reference(1)
    run_projection("tamper", [candidate(question)], beta([question]), assessments([question]), projection_root=tmp_path)
    path = tmp_path / "tamper" / "operator_state.json"
    path.write_text(path.read_text() + " ")
    with pytest.raises(ProjectionPlanningError, match="integrity check failed"):
        reopen_projection_run("tamper", projection_root=tmp_path)


def test_revision_cannot_drop_prior_lineage(tmp_path):
    old = reference(1)
    initial = run_projection("initial", [candidate(old)], beta([old]), assessments([old]), projection_root=tmp_path)
    prior_lineage = initial["records"][0]["lineage"]
    updated = reference(1, "r2")
    input_candidate = candidate(updated, prior=initial["records"][0]["proposed_revision_id"])
    input_candidate["source_lineage"] = []
    revised = run_projection("revised", [input_candidate], beta([updated]), assessments([updated]),
                             projection_root=tmp_path, previous_records=initial["records"])
    assert revised["records"][0]["lineage"][:-1] == prior_lineage


def test_operator_mode_dashboard_controls_and_protected_state(tmp_path):
    mode = projection_mode()
    assert mode["status_labels"] == {
        "noncanonical": True, "human_review_required": True, "student_visible": False,
        "database_write": False, "promotion_authorized": False, "canonical_write": False,
        "beta_import_live": False, "adaptive_platform_modified": False,
    }
    assert mode["forbidden_controls"] == ["promote", "write database", "import Beta", "publish to students"]
    ctrl = DashboardController(
        DashboardStorage(tmp_path / "dashboard"), canonical_projection_root=tmp_path / "projection"
    )
    assert ctrl.canonical_projection_mode() == mode
    question = reference(1)
    result = ctrl.canonical_projection_run({
        "run_id": "dashboard-projection", "candidates": [candidate(question)],
        "beta_export": beta([question]), "assessments": assessments([question]),
    })
    restarted = DashboardController(
        DashboardStorage(tmp_path / "dashboard"), canonical_projection_root=tmp_path / "projection"
    )
    assert restarted.canonical_projection_reopen("dashboard-projection")["manifest"] == result["manifest"]
    app = Path("tools/course_compiler_demo/dashboard/static/app.js").read_text()
    html = Path("tools/course_compiler_demo/dashboard/templates/index.html").read_text()
    assert "/api/canonical-projection/mode" in app
    assert "/api/canonical-projection/plan" in app
    assert 'data-view="canonicalProjection"' in html
