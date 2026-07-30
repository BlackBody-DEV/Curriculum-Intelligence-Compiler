from tools.course_compiler_demo.production_question_packs.statics import build_bank

def test_statics_real_locked_bank_and_coverage():
    bank,summary,evidence=build_bank()
    assert len(bank.candidates)==100==summary.locked
    assert summary.family_count==10 and summary.procedure_count>=5 and summary.micro_skill_count>=10
    assert {x["answer_contract"]["shape"] for x in bank.candidates}=={"numeric_scalar","numeric_vector"}
    assert {x["request"]["difficulty"] for x in bank.candidates}=={"introductory","intermediate","advanced"}
    assert {x["request"]["assessment_role"] for x in bank.candidates}=={"practice","assessment"}
    assert all(not x["consumed_generator_answer"] for x in bank.derivations)
    assert all(x["passed"] if "passed" in x else all(x[k] for k in ("grading_pass","procedure_compatibility_pass","failure_signal_pass","prompt_determinacy_pass","unit_tolerance_pass","answer_contract_pass")) for x in bank.validations)
    assert len({x["failure_signals"][-1] for x in bank.candidates})==10

def test_statics_is_deterministic_and_nonfixture():
    a=build_bank()[0]; b=build_bank()[0]
    assert a.to_json()==b.to_json()
    assert all(x["safety"]["synthetic_fixture"] is False and x["safety"]["production_candidate"] is True for x in a.candidates)
    assert all(x["findings"] and x["reviewer"]=="independent_statics_artifact_reviewer" for x in a.reviews)

def test_statics_validator_rejects_missing_units_and_axes():
    from tools.course_compiler_demo.production_question_packs.statics.bank import statics_validator
    from tools.course_compiler_demo.production_questions import ProductionQuestionCandidateV1,IndependentDerivationRecordV1
    bank=build_bank()[0]; p=dict(bank.candidates[0]); p["prompt"]="What are the components?"
    c=ProductionQuestionCandidateV1(**p); d=IndependentDerivationRecordV1(**bank.derivations[0])
    assert not statics_validator(c,d,d.normalized_answer).passed
    assert "at x=0" in next(x["prompt"] for x in bank.candidates if x["request"]["generation_family_id"].endswith("_08"))
    centroid=next(x for x in bank.candidates if x["request"]["generation_family_id"].endswith("_08")); cp=centroid["request"]["parameters"]
    cd=next(x for x in bank.derivations if x["candidate_id"]==centroid["candidate_id"])
    assert cd["normalized_answer"]==round(cp["b"]*cp["length"]/(cp["a"]+cp["b"]),10)
    from tools.course_compiler_demo.production_question_packs.statics.bank import artifact_reviewer,_family
    from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_reference_pack
    import pytest
    course=build_physics_engineering_reference_pack()["courses"]["STATICS"]
    with pytest.raises(ValueError): artifact_reviewer(tuple(_family(i,course) for i in range(10)),{},"STATICS_PRODUCTION_00","FAMILY")
