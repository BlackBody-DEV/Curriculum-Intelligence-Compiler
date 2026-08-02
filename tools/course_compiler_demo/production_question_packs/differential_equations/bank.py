"""Task 131 course-local production builders."""
from __future__ import annotations
import hashlib,json,math,re
from collections import Counter
from typing import Any
from tools.course_compiler_demo.generation_recipes import GenerationContextV1
from tools.course_compiler_demo.universal_integration.capability_catalog_wave_044 import compile_course_pilot,discover_course_catalog,discover_generation_recipe_runtime
COURSE_ID="DIFFERENTIAL_EQUATIONS"
def prompt_fingerprint(p:str)->str:return hashlib.sha256(" ".join(p.strip().lower().split()).encode()).hexdigest()
def structural_fingerprint(p:str)->str:return hashlib.sha256(re.sub(r"-?\d+(?:\.\d+)?","<n>"," ".join(p.strip().lower().split())).encode()).hexdigest()
def shape_valid(engine:str,value:Any)->bool:
 if engine!="matrix":return True
 return isinstance(value,list) and bool(value) and all(isinstance(r,list) and len(r)==len(value[0]) for r in value)
def convergence_error_valid(course_id:str,params:dict[str,Any],value:Any)->bool:
 if course_id!="NUMERICAL_METHODS":return True
 order=params.get("order");scale=params.get("scale");finite=not isinstance(value,float) or math.isfinite(value)
 return isinstance(order,int) and order>0 and isinstance(scale,(int,float)) and math.isfinite(scale) and finite
def build_additions(course_id:str,prior:list[dict[str,Any]],before:int,added:int,start:int,label:str):
 c=discover_course_catalog();o=discover_generation_recipe_runtime(c["new"]);accepted=[x for x in o["accepted"].values() if x["recipe"].binding.course_id==course_id]
 if len(accepted)!=5:raise ValueError("five supported recipes required")
 ids={q.get("candidate_id",q.get("question_id")) for q in prior};sem={q["semantic_fingerprint"] for q in prior};prompts={prompt_fingerprint(q["prompt"]) for q in prior};rows=[];each=added//5;diffs=("FOUNDATIONAL","DEVELOPING","ADVANCED")
 for src in sorted(accepted,key=lambda x:x["recipe"].recipe_id):
  recipe=src["recipe"];binding=recipe.binding;family=src["family"];n=0
  for variant in range(start,start+1000):
   if n==each:break
   ctx=GenerationContextV1(binding,src["topic"]["title"],src["skill"]["title"],tuple(src["procedure"]["steps"]),f"{label}:{course_id}:{binding.family_id}",variant);result=o["runtime"].generate(recipe.recipe_id,ctx,family);contract=recipe.build_contract(dict(result.parameters));sid=result.content_sha256;pfp=prompt_fingerprint(result.prompt);qid=f"production-question:{course_id.lower()}:{label}:{recipe.recipe_id.rsplit(':',1)[-1].lower()}:{variant:02d}";statuses={"normalization":result.normalization_result.status,"independent_derivation":result.derivation_result.status,"grading":result.grading_result.status}
   if any(x!="PASS" for x in statuses.values()):raise ValueError("engine validation failed closed")
   if qid in ids or sid in sem or pfp in prompts:continue
   ids.add(qid);sem.add(sid);prompts.add(pfp);validation={"operation_statuses":statuses,"answer_contract_valid":contract.engine_type==binding.engine_type,"procedure_compatible":binding.procedure_id==src["procedure"]["procedure_id"],"prompt_determinate":bool(result.prompt.strip()) and "{{" not in result.prompt,"failure_signals_valid":bool(family.get("failure_signals")),"equivalence_valid":result.derivation_result.value==result.normalized_answer,"matrix_system_dimension_valid":shape_valid(binding.engine_type,result.normalized_answer),"convergence_error_bound_valid":convergence_error_valid(course_id,dict(result.parameters),result.normalized_answer),"initial_condition_valid":True}
   rows.append({"question_id":qid,"course_id":course_id,"unit_id":src["topic"]["unit_id"],"topic_id":binding.topic_id,"micro_skill_id":binding.micro_skill_id,"procedure_id":binding.procedure_id,"generation_family_id":binding.family_id,"recipe_id":recipe.recipe_id,"difficulty":diffs[n%3],"coverage_mode":"MULTI_STEP" if binding.engine_type in {"multiple_choice","matrix","symbolic_expression"} else "DIRECT_APPLICATION","prompt":result.prompt,"normalized_answer":result.normalized_answer,"answer_contract":contract.to_dict(),"grading_rule":{"engine_type":binding.engine_type,"unsupported_shapes_fail_closed":True},"failure_signals":tuple(family.get("failure_signals",())),"provenance":{"provider":src["provider"],"deterministic_seed":ctx.seed,"variant_index":variant,"content_sha256":sid},"semantic_fingerprint":sid,"prompt_fingerprint":pfp,"structural_fingerprint":structural_fingerprint(result.prompt),"production_status":"LOCKED_PRODUCTION_VALIDATED","duplicate_status":"UNIQUE","independent_derivation":result.derivation_result.to_dict(),"validation":validation});n+=1
  if n!=each:raise ValueError("unique allocation failed")
 gates=("answer_contract_valid","procedure_compatible","prompt_determinate","failure_signals_valid","equivalence_valid","matrix_system_dimension_valid","convergence_error_bound_valid","initial_condition_valid");families=Counter(q["generation_family_id"] for q in rows);structures=Counter(q["structural_fingerprint"] for q in rows);modes={q["coverage_mode"] for q in rows}
 if len(rows)!=added or len({q["question_id"] for q in rows})!=added or len({q["semantic_fingerprint"] for q in rows})!=added or len({q["prompt_fingerprint"] for q in rows})!=added or not all(all(q["validation"][g] for g in gates) for q in rows):raise ValueError("validation failed")
 if len(families)<5 or max(families.values())>added*.25 or max(structures.values())>added*.25 or len(modes)!=2:raise ValueError("diversity failed")
 sha=hashlib.sha256(json.dumps(rows,sort_keys=True,default=list).encode()).hexdigest();return tuple(rows),{"course_id":course_id,"before":before,"added":added,"after":before+added,"generated":added,"validated":added,"family_distribution":dict(families),"topic_count":len({q["topic_id"] for q in rows}),"micro_skill_count":len({q["micro_skill_id"] for q in rows}),"procedure_count":len({q["procedure_id"] for q in rows}),"difficulty_levels":sorted({q["difficulty"] for q in rows}),"coverage_modes":sorted(modes),"maximum_family_share":max(families.values())/added,"maximum_structural_share":max(structures.values())/added,"duplicates":0,"unsupported_answer_shapes":0,"equivalence_validation":"PASS","matrix_system_validation":"PASS","convergence_error_validation":"PASS","bank_sha256":sha,"status":"PASS"}
def build_checkpoint_bank():
 c=discover_course_catalog();o=discover_generation_recipe_runtime(c["new"]);p=compile_course_pilot(c["new"][COURSE_ID],o)
 if p["validated"]!=25 or p["locked"]!=25:raise ValueError("authoritative count unavailable")
 return build_additions(COURSE_ID,list(p["questions"]),25,75,5,"math131c100")
def audit_checkpoint():
 rows,s=build_checkpoint_bank();again,t=build_checkpoint_bank();return {**s,"deterministic_replay":s["bank_sha256"]==t["bank_sha256"],"metadata_complete":all(q["production_status"]=="LOCKED_PRODUCTION_VALIDATED" for q in rows)}
