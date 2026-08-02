from .bank import COURSE_ID,build_checkpoint_bank
from tools.course_compiler_demo.production_question_packs.differential_equations.bank import build_additions
from tools.course_compiler_demo.universal_integration.capability_catalog_wave_044 import compile_course_pilot,discover_course_catalog,discover_generation_recipe_runtime
def build_checkpoint_200_bank():
 c=discover_course_catalog();o=discover_generation_recipe_runtime(c["new"]);p=compile_course_pilot(c["new"][COURSE_ID],o);b,s=build_checkpoint_bank()
 if p["validated"]!=25 or s["after"]!=100:raise ValueError("checkpoint 100 unavailable")
 return build_additions(COURSE_ID,list(p["questions"])+list(b),100,100,20,"math131c200")
def audit_checkpoint_200():
 r,s=build_checkpoint_200_bank();a,t=build_checkpoint_200_bank();return {**s,"deterministic_replay":s["bank_sha256"]==t["bank_sha256"],"metadata_complete":all(q["production_status"]=="LOCKED_PRODUCTION_VALIDATED" for q in r)}
