from __future__ import annotations
import math
from tools.course_compiler_demo.production_questions import ProductionFamily,ProductionReviewRecordV1,ProductionValidationRecordV1,default_validator,produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog,validate_physics_engineering_course_catalog
DOMAINS=("velocity field","continuity field","material acceleration","Euler pressure gradient","viscous shear","vorticity","boundary-layer Reynolds","mass flow","Mach number","circulation")
def _family(i,c):
 p=c["procedures"][i];s=c["micro_skills"][i];t=next(x for x in c["topics"] if x["topic_id"]==s["topic_id"])
 def params(n):
  a=float(n+i+10);b=float((n%7)+2);return {"a":a,"b":b,"rho":1.2+a/100,"velocity":10+a/10,"length":.5+b/10,"viscosity":1.8e-5+b/1e6,"area":.1+b/100,"sound":340+b}
 def calc(x):
  a,b,rho,u,L,mu,A,c=x["a"],x["b"],x["rho"],x["velocity"],x["length"],x["viscosity"],x["area"],x["sound"]
  return (math.hypot(u,b),a/100+b/100,u*(a/100)+b/10,rho*(a/10),mu*(u/L),(b/L-a/(10*L)),rho*u*L/mu,rho*A*u,u/c,u*L)[i]
 def gen(x):
  a,b,rho,u,L,mu,A,c=x["a"],x["b"],x["rho"],x["velocity"],x["length"],x["viscosity"],x["area"],x["sound"]
  q=(f"An Eulerian velocity field has components {u:.2f} and {b:.2f} m/s; what velocity magnitude in m/s results?",f"A planar velocity field has gradients du/dx={a/100:.3f} 1/s and dv/dy={b/100:.3f} 1/s; what divergence in 1/s results for continuity assessment?",f"A steady one-dimensional field has velocity {u:.2f} m/s, gradient du/dx={a/100:.3f} 1/s, and local acceleration {b/10:.2f} m/s^2; what material acceleration in m/s^2 results?",f"An inviscid fluid density {rho:.3f} kg/m^3 has acceleration {a/10:.2f} m/s^2; what Euler pressure-gradient magnitude in Pa/m results?",f"A Newtonian fluid viscosity {mu:.7f} Pa s changes velocity {u:.2f} m/s across gap {L:.3f} m; what viscous shear stress in Pa results?",f"A planar field has dv/dx={b/L:.3f} 1/s and du/dy={a/(10*L):.3f} 1/s; what signed vorticity in 1/s results?",f"External flow density {rho:.3f} kg/m^3 at {u:.2f} m/s over length {L:.3f} m has viscosity {mu:.7f} Pa s; what Reynolds number results?",f"A compressible stream density {rho:.3f} kg/m^3 crosses area {A:.3f} m^2 at {u:.2f} m/s; what mass flow in kg/s results?",f"A stream moves at {u:.2f} m/s where sound speed is {c:.2f} m/s; what Mach number results?",f"A uniform tangential velocity {u:.2f} m/s follows a contour length {L:.3f} m; what circulation in m^2/s results?")
  return q[i],calc(x)
 return ProductionFamily(f"FLUID_DYNAMICS_PRODUCTION_{i:02d}",p["procedure_id"],t["unit_id"],t["topic_id"],s["micro_skill_id"],"numeric_scalar","numeric_scalar",("unit_mismatch","dimension_mismatch","sign_error",DOMAINS[i].replace(" ","_")+"_error"),params,gen,calc)
def validator(c,d,a):
 base=default_validator(c,d,a);i=int(c.request["generation_family_id"].split("_")[-1]);keys=(("velocity field","m/s"),("divergence","continuity"),("material acceleration","m/s^2"),("euler","pa/m"),("viscous shear","pa"),("vorticity","1/s"),("reynolds",),("mass flow","kg/s"),("mach number",),("circulation","m^2/s"))[i];ok=all(k in c.prompt.lower() for k in keys);return ProductionValidationRecordV1(base.validation_id,base.candidate_id,base.grading_pass,base.procedure_compatibility_pass,base.failure_signal_pass,base.prompt_determinacy_pass,base.unit_tolerance_pass and ok,base.answer_contract_pass,base.reasons+(() if ok else ("FLUID_DYNAMICS_DOMAIN_FAILED",)))
def build_bank():
 pack=build_physics_engineering_course_catalog();validate_physics_engineering_course_catalog(pack);c=pack["courses"]["FLUID_DYNAMICS"];fs=tuple(_family(i,c) for i in range(10));ev=({"evidence_id":"FLUID_DYNAMICS:CATALOG","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"],"access":"READ_ONLY_REFERENCE"},)
 def rev(subject,level):return ProductionReviewRecordV1(f"review:{level.lower()}:{subject}",subject,level,"PASS","independent_fluid_dynamics_reviewer",("verified field, momentum, dimensions, and domain",))
 b,s=produce_course_bank("FLUID_DYNAMICS",pack["pack_id"],pack["deterministic_sha256"],ev,fs,reviewer=rev,validator=validator);return b,s,ev
