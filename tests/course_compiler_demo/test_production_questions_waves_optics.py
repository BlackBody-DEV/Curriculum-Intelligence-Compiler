from tools.course_compiler_demo.production_question_packs.waves_optics import build_bank


def test_waves_optics_real_locked_bank_and_coverage():
    bank, summary, evidence = build_bank()
    assert len(bank.candidates) == 100 == summary.locked
    assert summary.family_count == 10 and summary.procedure_count >= 5 and summary.micro_skill_count >= 10
    assert {x["answer_contract"]["shape"] for x in bank.candidates} == {"numeric_scalar"}
    assert {x["request"]["difficulty"] for x in bank.candidates} == {"introductory", "intermediate", "advanced"}
    assert {x["request"]["assessment_role"] for x in bank.candidates} == {"practice", "assessment"}
    assert all(not x["consumed_generator_answer"] for x in bank.derivations)
    assert all(x["passed"] if "passed" in x else all(x[k] for k in ("grading_pass", "procedure_compatibility_pass", "failure_signal_pass", "prompt_determinacy_pass", "unit_tolerance_pass", "answer_contract_pass")) for x in bank.validations)
    assert len({x["failure_signals"][-1] for x in bank.candidates}) == 10
    assert evidence[0]["access"] == "READ_ONLY_REFERENCE"
    assert len({x["candidate_id"] for x in bank.candidates}) == 100
    assert len({x["prompt"].strip().lower() for x in bank.candidates}) == 100
    assert len({x["fingerprint"] for x in bank.duplicates}) == 100
    assert max(sum(x["request"]["generation_family_id"] == family for x in bank.candidates) for family in {x["request"]["generation_family_id"] for x in bank.candidates}) <= 25
    assert all(not x["prompt"].lower().startswith("case ") for x in bank.candidates)
    diffraction = [x for x in bank.candidates if x["request"]["generation_family_id"].endswith("_06")]
    assert all(0 < (x["request"]["parameters"]["b"] * x["request"]["parameters"]["wavelength"]) / (x["request"]["parameters"]["a"] * 1e-3) <= 1 for x in diffraction)


def test_waves_optics_is_deterministic_and_nonfixture():
    a = build_bank()[0]
    b = build_bank()[0]
    assert a.to_json() == b.to_json()
    assert all(x["safety"]["synthetic_fixture"] is False and x["safety"]["production_candidate"] is True for x in a.candidates)
    assert all(x["findings"] and x["reviewer"] == "independent_waves_optics_artifact_reviewer" for x in a.reviews)


def test_waves_optics_validator_rejects_missing_domain_terms():
    from tools.course_compiler_demo.production_question_packs.waves_optics.bank import artifact_reviewer, waves_validator, _family
    from tools.course_compiler_demo.production_questions import ProductionQuestionCandidateV1, IndependentDerivationRecordV1
    from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog
    import pytest

    bank, _, _ = build_bank()
    first = dict(bank.candidates[0])
    first["prompt"] = "What is the result?"
    candidate = ProductionQuestionCandidateV1(**first)
    derivation = IndependentDerivationRecordV1(**bank.derivations[0])
    assert not waves_validator(candidate, derivation, derivation.normalized_answer).passed

    course = build_physics_engineering_course_catalog()["courses"]["WAVES_AND_OPTICS"]
    with pytest.raises(ValueError):
        artifact_reviewer(tuple(_family(i, course) for i in range(10)), {}, "WAVES_OPTICS_PRODUCTION_00", "FAMILY")
