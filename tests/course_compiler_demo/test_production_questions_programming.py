from tools.course_compiler_demo.production_question_packs.programming_fundamentals import build_programming_fundamentals_bank,write_programming_fundamentals_evidence
def test_bank():
 bank,s=build_programming_fundamentals_bank(); c=bank.candidates
 assert len(c)==100 and bank.locked and s.locked==100
 assert {x["request"]["difficulty"] for x in c}=={"introductory","intermediate","advanced"}
 assert sum(x["request"]["assessment_role"]=="practice" for x in c)==70
 assert {x["answer_contract"]["shape"] for x in c}=={"numeric_scalar","multiple_choice"}
 assert len({x["request"]["generation_family_id"] for x in c})==14 and len({x["procedure_id"] for x in c})==14 and len({x["micro_skill_id"] for x in c})==14
 assert all(x["safety"]["synthetic_fixture"] is False and x["answer_contract"]["engine_type"]!="code_execution" for x in c)
 assert all("Choices:" in x["prompt"] for x in c if x["answer_contract"]["shape"]=="multiple_choice")
 assert all(x["findings"] and x["reviewer"]=="independent_programming_content_review" for x in bank.reviews)
def test_deterministic_unique():
 a,_=build_programming_fundamentals_bank(); b,_=build_programming_fundamentals_bank()
 assert a.bank_sha256==b.bank_sha256 and len({x["candidate_id"] for x in a.candidates})==100
 assert all(x["classification"]!="EXACT_DUPLICATE" for x in a.duplicates) and all(x["grading_pass"] for x in a.validations)
 # A generator defect must be detectable because derivation uses separate logic.
 from tools.course_compiler_demo.production_question_packs.programming_fundamentals.bank import _independent_derivation
 assert _independent_derivation("expression_precedence",{"a":2,"b":3,"c":4})==14
def test_output(tmp_path):
 b,s=write_programming_fundamentals_evidence(tmp_path)
 assert len(list(tmp_path.iterdir()))==11 and (tmp_path/"banks"/"programming_fundamentals_locked_bank.json").is_file() and s.validated==100
def test_multiple_choice_and_review_fail_closed():
 import pytest
 from dataclasses import replace
 from tools.course_compiler_demo.production_question_packs.programming_fundamentals.bank import _choice_evidence
 from tools.course_compiler_demo.production_question_packs.programming_fundamentals.review import build_evidence_reviewer
 bank,_=build_programming_fundamentals_bank(); mc=next(x for x in bank.candidates if x["answer_contract"]["shape"]=="multiple_choice")
 from tools.course_compiler_demo.production_questions import ProductionQuestionCandidateV1
 candidate=ProductionQuestionCandidateV1(**mc)
 assert _choice_evidence(candidate,"not-an-option")["passed"] is False
 with pytest.raises(ValueError): build_evidence_reviewer({})(candidate.request["generation_family_id"],"FAMILY")
