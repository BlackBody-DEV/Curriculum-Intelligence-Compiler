from pathlib import Path
import hashlib
import json
import os
import shutil

import pytest

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
    select_mixed_family_cohort,
)
from tools.course_compiler_demo.phase_e_production.candidate_generator import generate_candidate
from tools.course_compiler_demo.testing.phase_e_portable import REQUIRED_SAFETY,portable_adapters


PORTABLE_FIXTURE=Path(__file__).resolve().parents[1]/"fixtures/course_compiler_demo/phase_e_portable_replay"
pytestmark = pytest.mark.portable_baseline


@pytest.fixture(autouse=True)
def portable_phase_e_replay(monkeypatch):
    """Default to synthetic public data; protected integration is explicit opt-in."""
    if os.environ.get("PHASE_E_PROTECTED_INTEGRATION")=="1":
        yield
        return
    from tools.course_compiler_demo.phase_e_production.family_adapters import protected_family_workspace_roots
    protected_roots=protected_family_workspace_roots()
    adapters=portable_adapters(PORTABLE_FIXTURE)
    monkeypatch.setattr("tools.course_compiler_demo.phase_e_production.family_adapters._ADAPTERS",adapters)
    monkeypatch.setattr("tools.course_compiler_demo.phase_e_production.production_mode.protected_family_workspace_roots",lambda:protected_roots+tuple(item.workspace for item in adapters.values()))
    yield


def test_portable_phase_e_fixture_declares_required_safety_flags(tmp_path):
    import json
    payload=json.loads((PORTABLE_FIXTURE/"fixture_config.json").read_text())
    assert all(payload[key]==value for key,value in REQUIRED_SAFETY.items())
    artifacts=list(PORTABLE_FIXTURE.glob("*/approved/*.json"))
    assert len(artifacts)==15
    inventory={item["path"]:item["sha256"] for item in payload["files"]}
    assert set(inventory)=={path.relative_to(PORTABLE_FIXTURE).as_posix() for path in artifacts}
    assert all(inventory[path.relative_to(PORTABLE_FIXTURE).as_posix()]==hashlib.sha256(path.read_bytes()).hexdigest() for path in artifacts)
    assert all(all(json.loads(path.read_text())[key]==value for key,value in REQUIRED_SAFETY.items()) for path in artifacts)
    from tools.course_compiler_demo.phase_e_production.common import sha256_file
    from tools.course_compiler_demo.phase_e_production.family_adapters import ForceSystemsFamilyAdapter
    adapters=portable_adapters(PORTABLE_FIXTURE)
    force=adapters["force_systems"].finalized_records(); vectors=adapters["vector_operations"].finalized_records()
    assert len(force)==10 and len(vectors)==5
    assert sum(item["row"]["answer_type"]=="multiple_choice" for item in force)==5
    assert sum(item["row"]["answer_type"]=="numeric" for item in force)==5
    assert all(item["row"]["adapter_identifier"]=="ForceSystemsFamilyAdapter" for item in force)
    assert all(item["row"]["adapter_identifier"]=="VectorOperationsFamilyAdapter" for item in vectors)
    assert all(item["source_sha256"]==sha256_file(Path(item["source_path"])) for item in force+vectors)
    assert all(item["row"]["signed_procedure"]["procedure_steps"] for item in force+vectors)
    assert {item["benchmark"]["correct_option_id"] for item in force if item["row"]["answer_type"]=="multiple_choice"} == {"A"}
    assert [item["benchmark"]["expected_answer"]["value"] for item in force if item["row"]["answer_type"]=="numeric"] == [5.0, 0.0, 5.0, 6.708204, 4.0]
    assert [item["benchmark"]["expected_answer"]["values"] for item in vectors] == [
        [{"label":"F_x","value":8.660254,"unit":"N"},{"label":"F_y","value":5.0,"unit":"N"}],
        [{"label":"F_x","value":-10.392305,"unit":"N"},{"label":"F_y","value":6.0,"unit":"N"}],
        [{"label":"F_x","value":-5.656854,"unit":"N"},{"label":"F_y","value":-5.656854,"unit":"N"}],
        [{"label":"F_x","value":10.0,"unit":"N"},{"label":"F_y","value":-17.320508,"unit":"N"}],
        [{"label":"F_x","value":-3.882286,"unit":"N"},{"label":"F_y","value":14.488887,"unit":"N"}],
    ]
    assert all("fixture_type" not in item["row"] and "review_evidence" not in item["benchmark"] for item in force+vectors)

    workspace=tmp_path/"force_systems"; shutil.copytree(PORTABLE_FIXTURE/"force_systems",workspace)
    malformed=json.loads(next((workspace/"approved").glob("*.json")).read_text()); malformed["author_status"]="INCOMPLETE"
    (workspace/"approved/malformed.json").write_text(json.dumps(malformed))
    adapter=ForceSystemsFamilyAdapter(); object.__setattr__(adapter,"workspace",workspace)
    assert len(adapter.finalized_records())==10


def test_portable_phase_e_fixture_rejects_procedure_mutation_and_host_paths(tmp_path):
    import json
    copied=tmp_path/"fixtures"; shutil.copytree(PORTABLE_FIXTURE,copied)
    target=copied/"vector_operations/approved/portable-vector-01.json"
    artifact=json.loads(target.read_text()); artifact["procedure_steps_verbatim"].append("Unreviewed changed step.")
    target.write_text(json.dumps(artifact,indent=2,sort_keys=True)+"\n")
    config_path=copied/"fixture_config.json"; config=json.loads(config_path.read_text())
    relative=target.relative_to(copied).as_posix()
    next(item for item in config["files"] if item["path"]==relative)["sha256"]=hashlib.sha256(target.read_bytes()).hexdigest()
    config_path.write_text(json.dumps(config,indent=2,sort_keys=True)+"\n")
    with pytest.raises(ValueError,match="procedure digest mismatch"):
        portable_adapters(copied)

    artifact["procedure_sha256"] = hashlib.sha256(json.dumps(artifact["procedure_steps_verbatim"],separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
    artifact["lineage"]["source"]="/Users/example/protected.json"
    target.write_text(json.dumps(artifact,indent=2,sort_keys=True)+"\n")
    next(item for item in config["files"] if item["path"]==relative)["sha256"]=hashlib.sha256(target.read_bytes()).hexdigest()
    config_path.write_text(json.dumps(config,indent=2,sort_keys=True)+"\n")
    with pytest.raises(ValueError,match="host or protected path"):
        portable_adapters(copied)

    artifact["lineage"]["source"]="newly_authored_portable_fixture"
    target.write_text(json.dumps(artifact,indent=2,sort_keys=True)+"\n")
    next(item for item in config["files"] if item["path"]==relative)["sha256"]=hashlib.sha256(target.read_bytes()).hexdigest()
    config_path.write_text(json.dumps(config,indent=2,sort_keys=True)+"\n")
    (copied/"unexpected.txt").write_text("TEST_FIXTURE unexpected")
    with pytest.raises(ValueError,match="unexpected file"):
        portable_adapters(copied)


@pytest.mark.skipif(os.environ.get("PHASE_E_PROTECTED_INTEGRATION")!="1",reason="protected Phase E integration is opt-in")
@pytest.mark.protected_fixture_integration
def test_protected_phase_e_integration_opt_in_only():
    assert all("tests/fixtures" not in item["source_path"] for item in select_mixed_family_cohort())


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
    assert sum(1 for record in cohort["records"] if record["family_identifier"] == "Force Systems") == 5
    assert sum(1 for record in cohort["records"] if record["family_identifier"] == "Vector Operations") == 5
    assert sum(1 for record in cohort["records"] if record["answer_type"] == "numeric_pair") == 5
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
    assert summary["numeric_pair_count"] == 5
    assert summary["multiple_choice_count"] == 5
    assert summary["families"] == ["Force Systems", "Vector Operations"]
    assert len(summary["packages"]) == 10
    assert all(not Path(item["path"]).is_absolute() for item in summary["packages"])
    assert all((injected_root / item["path"]).exists() for item in summary["packages"])
    assert all((injected_root / item["path"]).resolve().is_relative_to(injected_root.resolve()) for item in summary["packages"])
    comparisons=[json.loads(path.read_text()) for path in injected_root.glob("runs/RUN_PHASE_E_TEST/*/comparison/golden_comparison.json")]
    assert len(comparisons)==10
    assert all(item["benchmark_comparison_result"]=="PASS" and item["answer_agreement"] is True for item in comparisons)
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


def test_force_systems_compatibility_replay_still_passes(tmp_path):
    summary = run_golden_replay(run_id="RUN_FORCE_COMPAT", production_root=tmp_path)
    assert summary["families"] == ["Force Systems"]
    assert summary["numeric_count"] == 5
    assert summary["multiple_choice_count"] == 5
    assert len(summary["packages"]) == 10


def test_mixed_family_cohort_uses_registered_adapters():
    cohort = select_mixed_family_cohort()
    assert len(cohort) == 10
    adapters = {item["row"]["adapter_identifier"] for item in cohort}
    assert adapters == {"ForceSystemsFamilyAdapter", "VectorOperationsFamilyAdapter"}
    assert sum(1 for item in cohort if item["row"]["family_identifier"] == "Vector Operations") == 5
    assert all(item["row"]["answer_type"] == "numeric_pair" for item in cohort if item["row"]["family_identifier"] == "Vector Operations")


def test_vector_operations_numeric_pair_replay_agrees(tmp_path):
    vector_item = [item for item in select_mixed_family_cohort() if item["row"]["family_identifier"] == "Vector Operations"][0]
    generation_packet = build_generation_packet(vector_item["row"], generation_seed="seed")
    candidate = generate_candidate(generation_packet)
    derivation_packet = build_derivation_packet(candidate, vector_item["row"])
    assert vector_item["benchmark"]["benchmark_prompt"] not in str(generation_packet)
    assert vector_item["benchmark"]["benchmark_prompt"] not in str(derivation_packet)
    assert generation_packet["adapter_identifier"] == "VectorOperationsFamilyAdapter"
    assert generation_packet["adapter_contract_version"] == "PHASE_E_FAMILY_ADAPTER_v0_1"
    assert "adapter_metadata" in generation_packet
    assert candidate["answer_type"] == "numeric_pair"
    assert candidate["expected_answer_proposal"] == vector_item["benchmark"]["expected_answer"]


def test_unknown_phase_e_family_fails_closed():
    import pytest
    from tools.course_compiler_demo.phase_e_production.family_adapters import FamilyAdapterError, get_family_adapter

    with pytest.raises(FamilyAdapterError):
        get_family_adapter("unknown_family")


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
