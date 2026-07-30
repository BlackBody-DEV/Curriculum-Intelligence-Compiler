from tools.course_compiler_demo.generation_recipes.domains.science_cs import COURSE_IDS, RECIPES, recipes_for_course, self_audit
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
