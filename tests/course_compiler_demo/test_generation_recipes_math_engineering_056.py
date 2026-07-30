from dataclasses import replace

import pytest

from tools.course_compiler_demo.generation_recipes.domains.math_engineering import (
    COURSE_RECIPE_REGISTRY,GenerationContextV1,adapt_recipe,audit_recipe_catalog,
    build_math_engineering_runtime,generate_course_pilot,get_course_recipes,runtime_family,validate_catalog_semantics,
)
from tools.course_compiler_demo.generation_recipes.models import GenerationContextV1 as RuntimeGenerationContextV1
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
            validate_catalog_semantics(recipe,course)


def test_semantic_identity_rebinding_fails_even_when_target_ids_exist():
    course=all_courses()["CALCULUS_III"]; recipe=get_course_recipes("CALCULUS_III")[0]
    shifted=replace(recipe,binding=replace(recipe.binding,topic_id="CALCULUS_III_TOPIC_002",micro_skill_id="CALCULUS_III_SKILL_002",procedure_id="CALCULUS_III_PROC_002",family_id="CALCULUS_III_FAMILY_002"))
    with pytest.raises(ValueError,match="semantic identity"): validate_catalog_semantics(shifted,course)


def test_prior_shifted_topics_now_assess_substantive_topic_operations():
    probes={
        ("PRE_ALGEBRA",3):("ratio table","proportional total"),
        ("GEOMETRY",3):("similar figure","scale factor"),
        ("CALCULUS_III",3):("constant density","rectangular parameter area"),
        ("LINEAR_ALGEBRA",1):("subtract","corresponding matrix entries"),
        ("LINEAR_ALGEBRA",3):("apply scalar","linear transformation factor"),
        ("NUMERICAL_METHODS",1):("solve the bounded linear equation","exact root"),
        ("APPLIED_MATHEMATICS",1):("recurrence","next discrete state"),
    }
    for (course_id,index),terms in probes.items():
        recipe=get_course_recipes(course_id)[index]
        prompt=recipe.prompt_template.lower()
        assert all(term in prompt for term in terms)
        assert "use the local linear model" not in prompt


def test_runtime_family_requires_canonical_payload_and_rejects_fabrication():
    recipe=adapt_recipe(get_course_recipes("CALCULUS_III")[3])
    with pytest.raises(TypeError): runtime_family(recipe)
    with pytest.raises(ValueError,match="exactly match"):
        runtime_family(recipe,{"family_id":recipe.binding.family_id,"micro_skill_id":"SHIFTED","procedure_id":recipe.binding.procedure_id,"answer_engine":recipe.binding.engine_type})


def test_every_multiple_choice_product_uses_parameterized_independent_oracle():
    recipes=[recipe for values in COURSE_RECIPE_REGISTRY.values() for recipe in values if recipe.operation=="multiple_choice_product"]
    assert len(recipes)==8
    for recipe in recipes:
        first=GenerationContextV1({"variant":3,"coefficient_scale":4},0,"FOUNDATIONAL")
        mutated=GenerationContextV1({"variant":5,"coefficient_scale":4},1,"DEVELOPING")
        assert recipe.generate_answer(first)=="product:12"
        assert recipe.derive_independently(first).normalized_answer=="product:12"
        assert recipe.generate_answer(mutated)=="product:20"
        assert recipe.derive_independently(mutated).normalized_answer=="product:20"
        assert recipe.generate_answer(first)!=recipe.generate_answer(mutated)
        options=recipe.build_contract(first).grading_contract["options"]
        assert options==[{"option_id":"product:12","text":"12","correct":True},{"option_id":"sum:7","text":"7","correct":False}]


def test_root_recurrence_circle_and_trigonometry_relations_are_explicit_and_mutation_sensitive():
    root=get_course_recipes("NUMERICAL_METHODS")[1]; recurrence=get_course_recipes("APPLIED_MATHEMATICS")[1]
    engineering=lambda order,variant: GenerationContextV1({"scale":2,"order":order,"variant":variant},0,"FOUNDATIONAL")
    assert root.binding.family_id.endswith("_002") and root.generate_answer(engineering(2,6))=="-3"
    assert root.generate_answer(engineering(3,6))=="-2" and "=0" in root.prompt_template
    assert recurrence.binding.family_id.endswith("_002") and recurrence.generate_answer(engineering(2,6))=="8"
    assert recurrence.generate_answer(engineering(2,7))=="9" and "u[n+1]" in recurrence.prompt_template
    geometry=get_course_recipes("GEOMETRY")[4]; triangle=get_course_recipes("TRIGONOMETRY")[1]; unit_circle=get_course_recipes("TRIGONOMETRY")[2]
    assert "circumference ratio" in geometry.prompt_template
    assert "tan(theta)=opposite/adjacent" in triangle.prompt_template
    assert "unit-circle coordinates" in unit_circle.prompt_template


@pytest.mark.parametrize("course_id",sorted(EXPECTED))
def test_25_variants_per_course_are_domain_specific_independently_derived_and_engine_valid(course_id):
    records=generate_course_pilot(course_id)
    assert len(records)==25
    assert len({x["binding"].family_id for x in records})==5 and len({x["binding"].micro_skill_id for x in records})==5
    assert len({x["binding"].procedure_id for x in records})==5 and len({x["binding"].engine_type for x in records})>=2
    assert len({x["context"].difficulty for x in records})==3
    assert len({x["prompt"] for x in records})==25
    for record in records:
        recipe=next(x for x in get_course_recipes(course_id) if x.recipe_id==record["recipe_id"])
        assert any(term in record["prompt"] for term in recipe.domain_terms)
        assert record["generator_answer"]==record["derivation"].normalized_answer
        assert record["derivation"].consumed_generator_answer is False
        assert record["engine_validation"]["normalize"]["status"]==record["engine_validation"]["derive"]["status"]==record["engine_validation"]["grade"]["status"]=="PASS"


def test_generator_and_deriver_are_separate_paths_with_independent_methods():
    recipe=get_course_recipes("ENGINEERING_ANALYSIS")[2]; context=GenerationContextV1({"scale":7,"order":4,"variant":1},0,"ADVANCED")
    assert recipe.generate_answer.__func__ is not recipe.derive_independently.__func__
    assert recipe.generate_answer(context)==28
    packet=recipe.derive_independently(context)
    assert packet.normalized_answer==28 and packet.method=="repeated-addition cross-check" and not packet.consumed_generator_answer


@pytest.mark.parametrize("course_id",sorted(EXPECTED))
def test_shared_runtime_executes_25_distinct_validated_questions_per_course(course_id):
    runtime=build_math_engineering_runtime(); results=[]; course=all_courses()[course_id]
    topics={x["topic_id"]:x for x in course["topics"]}; skills={x["micro_skill_id"]:x for x in course["micro_skills"]}; families={x["family_id"]:x for x in course["generation_families"]}; procedures={x["procedure_id"]:x for x in course["procedures"]}
    for source in get_course_recipes(course_id):
        recipe=adapt_recipe(source)
        topic=topics[recipe.binding.topic_id]; skill=skills[recipe.binding.micro_skill_id]; family=families[recipe.binding.family_id]; procedure=procedures[recipe.binding.procedure_id]
        assert source.domain_terms[0].lower() in topic["title"].lower()
        assert family["answer_engine"]==recipe.binding.engine_type
        for variant in range(5):
            context=RuntimeGenerationContextV1(
                recipe.binding,
                topic["title"],skill["title"],tuple(procedure["steps"]),
                f"wave-056:{course_id}",variant,
            )
            result=runtime.generate(recipe.recipe_id,context,runtime_family(recipe,family))
            assert result.normalization_result.status==result.derivation_result.status==result.grading_result.status=="PASS"
            results.append(result)
    report=runtime.require_coverage(results)
    assert report["question_count"]==25 and report["exact_duplicates"]==0


def test_targeted_prompts_exercise_actual_course_semantics():
    prompts={course:" ".join(x["prompt"] for x in generate_course_pilot(course)) for course in ("CALCULUS_III","NUMERICAL_METHODS","ENGINEERING_ANALYSIS","PRE_ALGEBRA")}
    assert all(term in prompts["CALCULUS_III"] for term in ("vectors and geometry of space","vector-valued functions","line integrals","multiple integrals"))
    assert all(term in prompts["NUMERICAL_METHODS"] for term in ("error and conditioning","linear systems","numerical integration","boundary-value problems"))
    assert all(term in prompts["ENGINEERING_ANALYSIS"] for term in ("engineering models","linear algebraic models","partial differential equations","approximation methods"))
    assert all(term in prompts["PRE_ALGEBRA"] for term in ("whole-number reasoning","integer operations","fractions and decimals","ratios and rates"))


@pytest.mark.parametrize("course_id",sorted(EXPECTED))
def test_incompatible_operation_engine_pair_fails_closed(course_id):
    scalar=get_course_recipes(course_id)[0]; specialized=next(x for x in get_course_recipes(course_id) if x.binding.engine_type!="numeric_scalar")
    with pytest.raises(ValueError,match="incompatible"):
        replace(scalar,binding=replace(scalar.binding,engine_type=specialized.binding.engine_type)).validate()
    with pytest.raises(ValueError,match="incompatible"):
        replace(specialized,binding=replace(specialized.binding,engine_type="numeric_scalar")).validate()


def test_bad_parameters_unknown_course_and_undeclared_operation_fail_closed():
    recipe=get_course_recipes("APPLIED_MATHEMATICS")[3]
    with pytest.raises(ValueError,match="exactly match"): recipe.generate_answer(GenerationContextV1({"scale":3},0,"FOUNDATIONAL"))
    with pytest.raises(ValueError,match="integer"): recipe.generate_answer(GenerationContextV1({"scale":3,"order":0,"variant":1},0,"FOUNDATIONAL"))
    with pytest.raises(ValueError,match="no math/engineering recipe"): get_course_recipes("BIOLOGY")
    with pytest.raises(ValueError,match="incompatible"): replace(recipe,operation="component_pair").validate()
