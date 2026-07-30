from tools.course_compiler_demo.production_question_packs.electricity_magnetism import build_bank

def test_em_real_locked_bank_coverage_and_conventions():
    bank,summary,conventions=build_bank()
    assert len(bank.candidates)==100==summary.locked
    assert summary.family_count==12 and summary.procedure_count>=5 and summary.micro_skill_count>=10
    assert {x["answer_contract"]["shape"] for x in bank.candidates}=={"numeric_scalar","numeric_vector"}
    assert {x["request"]["difficulty"] for x in bank.candidates}=={"introductory","intermediate","advanced"}
    assert {x["request"]["assessment_role"] for x in bank.candidates}=={"practice","assessment"}
    assert conventions["si_units"] and conventions["validated_candidates"]==100
    assert len({x["failure_signals"][-1] for x in bank.candidates})==12
    assert all(not x["consumed_generator_answer"] for x in bank.derivations)

def test_em_is_deterministic_and_nonfixture():
    a=build_bank()[0]; b=build_bank()[0]
    assert a.to_json()==b.to_json()
    assert all(x["safety"]["synthetic_fixture"] is False and x["safety"]["production_candidate"] is True for x in a.candidates)
    assert all(x["findings"] and x["reviewer"]=="independent_em_artifact_reviewer" for x in a.reviews)

def test_em_validator_and_corrected_formulas():
    from tools.course_compiler_demo.production_question_packs.electricity_magnetism.bank import _family,em_validator
    from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_reference_pack
    from tools.course_compiler_demo.production_questions import ProductionQuestionCandidateV1,IndependentDerivationRecordV1
    bank=build_bank()[0]; potential=next(x for x in bank.candidates if x["request"]["generation_family_id"].endswith("_03")); p=potential["request"]["parameters"]
    deriv=next(x for x in bank.derivations if x["candidate_id"]==potential["candidate_id"])
    assert deriv["normalized_answer"]==round(p["b"]*p["distance"],10)
    faraday=next(x for x in bank.candidates if x["request"]["generation_family_id"].endswith("_09")); q=faraday["request"]["parameters"]
    d=next(x for x in bank.derivations if x["candidate_id"]==faraday["candidate_id"]); assert d["normalized_answer"]==round(q["b"]*1e-3/q["a"],10)
    bad=dict(potential); bad["prompt"]="What is the potential?"; c=ProductionQuestionCandidateV1(**bad); dr=IndependentDerivationRecordV1(**deriv)
    assert not em_validator(c,dr,dr.normalized_answer).passed
    magnetic=next(x for x in bank.candidates if x["request"]["generation_family_id"].endswith("_08")); md=next(x for x in bank.derivations if x["candidate_id"]==magnetic["candidate_id"])
    assert md["normalized_answer"][0]==0 and md["normalized_answer"][1]<0 and "right-hand" in magnetic["prompt"]
    assert any(x["request"]["generation_family_id"].endswith("_10") for x in bank.candidates)
    assert any(x["request"]["generation_family_id"].endswith("_11") for x in bank.candidates)
    maxwell=next(x for x in bank.candidates if x["request"]["generation_family_id"].endswith("_11")); xp=maxwell["request"]["parameters"]
    xd=next(x for x in bank.derivations if x["candidate_id"]==maxwell["candidate_id"])
    assert xd["normalized_answer"]==round(1.11265005545e-17*(xp["b"]*1e12),10)
    from tools.course_compiler_demo.production_question_packs.electricity_magnetism.bank import artifact_reviewer
    import pytest
    with pytest.raises(ValueError): artifact_reviewer((),{},"ELECTROMAGNETISM_PRODUCTION_00","FAMILY")
