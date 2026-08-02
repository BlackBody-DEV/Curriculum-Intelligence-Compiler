from dataclasses import replace
import hashlib
from tools.course_compiler_demo.production_questions import ProductionQuestionCandidateV1,duplicate_record,produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog
from .bank import build_bank,validator
from .checkpoint_200 import _f,build_checkpoint_bank
def _g(i,c):
 b=_f(i,c)
 def p(n):x=b.parameter_builder(n);x.update(a=x["a"]+200,b=x["b"]+10,flow=x["flow"]+.5,area=x["area"]+.2,velocity=x["velocity"]+10,head=x["head"]+20,width=x["width"]+2,depth=x["depth"]+1);return x
 return replace(b,parameter_builder=p)
def build_completion_bank():
 prior=(build_bank()[0],build_checkpoint_bank()[0]);pack=build_physics_engineering_course_catalog();fs=tuple(_g(i,pack["courses"]["HYDRAULICS"]) for i in range(10));seen={}
 for b in prior:
  for x in b.candidates:duplicate_record(ProductionQuestionCandidateV1(**x),seen)
 ev=({"evidence_id":"HYDRAULICS:CATALOG","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"]},);b,s=produce_course_bank("HYDRAULICS",pack["pack_id"],pack["deterministic_sha256"],ev,fs,duplicate_analyzer=lambda c,_:duplicate_record(c,seen),validator=validator);return replace(b,bank_id="bank:HYDRAULICS:completion-300:v1"),s
def audit_completion():
 bs=(build_bank()[0],build_checkpoint_bank()[0],build_completion_bank()[0]);r=[x for b in bs for x in b.candidates];v=([x["candidate_id"] for x in r],[hashlib.sha256(x["prompt"].lower().encode()).hexdigest() for x in r],[x["fingerprint"] for b in bs for x in b.duplicates],[ProductionQuestionCandidateV1(**x).to_json() for x in r]);return {"after":300,"status":"PASS" if all(len(set(x))==300 for x in v) else "FAIL"}
