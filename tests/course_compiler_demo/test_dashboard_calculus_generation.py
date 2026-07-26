from collections import Counter
import json

import pytest

from tools.course_compiler_demo.dashboard.calculus_generation import CALCULUS_FAMILY_ID, CALCULUS_REQUIRED_SKILLS, procedure_candidates
from tools.course_compiler_demo.dashboard.controller import DashboardController, DashboardControllerError
from tools.course_compiler_demo.dashboard.run_storage import DashboardStorage
from tools.course_compiler_demo.ingest.document_classifier import detect_math_course_level
from tests.course_compiler_demo.test_dashboard_compile_flow import CALCULUS_TEXT, _minimal_text_pdf
from tests.course_compiler_demo.test_dashboard_assessment_workflow import prepared_physics_run


DIFFERENTIAL_EQUATIONS_TEXT = (
    "Elementary differential equations. First order differential equations include separable equations "
    "and linear first order equations. Initial value problems use y(0)=1. Slope fields visualize "
    "solutions. Second order equations and systems of differential equations are later chapters."
)


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
        assert item["procedure_code"] == item["procedure_id"]
        assert item["subject"] == "MATHEMATICS"
        assert item["course_level"] == "CALCULUS_I"
        assert item["topic_code"]
        assert item["formula_or_rule"]
        assert item["steps"]
        assert item["ordered_solution_steps"] == item["steps"]
        assert item["worked_example"]["answer"]
        assert "common_errors" in item
        assert item["status"] == "demo_unverified"
        assert item["review_status"] == "pending"
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


def test_calculus_evidence_classifies_as_calculus_i_not_algebra_i():
    detected = detect_math_course_level(CALCULUS_TEXT + " Algebra review is not dominant.")

    assert detected["detected_course_level"] == "CALCULUS_I"
    assert detected["detected_course_level"] != "ALGEBRA_I"
    assert detected["classification_evidence"]
    assert detected["tie_breaking"] == "highest_evidence_score_then_advanced_math_before_algebra"
    assert detected["fail_closed"] is False


def test_unknown_mathematics_does_not_silently_default_to_algebra_i():
    detected = detect_math_course_level("Mathematics reading on abstract structures with examples and proofs.")

    assert detected["detected_course_level"] == "UNKNOWN_MATH_LEVEL"
    assert detected["detected_course_level"] != "ALGEBRA_I"
    assert detected["fail_closed"] is True


def test_calculus_compile_records_evidence_and_source_aligned_procedures(tmp_path):
    ctrl = DashboardController(DashboardStorage(tmp_path))
    run = ctrl.create_run({"source_title": "Calculus"}, run_id="RUN_CALC_EVIDENCE")
    ctrl.upload_source(
        run["run_id"],
        filename="calculus.txt",
        content=CALCULUS_TEXT.encode("utf-8"),
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
        },
    )
    compiled = ctrl.compile_run(run["run_id"])

    assert compiled["detected_course_level"] == "CALCULUS_I"
    interpretation = json.loads((tmp_path / "RUN_CALC_EVIDENCE/compiler/source_interpretation.json").read_text())
    assert interpretation["course_level_evidence"]
    assert interpretation["course_level_fail_closed"] is False
    results = ctrl.results(run["run_id"])
    assert {skill["micro_skill_code"] for skill in results["micro_skills"]} == set(CALCULUS_REQUIRED_SKILLS)
    assert len(results["procedure_candidates"]) == 5
    for candidate in results["procedure_candidates"]:
        assert candidate["procedure_code"] == candidate["procedure_id"]
        assert candidate["course_level"] == "CALCULUS_I"
        assert candidate["review_status"] == "pending"
        assert candidate["evidence_refs"]
        assert candidate["noncanonical"] is True
        assert candidate["canonical_approved"] is False
        assert candidate["eligible_for_alpha_import"] is False
        assert candidate["student_visible"] is False


def test_differential_equations_extracts_source_wide_topics_and_blocks_calculus_family(tmp_path):
    ctrl = DashboardController(DashboardStorage(tmp_path))
    run = ctrl.create_run({"source_title": "Elementary Differential Equations"}, run_id="RUN_DE")
    ctrl.upload_source(
        run["run_id"],
        filename="elementary-differential-equations.txt",
        content=DIFFERENTIAL_EQUATIONS_TEXT.encode("utf-8"),
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
        },
    )
    compiled = ctrl.compile_run(run["run_id"])

    assert compiled["detected_subject"] == "MATHEMATICS"
    assert compiled["detected_course_level"] == "DIFFERENTIAL_EQUATIONS"
    results = ctrl.results(run["run_id"])
    topic_codes = {item["topic_code"] for item in results["topics"]}
    assert {
        "first_order_differential_equations",
        "separable_equations",
        "linear_first_order_equations",
        "initial_value_problems",
        "slope_fields",
        "second_order_equations",
        "systems_of_differential_equations",
    } <= topic_codes
    assert all(item["evidence_refs"] for item in results["topics"])
    assert all(item["evidence_refs"] for item in results["micro_skills"])
    assert results["procedure_candidates"] == []

    ctrl.curriculum_review(
        run["run_id"],
        [
            {"candidate_id": skill["candidate_id"], "candidate_type": "micro_skill", "decision": "accepted"}
            for skill in results["micro_skills"]
        ],
    )
    compatible = ctrl.compatible_generation_families(run["run_id"])
    assert compatible["generation_families"] == []
    assert "Assessment generation remains a content gap" in compatible["content_gap"]
    with pytest.raises(DashboardControllerError, match="incompatible_assessment_generation_family"):
        ctrl.create_assessment(run["run_id"], {"assessment_id": "BAD_DE_CALC", "generation_family_id": CALCULUS_FAMILY_ID, "question_count": 10})


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


def test_assessment_review_refresh_hydrates_effective_regenerated_artifacts(tmp_path):
    ctrl, run_id = _prepared_calculus_run(tmp_path)
    ctrl.generate_practice(run_id)
    blueprint = ctrl.create_assessment(
        run_id,
        {"assessment_id": "ASSESSMENT_LOCAL", "generation_family_id": CALCULUS_FAMILY_ID, "question_count": 10, "random_seed": 20260723},
    )
    generated = ctrl.generate_assessment(run_id, blueprint["assessment_id"])["assessment"]
    q001 = generated["questions"][0]
    q002 = generated["questions"][1]
    ctrl.review_assessment(
        run_id,
        blueprint["assessment_id"],
        [
            {"question_id": question["question_id"], "decision": "accepted", "locked": index == 0}
            for index, question in enumerate(generated["questions"])
        ],
    )
    ctrl.regenerate(run_id, blueprint["assessment_id"], q002["slot_id"], child_seed=20260719)

    manifest = ctrl.get_run(run_id)
    for key in list(manifest["artifact_index"]):
        if "_export_" in key:
            manifest["artifact_index"].pop(key)
    ctrl.storage.save_manifest(manifest)

    refreshed = ctrl.get_assessment(run_id, blueprint["assessment_id"])
    active_questions = refreshed["assessment"]["questions"]
    assert len(active_questions) == 10
    assert active_questions[0]["question_id"] == q001["question_id"]
    assert active_questions[0]["locked"] is True
    assert active_questions[1]["slot_id"] == q002["slot_id"]
    assert active_questions[1]["question_id"] == "ASSESSMENT_LOCAL_Q002_R001"
    assert active_questions[1]["question_id"] != q002["question_id"]
    assert q002["question_id"] not in {q["question_id"] for q in active_questions}

    review_ids = {item["question_id"] for item in refreshed["review_decisions"]["review_records"]}
    assert "ASSESSMENT_LOCAL_Q002_R001" in review_ids
    assert q001["question_id"] in {
        item["question_id"]
        for item in refreshed["review_decisions"]["review_records"]
        if item.get("locked")
    }

    recovered_index = ctrl.get_run(run_id)["artifact_index"]
    for key in refreshed["artifact_keys"].values():
        assert key in recovered_index
        ctrl.artifact(run_id, key)

    student = json.loads(ctrl.export_path(run_id, blueprint["assessment_id"], "student_json").read_text())
    instructor = json.loads(ctrl.export_path(run_id, blueprint["assessment_id"], "instructor_json").read_text())
    assert student["questions"][1]["question_id"] == "ASSESSMENT_LOCAL_Q002_R001"
    assert instructor["questions"][1]["question_id"] == "ASSESSMENT_LOCAL_Q002_R001"

    reopened = DashboardController(DashboardStorage(tmp_path))
    reopened_data = reopened.get_assessment(run_id, blueprint["assessment_id"])
    assert reopened_data["assessment"]["questions"][0]["locked"] is True
    assert reopened_data["assessment"]["questions"][1]["question_id"] == "ASSESSMENT_LOCAL_Q002_R001"


def test_unsupported_artifact_key_is_controlled_error(tmp_path):
    ctrl, run_id = _prepared_calculus_run(tmp_path)

    with pytest.raises(DashboardControllerError, match="unsupported artifact key"):
        ctrl.artifact(run_id, "assessment_ASSESSMENT_LOCAL_exports_student_json")
