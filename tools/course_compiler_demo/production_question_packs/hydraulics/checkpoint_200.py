from dataclasses import replace
import hashlib
from tools.course_compiler_demo.production_questions import ProductionQuestionCandidateV1,duplicate_record,produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog
from .bank import _family,build_bank,validator
def _f(i,c):
 b=_family(i,c)
 def p(n):x=b.parameter_builder(n);x.update(a=x["a"]+200,b=x["b"]+10,flow=x["flow"]+.5,area=x["area"]+.2,velocity=x["velocity"]+10,head=x["head"]+20,width=x["width"]+2,depth=x["depth"]+1);return x
 return replace(b,parameter_builder=p)
def build_checkpoint_bank():
 old=build_bank()[0];pack=build_physics_engineering_course_catalog();fs=tuple(_f(i,pack["courses"]["HYDRAULICS"]) for i in range(10));seen={};[duplicate_record(ProductionQuestionCandidateV1(**x),seen) for x in old.candidates];ev=({"evidence_id":"HYDRAULICS:CATALOG","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"]},);b,s=produce_course_bank("HYDRAULICS",pack["pack_id"],pack["deterministic_sha256"],ev,fs,duplicate_analyzer=lambda c,_:duplicate_record(c,seen),validator=validator);return replace(b,bank_id="bank:HYDRAULICS:checkpoint-200:v1"),s
def audit_checkpoint():
 bs=(build_bank()[0],build_checkpoint_bank()[0]);r=[x for b in bs for x in b.candidates];v=([x["candidate_id"] for x in r],[hashlib.sha256(x["prompt"].lower().encode()).hexdigest() for x in r],[x["fingerprint"] for b in bs for x in b.duplicates]);return {"after":200,"status":"PASS" if all(len(set(x))==200 for x in v) else "FAIL"}
