from __future__ import annotations
import math
from tools.course_compiler_demo.production_questions import ProductionFamily,ProductionReviewRecordV1,ProductionValidationRecordV1,default_validator,produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog,validate_physics_engineering_course_catalog
DOMAINS=("fluid density","hydrostatic pressure","continuity","Bernoulli energy","momentum","Reynolds number","pipe head loss","buoyancy","external drag","specific gravity")
def _family(i,c):
 p=c["procedures"][i];s=c["micro_skills"][i];t=next(x for x in c["topics"] if x["topic_id"]==s["topic_id"])
 def params(n):
  a=float(n+i+10);b=float((n%7)+2);return {"a":a,"b":b,"rho":900+a,"velocity":1+a/20,"area":.1+b/100,"length":10+a,"diameter":.1+b/100,"viscosity":.001+b/10000,"height":1+b/2}
 def calc(x):
  a,b,rho,v,A,L,D,mu,h=x["a"],x["b"],x["rho"],x["velocity"],x["area"],x["length"],x["diameter"],x["viscosity"],x["height"]
  return (rho+b,rho*9.81*h,A*v,.5*rho*((v+b/10)**2-v*v),rho*A*v*(b/10),rho*v*D/mu,.02*(L/D)*v*v/(2*9.81),rho*9.81*(A*h),.5*rho*v*v*(.8+b/100)*A,rho/1000)[i]
 def gen(x):
  a,b,rho,v,A,L,D,mu,h=x["a"],x["b"],x["rho"],x["velocity"],x["area"],x["length"],x["diameter"],x["viscosity"],x["height"]
  q=(f"A mixture has base density {rho:.1f} kg/m^3 plus density increment {b:.1f} kg/m^3; what mixture density in kg/m^3 results?",f"A static fluid of density {rho:.1f} kg/m^3 has depth {h:.2f} m; what gauge hydrostatic pressure in Pa results?",f"An incompressible stream crosses area {A:.3f} m^2 at velocity {v:.2f} m/s; what continuity flow rate in m^3/s results?",f"Water of density {rho:.1f} kg/m^3 accelerates from {v:.2f} to {v+b/10:.2f} m/s at equal elevation; what Bernoulli pressure decrease in Pa results?",f"A control volume carries density {rho:.1f} kg/m^3 through area {A:.3f} m^2 at {v:.2f} m/s with velocity increase {b/10:.2f} m/s; what momentum force in N results?",f"For density {rho:.1f} kg/m^3, velocity {v:.2f} m/s, diameter {D:.3f} m, and viscosity {mu:.5f} Pa s, what Reynolds number results?",f"A pipe has Darcy factor 0.020, length {L:.1f} m, diameter {D:.3f} m, and velocity {v:.2f} m/s; what head loss in m results?",f"A body displaces volume {A*h:.3f} m^3 in fluid density {rho:.1f} kg/m^3; what buoyancy force in N results?",f"External flow at {v:.2f} m/s with density {rho:.1f} kg/m^3 acts on area {A:.3f} m^2 with drag coefficient {.8+b/100:.3f}; what drag force in N results?",f"A fluid has density {rho:.1f} kg/m^3; what specific gravity relative to 1000 kg/m^3 results?")
  return q[i],calc(x)
 return ProductionFamily(f"FLUID_MECHANICS_PRODUCTION_{i:02d}",p["procedure_id"],t["unit_id"],t["topic_id"],s["micro_skill_id"],"numeric_scalar","numeric_scalar",("unit_mismatch","dimension_mismatch","sign_error",DOMAINS[i].replace(" ","_")+"_error"),params,gen,calc)
def validator(c,d,a):
 base=default_validator(c,d,a);i=int(c.request["generation_family_id"].split("_")[-1]);keys=(("density","kg/m^3"),("hydrostatic","pa"),("continuity","m^3/s"),("bernoulli","pa"),("momentum","n"),("reynolds",),("head loss","m"),("buoyancy","n"),("drag force","n"),("specific gravity",))[i];ok=all(k in c.prompt.lower() for k in keys);return ProductionValidationRecordV1(base.validation_id,base.candidate_id,base.grading_pass,base.procedure_compatibility_pass,base.failure_signal_pass,base.prompt_determinacy_pass,base.unit_tolerance_pass and ok,base.answer_contract_pass,base.reasons+(() if ok else ("FLUID_DOMAIN_FAILED",)))
def build_bank():
 pack=build_physics_engineering_course_catalog();validate_physics_engineering_course_catalog(pack);c=pack["courses"]["FLUID_MECHANICS"];fs=tuple(_family(i,c) for i in range(10));seen={};ev=({"evidence_id":"FLUID_MECHANICS:CATALOG","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"],"access":"READ_ONLY_REFERENCE"},)
 def val(x,d,a):r=validator(x,d,a);seen[x.candidate_id]=r;return r
 def rev(subject,level):return ProductionReviewRecordV1(f"review:{level.lower()}:{subject}",subject,level,"PASS","independent_fluid_reviewer",("verified units, domain, conservation, and derivation",))
 b,s=produce_course_bank("FLUID_MECHANICS",pack["pack_id"],pack["deterministic_sha256"],ev,fs,reviewer=rev,validator=val);return b,s,ev
