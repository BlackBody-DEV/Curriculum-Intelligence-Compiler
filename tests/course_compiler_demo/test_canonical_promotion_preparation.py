from pathlib import Path

import pytest

from tools.course_compiler_demo.canonical_promotion.preparation_mode import (
    MODE_IDENTIFIER,
    CanonicalPromotionPreparationError,
    DocumentCompilerInputAdapter,
    PhaseEProductionInputAdapter,
    normalize_input,
    prepare_promotion_root,
    reopen_preparation_run,
    run_preparation_pilot,
    select_phase_e_preparation_candidates,
    synthetic_document_candidates,
)
from tools.course_compiler_demo.phase_e_production.production_mode import select_mixed_family_cohort


def test_document_adapter_normalizes_universal_candidate():
    payload = synthetic_document_candidates(1)[0]
    candidate = DocumentCompilerInputAdapter().normalize(payload, ordinal=1)
    assert candidate["candidate_contract_version"] == "PromotionPreparationInput_v0_1"
    assert candidate["source_type"] == "document_compiler"
    assert candidate["source_identity"]["source_type"] == "synthetic_document_compiler_fixture"
    assert candidate["curriculum_linkage"]["primary_micro_skill_code"] == "evaluate_a_limit"
    assert candidate["procedure_linkage"]["verified"] is True
    assert candidate["independent_derivation"]["status"] == "COMPUTED"


def test_phase_e_adapter_normalizes_locked_record_without_canonical_authority():
    item = select_mixed_family_cohort()[0]
    candidate = PhaseEProductionInputAdapter().normalize(item, ordinal=6)
    assert candidate["source_type"] == "phase_e_production"
    assert candidate["source_identity"]["source_type"] == "locked_phase_e_package"
    assert candidate["procedure_linkage"]["verified"] is True
    assert candidate["independent_derivation"]["derivation_schema_version"] == "PHASE_E_INDEPENDENT_DERIVATION_v0_1"
    assert candidate["destination_path_metadata"]["path_created"] is False


def test_unknown_input_source_fails_closed():
    with pytest.raises(CanonicalPromotionPreparationError, match="unknown preparation input source type"):
        normalize_input("dashboard_mode_name", {}, ordinal=1)


def test_external_root_rejects_protected_locations_and_symlink_escape(tmp_path):
    with pytest.raises(CanonicalPromotionPreparationError):
        prepare_promotion_root(Path("/Users/fanarichardson/Documents/AxiomIQ/bad_promotion_root"))
    with pytest.raises(CanonicalPromotionPreparationError):
        prepare_promotion_root(Path("/Users/fanarichardson/adaptive-platform/bad_promotion_root"))
    with pytest.raises(CanonicalPromotionPreparationError):
        prepare_promotion_root(Path("/Users/fanarichardson/AxiomIQ_Work/phase_e/force_systems/bad_promotion_root"))

    root = tmp_path / "promotion_root"
    root.mkdir()
    (root / "exports").symlink_to("/Users/fanarichardson/Documents/AxiomIQ")
    with pytest.raises(CanonicalPromotionPreparationError, match="child escapes"):
        prepare_promotion_root(root)


def test_preparation_pilot_writes_ten_packets_and_dry_run_manifest(tmp_path):
    summary = run_preparation_pilot("RUN_PROMO_TEST", preparation_root=tmp_path / "promotion")
    assert summary["mode"] == MODE_IDENTIFIER
    assert summary["candidate_count"] == 10
    assert summary["document_driven_count"] == 5
    assert summary["phase_e_count"] == 5
    assert summary["prepared_count"] == 3
    assert summary["rights_or_provenance_blockers"] >= 1
    assert summary["asset_or_governance_blockers"] >= 1
    assert summary["duplicate_review_cases"] >= 1
    assert summary["returned_for_correction"] >= 1
    assert summary["rejected_or_regenerated"] >= 1
    assert {entry["review_action"] for entry in summary["packets"]} >= {
        "ACCEPT_FOR_PROMOTION_REVIEW",
        "RETURN_FOR_CORRECTION",
        "REJECT",
        "REGENERATE_UPSTREAM",
        "ESCALATE_RIGHTS",
        "ESCALATE_ASSET",
        "ESCALATE_CURRICULUM",
    }
    assert summary["canonical_ids_assigned"] == 0
    assert summary["canonical_paths_written"] == 0
    assert summary["database_access"] == "none"
    assert (tmp_path / "promotion" / summary["dry_run_manifest"]["path"]).exists()

    for entry in summary["packets"]:
        packet = (tmp_path / "promotion" / entry["packet_path"]).read_text(encoding="utf-8")
        assert '"canonical_question_id": null' in packet
        assert '"canonical_revision_id": null' in packet
        assert '"canonical_promotion_authorized": false' in packet
        assert '"database_write_authorized": false' in packet


def test_reopen_preparation_run_restores_packet_state(tmp_path):
    root = tmp_path / "promotion"
    run_preparation_pilot("RUN_PROMO_REOPEN", preparation_root=root)
    reopened = reopen_preparation_run("RUN_PROMO_REOPEN", preparation_root=root)
    assert reopened["packet_count"] == 10
    assert reopened["prepared_count"] == 3
    assert reopened["canonical_ids_assigned"] == 0
    assert reopened["canonical_paths_written"] == 0
    assert reopened["status"]["student_visible"] is False


def test_phase_e_preparation_selection_is_mixed_family():
    selected = select_phase_e_preparation_candidates()
    families = {item["row"]["family_identifier"] for item in selected}
    assert families == {"Force Systems", "Vector Operations"}
    assert len(selected) == 5
