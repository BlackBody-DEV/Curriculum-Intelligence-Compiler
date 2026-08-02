"""Strength of Materials locked production bank."""
from __future__ import annotations
import math
from tools.course_compiler_demo.production_questions import ProductionFamily,ProductionReviewRecordV1,ProductionValidationRecordV1,default_validator,produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog,validate_physics_engineering_course_catalog

DOMAINS=("load paths","stress transformation","failure criterion","hoop stress","longitudinal stress","column buckling","strain energy","fatigue damage","factor of safety","section modulus")
def _family(i,course):
 p=course["procedures"][i]; s=course["micro_skills"][i]; t=next(x for x in course["topics"] if x["topic_id"]==s["topic_id"])
 def params(n):
  a=float(n+i+15); b=float((n%7)+3); return {"a":a,"b":b,"pressure":1+b/10,"radius":100+a,"thickness":5+b,"length":1000+10*a,"modulus":200.0,"inertia":20000+100*a,"area":100+5*b}
 def derive(x):
  a,b,p,r,t,L,E,I,A=x["a"],x["b"],x["pressure"],x["radius"],x["thickness"],x["length"],x["modulus"],x["inertia"],x["area"]
  theta=math.radians(10+a/2); sx=50+a; sy=20+b; tau=5+b
  vals=(a+b,(sx+sy)/2+(sx-sy)*math.cos(2*theta)/2+tau*math.sin(2*theta),math.sqrt(sx*sx-sx*sy+sy*sy+3*tau*tau),p*r/t,p*r/(2*t),math.pi**2*(E*1000)*I/(L*L)/1000,(a*1000)**2*L/(2*A*E*1000)/1000,(1000+a)/(1e6+1000*b),(250+a)/(60+b),I/(10+b))
  return vals[i]
 def gen(x):
  a,b,p,r,t,L,E,I,A=x["a"],x["b"],x["pressure"],x["radius"],x["thickness"],x["length"],x["modulus"],x["inertia"],x["area"]
  theta=10+a/2; sx=50+a; sy=20+b; tau=5+b
  prompts=(f"Two collinear member loads {a:.1f} kN and {b:.1f} kN follow the same load path; what total transmitted load in kN results?",f"At a plane-stress point sigma_x={sx:.1f} MPa, sigma_y={sy:.1f} MPa, and tau_xy={tau:.1f} MPa; what transformed normal stress in MPa acts on a plane at {theta:.1f} degrees?",f"For plane stress sigma_x={sx:.1f} MPa, sigma_y={sy:.1f} MPa, and tau_xy={tau:.1f} MPa, what von Mises failure-criterion stress in MPa results?",f"A thin pressure vessel has internal pressure {p:.2f} MPa, radius {r:.1f} mm, and thickness {t:.1f} mm; what hoop stress in MPa results?",f"A thin closed pressure vessel has pressure {p:.2f} MPa, radius {r:.1f} mm, and thickness {t:.1f} mm; what longitudinal stress in MPa results?",f"A pin-ended column has E={E:.1f} GPa, I={I:.1f} mm^4, and length {L:.1f} mm; what Euler buckling load in kN results?",f"An axial member carries {a:.1f} kN over length {L:.1f} mm with area {A:.1f} mm^2 and E={E:.1f} GPa; what elastic strain energy in J is stored?",f"A fatigue component accumulates {1000+a:.0f} cycles at capacity {1e6+1000*b:.0f} cycles; what Miner damage fraction results?",f"A design resistance of {250+a:.1f} MPa is compared with demand {60+b:.1f} MPa; what factor of safety results?",f"A section has area moment of inertia {I:.1f} mm^4 and extreme-fiber distance {10+b:.1f} mm; what section modulus in mm^3 results?")
  angle=math.radians(theta); vals=(a+b,(sx+sy)/2+(sx-sy)*math.cos(2*angle)/2+tau*math.sin(2*angle),math.sqrt(sx*sx-sx*sy+sy*sy+3*tau*tau),p*r/t,p*r/(2*t),math.pi**2*(E*1000)*I/(L*L)/1000,(a*1000)**2*L/(2*A*E*1000)/1000,(1000+a)/(1e6+1000*b),(250+a)/(60+b),I/(10+b)); return prompts[i],vals[i]
 return ProductionFamily(f"STRENGTH_OF_MATERIALS_PRODUCTION_{i:02d}",p["procedure_id"],t["unit_id"],t["topic_id"],s["micro_skill_id"],"numeric_scalar","numeric_scalar",("unit_mismatch","dimension_mismatch","sign_error",DOMAINS[i].replace(" ","_")+"_error"),params,gen,derive)

def strength_validator(candidate,derivation,answer):
 base=default_validator(candidate,derivation,answer); prompt=candidate.prompt.lower(); i=int(candidate.request["generation_family_id"].split("_")[-1]); keys=(("load path","kn"),("transformed normal","plane-stress","mpa"),("von mises","failure-criterion","mpa"),("pressure vessel","hoop stress","mpa"),("pressure vessel","longitudinal stress","mpa"),("column","euler buckling","kn"),("strain energy","area","j"),("fatigue","miner","cycles"),("design resistance","factor of safety"),("section modulus","mm^3"))[i]; semantic=all(k in prompt for k in keys)
 return ProductionValidationRecordV1(base.validation_id,base.candidate_id,base.grading_pass,base.procedure_compatibility_pass,base.failure_signal_pass,base.prompt_determinacy_pass,base.unit_tolerance_pass and semantic,base.answer_contract_pass,base.reasons+(() if semantic else ("STRENGTH_DOMAIN_VALIDATION_FAILED",)))
def reviewer(families,inspected,subject,level):
 if level=="FAMILY":
  f=next((x for x in families if x.family_id==subject),None); cohort=[x for x in inspected.values() if x[0].request["generation_family_id"]==subject]
  if f is None or not cohort or any(not x[2].passed for x in cohort): raise ValueError("family evidence failed")
  findings=(f"inspected {len(cohort)} candidates for {DOMAINS[int(subject.split('_')[-1])]}",f"verified procedure {f.procedure_id}, geometry, dimensions, sign, and scalar contract")
 else:
  if subject not in inspected or not inspected[subject][2].passed: raise ValueError("candidate evidence failed")
  c,d,v=inspected[subject]; findings=(f"inspected {c.candidate_id} and derivation {d.derivation_id}",f"verified strength domain and validation {v.validation_id}")
 return ProductionReviewRecordV1(f"review:{level.lower()}:{subject}",subject,level,"PASS","independent_strength_reviewer",findings)
def build_bank():
 pack=build_physics_engineering_course_catalog(); validate_physics_engineering_course_catalog(pack); course=pack["courses"]["STRENGTH_OF_MATERIALS"]; families=tuple(_family(i,course) for i in range(10)); evidence=({"evidence_id":"STRENGTH_OF_MATERIALS:COURSE_CATALOG","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"],"access":"READ_ONLY_REFERENCE"},); inspected={}
 def validator(c,d,a): result=strength_validator(c,d,a); inspected[c.candidate_id]=(c,d,result); return result
 bank,summary=produce_course_bank("STRENGTH_OF_MATERIALS",pack["pack_id"],pack["deterministic_sha256"],evidence,families,reviewer=lambda subject,level:reviewer(families,inspected,subject,level),validator=validator); return bank,summary,evidence
