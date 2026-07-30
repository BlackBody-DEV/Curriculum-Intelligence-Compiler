"""Thin adapter from Wave 056 domain declarations to the shared 056A runtime."""
from __future__ import annotations

from typing import Any, Mapping
import re

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


def validate_catalog_semantics(source:DomainRecipeV1,course:Mapping[str,Any])->None:
    """Fail closed unless identity relationships and reviewed semantic tokens agree."""
    topics={x["topic_id"]:x for x in course.get("topics",())}; skills={x["micro_skill_id"]:x for x in course.get("micro_skills",())}; procedures={x["procedure_id"]:x for x in course.get("procedures",())}; families={x["family_id"]:x for x in course.get("generation_families",())}
    try: topic=topics[source.binding.topic_id]; skill=skills[source.binding.micro_skill_id]; procedure=procedures[source.binding.procedure_id]; family=families[source.binding.family_id]
    except KeyError as exc: raise ValueError("recipe identity is absent from canonical catalog") from exc
    normalized=lambda value:" ".join(re.findall(r"[a-z0-9]+",value.lower()))
    concept=normalized(source.domain_terms[0])
    if concept not in normalized(topic["title"]) or skill.get("topic_id")!=source.binding.topic_id or concept not in normalized(skill["title"]): raise ValueError("recipe semantic identity does not match exact topic and skill")
    if source.binding.micro_skill_id not in procedure.get("micro_skill_ids",()) or family.get("micro_skill_id")!=source.binding.micro_skill_id or family.get("procedure_id")!=source.binding.procedure_id or family.get("answer_engine")!=source.binding.engine_type: raise ValueError("recipe procedure/family relationship is incompatible")


def semantic_compatibility_manifest()->tuple[dict[str,Any],...]:
    """Provider-owned evidence includes the assessed operation, not labels alone."""
    rows=[]
    for recipes in COURSE_RECIPE_REGISTRY.values():
        for source in recipes:
            operation_label=source.operation_terms[0]
            operation_evidence=source.operation_terms[1]
            if operation_label.lower() not in source.build_prompt(GenerationContextV1(
                ({"variant":3,"coefficient_scale":2} if any(x.name=="coefficient_scale" for x in source.parameter_domains) else {"scale":3,"order":2,"variant":4}),0,"FOUNDATIONAL"
            )).lower():
                raise ValueError(f"operation evidence missing from prompt: {source.recipe_id}")
            rows.append({"recipe_id":source.recipe_id,"binding":dict(source.binding.__dict__),"matched_terms":[source.domain_terms[0],operation_label,operation_evidence],"operation":source.operation,"status":"PASS"})
    return tuple(rows)


def adapt_recipe(source: DomainRecipeV1) -> BoundedGenerationRecipe:
    """Expose one declarative domain recipe through the shared strict protocol."""
    binding = RuntimeRecipeBindingV1(**source.binding.__dict__)
    domains = tuple(RuntimeParameterDomainV1(item.name, "integer" if item.integer else "number", item.minimum, item.maximum) for item in source.parameter_domains)

    def local(parameters: Mapping[str, Any]) -> GenerationContextV1:
        return GenerationContextV1(dict(parameters), 0, "FOUNDATIONAL")

    def generate(parameters: Mapping[str, Any]) -> Any:
        return source.generate_answer(local(parameters))

    def derive(parameters: Mapping[str, Any]) -> RuntimeDerivationPacketV1:
        packet = source.derive_independently(local(parameters))
        if source.operation=="matrix":
            a,b=source._parameters(local(parameters))
            return RuntimeDerivationPacketV1(f"independent:{source.operation}",{"operation":"addition","left":[[a,0],[0,a]],"right":[[0,b],[b,0]]},packet.normalized_answer)
        if source.operation=="derivative":
            a,b=source._parameters(local(parameters))
            return RuntimeDerivationPacketV1(f"independent:{source.operation}",{"expression":f"{a}*x+{b}","operation":"derivative"},packet.normalized_answer)
        if source.operation=="linear_root":
            a,b=source._parameters(local(parameters))
            return RuntimeDerivationPacketV1(f"independent:{source.operation}",{"expression":f"{a}*x+{b}","operation":"linear_root"},packet.normalized_answer)
        if source.operation=="recurrence_step":
            a,b=source._parameters(local(parameters))
            return RuntimeDerivationPacketV1(f"independent:{source.operation}",{"current":a,"increment":b,"operation":"recurrence_step"},packet.normalized_answer)
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
        source.operation_terms, (("variant","coefficient_scale") if any(item.name=="coefficient_scale" for item in source.parameter_domains) else (("order","variant") if source.operation in {"derivative","linear_root","recurrence_step"} else ("scale","order"))),
        f"candidate:{source.operation}", f"independent:{source.operation}",
        generate, derive, prompt, lambda parameters: source.build_contract(local(parameters)),
    )


def build_math_engineering_runtime() -> GenerationRecipeRuntime:
    registry = GenerationRecipeRegistry()
    for recipes in COURSE_RECIPE_REGISTRY.values():
        for source in recipes:
            registry.register(adapt_recipe(source))
    return GenerationRecipeRuntime(registry)


def runtime_family(recipe: BoundedGenerationRecipe, catalog_family: Mapping[str,Any]) -> dict[str, Any]:
    """Populate the runtime contract from an exact canonical family payload."""
    if catalog_family.get("family_id")!=recipe.binding.family_id or catalog_family.get("micro_skill_id")!=recipe.binding.micro_skill_id or catalog_family.get("procedure_id")!=recipe.binding.procedure_id or catalog_family.get("answer_engine")!=recipe.binding.engine_type:
        raise ValueError("catalog family does not exactly match recipe binding")
    result=dict(catalog_family); answer_contract=dict(result.get("answer_contract",{}))
    answer_contract.setdefault("answer_contract_id",f"{recipe.binding.course_id}_ANSWER_{recipe.binding.family_id.rsplit('_',1)[-1]}"); answer_contract["engine_type"]=recipe.binding.engine_type
    result["answer_contract"]=answer_contract
    return result
