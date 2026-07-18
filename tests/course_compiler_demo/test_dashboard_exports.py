from tests.course_compiler_demo.test_dashboard_assessment_workflow import prepared_physics_run


def test_student_and_instructor_exports_are_separated(tmp_path):
    ctrl, run_id = prepared_physics_run(tmp_path)
    blueprint = ctrl.create_assessment(run_id, {
        "assessment_id": "ASSESS_EXPORT",
        "generation_family_id": "GF_PHYSICS_NEWTON_SECOND_LAW_1D_V1",
        "question_count": 3,
        "difficulty_distribution": {"foundational": 1, "standard": 1, "advanced": 1},
        "question_type_distribution": {"numeric_with_unit": 3},
    })
    ctrl.generate_assessment(run_id, blueprint["assessment_id"])
    student_json = ctrl.export_path(run_id, blueprint["assessment_id"], "student_json").read_text()
    instructor_json = ctrl.export_path(run_id, blueprint["assessment_id"], "instructor_json").read_text()
    student_md = ctrl.export_path(run_id, blueprint["assessment_id"], "student_markdown").read_text()
    instructor_md = ctrl.export_path(run_id, blueprint["assessment_id"], "instructor_markdown").read_text()
    assert "expected_answer" not in student_json
    assert "solution_steps" not in student_json
    assert "Solution:" not in student_md
    assert "expected_answer" in instructor_json
    assert "Solution:" in instructor_md


def test_release_gate_blocks_pending_reviews_and_invalidated_math(tmp_path):
    ctrl, run_id = prepared_physics_run(tmp_path)
    blueprint = ctrl.create_assessment(run_id, {
        "assessment_id": "ASSESS_GATE",
        "generation_family_id": "GF_PHYSICS_NEWTON_SECOND_LAW_1D_V1",
        "question_count": 1,
        "difficulty_distribution": {"foundational": 1},
        "question_type_distribution": {"numeric_with_unit": 1},
    })
    data = ctrl.generate_assessment(run_id, blueprint["assessment_id"])
    assert ctrl.release_gate(run_id, blueprint["assessment_id"])["release_ready"] is False
    qid = data["assessment"]["questions"][0]["question_id"]
    ctrl.review_assessment(run_id, blueprint["assessment_id"], [{"question_id": qid, "decision": "needs_revision", "math_content_edited": True}])
    gate = ctrl.release_gate(run_id, blueprint["assessment_id"])
    assert gate["validation_invalidated"] is True
    assert gate["release_ready"] is False
