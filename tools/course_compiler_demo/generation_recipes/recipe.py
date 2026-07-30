"""Strict recipe protocol and bounded callable-backed implementation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

from tools.course_compiler_demo.universal_core import AnswerContractV1
from .models import DerivationPacketV1, GenerationContextV1, ParameterDomainV1, RecipeBindingV1


@runtime_checkable
class GenerationRecipe(Protocol):
    recipe_id: str
    recipe_version: str
    binding: RecipeBindingV1
    parameter_domains: tuple[ParameterDomainV1, ...]
    domain_terms: tuple[str, ...]
    operation_terms: tuple[str, ...]
    prompt_parameter_names: tuple[str, ...]
    generator_method_id: str
    derivation_method_id: str

    def generate_answer(self, parameters: Mapping[str, Any]) -> Any: ...
    def derive_independently(self, parameters: Mapping[str, Any]) -> DerivationPacketV1: ...
    def build_prompt(self, parameters: Mapping[str, Any], context: GenerationContextV1) -> str: ...
    def build_contract(self, parameters: Mapping[str, Any]) -> AnswerContractV1: ...


@dataclass(frozen=True)
class BoundedGenerationRecipe:
    recipe_id: str
    recipe_version: str
    binding: RecipeBindingV1
    parameter_domains: tuple[ParameterDomainV1, ...]
    domain_terms: tuple[str, ...]
    operation_terms: tuple[str, ...]
    prompt_parameter_names: tuple[str, ...]
    generator_method_id: str
    derivation_method_id: str
    answer_generator: Callable[[Mapping[str, Any]], Any]
    independent_deriver: Callable[[Mapping[str, Any]], DerivationPacketV1]
    prompt_builder: Callable[[Mapping[str, Any], GenerationContextV1], str]
    contract_builder: Callable[[Mapping[str, Any]], AnswerContractV1]

    def generate_answer(self, parameters: Mapping[str, Any]) -> Any:
        return self.answer_generator(parameters)

    def derive_independently(self, parameters: Mapping[str, Any]) -> DerivationPacketV1:
        return self.independent_deriver(parameters)

    def build_prompt(self, parameters: Mapping[str, Any], context: GenerationContextV1) -> str:
        return self.prompt_builder(parameters, context)

    def build_contract(self, parameters: Mapping[str, Any]) -> AnswerContractV1:
        return self.contract_builder(parameters)
