from collections import Counter
import json

import pytest

from tools.course_compiler_demo.dashboard.calculus_generation import CALCULUS_FAMILY_ID, CALCULUS_REQUIRED_SKILLS, procedure_candidates
from tools.course_compiler_demo.dashboard.controller import DashboardController, DashboardControllerError
from tools.course_compiler_demo.dashboard.run_storage import DashboardStorage
from tests.course_compiler_demo.test_dashboard_compile_flow import CALCULUS_TEXT, _minimal_text_pdf
from tests.course_compiler_demo.test_dashboard_assessment_workflow import prepared_physics_run


def _prepared_calculus_run(tmp_path, accepted=None):
    ctrl = DashboardController(DashboardStorage(tmp_path))
    run = ctrl.create_run({"source_title": "Calculus"}, run_id="RUN_CALC_GEN")
    ctrl.upload_source(
        run["run_id"],
        filename="calculus.pdf",
        content=_minimal_text_pdf([CALCULUS_TEXT]),
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
        },
    )
    compiled = ctrl.compile_run(run["run_id"])
    assert compiled["detected_subject"] == "MATHEMATICS"
    assert compiled["detected_course_level"] == "CALCULUS_I"
    skills = ctrl.results(run["run_id"])["micro_skills"]
    accepted_codes = set(accepted or CALCULUS_REQUIRED_SKILLS)
    decisions = [
        {"candidate_id": skill["candidate_id"], "candidate_type": "micro_skill", "decision": "accepted"}
        for skill in skills
        if skill["micro_skill_code"] in accepted_codes
    ]
    ctrl.curriculum_review(run["run_id"], decisions)
    return ctrl, run["run_id"]


def test_calculus_procedure_candidates_are_demo_safe():
    procedures = procedure_candidates()
    assert len(procedures) == 5
    assert {item["micro_skill_code"] for item in procedures} == set(CALCULUS_REQUIRED_SKILLS)
    for item in procedures:
        assert item["procedure_id"].startswith("PROC_DEMO_CALC_")
        assert item["subject"] == "MATHEMATICS"
        assert item["course_level"] == "CALCULUS_I"
        assert item["formula_or_rule"]
        assert item["steps"]
        assert item["worked_example"]["answer"]
        assert item["status"] == "demo_unverified"
        assert item["noncanonical"] is True
        assert item["canonical_approved"] is False
        assert item["eligible_for_alpha_import"] is False
        assert item["student_visible"] is False
        assert item["human_review_required"] is True


def test_calculus_family_available_only_after_all_accepted_skills(tmp_path):
    ctrl, run_id = _prepared_calculus_run(tmp_path)
    families = ctrl.compatible_generation_families(run_id)["generation_families"]
    assert [item["generation_family_id"] for item in families] == [CALCULUS_FAMILY_ID]

    partial_ctrl, partial_run_id = _prepared_calculus_run(tmp_path / "partial", accepted=CALCULUS_REQUIRED_SKILLS[:2])
    partial = partial_ctrl.compatible_generation_families(partial_run_id)
    assert partial["generation_families"] == []
    assert "Assessment generation remains a content gap" in partial["content_gap"]

    physics_ctrl, physics_run_id = prepared_physics_run(tmp_path / "physics")
    assert all(item["generation_family_id"] != CALCULUS_FAMILY_ID for item in physics_ctrl.compatible_generation_families(physics_run_id)["generation_families"])
    with pytest.raises(DashboardControllerError, match="incompatible_assessment_generation_family"):
        physics_ctrl.create_assessment(physics_run_id, {"assessment_id": "BAD_CALC", "generation_family_id": CALCULUS_FAMILY_ID, "question_count": 10})


def test_calculus_practice_assessment_locking_exports_and_persistence(tmp_path):
    ctrl, run_id = _prepared_calculus_run(tmp_path)

    practice = ctrl.generate_practice(run_id)
    assert practice["practice_item_count"] == 10
    assert practice["practice_package_id"]
    assert Counter(item["micro_skill_code"] for item in practice["items"]) == {skill: 2 for skill in CALCULUS_REQUIRED_SKILLS}
    manifest = ctrl.get_run(run_id)
    assert manifest["artifact_index"]["practice_package"] == "practice/calculus_i_foundations_practice.json"

    blueprint = ctrl.create_assessment(
        run_id,
        {"assessment_id": "ASSESS_CALCULUS", "generation_family_id": CALCULUS_FAMILY_ID, "question_count": 10, "random_seed": 20260723},
    )
    data = ctrl.generate_assessment(run_id, blueprint["assessment_id"])
    assessment = data["assessment"]
    assert assessment["validation_status"] == "pass"
    assert len(assessment["questions"]) == 10
    assert Counter(q["micro_skill_code"] for q in assessment["questions"]) == {skill: 2 for skill in CALCULUS_REQUIRED_SKILLS}
    assert assessment["subject_code"] == "MATHEMATICS"
    assert "PHYSICS" not in str(assessment)
    assert len({q["exact_fingerprint"] for q in assessment["questions"]}) == 10
    assert len({q["structural_fingerprint"] for q in assessment["questions"]}) == 10

    first, second = assessment["questions"][0], assessment["questions"][1]
    ctrl.review_assessment(run_id, blueprint["assessment_id"], [{"question_id": first["question_id"], "decision": "accepted", "locked": True}])
    locked_before = ctrl.get_assessment(run_id, blueprint["assessment_id"])["assessment"]["questions"][0]
    regen = ctrl.regenerate(run_id, blueprint["assessment_id"], second["slot_id"], child_seed=999)
    locked_after = ctrl.get_assessment(run_id, blueprint["assessment_id"])["assessment"]["questions"][0]
    regenerated = next(q for q in ctrl.get_assessment(run_id, blueprint["assessment_id"])["assessment"]["questions"] if q["slot_id"] == second["slot_id"])
    assert locked_before == locked_after
    assert regen["replacement_question_id"].endswith("_R001")
    assert regenerated["exact_fingerprint"] != second["exact_fingerprint"]

    with pytest.raises(ValueError, match="locked question"):
        ctrl.regenerate(run_id, blueprint["assessment_id"], first["slot_id"], child_seed=1000)

    student_json = ctrl.export_path(run_id, blueprint["assessment_id"], "student_json").read_text()
    student_md = ctrl.export_path(run_id, blueprint["assessment_id"], "student_markdown").read_text()
    instructor_json = ctrl.export_path(run_id, blueprint["assessment_id"], "instructor_json").read_text()
    instructor_md = ctrl.export_path(run_id, blueprint["assessment_id"], "instructor_markdown").read_text()
    forbidden = ["expected_answer", "solution_steps", "Answer:", "Solution:"]
    assert all(token not in student_json for token in forbidden)
    assert all(token not in student_md for token in forbidden)
    assert "expected_answer" in instructor_json
    assert "Answer:" in instructor_md

    reopened = DashboardController(DashboardStorage(tmp_path))
    persisted = reopened.get_run(run_id)
    assert persisted["assessment_ids"] == ["ASSESS_CALCULUS"]
    assert "practice_package" in persisted["artifact_index"]
    assert reopened.get_assessment(run_id, "ASSESS_CALCULUS")["assessment"]["questions"][0] == locked_after


def test_calculus_exports_refresh_after_regeneration_and_survive_reopen(tmp_path):
    ctrl, run_id = _prepared_calculus_run(tmp_path)
    ctrl.generate_practice(run_id)
    blueprint = ctrl.create_assessment(
        run_id,
        {"assessment_id": "ASSESS_CALCULUS", "generation_family_id": CALCULUS_FAMILY_ID, "question_count": 10, "random_seed": 20260723},
    )
    data = ctrl.generate_assessment(run_id, blueprint["assessment_id"])
    original = data["assessment"]
    first, second = original["questions"][0], original["questions"][1]
    stale_student = json.loads(ctrl.export_path(run_id, blueprint["assessment_id"], "student_json").read_text())
    assert second["question_id"] in {q["question_id"] for q in stale_student["questions"]}

    ctrl.review_assessment(run_id, blueprint["assessment_id"], [{"question_id": first["question_id"], "decision": "accepted", "locked": True}])
    locked_before = ctrl.get_assessment(run_id, blueprint["assessment_id"])["assessment"]["questions"][0]
    regen = ctrl.regenerate(run_id, blueprint["assessment_id"], second["slot_id"], child_seed=999)
    replacement_id = regen["replacement_question_id"]
    replacement = next(
        q for q in ctrl.get_assessment(run_id, blueprint["assessment_id"])["assessment"]["questions"]
        if q["question_id"] == replacement_id
    )

    manifest_after_regen = ctrl.get_run(run_id)
    assert all("_export_" not in key for key in manifest_after_regen["artifact_index"])

    student_json_path = ctrl.export_path(run_id, blueprint["assessment_id"], "student_json")
    student_md_path = ctrl.export_path(run_id, blueprint["assessment_id"], "student_markdown")
    instructor_json_path = ctrl.export_path(run_id, blueprint["assessment_id"], "instructor_json")
    instructor_md_path = ctrl.export_path(run_id, blueprint["assessment_id"], "instructor_markdown")

    student_json = json.loads(student_json_path.read_text())
    instructor_json = json.loads(instructor_json_path.read_text())
    student_md = student_md_path.read_text()
    instructor_md = instructor_md_path.read_text()

    student_ids = {q["question_id"] for q in student_json["questions"]}
    instructor_ids = {q["question_id"] for q in instructor_json["questions"]}
    assert replacement_id in student_ids
    assert replacement_id in instructor_ids
    assert second["question_id"] not in student_ids
    assert second["question_id"] not in instructor_ids
    assert second["prompt"] not in student_md
    assert second["prompt"] not in instructor_md
    assert replacement["prompt"] in student_md
    assert replacement["prompt"] in instructor_md
    assert ctrl.get_assessment(run_id, blueprint["assessment_id"])["assessment"]["questions"][0] == locked_before
    assert len(student_json["questions"]) == 10
    assert len(instructor_json["questions"]) == 10

    forbidden_student_tokens = ["expected_answer", "solution_steps", "Answer:", "Solution:"]
    assert all(token not in student_json_path.read_text() for token in forbidden_student_tokens)
    assert all(token not in student_md for token in forbidden_student_tokens)
    assert "expected_answer" in instructor_json_path.read_text()
    assert "solution_steps" in instructor_json_path.read_text()
    assert "Answer:" in instructor_md
    assert "Solution:" in instructor_md

    refreshed_index = ctrl.get_run(run_id)["artifact_index"]
    for filename in ["student_assessment.json", "student_assessment.md", "instructor_assessment.json", "instructor_assessment.md"]:
        key = f"assessment_{blueprint['assessment_id']}_export_{filename.replace('.', '_')}"
        assert refreshed_index[key] == f"assessments/{blueprint['assessment_id']}/exports/{filename}"

    reopened = DashboardController(DashboardStorage(tmp_path))
    reopened_assessment = reopened.get_assessment(run_id, blueprint["assessment_id"])["assessment"]
    reopened_ids = {q["question_id"] for q in reopened_assessment["questions"]}
    assert replacement_id in reopened_ids
    assert second["question_id"] not in reopened_ids
    assert reopened.get_assessment(run_id, blueprint["assessment_id"])["assessment"]["questions"][0] == locked_before
    assert replacement_id in json.loads(reopened.export_path(run_id, blueprint["assessment_id"], "student_json").read_text())["questions"][1]["question_id"]
