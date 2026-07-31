import pytest

from tools.course_compiler_demo.source_corpus.assessment_blueprints import (
    BlueprintType,
    SourceAssessmentBlueprintPackageV1,
    SourceAssessmentBlueprintV1,
    compile_assessment_blueprints,
    to_universal_blueprint,
    validate_blueprint_blocking,
)
from tools.course_compiler_demo.source_corpus.contracts import ContractError


def blueprint_payload(kind="DIAGNOSTIC"):
    return {
        "blueprint_id": f"bp-{kind.lower()}",
        "blueprint_type": kind,
        "course_id": "course-1",
        "question_count": 2,
        "time_budget_minutes": 10,
        "topic_weights": {"topic-1": 1.0},
        "difficulty_distribution": {"FOUNDATIONAL": 0.5, "ADVANCED": 0.5},
        "question_type_distribution": {"numeric_scalar": 1.0},
        "unit_scope": ("unit-1",),
        "micro_skill_coverage": ("skill-1", "skill-2"),
        "prerequisite_coverage": ("prereq-1",),
        "evidence_claim_ids": ("claim-1",),
        "course_outcome_ids": ("outcome-1",),
        "assessment_objective_ids": ("objective-1",),
        "generation_family_ids": ("family-1",),
        "grading_engine_ids": ("engine-1",),
        "source_example_ids": ("example-1",),
        "course_pack_policy_ids": ("policy-1",),
        "reuse_policy": {"allow_reuse": False},
        "variant_policy": {"variant_count": 3},
        "scoring_rules": {"points_per_question": 1},
        "rubrics": ({"rubric_id": "rubric-1"},),
    }


def blueprint(kind="DIAGNOSTIC", **changes):
    payload = blueprint_payload(kind)
    payload.update(changes)
    return SourceAssessmentBlueprintV1(**payload)


VALIDATION_CONTEXT = {
    "unit_courses": {"unit-1": "course-1"},
    "topic_courses": {"topic-1": "course-1"},
    "micro_skill_courses": {"skill-1": "course-1", "skill-2": "course-1"},
    "prerequisite_courses": {"prereq-1": "course-1"},
    "evidence_claim_courses": {"claim-1": "course-1"},
    "course_outcome_courses": {"outcome-1": "course-1"},
    "assessment_objective_courses": {"objective-1": "course-1"},
    "generation_family_courses": {"family-1": "course-1"},
    "grading_engine_courses": {"engine-1": "course-1"},
    "source_example_courses": {"example-1": "course-1"},
    "course_pack_policy_courses": {"policy-1": "course-1"},
    "required_topic_ids": ("topic-1",),
    "required_micro_skill_ids": ("skill-1", "skill-2"),
    "required_course_outcome_ids": ("outcome-1",),
    "required_assessment_objective_ids": ("objective-1",),
}


def validate(item, **changes):
    context = dict(VALIDATION_CONTEXT)
    context.update(changes)
    return validate_blueprint_blocking(item, course_id="course-1", **context)


def test_compiler_produces_exactly_four_deterministic_proposed_blueprints():
    declarations = tuple(
        blueprint_payload(kind.value) for kind in reversed(tuple(BlueprintType))
    )
    package = compile_assessment_blueprints(
        package_id="package-1",
        course_id="course-1",
        declarations=declarations,
        validation_context=VALIDATION_CONTEXT,
    )
    assert isinstance(package, SourceAssessmentBlueprintPackageV1)
    assert [item.blueprint_id for item in package.blueprints] == sorted(
        item["blueprint_id"] for item in declarations
    )
    assert {item.blueprint_type for item in package.blueprints} == {
        item.value for item in BlueprintType
    }
    assert package.review_state == "PROPOSED"
    assert package.canonical_authority is False
    assert package.to_json() == compile_assessment_blueprints(
        package_id="package-1",
        course_id="course-1",
        declarations=tuple(reversed(declarations)),
        validation_context=VALIDATION_CONTEXT,
    ).to_json()


def test_every_type_validates_and_projects_without_granting_authority():
    for kind in BlueprintType:
        item = blueprint(kind.value)
        assert validate(item)["valid"]
        projected = to_universal_blueprint(item)
        assert projected.blueprint_id == item.blueprint_id
        assert projected.question_count == 2
        assert projected.review_status == "PROPOSED"


@pytest.mark.parametrize(
    "field,foreign_value,foreign_error",
    [
        ("unit_scope", "unit-foreign", "CROSS_COURSE_UNIT"),
        ("topic_weights", "topic-foreign", "CROSS_COURSE_TOPIC"),
        ("micro_skill_coverage", "skill-foreign", "CROSS_COURSE_MICRO_SKILL"),
        ("prerequisite_coverage", "prereq-foreign", "CROSS_COURSE_PREREQUISITE"),
        ("evidence_claim_ids", "claim-foreign", "CROSS_COURSE_EVIDENCE"),
        ("course_outcome_ids", "outcome-foreign", "CROSS_COURSE_OUTCOME"),
        ("assessment_objective_ids", "objective-foreign", "CROSS_COURSE_OBJECTIVE"),
        ("generation_family_ids", "family-foreign", "CROSS_COURSE_GENERATION_FAMILY"),
        ("grading_engine_ids", "engine-foreign", "CROSS_COURSE_GRADING_ENGINE"),
        ("source_example_ids", "example-foreign", "CROSS_COURSE_SOURCE_EXAMPLE"),
        ("course_pack_policy_ids", "policy-foreign", "CROSS_COURSE_POLICY"),
    ],
)
def test_cross_course_contamination_is_blocked(field, foreign_value, foreign_error):
    payload = blueprint_payload()
    if field == "topic_weights":
        payload[field] = {foreign_value: 1.0}
        owner_key = "topic_courses"
    else:
        payload[field] = (foreign_value,)
        owner_key = {
            "unit_scope": "unit_courses",
            "micro_skill_coverage": "micro_skill_courses",
            "prerequisite_coverage": "prerequisite_courses",
            "evidence_claim_ids": "evidence_claim_courses",
            "course_outcome_ids": "course_outcome_courses",
            "assessment_objective_ids": "assessment_objective_courses",
            "generation_family_ids": "generation_family_courses",
            "grading_engine_ids": "grading_engine_courses",
            "source_example_ids": "source_example_courses",
            "course_pack_policy_ids": "course_pack_policy_courses",
        }[field]
    context_update = {
        owner_key: {**VALIDATION_CONTEXT[owner_key], foreign_value: "course-2"}
    }
    with pytest.raises(ContractError, match=foreign_error):
        validate(SourceAssessmentBlueprintV1(**payload), **context_update)


@pytest.mark.parametrize(
    "change,context_change,error",
    [
        ({"course_id": "other"}, {}, "COURSE_MISMATCH"),
        ({"topic_weights": {"other": 1.0}}, {"topic_courses": {"other": "course-1"}}, "TOPIC_DISTRIBUTION_INCOMPLETE"),
        ({"micro_skill_coverage": ("skill-1",)}, {}, "MICRO_SKILL_COVERAGE_INSUFFICIENT"),
        ({"course_outcome_ids": ("outcome-2",)}, {"course_outcome_courses": {"outcome-2": "course-1"}}, "COURSE_OUTCOME_COVERAGE_INSUFFICIENT"),
        ({"assessment_objective_ids": ("objective-2",)}, {"assessment_objective_courses": {"objective-2": "course-1"}}, "ASSESSMENT_OBJECTIVE_COVERAGE_INSUFFICIENT"),
        ({"question_count": 20, "time_budget_minutes": 10}, {}, "IMPOSSIBLE_TIME_BUDGET"),
        ({}, {"blocking_conflicts": ("conflict-1",)}, "SOURCE_CONFLICT_BLOCKED"),
        ({}, {"coverage_gaps": ("gap-1",)}, "SOURCE_COVERAGE_GAP_BLOCKED"),
    ],
)
def test_resolution_coverage_and_feasibility_fail_closed(change, context_change, error):
    with pytest.raises(ContractError, match=error):
        validate(blueprint(**change), **context_change)


@pytest.mark.parametrize(
    "change",
    [
        {"blueprint_type": "OTHER"},
        {"topic_weights": {"topic-1": 0.5}},
        {"difficulty_distribution": {"FOUNDATIONAL": float("nan")}},
        {"question_type_distribution": {"numeric_scalar": -0.1, "other": 1.1}},
        {"unit_scope": ()},
        {"micro_skill_coverage": ("skill-1", "skill-1")},
        {"evidence_claim_ids": ()},
        {"course_outcome_ids": ()},
        {"course_pack_policy_ids": ()},
        {"reuse_policy": {"allow_reuse": "no"}},
        {"variant_policy": {"variant_count": 0}},
        {"scoring_rules": {"points_per_question": True}},
        {"rubrics": ({"rubric_id": "same"}, {"rubric_id": "same"})},
        {"canonical_authority": True},
        {"review_state": "APPROVED_FOR_COMPILER_REVIEW"},
        {"question_count": 1},
    ],
)
def test_contract_fields_and_nested_policies_fail_closed(change):
    with pytest.raises(ContractError):
        blueprint(**change)


def test_missing_dependencies_and_incomplete_package_fail_closed():
    for owner_key in (
        "unit_courses",
        "topic_courses",
        "micro_skill_courses",
        "prerequisite_courses",
        "evidence_claim_courses",
        "course_outcome_courses",
        "assessment_objective_courses",
        "generation_family_courses",
        "grading_engine_courses",
        "source_example_courses",
        "course_pack_policy_courses",
    ):
        with pytest.raises(ContractError):
            validate(blueprint(), **{owner_key: {}})
    with pytest.raises(ContractError, match="CROSS_COURSE_UNIT"):
        validate(blueprint(), unit_courses={"unit-1": None})
    with pytest.raises(ContractError, match="exactly one blueprint"):
        compile_assessment_blueprints(
            package_id="package-1",
            course_id="course-1",
            declarations=(blueprint_payload("PRACTICE"),),
            validation_context=VALIDATION_CONTEXT,
        )


def test_performance_tracking_fields_remain_forbidden():
    with pytest.raises(ContractError, match="forbidden performance field"):
        blueprint(scoring_rules={"points_per_question": 1, "student_score": 0})
