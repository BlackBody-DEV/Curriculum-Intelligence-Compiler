from .bank import COURSE_ID,build_checkpoint_bank
from .checkpoint_200 import build_checkpoint_200_bank
from tools.course_compiler_demo.production_question_packs.differential_equations.bank import build_additions
from tools.course_compiler_demo.universal_integration.capability_catalog_wave_044 import compile_course_pilot,discover_course_catalog,discover_generation_recipe_runtime
def build_completion_300_bank():
 c=discover_course_catalog();o=discover_generation_recipe_runtime(c["new"]);p=compile_course_pilot(c["new"][COURSE_ID],o);a,x=build_checkpoint_bank();b,y=build_checkpoint_200_bank()
 if p["validated"]!=25 or x["after"]!=100 or y["after"]!=200:raise ValueError("checkpoint 200 unavailable")
 return build_additions(COURSE_ID,list(p["questions"])+list(a)+list(b),200,100,40,"math131c300")
def audit_completion_300():
 r,s=build_completion_300_bank();a,t=build_completion_300_bank();return {**s,"deterministic_replay":s["bank_sha256"]==t["bank_sha256"],"metadata_complete":all(q["production_status"]=="LOCKED_PRODUCTION_VALIDATED" for q in r)}
