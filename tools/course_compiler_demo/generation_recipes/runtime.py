"""Deterministic fail-closed execution runtime for generation recipes."""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Mapping

from tools.course_compiler_demo.answer_engines import AnswerEngineRegistry, build_default_registry
from tools.course_compiler_demo.universal_core import AnswerContractV1
from .models import GenerationContextV1, GenerationRecipeError, ParameterDomainV1, RecipeBindingV1, ValidatedGenerationV1
from .recipe import GenerationRecipe


_GENERIC_PHRASES = ("bounded problem", "apply the procedure", "demonstrate the micro-skill", "generic question", "insert topic")


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise GenerationRecipeError("NONDETERMINISTIC_VALUE", str(exc)) from None


def _normalized_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _validate_recipe(recipe: GenerationRecipe) -> None:
    if not isinstance(recipe, GenerationRecipe):
        raise GenerationRecipeError("INVALID_RECIPE_PROTOCOL", "recipe does not implement GenerationRecipe")
    for name in ("recipe_id", "recipe_version", "generator_method_id", "derivation_method_id"):
        if not isinstance(getattr(recipe, name), str) or not getattr(recipe, name).strip():
            raise GenerationRecipeError("INVALID_RECIPE_METADATA", f"{name} is required")
    if recipe.generator_method_id == recipe.derivation_method_id:
        raise GenerationRecipeError("DERIVATION_NOT_INDEPENDENT", "generator and deriver method identities must differ")
    if getattr(recipe, "answer_generator", None) is getattr(recipe, "independent_deriver", object()):
        raise GenerationRecipeError("DERIVATION_NOT_INDEPENDENT", "generator and deriver callables must be distinct")
    if not recipe.parameter_domains or len({item.name for item in recipe.parameter_domains}) != len(recipe.parameter_domains):
        raise GenerationRecipeError("INVALID_PARAMETER_DOMAINS", "unique parameter domains are required")
    if len(recipe.domain_terms) < 2 or len(recipe.operation_terms) < 1 or any(not _normalized_text(term) for term in recipe.domain_terms + recipe.operation_terms):
        raise GenerationRecipeError("INSUFFICIENT_SEMANTIC_CONTRACT", "at least two domain terms and one operation term are required")
    names = {item.name for item in recipe.parameter_domains}
    if not recipe.prompt_parameter_names or not set(recipe.prompt_parameter_names) <= names:
        raise GenerationRecipeError("INVALID_PROMPT_PARAMETERS", "prompt parameter names must resolve to declared domains")


class GenerationRecipeRegistry:
    def __init__(self) -> None:
        self._by_id: dict[str, GenerationRecipe] = {}
        self._by_binding: dict[RecipeBindingV1, str] = {}

    def register(self, recipe: GenerationRecipe) -> None:
        _validate_recipe(recipe)
        if recipe.recipe_id in self._by_id:
            raise GenerationRecipeError("DUPLICATE_RECIPE_ID", recipe.recipe_id)
        if recipe.binding in self._by_binding:
            raise GenerationRecipeError("DUPLICATE_RECIPE_BINDING", recipe.binding.family_id)
        self._by_id[recipe.recipe_id] = recipe
        self._by_binding[recipe.binding] = recipe.recipe_id

    def lookup(self, recipe_id: str) -> GenerationRecipe:
        recipe = self._by_id.get(recipe_id)
        if recipe is None:
            raise GenerationRecipeError("UNSUPPORTED_RECIPE", f"recipe {recipe_id!r} is not registered")
        return recipe

    def lookup_binding(self, binding: RecipeBindingV1) -> GenerationRecipe:
        recipe_id = self._by_binding.get(binding)
        if recipe_id is None:
            raise GenerationRecipeError("UNSUPPORTED_BINDING", "no exact topic-skill-procedure-family binding is registered")
        return self._by_id[recipe_id]


class GenerationRecipeRuntime:
    def __init__(self, recipes: GenerationRecipeRegistry, engines: AnswerEngineRegistry | None = None) -> None:
        self.recipes = recipes
        self.engines = engines or build_default_registry()

    @staticmethod
    def _parameters(recipe: GenerationRecipe, context: GenerationContextV1) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for position, domain in enumerate(recipe.parameter_domains):
            digest = hashlib.sha256(f"{context.seed}:{context.variant_index}:{recipe.recipe_id}:{position}:{domain.name}".encode()).digest()
            integer = int.from_bytes(digest[:8], "big")
            if domain.kind == "choice":
                value = domain.choices[integer % len(domain.choices)]
            elif domain.kind == "integer":
                low, high = int(domain.minimum), int(domain.maximum)
                value = low + integer % (high - low + 1)
            else:
                fraction = integer / ((1 << 64) - 1)
                value = float(domain.minimum) + fraction * (float(domain.maximum) - float(domain.minimum))
                if not math.isfinite(value):
                    raise GenerationRecipeError("INVALID_PARAMETER", domain.name)
                value = float(f"{value:.12g}")
            values[domain.name] = value
        return values

    @staticmethod
    def _family_compatibility(recipe: GenerationRecipe, context: GenerationContextV1, family: Mapping[str, Any]) -> None:
        if context.binding != recipe.binding:
            raise GenerationRecipeError("BINDING_MISMATCH", "context binding is not the recipe's exact binding")
        required = {"family_id", "procedure_id", "answer_engine", "answer_contract"}
        if not isinstance(family, Mapping) or not required <= set(family):
            raise GenerationRecipeError("INVALID_FAMILY", "family identity, procedure, and engine are required")
        expected = recipe.binding
        checks = {
            "family_id": expected.family_id, "procedure_id": expected.procedure_id,
            "answer_engine": expected.engine_type,
        }
        if "micro_skill_id" in family:
            checks["micro_skill_id"] = expected.micro_skill_id
        mismatches = [name for name, value in checks.items() if family.get(name) != value]
        if mismatches:
            raise GenerationRecipeError("FAMILY_COMPATIBILITY_MISMATCH", *mismatches)
        family_contract = family["answer_contract"]
        if not isinstance(family_contract, Mapping) or family_contract.get("engine_type") != expected.engine_type:
            raise GenerationRecipeError("FAMILY_COMPATIBILITY_MISMATCH", "answer_contract.engine_type")
        declared = family.get("parameter_domains")
        if not isinstance(declared, Mapping) or not {item.name for item in recipe.parameter_domains} <= set(declared):
            raise GenerationRecipeError("PARAMETER_DOMAIN_MISMATCH", "recipe parameters are not declared by the family")
        for domain in recipe.parameter_domains:
            specification = declared[domain.name]
            if not isinstance(specification, Mapping):
                raise GenerationRecipeError("PARAMETER_DOMAIN_MISMATCH", f"{domain.name} must be a structured domain")
            declared_kind = specification.get("type", specification.get("kind"))
            if declared_kind and declared_kind != domain.kind:
                raise GenerationRecipeError("PARAMETER_DOMAIN_MISMATCH", f"{domain.name} kind differs")
            if domain.kind == "choice":
                choices = specification.get("choices", specification.get("enum"))
                if not isinstance(choices, (list, tuple)) or not set(domain.choices) <= set(choices):
                    raise GenerationRecipeError("PARAMETER_DOMAIN_MISMATCH", f"{domain.name} choices exceed family domain")
            else:
                low, high = specification.get("minimum"), specification.get("maximum")
                if isinstance(low, bool) or isinstance(high, bool) or not isinstance(low, (int, float)) or not isinstance(high, (int, float)) or domain.minimum < low or domain.maximum > high:
                    raise GenerationRecipeError("PARAMETER_DOMAIN_MISMATCH", f"{domain.name} bounds exceed family domain")

    @staticmethod
    def _anti_generic(recipe: GenerationRecipe, prompt: Any, parameters: Mapping[str, Any], context: GenerationContextV1) -> str:
        if not isinstance(prompt, str) or len(prompt.strip()) < 80 or len(prompt) > 8_000:
            raise GenerationRecipeError("PROMPT_NOT_SUBSTANTIVE", "prompt must contain 80 to 8000 characters")
        normalized = _normalized_text(prompt)
        if any(phrase in normalized for phrase in _GENERIC_PHRASES):
            raise GenerationRecipeError("GENERIC_PROMPT", "prompt contains a prohibited generic template phrase")
        domain_hits = sum(_normalized_text(term) in normalized for term in recipe.domain_terms)
        operation_hits = sum(_normalized_text(term) in normalized for term in recipe.operation_terms)
        if domain_hits < 2 or operation_hits < 1:
            raise GenerationRecipeError("SEMANTIC_GROUNDING_FAILED", "prompt does not satisfy declared domain and operation semantics")
        if _normalized_text(context.topic_title) not in normalized or _normalized_text(context.skill_title) not in normalized:
            raise GenerationRecipeError("CURRICULUM_GROUNDING_FAILED", "prompt must name the exact topic and micro-skill titles")
        for name in recipe.prompt_parameter_names:
            if str(parameters[name]) not in prompt:
                raise GenerationRecipeError("PROMPT_PARAMETER_MISSING", name)
        return prompt.strip()

    def generate(self, recipe_id: str, context: GenerationContextV1, family: Mapping[str, Any]) -> ValidatedGenerationV1:
        recipe = self.recipes.lookup(recipe_id)
        self._family_compatibility(recipe, context, family)
        parameters = self._parameters(recipe, context)
        try:
            raw_answer = recipe.generate_answer(dict(parameters))
            derivation = recipe.derive_independently(dict(parameters))
            contract = recipe.build_contract(dict(parameters))
            prompt = recipe.build_prompt(dict(parameters), context)
        except GenerationRecipeError:
            raise
        except Exception as exc:
            raise GenerationRecipeError("RECIPE_EXECUTION_FAILED", type(exc).__name__, str(exc)) from None
        if derivation.method_id != recipe.derivation_method_id or derivation.method_id == recipe.generator_method_id:
            raise GenerationRecipeError("DERIVATION_NOT_INDEPENDENT", "derivation method identity is invalid")
        if not isinstance(contract, AnswerContractV1) or contract.engine_type != recipe.binding.engine_type:
            raise GenerationRecipeError("ANSWER_CONTRACT_MISMATCH", "contract engine does not match recipe binding")
        family_contract = family["answer_contract"]
        declared_contract_id = family_contract.get("answer_contract_id")
        if declared_contract_id is not None and contract.answer_contract_id != declared_contract_id:
            raise GenerationRecipeError("ANSWER_CONTRACT_MISMATCH", "constructed contract identity differs from family declaration")
        prompt = self._anti_generic(recipe, prompt, parameters, context)
        normalized = self.engines.normalize(raw_answer, contract)
        derived = self.engines.derive(derivation.derivation_input, contract)
        graded = self.engines.grade(raw_answer, derivation.expected_answer, contract)
        if normalized.status != "PASS" or derived.status != "PASS" or graded.status != "PASS":
            reasons = [f"normalize={normalized.status}", f"derive={derived.status}", f"grade={graded.status}"] + list(normalized.reasons + derived.reasons + graded.reasons)
            raise GenerationRecipeError("ANSWER_ENGINE_VALIDATION_FAILED", *reasons)
        if _canonical(normalized.value) != _canonical(derived.value):
            raise GenerationRecipeError("DERIVATION_DISAGREEMENT", "normalized generator answer differs from independent derivation")
        material = {"answer_engine": recipe.binding.engine_type, "normalized_answer": normalized.value, "parameters": parameters, "prompt": prompt}
        fingerprint = hashlib.sha256(_canonical(material).encode()).hexdigest()
        return ValidatedGenerationV1(recipe.recipe_id, recipe.recipe_version, recipe.binding, prompt, parameters, normalized.value, derived.value, normalized, derived, graded, derivation.method_id, fingerprint)

    @staticmethod
    def coverage(results: list[ValidatedGenerationV1]) -> dict[str, Any]:
        fingerprints = [item.content_sha256 for item in results]
        bindings = [item.binding for item in results]
        return {
            "answer_engine_count": len({item.engine_type for item in bindings}),
            "exact_duplicates": len(fingerprints) - len(set(fingerprints)),
            "family_count": len({item.family_id for item in bindings}),
            "micro_skill_count": len({item.micro_skill_id for item in bindings}),
            "procedure_count": len({item.procedure_id for item in bindings}),
            "question_count": len(results),
            "status": "PASS" if fingerprints and len(fingerprints) == len(set(fingerprints)) else "FAIL",
        }

    @staticmethod
    def require_coverage(
        results: list[ValidatedGenerationV1], *, minimum_questions: int = 25,
        minimum_families: int = 5, minimum_micro_skills: int = 5,
        minimum_procedures: int = 3, minimum_answer_engines: int = 2,
    ) -> dict[str, Any]:
        report = GenerationRecipeRuntime.coverage(results)
        requirements = {
            "question_count": minimum_questions, "family_count": minimum_families,
            "micro_skill_count": minimum_micro_skills, "procedure_count": minimum_procedures,
            "answer_engine_count": minimum_answer_engines,
        }
        shortfalls = [f"{name}={report[name]}<{required}" for name, required in requirements.items() if report[name] < required]
        if report["exact_duplicates"]:
            shortfalls.append(f"exact_duplicates={report['exact_duplicates']}")
        if shortfalls:
            raise GenerationRecipeError("COVERAGE_GATE_FAILED", *shortfalls)
        return report
