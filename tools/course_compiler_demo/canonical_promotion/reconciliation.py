"""Universal production-bank reconciliation for preparation-only review."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .common import load_json,root_relative,sha256_file,stable_hash,write_json
from .preparation_mode import (
    EXECUTION_PROFILE,MODE_IDENTIFIER,STATUS_FLAGS,CanonicalPromotionPreparationError,
    _duplicate_report,_fingerprint_report,_load_prior_packet_inventory,_process_candidate,
    normalize_input,prepare_promotion_root,reopen_preparation_run,
)

RUN_ID="CANONICAL_PROMOTION_UNIVERSAL_RECONCILIATION_045"
DEFAULT_ROOT=Path("/Users/fanarichardson/AxiomIQ_Work/canonical_promotion/universal_reconciliation_045")
PRODUCTION_ROOT=Path("/Users/fanarichardson/AxiomIQ_Work/universal_compiler/production_question_wave_032")

def _load_banks(root:Path)->list[tuple[Path,dict[str,Any]]]:
    banks=[]
    for path in sorted(root.glob("*/banks/*.json")):
        bank=load_json(path)
        if bank.get("locked") is not True or len(bank.get("candidates",()))!=100 or not bank.get("bank_sha256"):
            raise CanonicalPromotionPreparationError(f"invalid production bank: {path}")
        banks.append((path,bank))
    if len(banks)!=6 or len({bank["course_id"] for _,bank in banks})!=6:
        raise CanonicalPromotionPreparationError("exactly six unique production banks are required")
    return banks

def _pick(bank,difficulty,role,*,shape=None,exclude=None,exclude_families=None):
    exclude=exclude or set()
    exclude_families=exclude_families or set()
    eligible=[c for c in bank["candidates"] if c["candidate_id"] not in exclude and c["request"]["generation_family_id"] not in exclude_families and c["request"]["difficulty"]==difficulty and c["request"]["assessment_role"]==role and (shape is None or c["answer_contract"]["shape"]==shape)]
    if not eligible: raise CanonicalPromotionPreparationError(f"bank lacks semantic pilot slot {difficulty}/{role}/{shape}")
    return min(eligible,key=lambda c:stable_hash({"prompt":c["prompt"],"parameters":c["request"]["parameters"],"procedure":c["procedure_id"]}))

def _pick_prefer(bank,difficulty,role,shape,used,families):
    try: return _pick(bank,difficulty,role,shape=shape,exclude=used,exclude_families=families)
    except CanonicalPromotionPreparationError: return _pick(bank,difficulty,role,exclude=used,exclude_families=families)

def _select_five(bank):
    shapes=sorted({c["answer_contract"]["shape"] for c in bank["candidates"]}); chosen=[]; used=set(); families=set()
    for shape in shapes[:2]:
        item=_pick(bank,"introductory","practice",shape=shape,exclude=used,exclude_families=families); chosen.append(item); used.add(item["candidate_id"]); families.add(item["request"]["generation_family_id"])
    non_scalar=next((shape for shape in shapes if shape!="numeric_scalar"),shapes[0])
    item=_pick_prefer(bank,"intermediate","practice",non_scalar,used,families); chosen.append(item); used.add(item["candidate_id"]); families.add(item["request"]["generation_family_id"])
    assessment_shape="multiple_choice" if "multiple_choice" in shapes else shapes[0]
    item=_pick_prefer(bank,"intermediate","assessment",assessment_shape,used,families); chosen.append(item); used.add(item["candidate_id"]); families.add(item["request"]["generation_family_id"])
    item=_pick_prefer(bank,"advanced","assessment",assessment_shape,used,families); chosen.append(item)
    return chosen

def _record(bank,candidate):
    cid=candidate["candidate_id"]
    one=lambda field:next((item for item in bank[field] if item.get("candidate_id")==cid),None)
    return {"bank":bank,"candidate_id":cid,"candidate":candidate,"derivation":one("derivations"),"validation":one("validations"),"bank_id":bank["bank_id"],"bank_sha256":bank["bank_sha256"]}

def _action(action): return {"action":action,"actor":"universal_reconciliation_pilot_reviewer","timestamp":"2026-07-30T00:00:00+00:00","reason":"deterministic semantic qualification scenario"}

def _apply_semantic_case(root,payload,normalized):
    difficulty=normalized["difficulty"]; role=normalized["assessment_role"]; shape=payload["candidate"]["answer_contract"]["shape"]
    if difficulty=="introductory" and role=="practice": normalized["human_review_action"]=_action("ACCEPT_FOR_PROMOTION_REVIEW")
    elif difficulty=="intermediate" and role=="practice" and shape=="multiple_choice":
        normalized["rights_evidence"]={"classification":"UNKNOWN","verified":False,"unresolved_requirements":["explicit_candidate_rights_required"]}; normalized["human_review_action"]=_action("ESCALATE_RIGHTS")
    elif difficulty=="intermediate" and role=="practice":
        asset=root/"assets"/"review_only_asset.txt"; asset.parent.mkdir(parents=True,exist_ok=True)
        if not asset.exists(): asset.write_text("noncanonical reconciliation review asset\n")
        normalized["diagram_policy"]={"diagram_required":True,"alt_text_required":True}
        normalized["asset_references"]=[{"asset_identity":"RECONCILIATION_REVIEW_ASSET","path":"assets/review_only_asset.txt","sha256":sha256_file(asset),"role":"question_context","type":"text/plain","alt_text":"Review-only placeholder.","rights_evidence":True}]
        normalized["human_review_action"]=_action("ESCALATE_ASSET")
    elif difficulty=="intermediate" and role=="assessment" and shape=="multiple_choice":
        fp=_fingerprint_report(normalized); normalized["canonical_source_inventory"]=[{"inventory_source":"prior_packet_read_only","candidate_identity":"prior_review_candidate","fingerprints":{"structural_fingerprint":fp["structural_fingerprint"]}}]; normalized["human_review_action"]=_action("RETURN_FOR_CORRECTION")
    elif difficulty=="intermediate" and role=="assessment":
        normalized["curriculum_evidence"]={"validated":False,"reason":"explicit reconciliation curriculum review case"}; normalized["human_review_action"]=_action("ESCALATE_CURRICULUM")
    elif difficulty=="advanced" and role=="assessment" and shape=="multiple_choice": normalized["disallowed"]=True; normalized["human_review_action"]=_action("REJECT")
    elif difficulty=="advanced" and role=="assessment": normalized["upstream_generation_status"]="DEFECT"; normalized["human_review_action"]=_action("REGENERATE_UPSTREAM")
    else: raise CanonicalPromotionPreparationError("unsupported semantic pilot qualification case")

def run_universal_reconciliation_pilot(*,preparation_root=DEFAULT_ROOT,production_root=PRODUCTION_ROOT,run_id=RUN_ID):
    root=prepare_promotion_root(preparation_root)
    if (root/"logs"/run_id/"preparation_summary.json").exists(): raise CanonicalPromotionPreparationError("immutable reconciliation run already exists")
    bank_records=_load_banks(Path(production_root)); normalized=[]; source_rows=[]
    for bank_path,bank in bank_records:
        for candidate in _select_five(bank):
            payload=_record(bank,candidate); item=normalize_input("production_question_bank",payload,ordinal=len(normalized)+1); _apply_semantic_case(root,payload,item)
            normalized.append(item); source_rows.append({"course_id":bank["course_id"],"bank_id":bank["bank_id"],"bank_sha256":bank["bank_sha256"],"bank_path":str(bank_path),"candidate_id":candidate["candidate_id"]})
    if len(normalized)!=30 or len({row["course_id"] for row in source_rows})!=6: raise CanonicalPromotionPreparationError("pilot requires five candidates from each of six banks")
    fingerprints=[_fingerprint_report(item) for item in normalized]; prior=_load_prior_packet_inventory(root,run_id); entries=[]
    for candidate,fingerprint in zip(normalized,fingerprints):
        duplicate=_duplicate_report(candidate,fingerprint,normalized,fingerprints,prior)
        entries.append(_process_candidate(root,run_id,candidate,external_id=f"CPP_UR045_{stable_hash(candidate['candidate_identity'])[:16]}",fingerprint=fingerprint,duplicate=duplicate))
    prepared=[x for x in entries if x["packet_status"]=="PREPARED_FOR_CANONICAL_REVIEW"]
    manifest={"manifest_schema_version":"CANONICAL_PROMOTION_DRY_RUN_MANIFEST_v0_2","run_id":run_id,"plan_only":True,"canonical_write_authorized":False,"database_write_authorized":False,"prepared_external_ids":[x["external_preparation_id"] for x in prepared if x["review_action"]=="ACCEPT_FOR_PROMOTION_REVIEW"],"prepared_packets":[{"external_preparation_id":x["external_preparation_id"],"review_action":"ACCEPT_FOR_PROMOTION_REVIEW","canonical_question_id":None,"canonical_revision_id":None,"path_created":False} for x in prepared if x["review_action"]=="ACCEPT_FOR_PROMOTION_REVIEW"],"sql_instructions":[],"execution_instructions":[],"status":STATUS_FLAGS}
    manifest_path=root/"exports"/run_id/"dry_run_promotion_manifest.json"; manifest_hash=write_json(manifest_path,manifest)
    action_names=("ACCEPT_FOR_PROMOTION_REVIEW","RETURN_FOR_CORRECTION","REJECT","REGENERATE_UPSTREAM","ESCALATE_RIGHTS","ESCALATE_ASSET","ESCALATE_CURRICULUM"); actions={action:sum(x["review_action"]==action for x in entries) for action in action_names}
    summary={"run_id":run_id,"mode":MODE_IDENTIFIER,"execution_profile":EXECUTION_PROFILE,"status":STATUS_FLAGS,"candidate_count":30,"document_driven_count":0,"phase_e_count":0,"production_bank_count":6,"production_candidate_count":30,"prepared_count":len(prepared),"blocked_count":30-len(prepared),"rights_or_provenance_blockers":actions["ESCALATE_RIGHTS"],"asset_or_governance_blockers":actions["ESCALATE_ASSET"],"duplicate_review_cases":sum(x["duplicate_classification"]!="DISTINCT" for x in entries),"returned_for_correction":actions["RETURN_FOR_CORRECTION"],"rejected_or_regenerated":actions["REJECT"]+actions["REGENERATE_UPSTREAM"],"actions":actions,"source_banks":source_rows,"canonical_ids_assigned":0,"canonical_paths_written":0,"database_access":"none","adaptive_platform_writes":False,"source_candidate_mutation":False,"dry_run_manifest":{"path":root_relative(root,manifest_path),"sha256":manifest_hash},"packets":entries}
    write_json(root/"logs"/run_id/"preparation_summary.json",summary)
    audit={"verdict":"PASS" if len(prepared)>=12 and all(actions[x]>=1 for x in action_names) else "BLOCKED","candidate_count":30,"prepared_count":len(prepared),"asset_rights_truthiness_accepted":False,"ordinal_name_position_dependence":False,"canonical_ids_assigned":0,"canonical_paths_written":0,"database_access":"none","adaptive_platform_writes":False}
    write_json(root/"logs"/run_id/"reconciliation_gate_audit.json",audit)
    state=load_json(root/"state.json"); state.setdefault("runs",[]).append(run_id); state.setdefault("run_roots",{})[run_id]=str(root); write_json(root/"state.json",state)
    return summary

def reopen_universal_reconciliation_pilot(*,preparation_root=DEFAULT_ROOT,run_id=RUN_ID): return reopen_preparation_run(run_id,preparation_root=preparation_root)
