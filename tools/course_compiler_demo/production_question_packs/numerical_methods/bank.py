"""Task 131 Numerical Methods checkpoint 100."""
from tools.course_compiler_demo.production_question_packs.differential_equations.bank import build_additions
from tools.course_compiler_demo.universal_integration.capability_catalog_wave_044 import compile_course_pilot,discover_course_catalog,discover_generation_recipe_runtime
COURSE_ID="NUMERICAL_METHODS"
def build_checkpoint_bank():
 c=discover_course_catalog();o=discover_generation_recipe_runtime(c["new"]);p=compile_course_pilot(c["new"][COURSE_ID],o)
 if p["validated"]!=25 or p["locked"]!=25:raise ValueError("authoritative count unavailable")
 return build_additions(COURSE_ID,list(p["questions"]),25,75,5,"math131c100")
def audit_checkpoint():
 rows,s=build_checkpoint_bank();again,t=build_checkpoint_bank();return {**s,"deterministic_replay":s["bank_sha256"]==t["bank_sha256"],"metadata_complete":all(q["production_status"]=="LOCKED_PRODUCTION_VALIDATED" for q in rows)}
