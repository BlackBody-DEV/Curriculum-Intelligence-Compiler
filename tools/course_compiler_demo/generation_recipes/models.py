"""Immutable contracts for bounded topic-skill-procedure generation recipes."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

from tools.course_compiler_demo.answer_engines.registry import AnswerEngineResult


@dataclass(frozen=True)
class RecipeBindingV1:
    course_id: str
    topic_id: str
    micro_skill_id: str
    procedure_id: str
    family_id: str
    engine_type: str

    def __post_init__(self) -> None:
        for name, value in self.to_dict().items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty identity")

    def to_dict(self) -> dict[str, str]:
        return {name: getattr(self, name) for name in ("course_id", "topic_id", "micro_skill_id", "procedure_id", "family_id", "engine_type")}


@dataclass(frozen=True)
class ParameterDomainV1:
    name: str
    kind: str
    minimum: int | float | None = None
    maximum: int | float | None = None
    choices: tuple[Any, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("parameter name is required")
        if self.kind not in {"integer", "number", "choice"}:
            raise ValueError("parameter kind is unsupported")
        if self.kind == "choice":
            if len(self.choices) < 2 or self.minimum is not None or self.maximum is not None:
                raise ValueError("choice parameters require at least two choices and no bounds")
        elif self.choices or isinstance(self.minimum, bool) or isinstance(self.maximum, bool) or not isinstance(self.minimum, (int, float)) or not isinstance(self.maximum, (int, float)) or not math.isfinite(self.minimum) or not math.isfinite(self.maximum) or self.minimum >= self.maximum:
            raise ValueError("numeric parameters require increasing finite bounds")

    def to_dict(self) -> dict[str, Any]:
        return {"choices": list(self.choices), "kind": self.kind, "maximum": self.maximum, "minimum": self.minimum, "name": self.name}


@dataclass(frozen=True)
class GenerationContextV1:
    binding: RecipeBindingV1
    topic_title: str
    skill_title: str
    procedure_steps: tuple[str, ...]
    seed: str
    variant_index: int

    def __post_init__(self) -> None:
        for name in ("topic_title", "skill_title", "seed"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} is required")
        if not self.procedure_steps or any(not isinstance(step, str) or not step.strip() for step in self.procedure_steps):
            raise ValueError("meaningful procedure steps are required")
        if isinstance(self.variant_index, bool) or not isinstance(self.variant_index, int) or self.variant_index < 0:
            raise ValueError("variant_index must be a nonnegative integer")


@dataclass(frozen=True)
class DerivationPacketV1:
    method_id: str
    derivation_input: Mapping[str, Any]
    expected_answer: Any

    def __post_init__(self) -> None:
        if not isinstance(self.method_id, str) or not self.method_id.strip():
            raise ValueError("independent derivation method_id is required")
        if not isinstance(self.derivation_input, Mapping):
            raise ValueError("derivation_input must be a mapping")


@dataclass(frozen=True)
class ValidatedGenerationV1:
    recipe_id: str
    recipe_version: str
    binding: RecipeBindingV1
    prompt: str
    parameters: Mapping[str, Any]
    normalized_answer: Any
    derived_answer: Any
    normalization_result: AnswerEngineResult
    derivation_result: AnswerEngineResult
    grading_result: AnswerEngineResult
    derivation_method_id: str
    content_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "binding": self.binding.to_dict(), "content_sha256": self.content_sha256,
            "derivation_method_id": self.derivation_method_id, "derivation_result": self.derivation_result.to_dict(),
            "derived_answer": self.derived_answer, "grading_result": self.grading_result.to_dict(),
            "normalization_result": self.normalization_result.to_dict(), "normalized_answer": self.normalized_answer,
            "parameters": dict(sorted(self.parameters.items())), "prompt": self.prompt,
            "recipe_id": self.recipe_id, "recipe_version": self.recipe_version,
        }


class GenerationRecipeError(ValueError):
    """Structured fail-closed error returned by recipe registration/runtime."""

    def __init__(self, code: str, *reasons: str):
        self.code = code
        self.reasons = tuple(str(reason) for reason in reasons if str(reason)) or (code,)
        super().__init__(f"{code}: {'; '.join(self.reasons)}")

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "reasons": list(self.reasons), "status": "REJECTED"}
