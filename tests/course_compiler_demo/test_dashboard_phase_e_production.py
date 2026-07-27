from pathlib import Path

from tools.course_compiler_demo.dashboard.controller import DashboardController
from tools.course_compiler_demo.dashboard.run_storage import DashboardStorage
from tools.course_compiler_demo.phase_e_production.production_mode import (
    MODE_IDENTIFIER,
    build_generation_packet,
    build_derivation_packet,
    prepare_production_root,
    reopen_golden_replay,
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
    import tools.course_compiler_demo.phase_e_production.production_mode as production_mode

    monkeypatch.setattr(production_mode, "DEFAULT_PRODUCTION_ROOT", tmp_path)
    ctrl = DashboardController(DashboardStorage(tmp_path / "dashboard"))
    summary = ctrl.phase_e_run_golden_replay("RUN_PHASE_E_TEST")
    assert summary["mode"] == MODE_IDENTIFIER
    assert summary["numeric_count"] == 5
    assert summary["multiple_choice_count"] == 5
    assert len(summary["packages"]) == 10
    assert all(Path(item["path"]).exists() for item in summary["packages"])

    reopened = ctrl.phase_e_reopen("RUN_PHASE_E_TEST")
    assert reopened["export_count"] == 10
    assert reopened["locked_count"] == 10
    assert reopened["sealed_benchmark_contents_in_generator_state"] is False
    assert reopened["status_labels"]["student_visible"] is False


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
