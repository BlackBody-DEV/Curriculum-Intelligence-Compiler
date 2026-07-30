"""Thin adapters from domain-owned recipes to the shared 056A runtime API."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from tools.course_compiler_demo.generation_recipes import (
    BoundedGenerationRecipe, DerivationPacketV1, GenerationContextV1,
    GenerationRecipeRegistry, GenerationRecipeRuntime, ParameterDomainV1,
    RecipeBindingV1,
)
from tools.course_compiler_demo.universal_core import AnswerContractV1
from tools.course_compiler_demo.universal_integration.capability_catalog_wave_044 import discover_course_catalog

from .catalog import RECIPES
from .model import DomainRecipe


def _domains(family: Mapping[str, Any]) -> tuple[ParameterDomainV1, ...]:
    """Adapt the first two real declared domains without inventing a schema."""
    declared = family.get("parameter_domains")
    if not isinstance(declared, Mapping) or len(declared) < 2:
        raise ValueError("real family must declare at least two parameter domains")
    domains=[]
    for name, specification in list(declared.items())[:2]:
        kind=specification.get("type", specification.get("kind"))
        if kind == "choice":
            domains.append(ParameterDomainV1(name, kind, choices=tuple(specification.get("choices", specification.get("enum", ())))))
        else:
            domains.append(ParameterDomainV1(name, kind, specification.get("minimum"), specification.get("maximum")))
    return tuple(domains)


def _primitives(parameters: Mapping[str, Any]) -> dict[str, int]:
    values = list(parameters.values())
    return {"a": max(1, int(abs(float(values[0])))), "b": max(1, int(abs(float(values[1]))))}


def to_runtime_recipe(recipe: DomainRecipe, family: Mapping[str, Any]) -> BoundedGenerationRecipe:
    binding = RecipeBindingV1(**recipe.binding.__dict__)

    def generate(parameters: Mapping[str, Any]) -> Any:
        return recipe.generate_answer(_primitives(parameters))

    def derive(parameters: Mapping[str, Any]) -> DerivationPacketV1:
        answer, packet = recipe.derive_independently(_primitives(parameters))
        key = "structured_response" if binding.engine_type in {"scientific_structured_response", "rubric_scored_explanation"} else "independently_derived_answer"
        return DerivationPacketV1(f"domain-primitive-recompute:{recipe.recipe_id}", {key: answer, **dict(packet)}, answer)

    def prompt(parameters: Mapping[str, Any], context: GenerationContextV1) -> str:
        base = recipe.build_prompt(_primitives(parameters))
        declared = ", ".join(f"{name}={value}" for name, value in parameters.items())
        return f"Topic: {context.topic_title}. Micro-skill: {context.skill_title}. Declared runtime parameters: {declared}. {base}"

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

    parameter_domains = _domains(family)
    return BoundedGenerationRecipe(
        recipe.recipe_id, recipe.version, binding, parameter_domains, recipe.domain_terms,
        (recipe.operation, recipe.principle), tuple(x.name for x in parameter_domains),
        f"domain-generator:{recipe.recipe_id}", f"domain-primitive-recompute:{recipe.recipe_id}",
        generate, derive, prompt, contract,
    )


def build_runtime_registry() -> GenerationRecipeRegistry:
    courses = discover_course_catalog()["new"]
    registry = GenerationRecipeRegistry()
    for recipe in RECIPES:
        families={x["family_id"]:x for x in courses[recipe.binding.course_id]["generation_families"]}
        registry.register(to_runtime_recipe(recipe, families[recipe.binding.family_id]))
    return registry


def build_runtime() -> GenerationRecipeRuntime:
    return GenerationRecipeRuntime(build_runtime_registry())


def compatible_family(recipe: DomainRecipe, family: Mapping[str, Any]) -> dict[str, Any]:
    """Return an explicit, non-mutating runtime view of a legacy family.

    Older course packs used ``shape`` and the ``code_execution`` alias.  The
    recipe runtime intentionally requires the canonical engine identity nested
    in the contract, so the migration is visible here rather than a fallback.
    """
    prepared = deepcopy(dict(family))
    prepared["answer_engine"] = recipe.binding.engine_type
    contract = dict(prepared.get("answer_contract", {}))
    contract["engine_type"] = recipe.binding.engine_type
    prepared["answer_contract"] = contract
    return prepared
