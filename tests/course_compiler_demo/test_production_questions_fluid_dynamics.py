from tools.course_compiler_demo.production_question_packs.fluid_dynamics import build_bank
def test_fluid_dynamics_bank():
 b,s,_=build_bank();assert len(b.candidates)==100==s.validated;assert s.family_count==s.procedure_count==s.micro_skill_count==10;assert len({x["candidate_id"] for x in b.candidates})==len({x["prompt"].lower() for x in b.candidates})==len({x["fingerprint"] for x in b.duplicates})==100;assert all(x["request"]["parameters"]["viscosity"]>0 for x in b.candidates)
