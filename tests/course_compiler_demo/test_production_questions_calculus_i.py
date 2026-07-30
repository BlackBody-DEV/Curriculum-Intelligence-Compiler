from collections import Counter
from tools.course_compiler_demo.production_question_packs.calculus_i import build_bank
from tools.course_compiler_demo.production_question_packs.calculus_i.bank import AREAS
def test_calculus_i_locked_real_bank():
 bank,summary=build_bank(); req=[c["request"] for c in bank.candidates]
 assert bank.locked and len(bank.candidates)==100==summary.validated
 assert Counter(x["difficulty"] for x in req)=={"introductory":30,"intermediate":50,"advanced":20}
 assert Counter(x["assessment_role"] for x in req)=={"practice":70,"assessment":30}
 assert len({x["generation_family_id"] for x in req})>=10 and len({c["procedure_id"] for c in bank.candidates})>=5 and len({c["micro_skill_id"] for c in bank.candidates})>=10
 assert {c["answer_contract"]["shape"] for c in bank.candidates}=={"numeric_scalar","multiple_choice"}
 assert {x["parameters"]["coverage_area"] for x in req}==set(AREAS)
 assert all(not c["safety"]["synthetic_fixture"] and c["answer_contract"]["engine_enabled"] for c in bank.candidates)
 assert all(r["findings"] and r["reviewer"]=="calculus_i_independent_content_reviewer" for r in bank.reviews)
 assert all(d["derivation_source"].startswith("independent:") and not d["consumed_generator_answer"] for d in bank.derivations)
 assert all("Choices:" in c["prompt"] for c in bank.candidates if c["answer_contract"]["shape"]=="multiple_choice")
def test_calculus_i_deterministic(): assert build_bank()[0].to_json()==build_bank()[0].to_json()
def test_calculus_choice_and_review_fail_closed():
 import pytest
 from tools.course_compiler_demo.production_questions import ProductionQuestionCandidateV1
 from tools.course_compiler_demo.production_question_packs.calculus_i.bank import _choice_evidence
 from tools.course_compiler_demo.production_question_packs.calculus_i.reviewer import build_evidence_reviewer
 bank,_=build_bank(); raw=next(x for x in bank.candidates if x["answer_contract"]["shape"]=="multiple_choice"); candidate=ProductionQuestionCandidateV1(**raw)
 assert _choice_evidence(candidate,"A")["passed"]
 malformed=ProductionQuestionCandidateV1(**{**raw,"prompt":raw["prompt"].split("Choices:")[0]+"Choices: A, A."})
 assert not _choice_evidence(malformed,"A")["passed"]
 assert not _choice_evidence(candidate,"absent")["passed"]
 wrong=ProductionQuestionCandidateV1(**{**raw,"prompt":raw["prompt"].replace("Option A is ","Option A is 9999 # ")})
 assert not _choice_evidence(wrong,"A")["passed"]
 with pytest.raises(ValueError): build_evidence_reviewer({})(candidate.request["generation_family_id"],"FAMILY")
