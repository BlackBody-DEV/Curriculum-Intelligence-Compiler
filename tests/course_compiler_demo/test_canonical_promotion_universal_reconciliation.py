import json
from pathlib import Path
import pytest

from tools.course_compiler_demo.canonical_promotion.preparation_mode import CanonicalPromotionPreparationError,normalize_input
from tools.course_compiler_demo.canonical_promotion.reconciliation import RUN_ID,run_universal_reconciliation_pilot
from tools.course_compiler_demo.dashboard.controller import DashboardController
from tools.course_compiler_demo.dashboard.run_storage import DashboardStorage

PRODUCTION_ROOT=Path("/Users/fanarichardson/AxiomIQ_Work/universal_compiler/production_question_wave_032")

def test_universal_adapters_fail_closed_and_resolve_bank_candidate():
    with pytest.raises(CanonicalPromotionPreparationError): normalize_input("production_question_candidate",{},ordinal=1)
    with pytest.raises(CanonicalPromotionPreparationError): normalize_input("production_question_bank",{"bank":{},"candidate_id":"x"},ordinal=1)
    with pytest.raises(CanonicalPromotionPreparationError): normalize_input("beta_export_reference",{"reference":{"question_id":"x"}},ordinal=1)
    bank=json.loads(next(PRODUCTION_ROOT.glob("algebra_i/banks/*.json")).read_text()); candidate=bank["candidates"][0]
    result=normalize_input("production_question_bank",{"bank":bank,"candidate_id":candidate["candidate_id"]},ordinal=1)
    assert result["candidate_contract_version"]=="PromotionPreparationInput_v0_1"
    assert result["source_identity"]["bank_sha256"]==bank["bank_sha256"]
    assert result["curriculum_linkage"]["primary_micro_skill_code"]
    assert result["procedure_linkage"]["verified"] is True
    cid=candidate["candidate_id"]
    resolved={"candidate":candidate,"derivation":next(x for x in bank["derivations"] if x["candidate_id"]==cid),"validation":next(x for x in bank["validations"] if x["candidate_id"]==cid),"bank_id":bank["bank_id"],"bank_sha256":bank["bank_sha256"],"beta_export_id":"production-wave-032","reference":{"question_id":cid,"procedure_id":candidate["procedure_id"],"curriculum_mapping":{"course_id":bank["course_id"]}}}
    beta=normalize_input("beta_export_reference",resolved,ordinal=1)
    assert beta["source_type"]=="beta_export_reference" and beta["source_identity"]["beta_export_id"]=="production-wave-032"

def test_six_bank_reconciliation_pilot_and_dashboard_reopen(tmp_path):
    root=tmp_path/"promotion"; summary=run_universal_reconciliation_pilot(preparation_root=root,production_root=PRODUCTION_ROOT)
    assert summary["candidate_count"]==30 and summary["production_bank_count"]==6
    assert len({x["course_id"] for x in summary["source_banks"]})==6
    assert all(sum(x["course_id"]==course for x in summary["source_banks"])==5 for course in {x["course_id"] for x in summary["source_banks"]})
    assert summary["prepared_count"]>=12
    assert all(summary["actions"][action]>=1 for action in ("ACCEPT_FOR_PROMOTION_REVIEW","RETURN_FOR_CORRECTION","REJECT","REGENERATE_UPSTREAM","ESCALATE_RIGHTS","ESCALATE_ASSET","ESCALATE_CURRICULUM"))
    assert summary["rights_or_provenance_blockers"]>=1 and summary["asset_or_governance_blockers"]>=1 and summary["duplicate_review_cases"]>=1
    manifest=json.loads((root/summary["dry_run_manifest"]["path"]).read_text())
    assert manifest["plan_only"] is True and manifest["canonical_write_authorized"] is False and manifest["database_write_authorized"] is False
    assert not manifest["sql_instructions"] and not manifest["execution_instructions"]
    assert all(x["review_action"]=="ACCEPT_FOR_PROMOTION_REVIEW" and x["canonical_question_id"] is None and x["canonical_revision_id"] is None and x["path_created"] is False for x in manifest["prepared_packets"])
    assert all(x["canonical_question_id"] is None and x["canonical_revision_id"] is None for x in summary["packets"])
    source=Path("tools/course_compiler_demo/canonical_promotion/reconciliation.py").read_text()
    semantic=source[source.index("def _apply_semantic_case"):source.index("def run_universal_reconciliation_pilot")]
    assert 'normalized["candidate_identity"]' not in semantic and 'normalized["curriculum_linkage"]["course_id"]' not in semantic and "ordinal" not in semantic
    dashboard=tmp_path/"dashboard"; ctrl=DashboardController(DashboardStorage(dashboard),canonical_promotion_root=root)
    ctrl._remember_canonical_promotion_run_root(RUN_ID,root)
    for restarted_root in (tmp_path/"ignored-refresh",tmp_path/"ignored-dashboard",tmp_path/"ignored-server"):
        reopened=DashboardController(DashboardStorage(dashboard),canonical_promotion_root=restarted_root).canonical_promotion_reopen(RUN_ID)
        assert reopened["candidate_count"]==30 and reopened["packet_count"]==30 and reopened["canonical_ids_assigned"]==0 and reopened["canonical_paths_written"]==0
        assert all(item["source_identity"]["bank_sha256"] and item["curriculum_linkage"] and item["procedure_linkage"] and item["independent_derivation_evidence"] and item["grading_evidence"] and item["failure_signal_evidence"] and item["rights_provenance_evidence"] and item["asset_evidence"] and item["duplicate_evidence"] and item["system_recommendation"] and item["human_review_action"] and "unresolved_blockers" in item for item in reopened["packets"])
