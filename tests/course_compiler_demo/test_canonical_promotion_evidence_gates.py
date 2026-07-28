import copy
import json

import pytest

from tools.course_compiler_demo.canonical_promotion import preparation_mode as mode


def normalized_document(index=0):
    return mode.DocumentCompilerInputAdapter().normalize(mode.synthetic_document_candidates()[index], ordinal=index + 1)


def test_missing_document_rights_evidence_is_unknown_and_blocks():
    payload = mode.synthetic_document_candidates()[0]
    payload.pop("rights_evidence")
    payload.pop("human_review_action")
    candidate = mode.DocumentCompilerInputAdapter().normalize(payload, ordinal=1)
    rights = mode._rights_report(candidate)
    validation = mode._validation_report(candidate)
    duplicate = {"classification": "DISTINCT", "blockers": []}
    asset = {"status": "NOT_APPLICABLE", "blockers": []}
    review = mode._review_report(candidate, validation, rights, asset, duplicate)
    assert rights["classification"] == "UNKNOWN"
    assert rights["unresolved_requirements"]
    assert review["system_recommendation"] == "ESCALATE_RIGHTS"


def test_missing_phase_e_rights_evidence_is_unknown():
    payload = mode.select_phase_e_preparation_candidates()[0]
    candidate = mode.PhaseEProductionInputAdapter().normalize(payload, ordinal=6)
    assert mode._rights_report(candidate)["classification"] == "UNKNOWN"


def test_explicit_rights_requires_all_verifiable_source_fields():
    evidence = mode._synthetic_approval_evidence("CANDIDATE", "rights")
    assert mode._normalize_approval_evidence(evidence)["classification"] == "EXPLICIT_APPROVAL_EVIDENCE"
    evidence.pop("source_hash")
    normalized = mode._normalize_approval_evidence(evidence)
    assert normalized["classification"] == "UNKNOWN"
    assert "source_hash" in normalized["unresolved_requirements"]


def test_missing_independent_derivation_and_generator_answer_alone_block():
    candidate = normalized_document()
    candidate["independent_derivation"] = None
    report = mode._validation_report(candidate)
    assert "BLOCKED_MISSING_INDEPENDENT_DERIVATION" in report["blockers"]
    candidate = normalized_document()
    candidate["independent_derivation"]["source"] = candidate["independent_derivation"]["generator_answer_source"]
    assert mode._validation_report(candidate)["derivation"]["result"] == "BLOCKED"


def test_numeric_agreement_is_computed_and_invalid_contracts_fail():
    candidate = normalized_document()
    report = mode._validation_report(candidate)
    assert report["grading"]["agreement_computed"] is True
    assert report["grading"]["agreement"] is True
    candidate["answer_contract"] = {"type": "numeric", "shape": "tuple", "expected": [14, 2], "units": None, "tolerance": 0}
    assert "invalid_numeric_tuple_arity" in mode._validation_report(candidate)["grading"]["blockers"]
    candidate = normalized_document()
    candidate["answer_contract"].pop("tolerance")
    assert "missing_or_invalid_numeric_tolerance" in mode._validation_report(candidate)["grading"]["blockers"]


def test_multiple_choice_structure_and_solution_pairing_fail_closed():
    payload = mode.corrected_phase_e_candidates()[0]
    candidate = mode.PhaseEProductionInputAdapter().normalize(payload, ordinal=6)
    assert mode._validation_report(candidate)["grading"]["result"] == "PASS"
    candidate["question_payload"]["options"][1]["option_id"] = candidate["question_payload"]["options"][0]["option_id"]
    assert "invalid_multiple_choice_options" in mode._validation_report(candidate)["grading"]["blockers"]
    candidate = mode.PhaseEProductionInputAdapter().normalize(payload, ordinal=6)
    candidate["independent_derivation"]["normalized_answer"]["correct_option_id"] = "D"
    assert "multiple_choice_solution_option_mismatch" in mode._validation_report(candidate)["grading"]["blockers"]


def test_failure_signals_are_recognized_permitted_and_step_applicable():
    candidate = normalized_document()
    assert mode._validation_report(candidate)["failure_signals"]["result"] == "PASS"
    candidate["failure_signals"] = ["invented_signal"]
    report = mode._validation_report(candidate)["failure_signals"]
    assert report["result"] == "BLOCKED"
    candidate = normalized_document()
    candidate["permitted_failure_signals"] = ["algebra_error"]
    assert "rule_selection_error" in mode._validation_report(candidate)["failure_signals"]["rejected_signals"]


def test_asset_and_review_recommendation_do_not_depend_on_ordinal(tmp_path):
    passing = normalized_document(0)
    blocked = normalized_document(4)
    assert mode._asset_report(tmp_path, passing)["status"] == "NOT_APPLICABLE"
    assert mode._asset_report(tmp_path, blocked)["status"] == "BLOCKED"
    rights = mode._rights_report(passing)
    validation = mode._validation_report(passing)
    duplicate = {"classification": "DISTINCT", "blockers": []}
    recommendation = mode._review_report(passing, validation, rights, mode._asset_report(tmp_path, passing), duplicate)
    assert recommendation["system_recommendation"] == "ACCEPT_FOR_PROMOTION_REVIEW"
    assert recommendation["human_action"]["explicit"] is True
    assert "ordinal" not in json.dumps(recommendation).lower()


def test_human_action_must_be_explicit_attributed_and_safe(tmp_path):
    candidate = normalized_document()
    candidate["human_review_action"] = {"action": "ACCEPT_FOR_PROMOTION_REVIEW"}
    with pytest.raises(mode.CanonicalPromotionPreparationError, match="explicit, attributed"):
        mode._review_report(candidate, mode._validation_report(candidate), mode._rights_report(candidate), mode._asset_report(tmp_path, candidate), {"classification": "DISTINCT", "blockers": []})
    candidate = normalized_document(4)
    candidate["human_review_action"] = {"action": "ACCEPT_FOR_PROMOTION_REVIEW", "actor": "operator", "timestamp": "2026-07-27T00:00:00Z", "reason": "unsafe"}
    with pytest.raises(mode.CanonicalPromotionPreparationError, match="cannot accept"):
        mode._review_report(candidate, mode._validation_report(candidate), mode._rights_report(candidate), mode._asset_report(tmp_path, candidate), {"classification": "DISTINCT", "blockers": []})


def test_corrected_manifest_excludes_unresolved_and_reopen_restores_evidence(tmp_path):
    root = tmp_path / "promotion"
    summary = mode.run_preparation_pilot("CANONICAL_PROMOTION_PREPARATION_PILOT_018", preparation_root=root)
    manifest = json.loads((root / summary["dry_run_manifest"]["path"]).read_text())
    assert summary["prepared_count"] == 3
    assert manifest["prepared_external_ids"] == [entry["external_preparation_id"] for entry in summary["packets"] if entry["packet_status"] == "PREPARED_FOR_CANONICAL_REVIEW"]
    assert all(item["canonical_question_id"] is None and item["canonical_revision_id"] is None and item["path_created"] is False for item in manifest["prepared_packets"])
    reopened = mode.reopen_preparation_run("CANONICAL_PROMOTION_PREPARATION_PILOT_018", preparation_root=root)
    assert all("system_recommendation" in entry and "human_review_action" in entry and "duplicate_evidence" in entry for entry in reopened["packets"])


def test_candidate_permutation_does_not_change_outcomes(tmp_path):
    docs = mode.synthetic_document_candidates()
    phase = mode.corrected_phase_e_candidates()
    first = mode.run_preparation_pilot("RUN_ORDER_A", preparation_root=tmp_path / "a", document_candidates=docs, phase_e_candidates=phase)
    second = mode.run_preparation_pilot("RUN_ORDER_B", preparation_root=tmp_path / "b", document_candidates=list(reversed(docs)), phase_e_candidates=list(reversed(phase)))
    fields = lambda summary: {entry["candidate_identity"]: (entry["system_recommendation"], entry["review_action"], entry["packet_status"], entry["rights_provenance_classification"], entry["asset_status"], entry["duplicate_classification"]) for entry in summary["packets"]}
    assert fields(first) == fields(second)
