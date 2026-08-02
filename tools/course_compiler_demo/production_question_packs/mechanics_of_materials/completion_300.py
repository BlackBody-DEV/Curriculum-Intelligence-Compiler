from dataclasses import replace
import hashlib
from tools.course_compiler_demo.production_questions import ProductionQuestionCandidateV1,duplicate_record,produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog,validate_physics_engineering_course_catalog
from .bank import _family,build_bank,materials_validator,reviewer
from .checkpoint_200 import build_checkpoint_bank
def _completion_family(i,course):
 base=_family(i,course)
 def params(n,builder=base.parameter_builder):
  x=builder(n);x["a"]+=400;x["b"]+=20;x["load"]+=400;x["area"]+=400;x["length"]+=4000;x["modulus"]+=40;x["radius"]+=20;x["inertia"]+=40000;x["temperature"]+=40;return x
 return replace(base,parameter_builder=params)
def build_completion_bank():
 prior=(build_bank()[0],build_checkpoint_bank()[0]);pack=build_physics_engineering_course_catalog();validate_physics_engineering_course_catalog(pack);course=pack["courses"]["MECHANICS_OF_MATERIALS"];families=tuple(_completion_family(i,course) for i in range(10));evidence=({"evidence_id":"MECHANICS_OF_MATERIALS:COURSE_CATALOG","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"],"access":"READ_ONLY_REFERENCE"},);seen={};inspected={}
 for b in prior:
  for x in b.candidates:duplicate_record(ProductionQuestionCandidateV1(**x),seen)
 def validator(c,d,a):r=materials_validator(c,d,a);inspected[c.candidate_id]=(c,d,r);return r
 bank,summary=produce_course_bank("MECHANICS_OF_MATERIALS",pack["pack_id"],pack["deterministic_sha256"],evidence,families,reviewer=lambda s,l:reviewer(families,inspected,s,l),duplicate_analyzer=lambda c,_:duplicate_record(c,seen),validator=validator);return replace(bank,bank_id="bank:MECHANICS_OF_MATERIALS:completion-300:v1"),summary
def audit_completion():
 banks=(build_bank()[0],build_checkpoint_bank()[0],build_completion_bank()[0]);rows=[x for b in banks for x in b.candidates];ids=[x["candidate_id"] for x in rows];p=[hashlib.sha256(x["prompt"].lower().encode()).hexdigest() for x in rows];f=[x["fingerprint"] for b in banks for x in b.duplicates];r=[ProductionQuestionCandidateV1(**x).to_json() for x in rows];ok=len(set(ids))==len(set(p))==len(set(f))==len(set(r))==300;return {"before":200,"added":100,"after":len(set(ids)),"status":"PASS" if ok else "FAIL"}
