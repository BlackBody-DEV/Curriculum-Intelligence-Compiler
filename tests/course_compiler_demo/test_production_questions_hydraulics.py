from tools.course_compiler_demo.production_question_packs.hydraulics import build_bank
def test_hydraulics_bank():
 b,s,_=build_bank();assert len(b.candidates)==100==s.validated;assert s.family_count==s.procedure_count==s.micro_skill_count==10;assert len({x["candidate_id"] for x in b.candidates})==len({x["prompt"].lower() for x in b.candidates})==len({x["fingerprint"] for x in b.duplicates})==100;assert all(x["request"]["parameters"]["flow"]>0 for x in b.candidates)
