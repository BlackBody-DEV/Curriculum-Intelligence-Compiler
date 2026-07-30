"""Thin adapters from domain-owned recipes to the shared 056A runtime API."""
from __future__ import annotations

from typing import Any, Mapping

from tools.course_compiler_demo.generation_recipes import (
    BoundedGenerationRecipe, DerivationPacketV1, GenerationContextV1,
    GenerationRecipeRegistry, GenerationRecipeRuntime, ParameterDomainV1,
    RecipeBindingV1,
)
from tools.course_compiler_demo.universal_core import AnswerContractV1

from .catalog import RECIPES
from .model import DomainRecipe


def _domains(recipe: DomainRecipe) -> tuple[ParameterDomainV1, ...]:
    course = recipe.binding.course_id
    if course in {"DATA_STRUCTURES", "ALGORITHMS", "COMPUTATIONAL_THINKING"}:
        return (ParameterDomainV1("input_size", "integer", 1, 100), ParameterDomainV1("variant", "integer", 1, 20))
    if course in {"BIOLOGY", "ORGANIC_CHEMISTRY", "BIOCHEMISTRY"}:
        return (ParameterDomainV1("variant", "integer", 1, 1000), ParameterDomainV1("evidence_count", "integer", 1, 6))
    return (ParameterDomainV1("magnitude", "number", 1.0, 1000.0), ParameterDomainV1("direction_degrees", "number", -180.0, 180.0))


def _primitives(parameters: Mapping[str, Any]) -> dict[str, int]:
    values = list(parameters.values())
    return {"a": max(1, int(abs(float(values[0])))), "b": max(1, int(abs(float(values[1]))))}


def to_runtime_recipe(recipe: DomainRecipe) -> BoundedGenerationRecipe:
    binding = RecipeBindingV1(**recipe.binding.__dict__)

    def generate(parameters: Mapping[str, Any]) -> Any:
        return recipe.generate_answer(_primitives(parameters))

    def derive(parameters: Mapping[str, Any]) -> DerivationPacketV1:
        answer, packet = recipe.derive_independently(_primitives(parameters))
        key = "structured_response" if binding.engine_type in {"scientific_structured_response", "rubric_scored_explanation"} else "independently_derived_answer"
        return DerivationPacketV1(f"domain-primitive-recompute:{recipe.recipe_id}", {key: answer, **dict(packet)}, answer)

    def prompt(parameters: Mapping[str, Any], context: GenerationContextV1) -> str:
        base = recipe.build_prompt(_primitives(parameters))
        return f"Topic: {context.topic_title}. Micro-skill: {context.skill_title}. {base}"

    def contract(parameters: Mapping[str, Any]) -> AnswerContractV1:
        engine = binding.engine_type
        grading: dict[str, Any] = {}
        if engine in {"numeric_scalar", "numeric_vector"}: grading = {"absolute_tolerance": 1e-9, "relative_tolerance": 1e-9}
        elif engine == "multiple_choice":
            correct = generate(parameters)["option_id"]
            grading = {"options": [{"option_id": x, "text": f"computed remainder class {i}", "correct": x == correct} for i, x in enumerate("ABCD")]}
        elif engine in {"scientific_structured_response", "rubric_scored_explanation"}:
            grading = {"required_concepts": [recipe.principle], "minimum_evidence_threshold": 1, "passing_score": 1.0}
        elif engine in {"code_execution", "code_execution_python"}:
            independently_computed = recipe.derive_independently({"a": 6, "b": 2})[1]["result"]
            grading = {"cases": [{"entrypoint": "solve", "args": [6, 2], "expected": independently_computed}]}
        number = binding.family_id.rsplit("_", 1)[-1]
        contract_id = f"{binding.course_id}_ANSWER_{number}" if binding.course_id in {"BIOLOGY", "ORGANIC_CHEMISTRY", "BIOCHEMISTRY"} else f"W056_ANSWER_{binding.course_id}_{number}"
        return AnswerContractV1(contract_id, "code_execution_python" if engine == "code_execution" else engine, grading, {})

    return BoundedGenerationRecipe(
        recipe.recipe_id, recipe.version, binding, _domains(recipe), recipe.domain_terms,
        (recipe.operation, recipe.principle), tuple(x.name for x in _domains(recipe)),
        f"domain-generator:{recipe.recipe_id}", f"domain-primitive-recompute:{recipe.recipe_id}",
        generate, derive, prompt, contract,
    )


def build_runtime_registry() -> GenerationRecipeRegistry:
    registry = GenerationRecipeRegistry()
    for recipe in RECIPES: registry.register(to_runtime_recipe(recipe))
    return registry


def build_runtime() -> GenerationRecipeRuntime:
    return GenerationRecipeRuntime(build_runtime_registry())
