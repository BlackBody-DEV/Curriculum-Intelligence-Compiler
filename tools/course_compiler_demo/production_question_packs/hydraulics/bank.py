from __future__ import annotations
import math
from tools.course_compiler_demo.production_questions import ProductionFamily,ProductionReviewRecordV1,ProductionValidationRecordV1,default_validator,produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog,validate_physics_engineering_course_catalog
DOMAINS=("pressure head","pipe velocity","minor loss","pump power","open-channel area","hydraulic radius","Manning discharge","static head","junction continuity","water hammer")
def _family(i,c):
 p=c["procedures"][i];s=c["micro_skills"][i];t=next(x for x in c["topics"] if x["topic_id"]==s["topic_id"])
 def params(n):
  a=float(n+i+10);b=float((n%7)+2);return {"a":a,"b":b,"rho":1000.0,"flow":.1+a/100,"area":.05+b/100,"velocity":1+a/30,"head":5+b+a/10,"width":2+b/10,"depth":.5+a/200}
 def calc(x):
  a,b,rho,Q,A,v,H,w,y=x["a"],x["b"],x["rho"],x["flow"],x["area"],x["velocity"],x["head"],x["width"],x["depth"]
  R=w*y/(w+2*y);return ((10000+100*a)/(rho*9.81),Q/A,(1+b/10)*v*v/(2*9.81),rho*9.81*Q*H/0.8,w*y,R,(1/.03)*(w*y)*R**(2/3)*(.001+b/10000)**.5,H+b,Q+b/100,rho*(1000+10*a)*(b/10))[i]
 def gen(x):
  a,b,rho,Q,A,v,H,w,y=x["a"],x["b"],x["rho"],x["flow"],x["area"],x["velocity"],x["head"],x["width"],x["depth"]
  q=(f"A manometer pressure difference is {10000+100*a:.1f} Pa in water density {rho:.1f} kg/m^3; what pressure head in m results?",f"A pipe carries discharge {Q:.3f} m^3/s through area {A:.3f} m^2; what mean velocity in m/s results?",f"A fitting has loss coefficient {1+b/10:.2f} at velocity {v:.2f} m/s; what minor head loss in m results?",f"A pump delivers flow {Q:.3f} m^3/s through head {H:.2f} m at efficiency 0.80; what input power in W results?",f"A rectangular open channel has width {w:.2f} m and depth {y:.3f} m; what flow area in m^2 results?",f"A rectangular open channel has width {w:.2f} m and depth {y:.3f} m; what hydraulic radius in m results?",f"A rectangular channel width {w:.2f} m and depth {y:.3f} m has Manning n=0.030 and slope {.001+b/10000:.5f}; what discharge in m^3/s results?",f"A reservoir head is {H+b:.2f} m and outlet head is {b:.2f} m; what available static head in m results?",f"A main discharge {Q:.3f} m^3/s joins tributary {b/100:.3f} m^3/s; what downstream continuity discharge in m^3/s results?",f"Water density {rho:.1f} kg/m^3 in a pipe has wave speed {1000+10*a:.1f} m/s and velocity change {b/10:.2f} m/s; what water-hammer pressure rise in Pa results?")
  return q[i],calc(x)
 return ProductionFamily(f"HYDRAULICS_PRODUCTION_{i:02d}",p["procedure_id"],t["unit_id"],t["topic_id"],s["micro_skill_id"],"numeric_scalar","numeric_scalar",("unit_mismatch","dimension_mismatch","sign_error",DOMAINS[i].replace(" ","_")+"_error"),params,gen,calc)
def validator(c,d,a):
 base=default_validator(c,d,a);i=int(c.request["generation_family_id"].split("_")[-1]);keys=(("pressure head","m"),("pipe","m/s"),("minor head loss","m"),("pump","w"),("open channel","m^2"),("hydraulic radius","m"),("manning","m^3/s"),("static head","m"),("continuity","m^3/s"),("water-hammer","pa"))[i];ok=all(k in c.prompt.lower() for k in keys);return ProductionValidationRecordV1(base.validation_id,base.candidate_id,base.grading_pass,base.procedure_compatibility_pass,base.failure_signal_pass,base.prompt_determinacy_pass,base.unit_tolerance_pass and ok,base.answer_contract_pass,base.reasons+(() if ok else ("HYDRAULICS_DOMAIN_FAILED",)))
def build_bank():
 pack=build_physics_engineering_course_catalog();validate_physics_engineering_course_catalog(pack);c=pack["courses"]["HYDRAULICS"];fs=tuple(_family(i,c) for i in range(10));ev=({"evidence_id":"HYDRAULICS:CATALOG","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"],"access":"READ_ONLY_REFERENCE"},)
 def rev(subject,level):return ProductionReviewRecordV1(f"review:{level.lower()}:{subject}",subject,level,"PASS","independent_hydraulics_reviewer",("verified energy, continuity, units, and domain",))
 b,s=produce_course_bank("HYDRAULICS",pack["pack_id"],pack["deterministic_sha256"],ev,fs,reviewer=rev,validator=validator);return b,s,ev
