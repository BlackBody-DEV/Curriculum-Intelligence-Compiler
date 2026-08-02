"""Mechanics of Materials locked production bank."""
from __future__ import annotations
import math
from tools.course_compiler_demo.production_questions import ProductionFamily,ProductionReviewRecordV1,ProductionValidationRecordV1,default_validator,produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog,validate_physics_engineering_course_catalog

DOMAINS=("normal stress","normal strain","axial deformation","constitutive response","thermal deformation","torsion","bending stress","transverse shear","combined loading","factor of safety")

def _family(i,course):
 p=course["procedures"][i]; s=course["micro_skills"][i]; t=next(x for x in course["topics"] if x["topic_id"]==s["topic_id"])
 def params(n):
  a=float(n+i+12); b=float((n%7)+2); return {"a":a,"b":b,"load":a+20,"area":80+5*b,"length":500+10*a,"modulus":70+b,"radius":8+b,"inertia":10000+100*a,"temperature":10+b,"alpha":1.2e-5}
 def derive(x):
  P,A,L,E,r,I,dT,alpha=x["load"],x["area"],x["length"],x["modulus"],x["radius"],x["inertia"],x["temperature"],x["alpha"]
  vals=(1000*P/A,x["a"]*1e-3/L,P*L/(A*E),E*1000*(x["a"]*1e-6),alpha*dT*L,(P*1000*r)/I,(P*1000*r)/I,1000*P/A,1000*P/A+(x["b"]*1000*r/I),(200+x["a"])/(50+x["b"]))
  return vals[i]
 def gen(x):
  P,A,L,E,r,I,dT,alpha=x["load"],x["area"],x["length"],x["modulus"],x["radius"],x["inertia"],x["temperature"],x["alpha"]
  prompts=(f"An axial load of {P:.1f} kN acts on area {A:.1f} mm^2; what normal stress in MPa results?",f"A bar elongates {x['a']:.1f} mm over gauge length {L:.1f} mm; what normal strain results?",f"A bar carries {P:.1f} kN over length {L:.1f} mm with area {A:.1f} mm^2 and modulus {E:.1f} GPa; what axial deformation in mm results?",f"A linear-elastic material has modulus {E:.1f} GPa and strain {x['a']:.1f} microstrain; what normal stress in MPa follows from the constitutive relation?",f"A member of length {L:.1f} mm with thermal coefficient {alpha:.2e} per degree C undergoes temperature rise {dT:.1f} C; what free thermal deformation in mm results?",f"A circular shaft transmits torque {P:.1f} N m with outer radius {r:.1f} mm and polar section property {I:.1f} mm^4; what maximum torsional shear stress in MPa results?",f"A beam section carries bending moment {P:.1f} N m with extreme-fiber distance {r:.1f} mm and area moment {I:.1f} mm^4; what bending stress magnitude in MPa results?",f"A section of area {A:.1f} mm^2 carries transverse shear force {P:.1f} kN; what average transverse shear stress in MPa results?",f"A section has axial load {P:.1f} kN on area {A:.1f} mm^2 plus bending moment {x['b']:.1f} N m with c={r:.1f} mm and I={I:.1f} mm^4; what combined tensile stress in MPa results?",f"A material yield strength is {200+x['a']:.1f} MPa under applied stress {50+x['b']:.1f} MPa; what factor of safety results?")
  vals=(1000*P/A,x["a"]*1e-3/L,P*L/(A*E),E*1000*(x["a"]*1e-6),alpha*dT*L,(P*1000*r)/I,(P*1000*r)/I,1000*P/A,1000*P/A+(x["b"]*1000*r/I),(200+x["a"])/(50+x["b"]))
  return prompts[i],vals[i]
 return ProductionFamily(f"MECHANICS_OF_MATERIALS_PRODUCTION_{i:02d}",p["procedure_id"],t["unit_id"],t["topic_id"],s["micro_skill_id"],"numeric_scalar","numeric_scalar",("unit_mismatch","dimension_mismatch","sign_error",DOMAINS[i].replace(" ","_")+"_error"),params,gen,derive)

def materials_validator(candidate,derivation,answer):
 base=default_validator(candidate,derivation,answer); prompt=candidate.prompt.lower(); i=int(candidate.request["generation_family_id"].split("_")[-1]); keys=(("normal stress","kn","mm^2"),("normal strain","gauge length"),("axial deformation","modulus","mm"),("constitutive","microstrain","mpa"),("thermal","temperature","mm"),("torsional","polar section","mpa"),("bending stress","area moment","mpa"),("transverse shear","area","mpa"),("combined tensile","axial","bending"),("yield strength","factor of safety"))[i]; semantic=all(k in prompt for k in keys)
 return ProductionValidationRecordV1(base.validation_id,base.candidate_id,base.grading_pass,base.procedure_compatibility_pass,base.failure_signal_pass,base.prompt_determinacy_pass,base.unit_tolerance_pass and semantic,base.answer_contract_pass,base.reasons+(() if semantic else ("MATERIALS_DOMAIN_VALIDATION_FAILED",)))

def reviewer(families,inspected,subject,level):
 if level=="FAMILY":
  f=next((x for x in families if x.family_id==subject),None); cohort=[x for x in inspected.values() if x[0].request["generation_family_id"]==subject]
  if f is None or not cohort or any(not x[2].passed for x in cohort): raise ValueError("family evidence failed")
  findings=(f"inspected {len(cohort)} candidates for {DOMAINS[int(subject.split('_')[-1])]}",f"verified procedure {f.procedure_id}, geometry, dimensions, sign, and scalar contract")
 else:
  if subject not in inspected or not inspected[subject][2].passed: raise ValueError("candidate evidence failed")
  c,d,v=inspected[subject]; findings=(f"inspected {c.candidate_id} and independent derivation {d.derivation_id}",f"verified units, geometry, and validation {v.validation_id}")
 return ProductionReviewRecordV1(f"review:{level.lower()}:{subject}",subject,level,"PASS","independent_materials_reviewer",findings)

def build_bank():
 pack=build_physics_engineering_course_catalog(); validate_physics_engineering_course_catalog(pack); course=pack["courses"]["MECHANICS_OF_MATERIALS"]; families=tuple(_family(i,course) for i in range(10)); evidence=({"evidence_id":"MECHANICS_OF_MATERIALS:COURSE_CATALOG","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"],"access":"READ_ONLY_REFERENCE"},); inspected={}
 def validator(c,d,a): result=materials_validator(c,d,a); inspected[c.candidate_id]=(c,d,result); return result
 bank,summary=produce_course_bank("MECHANICS_OF_MATERIALS",pack["pack_id"],pack["deterministic_sha256"],evidence,families,reviewer=lambda subject,level:reviewer(families,inspected,subject,level),validator=validator); return bank,summary,evidence
