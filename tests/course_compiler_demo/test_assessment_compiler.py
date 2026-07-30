import pytest

from tools.course_compiler_demo.assessment_compiler import AssessmentCompilationError, compile_assessment
from tools.course_compiler_demo.universal_core import AssessmentBlueprintV1, ContractError, ValidatedQuestionReferenceV1


def reference(i, *, course="course-1"):
    topics = ["t1", "t2", "t3", "t4", "t5"]
    difficulty = "EASY" if i % 2 == 0 else "HARD"
    qtype = "MULTIPLE_CHOICE" if (i // 2) % 2 == 0 else "NUMERIC"
    topic = topics[(i // 4) % 5]
    return ValidatedQuestionReferenceV1(
        f"q-{i:04}", "r1", f"proc-{i % 7}", f"family-{i % 11}", "answer-1", f"valid-{i}",
        curriculum_mapping={"course_id": course, "unit_id": "u1", "topic_id": topic,
                            "micro_skill_ids": [f"m{i % 3}"], "prerequisite_ids": [f"p{i % 2}"]},
        difficulty=difficulty, grading_contract={"method": "EXACT"},
        failure_signals=({"code": "WRONG"},), assessment_identity="bank-assessment",
        assessment_role="VALIDATED_BANK", provenance={"provider": "fixture", "validated": True},
        asset_references=(), version_data={"question_type": qtype, "estimated_minutes": 1},
    )


def blueprint(count=40, budget=40):
    return AssessmentBlueprintV1(
        "bp-1", "course-1", count,
        {f"t{i}": .2 for i in range(1, 6)}, {"EASY": .5, "HARD": .5},
        {"MULTIPLE_CHOICE": .5, "NUMERIC": .5}, budget, unit_scope=("u1",),
        micro_skill_coverage=("m0", "m1", "m2"), prerequisite_coverage=("p0", "p1"),
        reuse_policy={"allow_reuse": False}, variant_policy={"assessment_role": "SUMMATIVE"},
        scoring_rules={"points_per_question": 1}, rubrics=({"id": "rubric-1"},),
    )


def test_blueprint_validation_and_exact_allocations():
    with pytest.raises(ContractError):
        AssessmentBlueprintV1("", "course", 1, {"t": 1}, {"E": 1}, {"N": 1}, 1)
    result = compile_assessment(blueprint(), [reference(i) for i in range(160)], "fixed")
    assert len(result.question_references) == 40
    assert result.allocation["topic"] == {f"t{i}": 8 for i in range(1, 6)}
    assert result.allocation["difficulty"] == {"EASY": 20, "HARD": 20}
    assert result.allocation["question_type"] == {"MULTIPLE_CHOICE": 20, "NUMERIC": 20}
    assert result.total_time_minutes == 40
    assert result.scoring_rules == {"points_per_question": 1}
    assert result.rubrics == ({"id": "rubric-1"},)
    assert result.variant_policy == {"assessment_role": "SUMMATIVE"}


def test_determinism_variants_reuse_and_time_budget():
    bank = [reference(i) for i in range(200)]
    first = compile_assessment(blueprint(), bank, "seed", variant_index=0)
    assert first.to_json() == compile_assessment(blueprint(), reversed(bank), "seed", variant_index=0).to_json()
    variants = [compile_assessment(blueprint(), bank, "seed", variant_index=i) for i in range(3)]
    assert len({tuple(q["question_id"] for q in v.question_references) for v in variants}) == 3
    used = [q["question_id"] for q in first.question_references]
    second = compile_assessment(blueprint(), bank, "seed-2", previously_used_question_ids=used)
    assert not set(used) & {q["question_id"] for q in second.question_references}
    with pytest.raises(AssessmentCompilationError, match="time budget"):
        compile_assessment(blueprint(budget=39), bank, "seed")


def test_search_uses_coverage_and_time_and_prevents_cross_revision_reuse():
    bank = [reference(i) for i in range(160)]
    # The early candidates cannot cover this skill, but later candidates can.
    special = reference(159).to_dict()
    special["curriculum_mapping"]["micro_skill_ids"] = ["required-special"]
    bank[-1] = ValidatedQuestionReferenceV1.from_dict(special)
    bp = blueprint()
    object.__setattr__(bp, "micro_skill_coverage", ("required-special",))
    result = compile_assessment(bp, bank, "coverage-search")
    assert any("required-special" in q["curriculum_mapping"]["micro_skill_ids"] for q in result.question_references)

    revision = reference(1).to_dict()
    revision["question_revision"] = "r2"
    revision["validation_result_id"] = "valid-revision"
    result = compile_assessment(blueprint(), bank + [revision], "revision")
    ids = [q["question_id"] for q in result.question_references]
    assert len(ids) == len(set(ids))
    with pytest.raises(AssessmentCompilationError):
        compile_assessment(blueprint(), bank, "used", previously_used_question_ids=[r.question_id for r in bank])


def test_incomplete_coverage_and_insufficient_bank_fail_closed():
    bank = [reference(i) for i in range(20)]
    with pytest.raises(AssessmentCompilationError):
        compile_assessment(blueprint(), bank, "seed")
    wrong_course = [reference(i, course="other") for i in range(100)]
    with pytest.raises(AssessmentCompilationError):
        compile_assessment(blueprint(), wrong_course, "seed")
    bad = blueprint()
    object.__setattr__(bad, "topic_weights", {"t1": .9})
    with pytest.raises(AssessmentCompilationError, match="sum to 1"):
        compile_assessment(bad, [reference(i) for i in range(100)], "seed")


def test_scale_proof_25_practice_40_summative_and_three_variants():
    bank = [reference(i) for i in range(300)]
    practice = blueprint(25, 25)
    object.__setattr__(practice, "blueprint_id", "practice-25")
    object.__setattr__(practice, "topic_weights", {f"t{i}": .2 for i in range(1, 6)})
    object.__setattr__(practice, "difficulty_distribution", {"EASY": .52, "HARD": .48})
    object.__setattr__(practice, "question_type_distribution", {"MULTIPLE_CHOICE": .52, "NUMERIC": .48})
    p = compile_assessment(practice, bank, "scale")
    s = compile_assessment(blueprint(), bank, "scale")
    variants = [compile_assessment(blueprint(), bank, "scale", variant_index=i) for i in range(3)]
    assert (len(p.question_references), len(s.question_references), len(variants)) == (25, 40, 3)
