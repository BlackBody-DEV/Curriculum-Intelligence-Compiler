"""Cache-free declarative recipe model for wave 056 domain lanes.

Generation and derivation deliberately consume separately copied primitives.  A
caller cannot substitute an answer from one path into the other without the
equality check in :meth:`DomainRecipe.compile` detecting the disagreement.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True)
class RecipeBinding:
    course_id: str
    topic_id: str
    micro_skill_id: str
    procedure_id: str
    family_id: str
    engine_type: str


@dataclass(frozen=True)
class RecipeResult:
    recipe_id: str
    binding: RecipeBinding
    difficulty: str
    prompt: str
    generated_answer: Any
    independently_derived_answer: Any
    derivation: Mapping[str, Any]
    contract: Mapping[str, Any]


def _calculate(operation: str, a: int, b: int) -> float:
    if operation == "add": return a + b
    if operation == "subtract": return a - b
    if operation == "multiply": return a * b
    if operation == "ratio": return a / b
    if operation == "percent": return 100 * a / b
    raise ValueError(f"unsupported operation {operation!r}")


@dataclass(frozen=True)
class DomainRecipe:
    recipe_id: str
    version: str
    binding: RecipeBinding
    domain_terms: tuple[str, str, str]
    operation: str
    principle: str
    context: str
    unit: str

    def parameters(self, variant: int) -> Mapping[str, int]:
        if variant not in range(5): raise ValueError("variant must be 0..4")
        # Denominators are nonzero; values change both operands across variants.
        return MappingProxyType({"a": 6 + 3 * variant, "b": 2 + variant})

    def generate_answer(self, parameters: Mapping[str, int]) -> Any:
        value = _calculate(self.operation, int(parameters["a"]), int(parameters["b"]))
        engine = self.binding.engine_type
        if engine == "numeric_scalar": return value
        if engine == "numeric_vector": return [value, int(parameters["a"]), int(parameters["b"])]
        if engine == "multiple_choice": return {"option_id": ("A", "B", "C", "D")[int(abs(value)) % 4]}
        if engine in {"code_execution", "code_execution_python"}:
            symbol = {"add": "+", "subtract": "-", "multiply": "*", "ratio": "/", "percent": "* 100 /"}[self.operation]
            return {"source": f"def solve(a, b):\n    return a {symbol} b\n"}
        return {"concepts": [self.principle], "quantities": [{"name": self.domain_terms[2], "value": value, "unit": self.unit}], "evidence": [f"computed by {self.operation} from the stated domain quantities"]}

    def derive_independently(self, parameters: Mapping[str, int]) -> tuple[Any, Mapping[str, Any]]:
        # Reconstruct from primitive values, never from generate_answer output.
        left, right = int(parameters["a"]), int(parameters["b"])
        derived = _calculate(str(self.operation), left, right)
        engine = self.binding.engine_type
        answer: Any = derived
        if engine == "numeric_vector": answer = [derived, left, right]
        elif engine == "multiple_choice": answer = {"option_id": ("A", "B", "C", "D")[int(abs(derived)) % 4]}
        elif engine in {"code_execution", "code_execution_python"}:
            symbol = {"add": "+", "subtract": "-", "multiply": "*", "ratio": "/", "percent": "* 100 /"}[self.operation]
            answer = {"source": f"def solve(a, b):\n    return a {symbol} b\n"}
        elif engine in {"scientific_structured_response", "rubric_scored_explanation"}:
            answer = {"concepts": [str(self.principle)], "quantities": [{"name": str(self.domain_terms[2]), "value": derived, "unit": str(self.unit)}], "evidence": [f"computed by {self.operation} from the stated domain quantities"]}
        packet = MappingProxyType({"primitive_inputs": {"a": left, "b": right}, "operation": self.operation, "result": derived, "principle": self.principle})
        return answer, packet

    def build_prompt(self, parameters: Mapping[str, int]) -> str:
        first, second, result = self.domain_terms
        verbs = {"add": "combine", "subtract": "find the change from", "multiply": "form the product of", "ratio": "divide", "percent": "express the first quantity as a percentage of the second"}
        return (f"{self.context} The {first} is {parameters['a']} {self.unit}; the {second} is {parameters['b']} {self.unit}. "
                f"Use {self.principle} to {verbs[self.operation]} these quantities and determine the {result}. "
                f"Show the procedure identified by {self.binding.procedure_id}; do not infer an unstated model.")

    def build_contract(self) -> Mapping[str, Any]:
        engine = self.binding.engine_type
        if engine in {"numeric_scalar", "numeric_vector"}:
            return MappingProxyType({"engine_type": engine, "absolute_tolerance": 1e-9, "unit": self.unit})
        if engine == "multiple_choice":
            return MappingProxyType({"engine_type": engine, "options": ["A", "B", "C", "D"], "exactly_one_correct": True})
        if engine in {"code_execution", "code_execution_python"}:
            return MappingProxyType({"engine_type": "code_execution_python", "entrypoint": "solve", "network": False, "filesystem": False})
        return MappingProxyType({"engine_type": engine, "required_concepts": [self.principle], "required_quantity": self.domain_terms[2], "minimum_evidence": 1})

    def compile(self, variant: int) -> RecipeResult:
        p1 = dict(self.parameters(variant)); p2 = dict(self.parameters(variant))
        generated = self.generate_answer(p1)
        derived, packet = self.derive_independently(p2)
        if generated != derived: raise ValueError(f"independent derivation mismatch: {self.recipe_id}")
        return RecipeResult(self.recipe_id, self.binding, ("FOUNDATIONAL", "INTERMEDIATE", "ADVANCED", "INTERMEDIATE", "ADVANCED")[variant], self.build_prompt(p1), generated, derived, packet, self.build_contract())
