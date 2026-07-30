import json
from dataclasses import replace

import pytest

from tools.course_compiler_demo.generation_recipes import (
    BoundedGenerationRecipe, DerivationPacketV1, GenerationContextV1,
    GenerationRecipeError, GenerationRecipeRegistry, GenerationRecipeRuntime,
    ParameterDomainV1, RecipeBindingV1,
)
from tools.course_compiler_demo.universal_core import AnswerContractV1


BINDING = RecipeBindingV1("COURSE", "TOPIC", "SKILL", "PROCEDURE", "FAMILY", "numeric_scalar")


def answer(parameters):
    return parameters["initial"] + parameters["increase"]


def derive(parameters):
    independently_computed = sum((parameters["initial"], parameters["increase"]))
    return DerivationPacketV1("sum-by-fold", {"independently_derived_answer": independently_computed}, independently_computed)


def prompt(parameters, context):
    return (f"For topic {context.topic_title} and skill {context.skill_title}, use the linear rate model to add "
            f"initial distance {parameters['initial']} and distance increase {parameters['increase']}; report total distance. "
            f"Follow the procedure constraint: {context.procedure_steps[0]}")


def contract(parameters):
    return AnswerContractV1("contract:distance-addition", "numeric_scalar", {"absolute_tolerance": 0, "relative_tolerance": 0})


def recipe(**changes):
    base = BoundedGenerationRecipe(
        "recipe:distance-addition", "1.0", BINDING,
        (ParameterDomainV1("initial", "integer", 1, 20), ParameterDomainV1("increase", "integer", 2, 12)),
        ("linear rate", "distance"), ("add", "total distance"), ("initial", "increase"),
        "candidate-addition", "sum-by-fold", answer, derive, prompt, contract,
    )
    return replace(base, **changes)


def context(**changes):
    base = GenerationContextV1(BINDING, "Linear Motion", "Combine Directed Distances", ("Preserve the declared sign convention.",), "seed-001", 0)
    return replace(base, **changes)


def family(**changes):
    base = {"family_id": "FAMILY", "micro_skill_id": "SKILL", "procedure_id": "PROCEDURE", "answer_engine": "numeric_scalar", "answer_contract": {"answer_contract_id": "contract:distance-addition", "engine_type": "numeric_scalar"}, "parameter_domains": {"initial": {"type": "integer", "minimum": 0, "maximum": 50}, "increase": {"type": "integer", "minimum": 0, "maximum": 50}}}
    base.update(changes); return base


def runtime(item=None):
    registry = GenerationRecipeRegistry(); registry.register(item or recipe())
    return GenerationRecipeRuntime(registry)


def test_generation_is_deterministic_validated_and_records_actual_engine():
    service = runtime()
    first = service.generate("recipe:distance-addition", context(), family())
    second = service.generate("recipe:distance-addition", context(), family())
    assert first.to_dict() == second.to_dict()
    assert first.binding.engine_type == "numeric_scalar"
    assert first.normalization_result.status == first.derivation_result.status == first.grading_result.status == "PASS"
    assert first.normalized_answer == first.derived_answer
    assert len(first.content_sha256) == 64
    assert json.loads(json.dumps(first.to_dict(), sort_keys=True)) == first.to_dict()


def test_variant_parameter_generation_is_bounded_and_repeatable():
    service = runtime(); seen = set()
    for index in range(25):
        result = service.generate("recipe:distance-addition", context(variant_index=index), family())
        assert 1 <= result.parameters["initial"] <= 20 and 2 <= result.parameters["increase"] <= 12
        seen.add(tuple(result.parameters.items()))
    assert len(seen) > 1


def test_coverage_reports_counts_and_content_duplicates():
    service = runtime()
    results = [service.generate("recipe:distance-addition", context(variant_index=index), family()) for index in range(5)]
    report = service.coverage(results)
    assert report == {"answer_engine_count": 1, "exact_duplicates": 0, "family_count": 1, "micro_skill_count": 1, "procedure_count": 1, "question_count": 5, "status": "PASS"}
    duplicate = service.coverage([results[0], results[0]])
    assert duplicate["status"] == "FAIL" and duplicate["exact_duplicates"] == 1
    with pytest.raises(GenerationRecipeError) as shortfall:
        service.require_coverage(results)
    assert shortfall.value.code == "COVERAGE_GATE_FAILED" and "family_count=1<5" in shortfall.value.reasons
    assert service.require_coverage(results, minimum_questions=5, minimum_families=1, minimum_micro_skills=1, minimum_procedures=1, minimum_answer_engines=1)["status"] == "PASS"


@pytest.mark.parametrize(("changes", "code"), [
    ({"binding": replace(BINDING, topic_id="OTHER")}, "BINDING_MISMATCH"),
    ({"binding": replace(BINDING, micro_skill_id="OTHER")}, "BINDING_MISMATCH"),
    ({"binding": replace(BINDING, procedure_id="OTHER")}, "BINDING_MISMATCH"),
    ({"binding": replace(BINDING, family_id="OTHER")}, "BINDING_MISMATCH"),
    ({"binding": replace(BINDING, engine_type="numeric_pair")}, "BINDING_MISMATCH"),
])
def test_context_requires_exact_complete_binding(changes, code):
    with pytest.raises(GenerationRecipeError) as error:
        runtime().generate("recipe:distance-addition", context(**changes), family())
    assert error.value.code == code


@pytest.mark.parametrize(("changes", "reason"), [
    ({"family_id": "OTHER"}, "family_id"), ({"micro_skill_id": "OTHER"}, "micro_skill_id"),
    ({"procedure_id": "OTHER"}, "procedure_id"), ({"answer_engine": "multiple_choice"}, "answer_engine"),
])
def test_family_identity_engine_and_relationship_mismatches_fail_closed(changes, reason):
    with pytest.raises(GenerationRecipeError) as error:
        runtime().generate("recipe:distance-addition", context(), family(**changes))
    assert error.value.code == "FAMILY_COMPATIBILITY_MISMATCH" and reason in error.value.reasons


@pytest.mark.parametrize("domains", [
    {},
    {"initial": {"type": "integer", "minimum": 5, "maximum": 10}, "increase": {"type": "integer", "minimum": 0, "maximum": 50}},
    {"initial": {"type": "number", "minimum": 0, "maximum": 50}, "increase": {"type": "integer", "minimum": 0, "maximum": 50}},
])
def test_recipe_parameter_domains_must_fit_declared_family_domains(domains):
    with pytest.raises(GenerationRecipeError, match="PARAMETER_DOMAIN_MISMATCH"):
        runtime().generate("recipe:distance-addition", context(), family(parameter_domains=domains))


def test_unknown_recipe_and_binding_never_fall_back():
    registry = GenerationRecipeRegistry(); registry.register(recipe())
    with pytest.raises(GenerationRecipeError) as unknown:
        registry.lookup("missing")
    assert unknown.value.code == "UNSUPPORTED_RECIPE"
    with pytest.raises(GenerationRecipeError) as binding_error:
        registry.lookup_binding(replace(BINDING, micro_skill_id="MISSING"))
    assert binding_error.value.code == "UNSUPPORTED_BINDING"


def test_duplicate_recipe_id_and_binding_are_rejected():
    registry = GenerationRecipeRegistry(); registry.register(recipe())
    with pytest.raises(GenerationRecipeError, match="DUPLICATE_RECIPE_ID"):
        registry.register(recipe())
    with pytest.raises(GenerationRecipeError, match="DUPLICATE_RECIPE_BINDING"):
        registry.register(recipe(recipe_id="recipe:other"))


@pytest.mark.parametrize(("changes", "code"), [
    ({"derivation_method_id": "candidate-addition"}, "DERIVATION_NOT_INDEPENDENT"),
    ({"domain_terms": ("distance",)}, "INSUFFICIENT_SEMANTIC_CONTRACT"),
    ({"operation_terms": ()}, "INSUFFICIENT_SEMANTIC_CONTRACT"),
    ({"prompt_parameter_names": ("missing",)}, "INVALID_PROMPT_PARAMETERS"),
])
def test_invalid_recipe_protocol_and_independence_metadata_are_rejected(changes, code):
    registry = GenerationRecipeRegistry()
    with pytest.raises(GenerationRecipeError) as error:
        registry.register(recipe(**changes))
    assert error.value.code == code


def test_same_generator_and_deriver_callable_is_rejected_even_with_different_labels():
    shared = lambda parameters: answer(parameters)
    registry = GenerationRecipeRegistry()
    with pytest.raises(GenerationRecipeError) as error:
        registry.register(recipe(answer_generator=shared, independent_deriver=shared))
    assert error.value.code == "DERIVATION_NOT_INDEPENDENT"


@pytest.mark.parametrize(("bad_prompt", "code"), [
    ("generic question", "PROMPT_NOT_SUBSTANTIVE"),
    ("This is a generic question about linear rate and distance where we add 1 and 2 to obtain total distance for Linear Motion and Combine Directed Distances." * 2, "GENERIC_PROMPT"),
    ("For Linear Motion and Combine Directed Distances, add initial 1 and increase 2 to report total distance while following the sign convention." * 2, "SEMANTIC_GROUNDING_FAILED"),
    ("For a linear rate distance model, add initial 1 and increase 2 to report total distance while following the sign convention." * 2, "CURRICULUM_GROUNDING_FAILED"),
])
def test_anti_generic_and_semantic_grounding_gates(bad_prompt, code):
    item = recipe(prompt_builder=lambda parameters, context: bad_prompt)
    with pytest.raises(GenerationRecipeError) as error:
        runtime(item).generate(item.recipe_id, context(), family())
    assert error.value.code == code


def test_prompt_must_expose_determinative_parameters():
    item = recipe(prompt_builder=lambda parameters, ctx: f"For topic {ctx.topic_title} and skill {ctx.skill_title}, use a linear rate distance model to add values and report total distance under the procedure. " * 2)
    with pytest.raises(GenerationRecipeError) as error:
        runtime(item).generate(item.recipe_id, context(), family())
    assert error.value.code == "PROMPT_PARAMETER_MISSING"


def test_generator_deriver_disagreement_is_rejected():
    item = recipe(answer_generator=lambda parameters: answer(parameters) + 1)
    with pytest.raises(GenerationRecipeError) as error:
        runtime(item).generate(item.recipe_id, context(), family())
    assert error.value.code in {"ANSWER_ENGINE_VALIDATION_FAILED", "DERIVATION_DISAGREEMENT"}


def test_wrong_answer_engine_contract_and_engine_failure_are_rejected():
    wrong = recipe(contract_builder=lambda parameters: AnswerContractV1("wrong", "numeric_pair", {}))
    with pytest.raises(GenerationRecipeError) as mismatch:
        runtime(wrong).generate(wrong.recipe_id, context(), family())
    assert mismatch.value.code == "ANSWER_CONTRACT_MISMATCH"
    invalid = recipe(answer_generator=lambda parameters: "not numeric")
    with pytest.raises(GenerationRecipeError) as failed:
        runtime(invalid).generate(invalid.recipe_id, context(), family())
    assert failed.value.code == "ANSWER_ENGINE_VALIDATION_FAILED"


def test_family_and_constructed_answer_contract_identities_must_match():
    with pytest.raises(GenerationRecipeError) as family_error:
        runtime().generate("recipe:distance-addition", context(), family(answer_contract={"engine_type": "numeric_pair"}))
    assert family_error.value.code == "FAMILY_COMPATIBILITY_MISMATCH"
    with pytest.raises(GenerationRecipeError) as identity_error:
        runtime().generate("recipe:distance-addition", context(), family(answer_contract={"answer_contract_id": "other", "engine_type": "numeric_scalar"}))
    assert identity_error.value.code == "ANSWER_CONTRACT_MISMATCH"


@pytest.mark.parametrize("domain", [
    lambda: ParameterDomainV1("x", "unknown", 0, 1), lambda: ParameterDomainV1("x", "integer", 1, 1),
    lambda: ParameterDomainV1("x", "number", float("-inf"), 1), lambda: ParameterDomainV1("x", "choice", choices=("only",)),
])
def test_invalid_parameter_contracts_fail_at_construction(domain):
    with pytest.raises(ValueError):
        domain()


def test_structured_errors_are_deterministic():
    try: runtime().generate("missing", context(), family())
    except GenerationRecipeError as error:
        assert error.to_dict() == {"code": "UNSUPPORTED_RECIPE", "reasons": ["recipe 'missing' is not registered"], "status": "REJECTED"}
