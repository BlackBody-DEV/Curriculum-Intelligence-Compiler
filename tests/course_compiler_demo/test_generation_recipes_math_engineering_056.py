from dataclasses import replace

import pytest

from tools.course_compiler_demo.generation_recipes.domains.math_engineering import (
    COURSE_RECIPE_REGISTRY,GenerationContextV1,audit_recipe_catalog,generate_course_pilot,get_course_recipes,
)
from tools.course_compiler_demo.subject_packs.engineering_mathematics import build_engineering_mathematics_catalog
from tools.course_compiler_demo.subject_packs.mathematics import build_remaining_mathematics_catalog


EXPECTED={"PRE_ALGEBRA","ALGEBRA_II","GEOMETRY","TRIGONOMETRY","PRE_CALCULUS","CALCULUS_II","CALCULUS_III","DIFFERENTIAL_EQUATIONS","LINEAR_ALGEBRA","NUMERICAL_METHODS","ENGINEERING_ANALYSIS","APPLIED_MATHEMATICS"}


def all_courses():
    return {**build_remaining_mathematics_catalog()["courses"],**build_engineering_mathematics_catalog()["courses"]}


def test_exact_twelve_course_registry_and_sixty_valid_recipes():
    assert set(COURSE_RECIPE_REGISTRY)==EXPECTED
    assert audit_recipe_catalog()=={"courses":12,"recipes":60,"status":"PASS"}
    assert all(len(recipes)==5 for recipes in COURSE_RECIPE_REGISTRY.values())


def test_bindings_resolve_exact_catalog_family_skill_topic_and_procedure():
    courses=all_courses()
    for course_id,recipes in COURSE_RECIPE_REGISTRY.items():
        course=courses[course_id]; topics={x["topic_id"] for x in course["topics"]}; skills={x["micro_skill_id"] for x in course["micro_skills"]}; procedures={x["procedure_id"] for x in course["procedures"]}; families={x["family_id"]:x for x in course["generation_families"]}
        for recipe in recipes:
            binding=recipe.binding; family=families[binding.family_id]
            assert binding.topic_id in topics and binding.micro_skill_id in skills and binding.procedure_id in procedures
            assert family["micro_skill_id"]==binding.micro_skill_id and family["procedure_id"]==binding.procedure_id


@pytest.mark.parametrize("course_id",sorted(EXPECTED))
def test_25_variants_per_course_are_domain_specific_independently_derived_and_engine_valid(course_id):
    records=generate_course_pilot(course_id)
    assert len(records)==25
    assert len({x["binding"].family_id for x in records})==5 and len({x["binding"].micro_skill_id for x in records})==5
    assert len({x["binding"].procedure_id for x in records})==5 and len({x["binding"].engine_type for x in records})==2
    assert len({x["context"].difficulty for x in records})==3
    assert len({x["prompt"] for x in records})==25
    for record in records:
        recipe=next(x for x in get_course_recipes(course_id) if x.recipe_id==record["recipe_id"])
        assert any(term in record["prompt"] for term in recipe.domain_terms)
        assert record["generator_answer"]==record["derivation"].normalized_answer
        assert record["derivation"].consumed_generator_answer is False
        assert record["engine_validation"]["normalize"]["status"]==record["engine_validation"]["derive"]["status"]==record["engine_validation"]["grade"]["status"]=="PASS"


def test_generator_and_deriver_are_separate_paths_with_independent_methods():
    recipe=get_course_recipes("CALCULUS_III")[2]; context=GenerationContextV1({"a":7,"b":4},0,"ADVANCED")
    assert recipe.generate_answer.__func__ is not recipe.derive_independently.__func__
    assert recipe.generate_answer(context)==28
    packet=recipe.derive_independently(context)
    assert packet.normalized_answer==28 and packet.method=="repeated-addition cross-check" and not packet.consumed_generator_answer


def test_targeted_prompts_exercise_actual_course_semantics():
    prompts={course:" ".join(x["prompt"] for x in generate_course_pilot(course)) for course in ("CALCULUS_III","NUMERICAL_METHODS","ENGINEERING_ANALYSIS","PRE_ALGEBRA")}
    assert all(term in prompts["CALCULUS_III"] for term in ("space vector","double integral","surface flux","three-dimensional"))
    assert all(term in prompts["NUMERICAL_METHODS"] for term in ("iterative correction","quadrature","finite-difference","solver"))
    assert all(term in prompts["ENGINEERING_ANALYSIS"] for term in ("superposition","balance residual","transfer model","field"))
    assert all(term in prompts["PRE_ALGEBRA"] for term in ("inventory","temperature","tile array","unit rate"))


@pytest.mark.parametrize("course_id",sorted(EXPECTED))
def test_incompatible_operation_engine_pair_fails_closed(course_id):
    scalar=get_course_recipes(course_id)[0]; vector=get_course_recipes(course_id)[4]
    with pytest.raises(ValueError,match="incompatible"):
        replace(scalar,binding=replace(scalar.binding,engine_type="numeric_vector")).validate()
    with pytest.raises(ValueError,match="incompatible"):
        replace(vector,binding=replace(vector.binding,engine_type="numeric_scalar")).validate()


def test_bad_parameters_unknown_course_and_undeclared_operation_fail_closed():
    recipe=get_course_recipes("APPLIED_MATHEMATICS")[3]
    with pytest.raises(ValueError,match="exactly match"): recipe.generate_answer(GenerationContextV1({"a":3},0,"FOUNDATIONAL"))
    with pytest.raises(ValueError,match="integer"): recipe.generate_answer(GenerationContextV1({"a":3,"b":0},0,"FOUNDATIONAL"))
    with pytest.raises(ValueError,match="no math/engineering recipe"): get_course_recipes("BIOLOGY")
    with pytest.raises(ValueError,match="incompatible"): replace(recipe,operation="component_pair").validate()
