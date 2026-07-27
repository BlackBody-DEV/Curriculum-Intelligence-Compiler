from pathlib import Path
import shutil

from tools.course_compiler_demo.dashboard.controller import DashboardController
from tools.course_compiler_demo.dashboard.run_storage import DashboardStorage
from tools.course_compiler_demo.phase_e_production.production_mode import (
    MODE_IDENTIFIER,
    build_generation_packet,
    build_derivation_packet,
    prepare_production_root,
    reopen_golden_replay,
    resolve_production_root,
    run_golden_replay,
    select_force_systems_cohort,
)
from tools.course_compiler_demo.phase_e_production.candidate_generator import generate_candidate


def test_phase_e_mode_and_cohort_are_dashboard_visible(tmp_path):
    ctrl = DashboardController(DashboardStorage(tmp_path))
    mode = ctrl.phase_e_mode()
    assert mode["mode_identifier"] == MODE_IDENTIFIER
    assert mode["execution_profiles"] == ["GOLDEN_REPLAY"]
    labels = mode["status_labels"]
    assert labels["noncanonical"] is True
    assert labels["human_review_required"] is True
    assert labels["student_visible"] is False
    assert labels["eligible_for_alpha_import"] is False
    assert labels["golden_replay"] is True
    assert labels["production_candidate"] is False

    cohort = ctrl.phase_e_cohort()
    assert len(cohort["records"]) == 10
    assert sum(1 for record in cohort["records"] if record["answer_type"] == "numeric") == 5
    assert sum(1 for record in cohort["records"] if record["answer_type"] == "multiple_choice") == 5


def test_phase_e_golden_replay_exports_and_reopens_from_external_root(tmp_path, monkeypatch):
    default_probe = tmp_path / "default_should_remain_empty"
    injected_root = tmp_path / "phase_e_root"
    monkeypatch.setattr(
        "tools.course_compiler_demo.phase_e_production.production_mode.DEFAULT_PRODUCTION_ROOT",
        default_probe,
    )
    ctrl = DashboardController(DashboardStorage(tmp_path / "dashboard"), phase_e_production_root=injected_root)
    summary = ctrl.phase_e_run_golden_replay("RUN_PHASE_E_TEST")
    assert summary["mode"] == MODE_IDENTIFIER
    assert summary["numeric_count"] == 5
    assert summary["multiple_choice_count"] == 5
    assert len(summary["packages"]) == 10
    assert all(not Path(item["path"]).is_absolute() for item in summary["packages"])
    assert all((injected_root / item["path"]).exists() for item in summary["packages"])
    assert all((injected_root / item["path"]).resolve().is_relative_to(injected_root.resolve()) for item in summary["packages"])
    assert not default_probe.exists()

    reopened = ctrl.phase_e_reopen("RUN_PHASE_E_TEST")
    assert reopened["export_count"] == 10
    assert reopened["locked_count"] == 10
    assert reopened["production_root"] == str(injected_root.resolve())
    assert reopened["sealed_benchmark_contents_in_generator_state"] is False
    assert reopened["status_labels"]["student_visible"] is False


def test_phase_e_reopen_is_portable_after_root_copy(tmp_path):
    original_root = tmp_path / "original_root"
    copied_root = tmp_path / "copied_root"
    ctrl = DashboardController(DashboardStorage(tmp_path / "dashboard"), phase_e_production_root=original_root)
    ctrl.phase_e_run_golden_replay("RUN_PHASE_E_COPIED_ROOT")
    shutil.copytree(original_root, copied_root)
    shutil.rmtree(original_root)

    reopened = reopen_golden_replay("RUN_PHASE_E_COPIED_ROOT", production_root=copied_root)
    assert reopened["export_count"] == 10
    assert reopened["locked_count"] == 10
    assert reopened["production_root"] == str(copied_root.resolve())


def test_phase_e_root_resolution_precedence_and_persistence(tmp_path, monkeypatch):
    explicit_root = tmp_path / "explicit"
    env_root = tmp_path / "env"
    changed_env_root = tmp_path / "changed_env"
    default_probe = tmp_path / "default_probe"
    dashboard_root = tmp_path / "dashboard"
    monkeypatch.setattr(
        "tools.course_compiler_demo.phase_e_production.production_mode.DEFAULT_PRODUCTION_ROOT",
        default_probe,
    )
    monkeypatch.setenv("PHASE_E_COMPILER_PRODUCTION_ROOT", str(env_root))

    assert resolve_production_root() == env_root.resolve()
    assert resolve_production_root(explicit_root) == explicit_root.resolve()

    ctrl = DashboardController(DashboardStorage(dashboard_root), phase_e_production_root=explicit_root)
    ctrl.phase_e_run_golden_replay("RUN_PHASE_E_PERSISTED_ROOT")
    assert (explicit_root / "exports/RUN_PHASE_E_PERSISTED_ROOT/shadow_export_manifest.json").exists()
    assert not env_root.exists()
    assert not default_probe.exists()

    monkeypatch.setenv("PHASE_E_COMPILER_PRODUCTION_ROOT", str(changed_env_root))
    restarted = DashboardController(DashboardStorage(dashboard_root))
    reopened = restarted.phase_e_reopen("RUN_PHASE_E_PERSISTED_ROOT")
    assert reopened["production_root"] == str(explicit_root.resolve())
    assert not changed_env_root.exists()


def test_phase_e_environment_root_is_used_when_no_explicit_root(tmp_path, monkeypatch):
    env_root = tmp_path / "env_root"
    default_probe = tmp_path / "default_probe"
    monkeypatch.setattr(
        "tools.course_compiler_demo.phase_e_production.production_mode.DEFAULT_PRODUCTION_ROOT",
        default_probe,
    )
    monkeypatch.setenv("PHASE_E_COMPILER_PRODUCTION_ROOT", str(env_root))
    ctrl = DashboardController(DashboardStorage(tmp_path / "dashboard"))
    ctrl.phase_e_run_golden_replay("RUN_PHASE_E_ENV_ROOT")
    assert (env_root / "exports/RUN_PHASE_E_ENV_ROOT/shadow_export_manifest.json").exists()
    assert not default_probe.exists()


def test_numeric_golden_replay_packets_do_not_include_exact_benchmark_prompt():
    cohort = select_force_systems_cohort()
    numeric = [item for item in cohort if item["row"]["answer_type"] == "numeric"][0]
    generation_packet = build_generation_packet(numeric["row"], generation_seed="seed")
    candidate = generate_candidate(generation_packet)
    derivation_packet = build_derivation_packet(candidate, numeric["row"])
    benchmark_prompt = numeric["benchmark"]["benchmark_prompt"]
    assert benchmark_prompt not in str(generation_packet)
    assert benchmark_prompt not in str(derivation_packet)
    assert numeric["row"]["primitive_input_data"] in str(generation_packet)


def test_phase_e_external_root_rejects_protected_locations():
    import pytest
    from tools.course_compiler_demo.phase_e_production.production_mode import PhaseEProductionError

    with pytest.raises(PhaseEProductionError):
        prepare_production_root(Path("/Users/fanarichardson/Documents/AxiomIQ/phase_e_bad"))
    with pytest.raises(PhaseEProductionError):
        prepare_production_root(Path("/Users/fanarichardson/adaptive-platform/phase_e_bad"))
    with pytest.raises(PhaseEProductionError):
        prepare_production_root(Path("/Users/fanarichardson/AxiomIQ_Work/phase_e/force_systems/bad"))


def test_phase_e_external_root_rejects_relative_and_symlink_escape(tmp_path):
    import pytest
    from tools.course_compiler_demo.phase_e_production.production_mode import PhaseEProductionError

    with pytest.raises(PhaseEProductionError):
        prepare_production_root(Path("relative/phase_e"))

    protected_target = tmp_path / "protected_compiler_link"
    protected_target.symlink_to("/Users/fanarichardson/Documents/AxiomIQ")
    with pytest.raises(PhaseEProductionError):
        prepare_production_root(protected_target / "phase_e_bad")
    assert not (protected_target / "phase_e_bad").exists()


def test_phase_e_external_root_rejects_preexisting_child_symlink_escape(tmp_path):
    import pytest
    from tools.course_compiler_demo.phase_e_production.production_mode import PhaseEProductionError

    root = tmp_path / "phase_e_root"
    root.mkdir()
    (root / "exports").symlink_to("/Users/fanarichardson/Documents/AxiomIQ")
    with pytest.raises(PhaseEProductionError):
        prepare_production_root(root)
