"""Modern Physics third locked cohort and cumulative completion audit."""
from dataclasses import replace
import hashlib
from tools.course_compiler_demo.production_questions import ProductionQuestionCandidateV1,duplicate_record,produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog,validate_physics_engineering_course_catalog
from .bank import _family,artifact_reviewer,build_bank,modern_physics_validator
from .checkpoint_200 import build_checkpoint_bank


def _completion_family(index,course):
    base=_family(index,course)
    def parameters(n,builder=base.parameter_builder):
        row=builder(n); row["a"]+=400.0; row["b"]+=20.0; row["frequency"]+=2e15; row["beta"]+=0.20; row["angle"]+=40.0; return row
    return replace(base,parameter_builder=parameters)


def build_completion_bank():
    prior=(build_bank()[0],build_checkpoint_bank()[0]); pack=build_physics_engineering_course_catalog(); validate_physics_engineering_course_catalog(pack); course=pack["courses"]["MODERN_PHYSICS"]; families=tuple(_completion_family(i,course) for i in range(10)); evidence=({"evidence_id":"MODERN_PHYSICS:COURSE_CATALOG","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"],"access":"READ_ONLY_REFERENCE"},); seen={}
    for bank in prior:
        for row in bank.candidates: duplicate_record(ProductionQuestionCandidateV1(**row),seen)
    inspected={}
    def validator(candidate,derivation,answer): result=modern_physics_validator(candidate,derivation,answer); inspected[candidate.candidate_id]=(candidate,derivation,result); return result
    bank,summary=produce_course_bank("MODERN_PHYSICS",pack["pack_id"],pack["deterministic_sha256"],evidence,families,reviewer=lambda subject,level:artifact_reviewer(families,inspected,subject,level),duplicate_analyzer=lambda candidate,_local:duplicate_record(candidate,seen),validator=validator)
    return replace(bank,bank_id="bank:MODERN_PHYSICS:completion-300:v1"),replace(summary,summary_id="summary:MODERN_PHYSICS:completion-300:v1")


def audit_completion():
    banks=(build_bank()[0],build_checkpoint_bank()[0],build_completion_bank()[0]); candidates=[row for bank in banks for row in bank.candidates]; ids=[row["candidate_id"] for row in candidates]; prompts=[hashlib.sha256(row["prompt"].lower().encode()).hexdigest() for row in candidates]; fingerprints=[row["fingerprint"] for bank in banks for row in bank.duplicates]; records=[ProductionQuestionCandidateV1(**row).to_json() for row in candidates]; passed=len(set(ids))==len(set(prompts))==len(set(fingerprints))==len(set(records))==300
    return {"course_id":"MODERN_PHYSICS","before":200,"added":100,"after":len(set(ids)),"duplicate_identities":len(ids)-len(set(ids)),"exact_prompt_duplicates":len(prompts)-len(set(prompts)),"fingerprint_duplicates":len(fingerprints)-len(set(fingerprints)),"exact_record_duplicates":len(records)-len(set(records)),"validated":100,"status":"PASS" if passed else "FAIL"}
