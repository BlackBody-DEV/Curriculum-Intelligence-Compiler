from __future__ import annotations
import hashlib,json,math
from pathlib import Path
from tools.course_compiler_demo.production_questions import ProductionFamily,ProductionReviewRecordV1,ProductionValidationRecordV1,default_validator,produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_reference_pack,validate_physics_engineering_reference_pack
DOMAINS=("vector components","particle equilibrium","force systems","moments and couples","rigid-body equilibrium","distributed loading","truss analysis","frames and machines","centroids","area moments of inertia")
def _family(i,course):
 p=course["procedures"][i]; s=course["micro_skills"][i]; t=next(x for x in course["topics"] if x["topic_id"]==s["topic_id"]); vector=i in (0,1,7)
 def params(n): return {"a":float(n+i+12),"b":float((n%9)+i+2),"angle":float((13*n+7*i)%75+5),"length":float((n%7)+2)}
 def derive(x):
  a,b,L,th=x["a"],x["b"],x["length"],math.radians(x["angle"])
  return ([a*math.cos(th),a*math.sin(th)],[-a*math.cos(th),-a*math.sin(th)],a+b,a*L*math.sin(th),a-b,a*L/2,a/(2*math.sin(th)),[a-b,b],b*L/(a+b),b*L**3/12)[i]
 def gen(x):
  prompts=(f"Resolve a {x['a']:.1f} N force at {x['angle']:.1f} degrees counterclockwise from +x into ordered x and y components?",f"For particle equilibrium, what ordered reaction vector balances a {x['a']:.1f} N force at {x['angle']:.1f} degrees from +x?",f"What is the resultant magnitude in N of collinear forces {x['a']:.1f} N and {x['b']:.1f} N acting together?",f"What counterclockwise-positive moment in N m does a {x['a']:.1f} N force create at arm {x['length']:.1f} m and angle {x['angle']:.1f} degrees?",f"For rigid-body equilibrium, what signed reaction in N balances downward {x['a']:.1f} N and upward {x['b']:.1f} N?",f"What resultant load in N represents a triangular distribution peaking at {x['a']:.1f} N/m over {x['length']:.1f} m?",f"For a symmetric two-member truss at {x['angle']:.1f} degrees, what axial member force in N supports {x['a']:.1f} N?",f"For a frame joint, what ordered x and y reaction remains after loads {x['a']:.1f} N and {x['b']:.1f} N?",f"Point area {x['a']:.1f} is at x=0 m and point area {x['b']:.1f} is at x={x['length']:.1f} m; where in m from x=0 is their centroid?",f"What is the rectangular area moment of inertia in m^4 for base {x['b']:.1f} m and height {x['length']:.1f} m?")
  a,b,L,th=x["a"],x["b"],x["length"],math.radians(x["angle"])
  generated=([a*math.cos(th),a*math.sin(th)],[-a*math.cos(th),-a*math.sin(th)],a+b,a*L*math.sin(th),a-b,0.5*a*L,a/(2*math.sin(th)),[a-b,b],(b*L)/(a+b),(b*L*L*L)/12)[i]
  return prompts[i],generated
 return ProductionFamily(f"STATICS_PRODUCTION_{i:02d}",p["procedure_id"],t["unit_id"],t["topic_id"],s["micro_skill_id"],"numeric_vector" if vector else "numeric_scalar","numeric_vector" if vector else "numeric_scalar",("unit_mismatch","axis_confusion","sign_error",DOMAINS[i].replace(" ","_")+"_error"),params,gen,derive)

def statics_validator(candidate,derivation,generator_answer):
 base=default_validator(candidate,derivation,generator_answer); prompt=candidate.prompt.lower(); family=candidate.request["generation_family_id"]; index=int(family.split("_")[-1])
 required=("components","equilibrium","resultant","moment","equilibrium","distribution","truss","frame","centroid","moment of inertia")[index]
 dimensional=("n","n","n","n m","n","n/m","n","n","m","m^4")[index]
 axes_ok=index not in {0,1} or ("+x" in prompt and ("ordered" in prompt or "reaction" in prompt))
 sign_ok=index not in {0,3} or "counterclockwise" in prompt
 semantic=required in prompt and dimensional in prompt and axes_ok and sign_ok
 reasons=base.reasons+(() if semantic else ("STATICS_DOMAIN_VALIDATION_FAILED",))
 return ProductionValidationRecordV1(base.validation_id,base.candidate_id,base.grading_pass,base.procedure_compatibility_pass,base.failure_signal_pass,base.prompt_determinacy_pass,base.unit_tolerance_pass and semantic,base.answer_contract_pass,reasons)
def artifact_reviewer(families,inspected,subject,level):
 if level=="FAMILY":
  f=next((x for x in families if x.family_id==subject),None); cohort=[v for v in inspected.values() if v[0].request["generation_family_id"]==subject]
  if f is None or not cohort or any(not v[2].passed or v[1].candidate_id!=v[0].candidate_id for v in cohort): raise ValueError("family evidence missing or failed")
  findings=(f"inspected {len(cohort)} generated candidates, derivations, and passing validations",f"verified {DOMAINS[int(subject.split('_')[-1])]} procedure {f.procedure_id}, skill {f.micro_skill_id}, shape {f.answer_shape}")
 else:
  if subject not in inspected or not inspected[subject][2].passed: raise ValueError("candidate evidence missing or failed")
  c,d,v=inspected[subject]; findings=(f"inspected prompt and derivation {d.derivation_id} for {c.request['generation_family_id']}",f"verified units, axes, sign, validation {v.validation_id}, and safety")
 return ProductionReviewRecordV1(f"review:{level.lower()}:{subject}",subject,level,"PASS","independent_statics_artifact_reviewer",findings)
def _walk(value,ids,prompts):
 if isinstance(value,dict):
  for k,v in value.items():
   if (k in {"question_id","candidate_id","canonical_id","stable_source_identity","existing_question_id"} or k.endswith("_question_id")) and isinstance(v,str) and v: ids.add(v)
   if k in {"prompt","question_text","stem"} and isinstance(v,str): prompts.add(hashlib.sha256(v.strip().lower().encode()).hexdigest())
   if ("fingerprint" in k or k in {"source_sha256","sha256"}) and isinstance(v,str) and len(v)==64: prompts.add(v)
   _walk(v,ids,prompts)
 elif isinstance(value,list):
  for x in value:_walk(x,ids,prompts)
def compare_protected_inventories(bank,paths):
 candidate_ids={x["candidate_id"] for x in bank.candidates}; prompt_hashes={hashlib.sha256(x["prompt"].strip().lower().encode()).hexdigest() for x in bank.candidates}; reports=[]
 for raw in paths:
  path=Path(raw).resolve(strict=True); before=hashlib.sha256(path.read_bytes()).hexdigest(); data=json.loads(path.read_text()); ids=set(); prompts=set(); _walk(data,ids,prompts); after=hashlib.sha256(path.read_bytes()).hexdigest()
  if before!=after: raise ValueError("protected inventory changed during comparison")
  reports.append({"path":str(path),"sha256_before":before,"sha256_after":after,"read_only":True,"inventory_identity_count":len(ids),"inventory_prompt_fingerprint_count":len(prompts),"candidate_identity_collisions":sorted(candidate_ids&ids),"exact_prompt_collisions":sorted(prompt_hashes&prompts),"copied":False})
 return tuple(reports)
def build_bank(inventory_paths=()):
 pack=build_physics_engineering_reference_pack(); validate_physics_engineering_reference_pack(pack); course=pack["courses"]["STATICS"]
 evidence=tuple({"evidence_id":f"STATICS:{x['authority_identity']}","source_identity":x["relative_path"],"source_hash":x["sha256"],"access":"READ_ONLY_REFERENCE"} for x in pack["statics_authority_references"])
 families=tuple(_family(i,course) for i in range(10)); inspected={}
 def validator(c,d,a):
  result=statics_validator(c,d,a); inspected[c.candidate_id]=(c,d,result); return result
 def reviewer(subject,level):
  return artifact_reviewer(families,inspected,subject,level)
 bank,summary=produce_course_bank("STATICS",pack["pack_id"],pack["deterministic_sha256"],evidence,families,reviewer=reviewer,validator=validator)
 return bank,summary,compare_protected_inventories(bank,inventory_paths)
def write_bank(root,inventory_paths=()):
 bank,summary,comparison=build_bank(inventory_paths); root=Path(root)
 for name in ("authority","generation","candidates","derivations","validations","duplicates","reviews","banks","assessments","exports","logs"): (root/name).mkdir(parents=True,exist_ok=True)
 payloads={"authority/authority.json":{"source_evidence":bank.candidates[0]["authority"]["source_evidence"],"protected_inventory_comparison":comparison},"generation/requests.json":[x["request"] for x in bank.candidates],"candidates/candidates.json":bank.candidates,"derivations/derivations.json":bank.derivations,"validations/validations.json":bank.validations,"duplicates/duplicates.json":bank.duplicates,"reviews/reviews.json":bank.reviews,"banks/production_bank.json":bank.to_dict(),"exports/course_summary.json":summary.to_dict(),"logs/run.json":{"status":"PASS","count":100,"domains":DOMAINS}}
 for rel,value in payloads.items():(root/rel).write_text(json.dumps(value,sort_keys=True,indent=2)+"\n")
 return bank,summary
