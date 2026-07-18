from tests.course_compiler_demo.test_dashboard_controller import PHYSICS_TEXT, controller


def prepared_physics_run(tmp_path):
    ctrl = controller(tmp_path)
    run = ctrl.create_run({"source_title": "Physics"}, run_id="RUN_ASSESS")
    ctrl.upload_source(run["run_id"], filename="physics.txt", content=PHYSICS_TEXT, metadata={"retain_normalized_source": True})
    ctrl.confirm_rights(run["run_id"], {"rights_status": "owned_by_axiomiq", "privacy_status": "non_private"})
    ctrl.select_profile(run["run_id"], "PHYSICS_INTRO_MECHANICS_PROFILE_V1")
    ctrl.compile_run(run["run_id"])
    ctrl.curriculum_review(run["run_id"], [{"candidate_id": "MS_003", "candidate_type": "micro_skill", "decision": "accepted"}])
    return ctrl, run["run_id"]


def test_assessment_blueprint_generation_determinism_and_regeneration(tmp_path):
    ctrl, run_id = prepared_physics_run(tmp_path)
    blueprint = ctrl.create_assessment(run_id, {
        "assessment_id": "ASSESS_PHYS",
        "generation_family_id": "GF_PHYSICS_NEWTON_SECOND_LAW_1D_V1",
        "question_count": 10,
        "random_seed": 12345,
    })
    first = ctrl.generate_assessment(run_id, blueprint["assessment_id"])
    second = ctrl.generate_assessment(run_id, blueprint["assessment_id"])
    assert first["assessment"] == second["assessment"]
    assert len(first["assessment"]["questions"]) == 10
    q1, q2 = first["assessment"]["questions"][0], first["assessment"]["questions"][1]
    ctrl.review_assessment(run_id, blueprint["assessment_id"], [{"question_id": q1["question_id"], "decision": "accepted", "locked": True}])
    before = ctrl.get_assessment(run_id, blueprint["assessment_id"])["assessment"]["questions"][0]
    regen = ctrl.regenerate(run_id, blueprint["assessment_id"], q2["slot_id"], child_seed=98765)
    after = ctrl.get_assessment(run_id, blueprint["assessment_id"])["assessment"]["questions"][0]
    assert before == after
    assert regen["replacement_question_id"].endswith("_R001")


def test_historical_duplicate_loading_and_exhaustion_display(tmp_path, monkeypatch):
    from tools.course_compiler_demo.assessment_generation import generator

    ctrl, run_id = prepared_physics_run(tmp_path)
    blueprint = ctrl.create_assessment(run_id, {
        "assessment_id": "ASSESS_EXHAUST",
        "generation_family_id": "GF_PHYSICS_NEWTON_SECOND_LAW_1D_V1",
        "question_count": 2,
        "difficulty_distribution": {"foundational": 2},
        "question_type_distribution": {"numeric_with_unit": 2},
    })

    def constant_params(_difficulty, _rng):
        return {"target_variable": "acceleration", "mass_kg": 2, "acceleration_mps2": 3, "net_force_n": 6}

    monkeypatch.setitem(generator.PARAM_BUILDERS, "newtons_second_law_numeric_1d", constant_params)
    monkeypatch.setattr(generator, "MAX_ATTEMPTS_PER_SLOT", 3)
    generated = ctrl.generate_assessment(run_id, blueprint["assessment_id"])
    assert generated["duplicate_report"]["parameter_space_exhausted"] is True
    assert generated["duplicate_report"]["generated_count"] == 1
