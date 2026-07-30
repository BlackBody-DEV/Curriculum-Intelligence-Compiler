from tools.course_compiler_demo.generation_recipes import GenerationContextV1, GenerationRecipeRuntime, RecipeBindingV1
from tools.course_compiler_demo.generation_recipes.domains.science_cs import COURSE_IDS, RECIPES, build_runtime, recipes_for_course, self_audit
from tools.course_compiler_demo.universal_integration.capability_catalog_wave_044 import discover_course_catalog


def test_self_audit_proves_all_lane_requirements():
    audit = self_audit()
    assert audit["status"] == "PASS"
    assert audit["course_count"] == 15
    assert audit["recipe_count"] == 75
    assert audit["question_count"] == 375
    assert audit["independent_derivations"] == 375
    assert audit["exact_prompt_duplicates"] == 0


def test_every_binding_is_exactly_present_in_source_course_pack():
    courses = discover_course_catalog()["new"]
    for recipe in RECIPES:
        course = courses[recipe.binding.course_id]
        topics = {x["topic_id"] for x in course["topics"]}
        skills = {x["micro_skill_id"]: x for x in course["micro_skills"]}
        procedures = {x["procedure_id"] for x in course["procedures"]}
        families = {x["family_id"]: x for x in course["generation_families"]}
        assert recipe.binding.topic_id in topics
        assert skills[recipe.binding.micro_skill_id]["topic_id"] == recipe.binding.topic_id
        assert recipe.binding.procedure_id in procedures
        family = families[recipe.binding.family_id]
        assert family["micro_skill_id"] == recipe.binding.micro_skill_id
        assert family["procedure_id"] == recipe.binding.procedure_id
        assert family["answer_engine"] == recipe.binding.engine_type


def test_generation_and_derivation_are_repeatable_but_separate():
    for recipe in RECIPES:
        first = recipe.compile(3)
        second = recipe.compile(3)
        assert first == second
        assert first.generated_answer == first.independently_derived_answer
        assert first.derivation["primitive_inputs"] == {"a": 15, "b": 5}
        assert "generated_answer" not in first.derivation


def test_prompts_contain_domain_semantics_not_course_label_wrapping():
    banned = ("in this course", "course label", "generic question", "placeholder", "unsupported engine")
    for course_id in COURSE_IDS:
        recipes = recipes_for_course(course_id)
        assert len({r.context for r in recipes}) == 5
        assert len({r.principle for r in recipes}) == 5
        for recipe in recipes:
            prompt = recipe.compile(0).prompt.lower()
            assert recipe.principle.lower() in prompt
            assert all(term.lower() in prompt for term in recipe.domain_terms)
            assert not any(token in prompt for token in banned)


def test_unknown_course_and_variant_fail_closed():
    try:
        recipes_for_course("GENERAL_SCIENCE")
    except KeyError as exc:
        assert "no exact recipe binding" in str(exc)
    else:
        raise AssertionError("unknown courses must fail closed")
    try:
        RECIPES[0].compile(5)
    except ValueError as exc:
        assert "variant must be 0..4" in str(exc)
    else:
        raise AssertionError("out-of-domain variants must fail closed")


def test_all_domain_recipes_register_with_shared_runtime_exactly():
    runtime = build_runtime()
    assert isinstance(runtime, GenerationRecipeRuntime)
    for domain in RECIPES:
        binding = RecipeBindingV1(**domain.binding.__dict__)
        adapted = runtime.recipes.lookup_binding(binding)
        assert adapted.recipe_id == domain.recipe_id
        assert adapted.generator_method_id != adapted.derivation_method_id
        assert len(adapted.parameter_domains) == 2


def test_life_science_recipe_executes_through_shared_runtime():
    course = discover_course_catalog()["new"]["BIOLOGY"]
    binding = RecipeBindingV1("BIOLOGY", "BIOLOGY_TOPIC_001", "BIOLOGY_SKILL_001", "BIOLOGY_PROC_001", "BIOLOGY_FAMILY_001", "scientific_structured_response")
    context = GenerationContextV1(binding, course["topics"][0]["title"], course["micro_skills"][0]["title"], tuple(course["procedures"][0]["steps"]), "independent-proof", 0)
    result = build_runtime().generate("W056:BIOLOGY:001", context, course["generation_families"][0])
    assert result.normalization_result.status == "PASS"
    assert result.derivation_result.status == "PASS"
    assert result.grading_result.status == "PASS"
    assert result.normalized_answer == result.derived_answer
