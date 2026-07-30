"""Thin adapter from Wave 056 domain declarations to the shared 056A runtime."""
from __future__ import annotations

from typing import Any, Mapping

from tools.course_compiler_demo.generation_recipes.models import (
    DerivationPacketV1 as RuntimeDerivationPacketV1,
    GenerationContextV1 as RuntimeGenerationContextV1,
    ParameterDomainV1 as RuntimeParameterDomainV1,
    RecipeBindingV1 as RuntimeRecipeBindingV1,
)
from tools.course_compiler_demo.generation_recipes.recipe import BoundedGenerationRecipe
from tools.course_compiler_demo.generation_recipes.runtime import GenerationRecipeRegistry, GenerationRecipeRuntime

from .catalog import COURSE_RECIPE_REGISTRY
from .models import DomainRecipeV1, GenerationContextV1


def adapt_recipe(source: DomainRecipeV1) -> BoundedGenerationRecipe:
    """Expose one declarative domain recipe through the shared strict protocol."""
    binding = RuntimeRecipeBindingV1(**source.binding.__dict__)
    domains = tuple(RuntimeParameterDomainV1(item.name, "integer", item.minimum, item.maximum) for item in source.parameter_domains)

    def local(parameters: Mapping[str, Any]) -> GenerationContextV1:
        return GenerationContextV1(dict(parameters), 0, "FOUNDATIONAL")

    def generate(parameters: Mapping[str, Any]) -> Any:
        return source.generate_answer(local(parameters))

    def derive(parameters: Mapping[str, Any]) -> RuntimeDerivationPacketV1:
        packet = source.derive_independently(local(parameters))
        return RuntimeDerivationPacketV1(
            f"independent:{source.operation}",
            {"independently_derived_answer": packet.normalized_answer},
            packet.normalized_answer,
        )

    def prompt(parameters: Mapping[str, Any], context: RuntimeGenerationContextV1) -> str:
        domain_prompt = source.build_prompt(local(parameters))
        return f"Topic {context.topic_title}; micro-skill {context.skill_title}. {domain_prompt} Procedure: {' '.join(context.procedure_steps)}"

    return BoundedGenerationRecipe(
        source.recipe_id, source.version, binding, domains, source.domain_terms,
        source.operation_terms, tuple(item.name for item in source.parameter_domains),
        f"candidate:{source.operation}", f"independent:{source.operation}",
        generate, derive, prompt, lambda parameters: source.build_contract(),
    )


def build_math_engineering_runtime() -> GenerationRecipeRuntime:
    registry = GenerationRecipeRegistry()
    for recipes in COURSE_RECIPE_REGISTRY.values():
        for source in recipes:
            registry.register(adapt_recipe(source))
    return GenerationRecipeRuntime(registry)


def runtime_family(recipe: BoundedGenerationRecipe) -> dict[str, Any]:
    """Construct the exact family declaration consumed by the shared runtime."""
    contract = recipe.build_contract({})
    return {
        "family_id": recipe.binding.family_id,
        "micro_skill_id": recipe.binding.micro_skill_id,
        "procedure_id": recipe.binding.procedure_id,
        "answer_engine": recipe.binding.engine_type,
        "answer_contract": {"answer_contract_id": contract.answer_contract_id, "engine_type": contract.engine_type},
        "parameter_domains": {
            domain.name: {"type": domain.kind, "minimum": domain.minimum, "maximum": domain.maximum}
            for domain in recipe.parameter_domains
        },
    }
