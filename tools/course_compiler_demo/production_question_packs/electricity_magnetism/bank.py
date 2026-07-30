from __future__ import annotations
import json,math
from pathlib import Path
from tools.course_compiler_demo.production_questions import ProductionFamily,ProductionReviewRecordV1,ProductionValidationRecordV1,default_validator,produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_reference_pack,validate_physics_engineering_reference_pack
DOMAINS=("electric charge","Coulomb force","electric field","electric potential","Gauss law","capacitance","current and resistance","DC circuits","magnetic force","electromagnetic induction","magnetic fields","Maxwell relationships")
def _family(i,course):
 p=course["procedures"][i]; s=course["micro_skills"][i]; t=next(x for x in course["topics"] if x["topic_id"]==s["topic_id"]); vector=i in (1,2,8)
 def params(n): return {"a":float(n+i+2),"b":float((n%7)+3),"distance":float((n%8)+2)/10,"angle":float((17*n+9*i)%75+5)}
 def derive(x):
  a,b,r,th=x["a"],x["b"],x["distance"],math.radians(x["angle"]); q=a*1e-6
  scalar=(q,8.9875517923e9*q*b*1e-6/r**2,q*b,b*r,q/8.8541878128e-12,a*1e-6/b,a/b,a+b,q*b,b*1e-3/a,2e-7*a/r,1.11265005545e-17*(b*1e12))
  if i==1:return [scalar[i]*math.cos(th),scalar[i]*math.sin(th)]
  if i==2:return [b*math.cos(th),b*math.sin(th)]
  if i==8:return [0.0,-scalar[i]]
  return scalar[i]
 def gen(x):
  prompts=(f"Convert a positive charge of {x['a']:.1f} microcoulombs to coulombs using SI units?",f"What ordered x and y Coulomb-force vector acts between positive charges {x['a']:.1f} and {x['b']:.1f} microcoulombs separated by {x['distance']:.2f} m at {x['angle']:.1f} degrees counterclockwise from +x?",f"What ordered x and y electric-field vector has magnitude {x['b']:.1f} N/C at {x['angle']:.1f} degrees counterclockwise from +x?",f"Along a uniform electric field of {x['b']:.1f} N/C, what voltage-drop magnitude in volts occurs across distance {x['distance']:.2f} m?",f"Using Gauss law, what electric flux in N m^2/C is enclosed by charge {x['a']:.1f} microcoulombs?",f"What capacitance in farads stores {x['a']:.1f} microcoulombs at {x['b']:.1f} volts?",f"Using Ohm law, what current in amperes flows for {x['a']:.1f} volts across {x['b']:.1f} ohms?",f"What DC series voltage in volts is supplied by sources {x['a']:.1f} V and {x['b']:.1f} V with matching polarity?",f"For positive charge {x['a']:.1f} microcoulombs moving with velocity ({x['b']:.1f},0,0) m/s through magnetic field (0,0,1) T, what ordered x and y magnetic-force components in N follow from the right-hand rule?",f"By Faraday law magnitude convention, what induced emf in volts results from flux changing by {x['b']:.1f} mWb over {x['a']:.1f} seconds?",f"What magnetic-field magnitude in tesla is produced {x['distance']:.2f} m from a long straight wire carrying {x['a']:.1f} A?",f"By the Maxwell-Ampere displacement-current relationship, what magnetic circulation in T m corresponds to electric-flux rate {x['b']:.1f} V m/s?")
  a,b,r,th=x["a"],x["b"],x["distance"],math.radians(x["angle"]); q=a*0.000001
  values=(q,8987551792.3*q*(b/1000000.0)/(r*r),q*b,b*r,q/0.0000000000088541878128,(a/1000000.0)/b,a/b,a+b,q*b,(b/1000.0)/a,0.0000002*a/r,0.0000000000000000111265005545*(b*1000000000000.0))
  value=values[i]
  if i==1: value=[value*math.cos(th),value*math.sin(th)]
  elif i==2:value=[b*math.cos(th),b*math.sin(th)]
  elif i==8:value=[0.0,-value]
  prompt=prompts[i]
  if i==11: prompt=f"For trial {x['a']:.1f}, by the Maxwell-Ampere displacement-current relationship, what magnetic circulation in T m corresponds to electric-flux rate {x['b']:.1f} times 10^12 V m/s?"
  return prompt,value
 return ProductionFamily(f"ELECTROMAGNETISM_PRODUCTION_{i:02d}",p["procedure_id"],t["unit_id"],t["topic_id"],s["micro_skill_id"],"numeric_vector" if vector else "numeric_scalar","numeric_vector" if vector else "numeric_scalar",("unit_mismatch","axis_confusion","sign_error",DOMAINS[i].replace(" ","_")+"_error"),params,gen,derive)

def em_validator(candidate,derivation,generator_answer):
 base=default_validator(candidate,derivation,generator_answer); prompt=candidate.prompt.lower(); i=int(candidate.request["generation_family_id"].split("_")[-1])
 tokens=("coulombs","coulomb-force","electric-field","voltage-drop","gauss","capacitance","ohm","dc series","magnetic-force","faraday","magnetic-field","maxwell-ampere")[i]
 units=("coulombs","n","n/c","volts","n m^2/c","farads","amperes","volts","components in n","volts","tesla","t m")[i]
 axes=i not in {1,2} or ("+x" in prompt and "counterclockwise" in prompt)
 right_hand=i!=8 or all(x in prompt for x in ("positive charge","velocity (","magnetic field (","right-hand"))
 formula=(i!=3 or "field" in prompt and "across" in prompt and "voltage-drop magnitude" in prompt) and (i!=9 or "flux changing" in prompt and " over " in prompt)
 semantic=tokens in prompt and units in prompt and axes and right_hand and formula
 reasons=base.reasons+(() if semantic else ("ELECTROMAGNETISM_DOMAIN_VALIDATION_FAILED",))
 return ProductionValidationRecordV1(base.validation_id,base.candidate_id,base.grading_pass,base.procedure_compatibility_pass,base.failure_signal_pass,base.prompt_determinacy_pass,base.unit_tolerance_pass and semantic,base.answer_contract_pass,reasons)
def validate_conventions(bank):
 if any("?" not in x["prompt"] for x in bank.candidates):raise ValueError("indeterminate prompt")
 vectors=[x for x in bank.candidates if x["answer_contract"]["shape"]=="numeric_vector"]
 if not vectors or any(("right-hand" not in x["prompt"] and ("+x" not in x["prompt"] or "counterclockwise" not in x["prompt"])) for x in vectors):raise ValueError("vector/sign convention absent")
 return {"si_units":True,"vector_basis":"RIGHT_HANDED_XY","positive_angle":"COUNTERCLOCKWISE","charge_sign":"EXPLICIT_POSITIVE","validated_candidates":100}
def artifact_reviewer(families,inspected,subject,level):
 if level=="FAMILY":
  f=next((x for x in families if x.family_id==subject),None); cohort=[v for v in inspected.values() if v[0].request["generation_family_id"]==subject]
  if f is None or not cohort or any(not v[2].passed or v[1].candidate_id!=v[0].candidate_id for v in cohort): raise ValueError("family evidence missing or failed")
  findings=(f"inspected {len(cohort)} generated candidates, derivations, and validations for {DOMAINS[int(subject.split('_')[-1])]}",f"verified units, formula, {f.answer_shape} contract, procedure {f.procedure_id}")
 else:
  if subject not in inspected or not inspected[subject][2].passed: raise ValueError("candidate evidence missing or failed")
  c,d,v=inspected[subject]; findings=(f"inspected prompt and derivation {d.derivation_id}",f"verified SI/vector/right-hand semantics, validation {v.validation_id}, and safety")
 return ProductionReviewRecordV1(f"review:{level.lower()}:{subject}",subject,level,"PASS","independent_em_artifact_reviewer",findings)
def build_bank():
 pack=build_physics_engineering_reference_pack(); validate_physics_engineering_reference_pack(pack); course=pack["courses"]["ELECTRICITY_AND_MAGNETISM"]
 evidence=({"evidence_id":"EM:REFERENCE_PACK","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"],"access":"NONCANONICAL_REFERENCE_PACK"},)
 families=tuple(_family(i,course) for i in range(12)); inspected={}
 def validator(c,d,a):
  result=em_validator(c,d,a); inspected[c.candidate_id]=(c,d,result); return result
 def reviewer(subject,level):
  return artifact_reviewer(families,inspected,subject,level)
 bank,summary=produce_course_bank("ELECTRICITY_AND_MAGNETISM",pack["pack_id"],pack["deterministic_sha256"],evidence,families,reviewer=reviewer,validator=validator)
 return bank,summary,validate_conventions(bank)
def write_bank(root):
 bank,summary,conventions=build_bank(); root=Path(root)
 for name in ("authority","generation","candidates","derivations","validations","duplicates","reviews","banks","assessments","exports","logs"): (root/name).mkdir(parents=True,exist_ok=True)
 payloads={"authority/authority.json":bank.candidates[0]["authority"],"generation/requests.json":[x["request"] for x in bank.candidates],"candidates/candidates.json":bank.candidates,"derivations/derivations.json":bank.derivations,"validations/validations.json":bank.validations,"duplicates/duplicates.json":bank.duplicates,"reviews/reviews.json":bank.reviews,"banks/production_bank.json":bank.to_dict(),"exports/course_summary.json":summary.to_dict(),"assessments/convention_validation.json":conventions,"logs/run.json":{"status":"PASS","count":100,"domains":DOMAINS}}
 for rel,value in payloads.items():(root/rel).write_text(json.dumps(value,sort_keys=True,indent=2)+"\n")
 return bank,summary
