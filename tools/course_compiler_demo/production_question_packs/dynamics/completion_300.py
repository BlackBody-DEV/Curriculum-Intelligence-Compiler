"""Dynamics third locked cohort and cumulative completion audit."""
from dataclasses import replace
import hashlib
from tools.course_compiler_demo.production_questions import ProductionQuestionCandidateV1,duplicate_record,produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog,validate_physics_engineering_course_catalog
from .bank import _family,artifact_reviewer,build_bank,dynamics_validator
from .checkpoint_200 import build_checkpoint_bank


def _completion_family(index,course):
    base=_family(index,course)
    def parameters(n,builder=base.parameter_builder):
        row=builder(n); row["a"]+=400.0; row["b"]+=40.0; row["time"]+=20.0; row["mass"]+=40.0; row["speed"]+=40.0; row["radius"]+=20.0; return row
    return replace(base,parameter_builder=parameters)


def build_completion_bank():
    prior=(build_bank()[0],build_checkpoint_bank()[0]); pack=build_physics_engineering_course_catalog(); validate_physics_engineering_course_catalog(pack); course=pack["courses"]["DYNAMICS"]; families=tuple(_completion_family(i,course) for i in range(10)); evidence=({"evidence_id":"DYNAMICS:COURSE_CATALOG","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"],"access":"READ_ONLY_REFERENCE"},); seen={}
    for bank in prior:
        for row in bank.candidates: duplicate_record(ProductionQuestionCandidateV1(**row),seen)
    inspected={}
    def validator(candidate,derivation,answer): result=dynamics_validator(candidate,derivation,answer); inspected[candidate.candidate_id]=(candidate,derivation,result); return result
    bank,summary=produce_course_bank("DYNAMICS",pack["pack_id"],pack["deterministic_sha256"],evidence,families,reviewer=lambda subject,level:artifact_reviewer(families,inspected,subject,level),duplicate_analyzer=lambda candidate,_local:duplicate_record(candidate,seen),validator=validator)
    return replace(bank,bank_id="bank:DYNAMICS:completion-300:v1"),replace(summary,summary_id="summary:DYNAMICS:completion-300:v1")


def audit_completion():
    banks=(build_bank()[0],build_checkpoint_bank()[0],build_completion_bank()[0]); candidates=[row for bank in banks for row in bank.candidates]; ids=[row["candidate_id"] for row in candidates]; prompts=[hashlib.sha256(row["prompt"].lower().encode()).hexdigest() for row in candidates]; fingerprints=[row["fingerprint"] for bank in banks for row in bank.duplicates]; records=[ProductionQuestionCandidateV1(**row).to_json() for row in candidates]; passed=len(set(ids))==len(set(prompts))==len(set(fingerprints))==len(set(records))==300
    return {"course_id":"DYNAMICS","before":200,"added":100,"after":len(set(ids)),"duplicate_identities":len(ids)-len(set(ids)),"exact_prompt_duplicates":len(prompts)-len(set(prompts)),"fingerprint_duplicates":len(fingerprints)-len(set(fingerprints)),"exact_record_duplicates":len(records)-len(set(records)),"validated":100,"status":"PASS" if passed else "FAIL"}
