from tools.course_compiler_demo.production_question_packs.dynamics import build_bank


def test_dynamics_locked_bank_quality():
    bank,summary,evidence=build_bank(); assert len(bank.candidates)==100==summary.validated==summary.locked; assert summary.family_count==10 and summary.procedure_count==10 and summary.micro_skill_count==10; assert {row["answer_contract"]["shape"] for row in bank.candidates}=={"numeric_scalar","numeric_vector"}; assert {row["request"]["difficulty"] for row in bank.candidates}=={"introductory","intermediate","advanced"}; assert len({row["candidate_id"] for row in bank.candidates})==len({row["prompt"].lower() for row in bank.candidates})==len({row["fingerprint"] for row in bank.duplicates})==100; assert all(not row["consumed_generator_answer"] for row in bank.derivations); assert evidence[0]["access"]=="READ_ONLY_REFERENCE"


def test_dynamics_deterministic_and_fail_closed():
    from tools.course_compiler_demo.production_question_packs.dynamics.bank import dynamics_validator
    from tools.course_compiler_demo.production_questions import ProductionQuestionCandidateV1,IndependentDerivationRecordV1
    a=build_bank()[0]; b=build_bank()[0]; assert a.to_json()==b.to_json(); payload=dict(a.candidates[0]); payload["prompt"]="What is the result?"; assert not dynamics_validator(ProductionQuestionCandidateV1(**payload),IndependentDerivationRecordV1(**a.derivations[0]),a.derivations[0]["normalized_answer"]).passed
