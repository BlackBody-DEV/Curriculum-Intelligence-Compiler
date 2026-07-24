from pathlib import Path

import pytest

from tools.course_compiler_demo.dashboard.controller import DashboardController, DashboardControllerError
from tools.course_compiler_demo.dashboard.run_storage import DashboardStorage


PHYSICS_TEXT = b"Subject: Physics\nINTRO_PHYSICS_MECHANICS\nNewton's Second Law states F_net = m a. practice problem."


def controller(tmp_path):
    return DashboardController(DashboardStorage(tmp_path))


def test_profiles_families_run_creation_and_rights_gate(tmp_path):
    ctrl = controller(tmp_path)
    assert any(p["profile_id"] == "PHYSICS_INTRO_MECHANICS_PROFILE_V1" for p in ctrl.list_profiles())
    assert any(f["generation_family_id"] == "GF_PHYSICS_NEWTON_SECOND_LAW_1D_V1" for f in ctrl.list_generation_families())
    run = ctrl.create_run({"source_title": "Physics"}, run_id="RUN_PHYS")
    uploaded = ctrl.upload_source(
        run["run_id"],
        filename="physics.txt",
        content=PHYSICS_TEXT,
        metadata={"retain_normalized_source": True, "profile_id": "PHYSICS_INTRO_MECHANICS_PROFILE_V1"},
    )
    assert uploaded["status"] == "source_ready"
    assert uploaded["source_display_filename"] == "physics.txt"
    assert uploaded["source_format"] == "txt"
    assert uploaded["source_sha256"]
    assert uploaded["selected_profile_id"] == "PHYSICS_INTRO_MECHANICS_PROFILE_V1"
    ctrl.confirm_rights(run["run_id"], {"rights_status": "owned_by_axiomiq", "privacy_status": "non_private"})
    updated = ctrl.select_profile(run["run_id"], "PHYSICS_INTRO_MECHANICS_PROFILE_V1")
    assert updated["status"] == "source_ready"


def test_compiler_invocation_results_and_review(tmp_path):
    ctrl = controller(tmp_path)
    run = ctrl.create_run({"source_title": "Physics"}, run_id="RUN_COMPILE")
    ctrl.upload_source(run["run_id"], filename="physics.md", content=PHYSICS_TEXT, metadata={"retain_normalized_source": True})
    with pytest.raises(DashboardControllerError, match="source upload, rights, privacy"):
        ctrl.compile_run(run["run_id"])
    ctrl.confirm_rights(run["run_id"], {"rights_status": "approved_local_use", "privacy_status": "non_private"})
    compiled = ctrl.compile_run(run["run_id"])
    assert compiled["compiler_status"] == "complete"
    assert compiled["status"] == "compiled"
    assert compiled["detected_subject"] == "PHYSICS"
    assert compiled["detected_course_level"] == "INTRO_PHYSICS_MECHANICS"
    assert compiled["topic_count"] > 0
    assert compiled["micro_skill_count"] > 0
    results = ctrl.results(run["run_id"])
    assert results["topics"]
    decision = ctrl.curriculum_review(run["run_id"], [{"candidate_id": "MS_003", "candidate_type": "micro_skill", "decision": "accepted"}])
    assert decision["decisions"][0]["decision"] == "accepted"


def test_assessment_requires_saved_curriculum_review(tmp_path):
    ctrl = controller(tmp_path)
    run = ctrl.create_run({"source_title": "Physics"}, run_id="RUN_ASSESSMENT_REVIEW_GATE")
    ctrl.upload_source(
        run["run_id"],
        filename="physics.txt",
        content=PHYSICS_TEXT,
        metadata={
            "retain_normalized_source": True,
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "profile_id": "PHYSICS_INTRO_MECHANICS_PROFILE_V1",
        },
    )
    ctrl.compile_run(run["run_id"])

    payload = {
        "generation_family_id": "GF_PHYSICS_NEWTON_SECOND_LAW_1D_V1",
        "assessment_id": "ASSESSMENT_LOCAL",
        "question_count": 10,
    }
    with pytest.raises(DashboardControllerError, match="save curriculum review decisions"):
        ctrl.create_assessment(run["run_id"], payload)

    ctrl.curriculum_review(
        run["run_id"],
        [{"candidate_id": "apply_newtons_second_law_1d", "candidate_type": "micro_skill", "decision": "accepted"}],
    )
    blueprint = ctrl.create_assessment(run["run_id"], payload)
    assert blueprint["status"] == "generation_ready"


def test_no_retention_compile_uses_session_cache_not_external_fallback(tmp_path):
    ctrl = controller(tmp_path)
    run = ctrl.create_run({"source_title": "Physics"}, run_id="RUN_NO_RETAIN")
    ctrl.upload_source(
        run["run_id"],
        filename="physics_source.txt",
        content=PHYSICS_TEXT,
        metadata={"retain_normalized_source": False, "rights_status": "approved_local_use", "privacy_status": "non_private"},
    )
    assert ctrl.compile_run(run["run_id"])["compiler_status"] == "complete"
    assert not (tmp_path / "RUN_NO_RETAIN/source/normalized_source.txt").exists()

    restarted = DashboardController(DashboardStorage(tmp_path))
    restarted_run = restarted.get_run(run["run_id"])
    restarted_run["status"] = "source_ready"
    restarted.storage.save_manifest(restarted_run)
    failed = restarted.compile_run(run["run_id"])
    assert failed["compiler_status"] == "failed"
    assert failed["status"] == "failed"
    assert "source text is unavailable" in failed["last_error"]


def test_compile_persists_running_state_before_execution(tmp_path):
    ctrl = controller(tmp_path)
    run = ctrl.create_run({"source_title": "Physics"}, run_id="RUN_TRANSITION")
    ctrl.upload_source(
        run["run_id"],
        filename="physics.txt",
        content=PHYSICS_TEXT,
        metadata={"retain_normalized_source": True, "rights_status": "approved_local_use", "privacy_status": "non_private"},
    )

    def inspect_transition(manifest, _selected_micro_skill):
        persisted = ctrl.get_run(manifest["run_id"])
        assert persisted["status"] == "compiling"
        assert persisted["compiler_status"] == "running"
        ctrl.storage.write_json_artifact(manifest, "topic_candidates", "compiler/topic_candidates.json", {"topic_candidates": [{"topic_code": "forces"}]})
        ctrl.storage.write_json_artifact(manifest, "micro_skill_candidates", "compiler/micro_skill_candidates.json", {"micro_skill_candidates": [{"micro_skill_code": "apply_newtons_second_law_1d"}]})
        ctrl.storage.write_json_artifact(manifest, "content_gaps", "compiler/content_gaps.json", {"content_gaps": []})

    ctrl._compile_physics = inspect_transition
    compiled = ctrl.compile_run(run["run_id"])
    assert compiled["status"] == "compiled"
    assert compiled["compiler_status"] == "complete"
