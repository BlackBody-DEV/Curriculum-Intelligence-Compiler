from dataclasses import replace
import hashlib
from tools.course_compiler_demo.production_questions import ProductionQuestionCandidateV1,duplicate_record,produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog,validate_physics_engineering_course_catalog
from .bank import _family,build_bank,materials_validator,reviewer
def _checkpoint_family(i,course):
 base=_family(i,course)
 def params(n,builder=base.parameter_builder):
  x=builder(n); x["a"]+=200;x["b"]+=10;x["load"]+=200;x["area"]+=200;x["length"]+=2000;x["modulus"]+=20;x["radius"]+=10;x["inertia"]+=20000;x["temperature"]+=20;return x
 return replace(base,parameter_builder=params)
def build_checkpoint_bank():
 old=build_bank()[0];pack=build_physics_engineering_course_catalog();validate_physics_engineering_course_catalog(pack);course=pack["courses"]["MECHANICS_OF_MATERIALS"];families=tuple(_checkpoint_family(i,course) for i in range(10));evidence=({"evidence_id":"MECHANICS_OF_MATERIALS:COURSE_CATALOG","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"],"access":"READ_ONLY_REFERENCE"},);seen={};inspected={}
 for x in old.candidates:duplicate_record(ProductionQuestionCandidateV1(**x),seen)
 def validator(c,d,a):r=materials_validator(c,d,a);inspected[c.candidate_id]=(c,d,r);return r
 bank,summary=produce_course_bank("MECHANICS_OF_MATERIALS",pack["pack_id"],pack["deterministic_sha256"],evidence,families,reviewer=lambda s,l:reviewer(families,inspected,s,l),duplicate_analyzer=lambda c,_:duplicate_record(c,seen),validator=validator);return replace(bank,bank_id="bank:MECHANICS_OF_MATERIALS:checkpoint-200:v1"),summary
def audit_checkpoint():
 banks=(build_bank()[0],build_checkpoint_bank()[0]);rows=[x for b in banks for x in b.candidates];ids=[x["candidate_id"] for x in rows];prompts=[hashlib.sha256(x["prompt"].lower().encode()).hexdigest() for x in rows];fps=[x["fingerprint"] for b in banks for x in b.duplicates];records=[ProductionQuestionCandidateV1(**x).to_json() for x in rows];ok=len(set(ids))==len(set(prompts))==len(set(fps))==len(set(records))==200;return {"before":100,"added":100,"after":len(set(ids)),"status":"PASS" if ok else "FAIL"}
