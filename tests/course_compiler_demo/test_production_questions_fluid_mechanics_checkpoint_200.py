from tools.course_compiler_demo.production_question_packs.fluid_mechanics.checkpoint_200 import *
def test_checkpoint():b,s=build_checkpoint_bank();assert len(b.candidates)==100==s.validated;assert audit_checkpoint()["status"]=="PASS"
