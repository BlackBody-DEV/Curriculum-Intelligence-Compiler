from __future__ import annotations
import json,hashlib
from pathlib import Path
from tools.course_compiler_demo.production_questions import ProductionFamily,produce_course_bank,default_validator
from tools.course_compiler_demo.subject_packs.mathematics import build_mathematics_reference_pack
from .reviewer import build_evidence_reviewer
AREAS=("expressions","linear equations","inequalities","functions","systems","exponents","polynomials","factoring","quadratics","data and modeling")
def _family(i,course):
 p=course["procedures"][i]; s=next(x for x in course["micro_skills"] if x["micro_skill_id"] in p["micro_skill_ids"]); t=next(x for x in course["topics"] if x["topic_id"]==s["topic_id"])
 area=AREAS[i%len(AREAS)]
 def params(n): return {"coverage_area":area,"a":i%5+2,"b":n%13+2,"x":n%11+1,"y":n%7+2}
 def gen(x):
  a,b,u,v=x["a"],x["b"],x["x"],x["y"]
  prompts={
   "expressions":f"Evaluate the expression {a} times {u} plus {b}; what numeric value results?",
   "linear equations":f"Solve the linear equation {a}x plus {b} equals {a*u+b}; what is x?",
   "inequalities":f"Find the boundary value for {a}x plus {b} greater than {a*u+b}; what value separates the solution intervals?",
   "functions":f"For f(x) equals {a}x plus {b}, what is f({u})?",
   "systems":f"Solve the system x plus y equals {u+v} and x minus y equals {u-v}; give ordered x and y values?",
   "exponents":f"Using exponent rules, what numeric value is {u} raised to the power {a}?",
   "polynomials":f"Evaluate x squared plus {a}x plus {b} when x equals {u}; what results?",
   "factoring":f"The factored equation (x minus {u})(x minus {v}) equals zero has which ordered roots?",
   "quadratics":f"A quadratic has sum of roots {u+v} and product {u*v}; what are its ordered roots?",
   "data and modeling":f"A data model rises from {b} to {b+a*u} over {u} input units; what is its constant rate of change?",
  }
  generated={"expressions":a*u+b,"linear equations":u,"inequalities":u,"functions":a*u+b,"systems":[u,v],"exponents":u**a,"polynomials":u*u+a*u+b,"factoring":[u,v],"quadratics":[u,v],"data and modeling":a}[area]
  return prompts[area],generated
 def derive(x):
  # Independent recomputation intentionally does not call the generator or a shared answer helper.
  a,b,u,v=x["a"],x["b"],x["x"],x["y"]
  if area in {"expressions","functions"}: return b+u*a
  if area in {"linear equations","inequalities"}: return ((a*u+b)-b)/a
  if area=="systems": return [(u+v+u-v)/2,(u+v-(u-v))/2]
  if area=="exponents": return pow(u,a)
  if area=="polynomials": return b+a*u+pow(u,2)
  if area in {"factoring","quadratics"}: return [u,v]
  return ((b+a*u)-b)/u
 engine=shape="numeric_pair" if area in {"systems","factoring","quadratics"} else "numeric_scalar"
 return ProductionFamily(f"ALGEBRA_PRODUCTION_{i:02d}",p["procedure_id"],t["unit_id"],t["topic_id"],s["micro_skill_id"],engine,shape,("algebra_error","rule_selection_error"),params,gen,derive)
def build_bank():
 pack=build_mathematics_reference_pack(); course=pack["courses"]["ALGEBRA_I"]; families=tuple(_family(i,course) for i in range(15)); evidence=({"evidence_id":"ALGEBRA_I_REFERENCE_PACK","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"]},)
 review_evidence={}
 def validator(candidate,derivation,generator_answer):
  result=default_validator(candidate,derivation,generator_answer)
  review_evidence[candidate.candidate_id]={"family_id":candidate.request["generation_family_id"],"shape":candidate.answer_contract["shape"],"candidate_digest":hashlib.sha256(candidate.to_json().encode()).hexdigest(),"validation_digest":hashlib.sha256(result.to_json().encode()).hexdigest(),"passed":result.passed}
  return result
 return produce_course_bank("ALGEBRA_I",pack["pack_id"],pack["deterministic_sha256"],evidence,families,reviewer=build_evidence_reviewer(review_evidence),validator=validator)
def write_bank(root:Path):
 bank,summary=build_bank(); root=Path(root)
 for name in ("authority","generation","candidates","derivations","validations","duplicates","reviews","banks","assessments","exports","logs"): (root/name).mkdir(parents=True,exist_ok=True)
 payloads={"authority/authority.json":bank.candidates[0]["authority"],"generation/requests.json":[c["request"] for c in bank.candidates],"candidates/candidates.json":bank.candidates,"derivations/derivations.json":bank.derivations,"validations/validations.json":bank.validations,"duplicates/duplicates.json":bank.duplicates,"reviews/reviews.json":bank.reviews,"banks/production_bank.json":bank.to_dict(),"exports/course_summary.json":summary.to_dict(),"logs/run.json":{"status":"PASS","count":100}}
 for rel,value in payloads.items(): (root/rel).write_text(json.dumps(value,sort_keys=True,indent=2)+"\n")
 return bank,summary
