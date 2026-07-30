from tools.course_compiler_demo.production_question_packs.general_chemistry import build_general_chemistry_bank,write_general_chemistry_evidence
def test_bank():
 bank,s=build_general_chemistry_bank(); c=bank.candidates
 assert len(c)==100 and bank.locked and s.locked==100
 assert {x["request"]["difficulty"] for x in c}=={"introductory","intermediate","advanced"} and sum(x["request"]["assessment_role"]=="practice" for x in c)==70
 assert {x["answer_contract"]["shape"] for x in c}=={"numeric_scalar","multiple_choice"}
 assert len({x["request"]["generation_family_id"] for x in c})==14 and len({x["procedure_id"] for x in c})==14 and len({x["micro_skill_id"] for x in c})==14
 assert all(x["safety"]["synthetic_fixture"] is False and x["answer_contract"]["engine_type"]!="chemical_reaction" for x in c)
 assert all("Choices:" in x["prompt"] for x in c if x["answer_contract"]["shape"]=="multiple_choice")
 assert all("significant figures" in x["prompt"] for x in c if x["answer_contract"]["shape"]=="numeric_scalar")
 assert all(x["findings"] and x["reviewer"]=="independent_chemistry_content_review" for x in bank.reviews)
def test_deterministic_unique_and_chemistry_gates():
 a,_=build_general_chemistry_bank(); b,_=build_general_chemistry_bank()
 assert a.bank_sha256==b.bank_sha256 and len({x["candidate_id"] for x in a.candidates})==100
 assert all(x["classification"]!="EXACT_DUPLICATE" for x in a.duplicates) and all(x["grading_pass"] and x["unit_tolerance_pass"] for x in a.validations)
 assert all({"unit_conversion_error","significant_figure_error","stoichiometric_ratio_error","formula_consistency_error"}.issubset(x["failure_signals"]) for x in a.candidates)
 assert all(x["unit_tolerance_pass"] and not x["reasons"] for x in a.validations)
def test_output(tmp_path):
 b,s=write_general_chemistry_evidence(tmp_path)
 assert len(list(tmp_path.iterdir()))==11 and (tmp_path/"banks"/"general_chemistry_locked_bank.json").is_file() and s.validated==100
def test_multiple_choice_and_review_fail_closed():
 import pytest
 from tools.course_compiler_demo.production_question_packs.general_chemistry.bank import _choice_evidence
 from tools.course_compiler_demo.production_question_packs.general_chemistry.review import build_evidence_reviewer
 from tools.course_compiler_demo.production_questions import ProductionQuestionCandidateV1
 bank,_=build_general_chemistry_bank(); mc=ProductionQuestionCandidateV1(**next(x for x in bank.candidates if x["answer_contract"]["shape"]=="multiple_choice"))
 assert _choice_evidence(mc,"not-an-option")["passed"] is False
 with pytest.raises(ValueError): build_evidence_reviewer({})(mc.request["generation_family_id"],"FAMILY")
