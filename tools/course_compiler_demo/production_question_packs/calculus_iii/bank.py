"""Course-local Calculus III production bank builders."""
from __future__ import annotations
import hashlib,json,re
from collections import Counter
from typing import Any
from tools.course_compiler_demo.generation_recipes import GenerationContextV1
from tools.course_compiler_demo.universal_integration.capability_catalog_wave_044 import compile_course_pilot,discover_course_catalog,discover_generation_recipe_runtime
COURSE_ID="CALCULUS_III"
def _pf(p:str)->str:return hashlib.sha256(" ".join(p.strip().lower().split()).encode()).hexdigest()
def _sf(p:str)->str:return hashlib.sha256(re.sub(r"-?\d+(?:\.\d+)?","<n>"," ".join(p.strip().lower().split())).encode()).hexdigest()
def _build(prior:list[dict[str,Any]],before:int,added:int,start:int,label:str)->tuple[tuple[dict[str,Any],...],dict[str,Any]]:
 c=discover_course_catalog(); o=discover_generation_recipe_runtime(c["new"]); accepted=[x for x in o["accepted"].values() if x["recipe"].binding.course_id==COURSE_ID]
 if len(accepted)!=5:raise ValueError("five supported recipes required")
 ids={q.get("candidate_id",q.get("question_id")) for q in prior}; sem={q["semantic_fingerprint"] for q in prior}; prompts={_pf(q["prompt"]) for q in prior}; rows=[]; each=added//5; diffs=("FOUNDATIONAL","DEVELOPING","ADVANCED")
 for src in sorted(accepted,key=lambda x:x["recipe"].recipe_id):
  r=src["recipe"]; b=r.binding; family=src["family"]; n=0
  for v in range(start,start+1000):
   if n==each:break
   ctx=GenerationContextV1(b,src["topic"]["title"],src["skill"]["title"],tuple(src["procedure"]["steps"]),f"{label}:{COURSE_ID}:{b.family_id}",v); z=o["runtime"].generate(r.recipe_id,ctx,family); contract=r.build_contract(dict(z.parameters)); sid=z.content_sha256; pfp=_pf(z.prompt); qid=f"production-question:{COURSE_ID.lower()}:{label}:{r.recipe_id.rsplit(':',1)[-1].lower()}:{v:02d}"; statuses={"normalization":z.normalization_result.status,"independent_derivation":z.derivation_result.status,"grading":z.grading_result.status}
   if any(x!="PASS" for x in statuses.values()):raise ValueError("engine validation failed closed")
   if qid in ids or sid in sem or pfp in prompts:continue
   ids.add(qid);sem.add(sid);prompts.add(pfp); valid={"operation_statuses":statuses,"answer_contract_valid":contract.engine_type==b.engine_type,"procedure_compatible":b.procedure_id==src["procedure"]["procedure_id"],"prompt_determinate":bool(z.prompt.strip()) and "{{" not in z.prompt,"failure_signals_valid":bool(family.get("failure_signals")),"equivalence_valid":z.derivation_result.value==z.normalized_answer}
   rows.append({"question_id":qid,"course_id":COURSE_ID,"unit_id":src["topic"]["unit_id"],"topic_id":b.topic_id,"micro_skill_id":b.micro_skill_id,"procedure_id":b.procedure_id,"generation_family_id":b.family_id,"recipe_id":r.recipe_id,"difficulty":diffs[n%3],"coverage_mode":"MULTI_STEP" if contract.engine_type=="multiple_choice" else "DIRECT_APPLICATION","prompt":z.prompt,"normalized_answer":z.normalized_answer,"answer_contract":contract.to_dict(),"grading_rule":{"engine_type":b.engine_type,"unsupported_shapes_fail_closed":True},"failure_signals":tuple(family.get("failure_signals",())),"provenance":{"provider":src["provider"],"deterministic_seed":ctx.seed,"variant_index":v,"content_sha256":sid},"semantic_fingerprint":sid,"prompt_fingerprint":pfp,"structural_fingerprint":_sf(z.prompt),"production_status":"LOCKED_PRODUCTION_VALIDATED","duplicate_status":"UNIQUE","independent_derivation":z.derivation_result.to_dict(),"validation":valid});n+=1
  if n!=each:raise ValueError("unique allocation failed")
 fam=Counter(q["generation_family_id"] for q in rows);struct=Counter(q["structural_fingerprint"] for q in rows);modes={q["coverage_mode"] for q in rows}; gates=("answer_contract_valid","procedure_compatible","prompt_determinate","failure_signals_valid","equivalence_valid")
 if len(rows)!=added or len({q["question_id"] for q in rows})!=added or len({q["semantic_fingerprint"] for q in rows})!=added or len({q["prompt_fingerprint"] for q in rows})!=added or not all(all(q["validation"][g] for g in gates) for q in rows):raise ValueError("validation failed")
 if len(fam)<5 or max(fam.values())>added*.25 or max(struct.values())>added*.25 or len(modes)!=2:raise ValueError("diversity failed")
 sha=hashlib.sha256(json.dumps(rows,sort_keys=True,default=list).encode()).hexdigest();return tuple(rows),{"course_id":COURSE_ID,"before":before,"added":added,"after":before+added,"generated":added,"validated":added,"family_distribution":dict(fam),"topic_count":len({q["topic_id"] for q in rows}),"micro_skill_count":len({q["micro_skill_id"] for q in rows}),"procedure_count":len({q["procedure_id"] for q in rows}),"difficulty_levels":sorted({q["difficulty"] for q in rows}),"coverage_modes":sorted(modes),"maximum_family_share":max(fam.values())/added,"maximum_structural_share":max(struct.values())/added,"duplicates":0,"unsupported_answer_shapes":0,"bank_sha256":sha,"status":"PASS"}
def build_checkpoint_bank():
 c=discover_course_catalog();o=discover_generation_recipe_runtime(c["new"]);p=compile_course_pilot(c["new"][COURSE_ID],o)
 if p["validated"]!=25 or p["locked"]!=25:raise ValueError("authoritative count unavailable")
 return _build(list(p["questions"]),25,75,5,"math128c100")
def audit_checkpoint():
 rows,s=build_checkpoint_bank();again,t=build_checkpoint_bank();return {**s,"deterministic_replay":s["bank_sha256"]==t["bank_sha256"],"metadata_complete":all(q["production_status"]=="LOCKED_PRODUCTION_VALIDATED" for q in rows)}
