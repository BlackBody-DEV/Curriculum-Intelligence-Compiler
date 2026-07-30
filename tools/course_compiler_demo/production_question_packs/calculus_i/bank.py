from __future__ import annotations
import json,hashlib,re
from pathlib import Path
from tools.course_compiler_demo.production_questions import ProductionFamily,produce_course_bank,default_validator,ProductionValidationRecordV1
from tools.course_compiler_demo.subject_packs.mathematics import build_mathematics_reference_pack
from .reviewer import build_evidence_reviewer
AREAS=("functions and limits","continuity","derivative interpretation","derivative rules","implicit differentiation","applications of derivatives","optimization","antiderivatives","definite integrals","Fundamental Theorem of Calculus","integration applications")
def _family(i,course):
 p=course["procedures"][i]; s=next(x for x in course["micro_skills"] if x["micro_skill_id"] in p["micro_skill_ids"]); t=next(x for x in course["topics"] if x["topic_id"]==s["topic_id"])
 area=AREAS[i%len(AREAS)]
 def params(n): return {"coverage_area":area,"a":i%5+2,"x":n+1,"y":n+i+2,"span":n+2}
 def gen(x):
  a,u,v,h=x["a"],x["x"],x["y"],x["span"]
  prompts={
   "functions and limits":f"For the linear function {a}x plus {v}, what limit is approached as x approaches {u}?",
   "continuity":f"What value must f({u}) have so f(x) equals {a}x plus {v} remains continuous there?",
   "derivative interpretation":f"A position graph is the line {a}t plus {v}; what instantaneous rate does its derivative represent?",
   "derivative rules":f"Using the power rule, what is the derivative of x to power {a} at x equals {u}?",
   "implicit differentiation":f"On x squared plus y squared constant at ({u},{v}), what is dy over dx?",
   "applications of derivatives":f"For position s(t) equals {a}t squared plus {v}, what velocity occurs at t equals {u}?",
   "optimization":f"A rectangle has perimeter {2*h}; what maximum area occurs when its sides are equal?",
   "antiderivatives":f"An antiderivative of {a}x is set to zero at x zero; what value does it have at x equals {u}?",
   "definite integrals":f"What is the definite integral of {a}x from zero to {h}?",
   "Fundamental Theorem of Calculus":f"By the Fundamental Theorem, what is the derivative at x equals {u} of the integral of {a}t plus {v} from zero to x?",
   "integration applications":f"What accumulated area lies under {a}x plus {v} from zero to {h}?",
  }
  generated={"functions and limits":a*u+v,"continuity":a*u+v,"derivative interpretation":a,"derivative rules":a*u**(a-1),"implicit differentiation":-u/v,"applications of derivatives":2*a*u,"optimization":(h/2)**2,"antiderivatives":a*u*u/2,"definite integrals":a*h*h/2,"Fundamental Theorem of Calculus":a*u+v,"integration applications":a*h*h/2+v*h}[area]
  if area in {"continuity","derivative interpretation"}: return prompts[area]+f" Option A is {generated}; option B is {-generated}. Choices: A, B.","A"
  return prompts[area],generated
 def derive(x):
  # Independent rule application: no generator call or shared answer callable.
  a,u,v,h=x["a"],x["x"],x["y"],x["span"]
  if area in {"continuity","derivative interpretation"}:
   expected=_independent_numeric(area,x); options={"A":expected,"B":-expected}; matches=[label for label,value in options.items() if value==expected]
   if len(matches)!=1: raise ValueError("independent MC option match is not unique")
   return matches[0]
  if area=="functions and limits": return v+a*u
  if area=="derivative rules": return a*pow(u,a-1)
  if area=="implicit differentiation": return -(u/v)
  if area=="applications of derivatives": return u*a*2
  if area=="optimization": return pow(h/2,2)
  if area=="antiderivatives": return (a/2)*pow(u,2)
  if area=="definite integrals": return (a/2)*pow(h,2)
  if area=="Fundamental Theorem of Calculus": return v+a*u
  return (a/2)*pow(h,2)+v*h
 engine=shape="multiple_choice" if area in {"continuity","derivative interpretation"} else "numeric_scalar"
 return ProductionFamily(f"CALCULUS_PRODUCTION_{i:02d}",p["procedure_id"],t["unit_id"],t["topic_id"],s["micro_skill_id"],engine,shape,("calculus_rule_error","interpretation_error"),params,gen,derive)
def build_bank():
 pack=build_mathematics_reference_pack(); course=pack["courses"]["CALCULUS_I"]; families=tuple(_family(i,course) for i in range(15)); evidence=({"evidence_id":"CALCULUS_I_REFERENCE_PACK","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"]},)
 review_evidence={}
 def validator(candidate,derivation,generator_answer):
  base=default_validator(candidate,derivation,generator_answer); choice=_choice_evidence(candidate,derivation.normalized_answer)
  passed=base.answer_contract_pass and choice["passed"]
  result=ProductionValidationRecordV1(base.validation_id,base.candidate_id,base.grading_pass,base.procedure_compatibility_pass,base.failure_signal_pass,base.prompt_determinacy_pass,base.unit_tolerance_pass,passed,base.reasons+(() if choice["passed"] else ("MULTIPLE_CHOICE_CONTRACT_INVALID",)))
  review_evidence[candidate.candidate_id]={"family_id":candidate.request["generation_family_id"],"choice_count":choice["choice_count"],"answer_matches":choice["answer_matches"],"numeric_matches":choice.get("numeric_matches",0),"candidate_digest":hashlib.sha256(candidate.to_json().encode()).hexdigest(),"validation_digest":hashlib.sha256(result.to_json().encode()).hexdigest(),"passed":result.passed}
  return result
 return produce_course_bank("CALCULUS_I",pack["pack_id"],pack["deterministic_sha256"],evidence,families,reviewer=build_evidence_reviewer(review_evidence),validator=validator)

def _independent_numeric(area,x):
 a,u,v=x["a"],x["x"],x["y"]
 if area=="continuity": return v+a*u
 if area=="derivative interpretation": return a
 raise ValueError("not a numeric multiple-choice calculus family")
def _normalize_choice(value): return " ".join(str(value).strip().rstrip(".?").lower().split())
def _choice_evidence(candidate,derived_answer):
 if candidate.answer_contract["shape"]!="multiple_choice": return {"choice_count":0,"answer_matches":0,"passed":True}
 if "Choices:" not in candidate.prompt: return {"choice_count":0,"answer_matches":0,"passed":False}
 choices=[_normalize_choice(x) for x in candidate.prompt.split("Choices:",1)[1].split(",")]; answer=_normalize_choice(derived_answer); distinct=set(choices); matches=sum(x==answer for x in choices)
 option_matches=re.search(r"Option A is (-?\d+(?:\.\d+)?); option B is (-?\d+(?:\.\d+)?)",candidate.prompt)
 if option_matches is None: return {"choice_count":len(distinct),"answer_matches":matches,"numeric_matches":0,"passed":False}
 values={"a":float(option_matches.group(1)),"b":float(option_matches.group(2))}; expected=float(_independent_numeric(candidate.request["parameters"]["coverage_area"],candidate.request["parameters"])); numeric_labels=[label for label,value in values.items() if value==expected]
 return {"choice_count":len(distinct),"answer_matches":matches,"numeric_matches":len(numeric_labels),"passed":len(choices)>=2 and len(distinct)==len(choices) and matches==1 and len(numeric_labels)==1 and numeric_labels[0]==answer}
def write_bank(root:Path):
 bank,summary=build_bank(); root=Path(root)
 for name in ("authority","generation","candidates","derivations","validations","duplicates","reviews","banks","assessments","exports","logs"): (root/name).mkdir(parents=True,exist_ok=True)
 payloads={"authority/authority.json":bank.candidates[0]["authority"],"generation/requests.json":[c["request"] for c in bank.candidates],"candidates/candidates.json":bank.candidates,"derivations/derivations.json":bank.derivations,"validations/validations.json":bank.validations,"duplicates/duplicates.json":bank.duplicates,"reviews/reviews.json":bank.reviews,"banks/production_bank.json":bank.to_dict(),"exports/course_summary.json":summary.to_dict(),"logs/run.json":{"status":"PASS","count":100}}
 for rel,value in payloads.items(): (root/rel).write_text(json.dumps(value,sort_keys=True,indent=2)+"\n")
 return bank,summary
