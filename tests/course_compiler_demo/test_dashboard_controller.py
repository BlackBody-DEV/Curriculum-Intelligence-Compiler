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
    ctrl.upload_source(run["run_id"], filename="physics.txt", content=PHYSICS_TEXT, metadata={"retain_normalized_source": True})
    with pytest.raises(DashboardControllerError):
        ctrl.select_profile(run["run_id"], "PHYSICS_INTRO_MECHANICS_PROFILE_V1")
    ctrl.confirm_rights(run["run_id"], {"rights_status": "owned_by_axiomiq", "privacy_status": "non_private"})
    updated = ctrl.select_profile(run["run_id"], "PHYSICS_INTRO_MECHANICS_PROFILE_V1")
    assert updated["status"] == "profile_selected"


def test_compiler_invocation_results_and_review(tmp_path):
    ctrl = controller(tmp_path)
    run = ctrl.create_run({"source_title": "Physics"}, run_id="RUN_COMPILE")
    ctrl.upload_source(run["run_id"], filename="physics.md", content=PHYSICS_TEXT, metadata={"retain_normalized_source": True})
    ctrl.confirm_rights(run["run_id"], {"rights_status": "owned_by_axiomiq", "privacy_status": "non_private"})
    ctrl.select_profile(run["run_id"], "PHYSICS_INTRO_MECHANICS_PROFILE_V1")
    compiled = ctrl.compile_run(run["run_id"])
    assert compiled["compiler_status"] == "pass"
    results = ctrl.results(run["run_id"])
    assert results["topics"]
    decision = ctrl.curriculum_review(run["run_id"], [{"candidate_id": "MS_003", "candidate_type": "micro_skill", "decision": "accepted"}])
    assert decision["decisions"][0]["decision"] == "accepted"


def test_no_retention_compile_uses_session_cache_not_external_fallback(tmp_path):
    ctrl = controller(tmp_path)
    run = ctrl.create_run({"source_title": "Physics"}, run_id="RUN_NO_RETAIN")
    ctrl.upload_source(run["run_id"], filename="physics_source.txt", content=PHYSICS_TEXT, metadata={"retain_normalized_source": False})
    ctrl.confirm_rights(run["run_id"], {"rights_status": "owned_by_axiomiq", "privacy_status": "non_private"})
    ctrl.select_profile(run["run_id"], "PHYSICS_INTRO_MECHANICS_PROFILE_V1")
    assert ctrl.compile_run(run["run_id"])["compiler_status"] == "pass"
    assert not (tmp_path / "RUN_NO_RETAIN/source/normalized_source.txt").exists()

    restarted = DashboardController(DashboardStorage(tmp_path))
    restarted_run = restarted.get_run(run["run_id"])
    restarted_run["status"] = "profile_selected"
    restarted.storage.save_manifest(restarted_run)
    failed = restarted.compile_run(run["run_id"])
    assert failed["compiler_status"] == "fail"
    assert "source text is unavailable" in failed["last_error"]
