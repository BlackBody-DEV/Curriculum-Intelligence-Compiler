from tools.course_compiler_demo.production_question_packs.fluid_dynamics.completion_300 import *
def test_completion():b,s=build_completion_bank();assert len(b.candidates)==100==s.validated;assert audit_completion()["status"]=="PASS"
