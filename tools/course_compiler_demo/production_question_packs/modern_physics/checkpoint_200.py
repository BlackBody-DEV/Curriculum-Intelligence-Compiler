"""Modern Physics second locked cohort."""
from dataclasses import replace
import hashlib
from tools.course_compiler_demo.production_questions import ProductionQuestionCandidateV1, duplicate_record, produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog, validate_physics_engineering_course_catalog
from .bank import _family, artifact_reviewer, build_bank, modern_physics_validator


def _checkpoint_family(index, course):
    base=_family(index,course)
    def parameters(n,builder=base.parameter_builder):
        row=builder(n); row["a"]+=200.0; row["b"]+=10.0; row["frequency"]+=1e15; row["beta"]+=0.10; row["angle"]+=20.0; return row
    return replace(base,parameter_builder=parameters)


def build_checkpoint_bank():
    existing=build_bank()[0]; pack=build_physics_engineering_course_catalog(); validate_physics_engineering_course_catalog(pack); course=pack["courses"]["MODERN_PHYSICS"]; families=tuple(_checkpoint_family(i,course) for i in range(10)); evidence=({"evidence_id":"MODERN_PHYSICS:COURSE_CATALOG","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"],"access":"READ_ONLY_REFERENCE"},); seen={}
    for row in existing.candidates: duplicate_record(ProductionQuestionCandidateV1(**row),seen)
    inspected={}
    def validator(candidate,derivation,answer): result=modern_physics_validator(candidate,derivation,answer); inspected[candidate.candidate_id]=(candidate,derivation,result); return result
    bank,summary=produce_course_bank("MODERN_PHYSICS",pack["pack_id"],pack["deterministic_sha256"],evidence,families,reviewer=lambda subject,level:artifact_reviewer(families,inspected,subject,level),duplicate_analyzer=lambda candidate,_local:duplicate_record(candidate,seen),validator=validator)
    return replace(bank,bank_id="bank:MODERN_PHYSICS:checkpoint-200:v1"),replace(summary,summary_id="summary:MODERN_PHYSICS:checkpoint-200:v1")


def audit_checkpoint():
    old=build_bank()[0]; new,summary=build_checkpoint_bank(); banks=(old,new); candidates=[row for bank in banks for row in bank.candidates]; ids=[row["candidate_id"] for row in candidates]; prompts=[hashlib.sha256(row["prompt"].lower().encode()).hexdigest() for row in candidates]; fingerprints=[row["fingerprint"] for bank in banks for row in bank.duplicates]; records=[ProductionQuestionCandidateV1(**row).to_json() for row in candidates]; passed=len(set(ids))==len(set(prompts))==len(set(fingerprints))==len(set(records))==200 and summary.validated==100
    return {"course_id":"MODERN_PHYSICS","before":100,"added":100,"after":len(set(ids)),"duplicate_identities":len(ids)-len(set(ids)),"exact_prompt_duplicates":len(prompts)-len(set(prompts)),"fingerprint_duplicates":len(fingerprints)-len(set(fingerprints)),"exact_record_duplicates":len(records)-len(set(records)),"validated":summary.validated,"status":"PASS" if passed else "FAIL"}
