from collections import Counter
from tools.course_compiler_demo.production_question_packs.algebra_i import build_bank
from tools.course_compiler_demo.production_question_packs.algebra_i.bank import AREAS
def test_algebra_i_locked_real_bank():
 bank,summary=build_bank(); req=[c["request"] for c in bank.candidates]
 assert bank.locked and len(bank.candidates)==100==summary.validated
 assert Counter(x["difficulty"] for x in req)=={"introductory":30,"intermediate":50,"advanced":20}
 assert Counter(x["assessment_role"] for x in req)=={"practice":70,"assessment":30}
 assert len({x["generation_family_id"] for x in req})>=10 and len({c["procedure_id"] for c in bank.candidates})>=5 and len({c["micro_skill_id"] for c in bank.candidates})>=10
 assert {c["answer_contract"]["shape"] for c in bank.candidates}=={"numeric_scalar","numeric_pair"}
 assert {x["parameters"]["coverage_area"] for x in req}==set(AREAS)
 assert all(not c["safety"]["synthetic_fixture"] and c["answer_contract"]["engine_enabled"] for c in bank.candidates)
 assert all(r["findings"] and r["reviewer"]=="algebra_i_independent_content_reviewer" for r in bank.reviews)
 assert all(d["derivation_source"].startswith("independent:") and not d["consumed_generator_answer"] for d in bank.derivations)
def test_algebra_i_deterministic(): assert build_bank()[0].to_json()==build_bank()[0].to_json()
def test_algebra_review_fails_without_artifact_evidence():
 import pytest
 from tools.course_compiler_demo.production_question_packs.algebra_i.reviewer import build_evidence_reviewer
 with pytest.raises(ValueError): build_evidence_reviewer({})("ALGEBRA_PRODUCTION_00","FAMILY")
 with pytest.raises(ValueError): build_evidence_reviewer({"c":{"family_id":"f","shape":"numeric_scalar","candidate_digest":"x","validation_digest":"y","passed":False}})("c","INSTANCE")
