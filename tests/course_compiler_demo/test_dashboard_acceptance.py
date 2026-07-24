from pathlib import Path

from tools.course_compiler_demo.dashboard.controller import DashboardController
from tools.course_compiler_demo.dashboard.run_storage import DashboardStorage


PHYSICS_SOURCE = Path("/Users/fanarichardson/Documents/AxiomIQ_Source_Inbox/Physics/intro_mechanics_real_source_v1/normalized_source.txt")
STATICS_SOURCE = Path("/Users/fanarichardson/Documents/AxiomIQ_Source_Inbox/Statics/User_Authored/me_2301_statics_curriculum_extraction.md")


def _proof(ctrl, run_id, source_path, profile_id, family_id, assessment_id):
    run = ctrl.create_run({"source_title": source_path.stem}, run_id=run_id)
    ctrl.upload_source(
        run["run_id"],
        filename=source_path.name,
        content=source_path.read_bytes(),
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": False,
            "profile_id": profile_id,
        },
    )
    ctrl.confirm_rights(run["run_id"], {"rights_status": "approved_local_use", "privacy_status": "non_private"})
    ctrl.select_profile(run["run_id"], profile_id)
    compiled = ctrl.compile_run(run["run_id"])
    assert compiled["compiler_status"] == "complete"
    ctrl.curriculum_review(run["run_id"], [{"candidate_id": "MS_003" if "PHYSICS" in profile_id else "MS_STATICS_VECTOR_COMPONENTS_2D", "candidate_type": "micro_skill", "decision": "accepted"}])
    blueprint = ctrl.create_assessment(run["run_id"], {"assessment_id": assessment_id, "generation_family_id": family_id, "question_count": 10, "random_seed": 20260718})
    data = ctrl.generate_assessment(run["run_id"], blueprint["assessment_id"])
    q1, q2 = data["assessment"]["questions"][0], data["assessment"]["questions"][1]
    ctrl.review_assessment(run["run_id"], blueprint["assessment_id"], [{"question_id": q1["question_id"], "decision": "accepted", "locked": True}])
    before = ctrl.get_assessment(run["run_id"], blueprint["assessment_id"])["assessment"]["questions"][0]
    regen = ctrl.regenerate(run["run_id"], blueprint["assessment_id"], q2["slot_id"], child_seed=20260719)
    after = ctrl.get_assessment(run["run_id"], blueprint["assessment_id"])["assessment"]["questions"][0]
    assert before == after
    assert len(data["assessment"]["questions"]) == 10
    assert data["validation_report"]["validation_status"] == "pass"
    assert "expected_answer" not in ctrl.export_path(run["run_id"], blueprint["assessment_id"], "student_json").read_text()
    assert "expected_answer" in ctrl.export_path(run["run_id"], blueprint["assessment_id"], "instructor_json").read_text()
    ctrl.write_run_summary(run["run_id"], blueprint["assessment_id"], source_identity=source_path.name, profile=profile_id, regeneration=regen)
    assert any(item["run_id"] == run["run_id"] for item in ctrl.list_runs())
    return ctrl.get_run(run["run_id"])


def test_physics_and_statics_dashboard_acceptance_workflows(tmp_path):
    assert PHYSICS_SOURCE.exists()
    assert STATICS_SOURCE.exists()
    ctrl = DashboardController(DashboardStorage(tmp_path))
    physics = _proof(ctrl, "physics_acceptance_test", PHYSICS_SOURCE, "PHYSICS_INTRO_MECHANICS_PROFILE_V1", "GF_PHYSICS_NEWTON_SECOND_LAW_1D_V1", "ASSESS_PHYSICS_ACCEPTANCE")
    statics = _proof(ctrl, "statics_acceptance_test", STATICS_SOURCE, "STATICS_VECTOR_COMPONENTS_RELEASE_PROFILE_V1", "GF_STATICS_VECTOR_COMPONENTS_2D_V1", "ASSESS_STATICS_ACCEPTANCE")
    assert physics["raw_or_normalized_source_retained"] is False
    assert statics["raw_or_normalized_source_retained"] is False
    for path in tmp_path.rglob("*.json"):
        assert "/Users/fanarichardson/Documents/AxiomIQ_Source_Inbox" not in path.read_text()
