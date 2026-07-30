"""Versioned, deterministic answer engines and fail-closed registry lookup."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

from tools.course_compiler_demo.universal_core import AnswerContractV1, SupportDecisionV1


ENABLED_ENGINE_TYPES = (
    "multiple_choice", "numeric_pair", "numeric_scalar", "numeric_vector",
)
DISABLED_ENGINE_TYPES = (
    "chemical_reaction", "code_execution", "equation_system", "graph_diagram",
    "matrix", "proof_logic", "rubric_scored_explanation",
    "scientific_structured_response", "symbolic_expression",
)


@dataclass(frozen=True)
class AnswerEngineResult:
    """Structured operation result; failures never contain a usable answer."""

    status: str
    engine_type: str
    operation: str
    value: Any = None
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine_type": self.engine_type,
            "operation": self.operation,
            "reasons": list(self.reasons),
            "status": self.status,
            "value": self.value,
        }

    def _replace_operation(self, operation: str) -> "AnswerEngineResult":
        return AnswerEngineResult(self.status, self.engine_type, operation, self.value, self.reasons)


@runtime_checkable
class AnswerEngine(Protocol):
    """Interface implemented by enabled answer-engine adapters."""

    engine_type: str

    def normalize(self, answer: Any, contract: AnswerContractV1) -> AnswerEngineResult: ...
    def derive(self, derivation_input: Mapping[str, Any], contract: AnswerContractV1) -> AnswerEngineResult: ...
    def grade(self, response: Any, expected: Any, contract: AnswerContractV1) -> AnswerEngineResult: ...


@dataclass(frozen=True)
class AnswerEngineDescriptor:
    engine_type: str
    enabled: bool
    reason: str
    interface_version: str = "1.0"


def _failure(engine: str, operation: str, reason: str, status: str = "INVALID") -> AnswerEngineResult:
    return AnswerEngineResult(status, engine, operation, None, (reason,))


def _finite_number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("number must be finite")
    return result


def _tolerance(contract: AnswerContractV1) -> tuple[float, float]:
    spec = contract.grading_contract
    absolute = _finite_number(spec.get("absolute_tolerance", spec.get("absolute", 0.0)))
    relative = _finite_number(spec.get("relative_tolerance", spec.get("relative", 0.0)))
    if absolute < 0 or relative < 0:
        raise ValueError("tolerances must be nonnegative")
    return absolute, relative


def _close(actual: float, expected: float, contract: AnswerContractV1) -> bool:
    absolute, relative = _tolerance(contract)
    return abs(actual - expected) <= max(absolute, relative * abs(expected))


class _BaseEngine:
    engine_type = ""

    def derive(self, derivation_input: Mapping[str, Any], contract: AnswerContractV1) -> AnswerEngineResult:
        if not isinstance(derivation_input, Mapping) or "independently_derived_answer" not in derivation_input:
            return _failure(self.engine_type, "derive", "independently_derived_answer is required")
        # This adapter deliberately consumes a separately supplied derivation result,
        # never generator answer state.
        return self.normalize(derivation_input["independently_derived_answer"], contract)._replace_operation("derive")

    def _validate_contract(self, contract: AnswerContractV1, operation: str) -> AnswerEngineResult | None:
        if not isinstance(contract, AnswerContractV1) or contract.engine_type != self.engine_type:
            return _failure(self.engine_type, operation, "answer contract does not match engine")
        return None


def _replace_operation(result: AnswerEngineResult, operation: str) -> AnswerEngineResult:
    return result._replace_operation(operation)


class NumericScalarEngine(_BaseEngine):
    engine_type = "numeric_scalar"

    def normalize(self, answer: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._validate_contract(contract, "normalize"): return invalid
        try:
            raw = answer.get("value") if isinstance(answer, Mapping) else answer
            value = _finite_number(raw)
        except (TypeError, ValueError) as exc:
            return _failure(self.engine_type, "normalize", str(exc))
        return AnswerEngineResult("PASS", self.engine_type, "normalize", value)

    def grade(self, response: Any, expected: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._validate_contract(contract, "grade"): return invalid
        actual, target = self.normalize(response, contract), self.normalize(expected, contract)
        if actual.status != "PASS" or target.status != "PASS":
            return _failure(self.engine_type, "grade", "response and expected answer must be valid")
        try: passed = _close(actual.value, target.value, contract)
        except ValueError as exc: return _failure(self.engine_type, "grade", str(exc))
        return AnswerEngineResult("PASS" if passed else "FAIL", self.engine_type, "grade", passed)


class _NumericSequenceEngine(_BaseEngine):
    arity: int | None = None

    def normalize(self, answer: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._validate_contract(contract, "normalize"): return invalid
        raw = answer.get("values") if isinstance(answer, Mapping) else answer
        if not isinstance(raw, (list, tuple)):
            return _failure(self.engine_type, "normalize", "ordered numeric values are required")
        if self.arity is not None and len(raw) != self.arity:
            return _failure(self.engine_type, "normalize", f"exactly {self.arity} values are required")
        if self.arity is None and not raw:
            return _failure(self.engine_type, "normalize", "at least one value is required")
        try: values = tuple(_finite_number(item.get("value") if isinstance(item, Mapping) else item) for item in raw)
        except (TypeError, ValueError) as exc: return _failure(self.engine_type, "normalize", str(exc))
        return AnswerEngineResult("PASS", self.engine_type, "normalize", list(values))

    def grade(self, response: Any, expected: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._validate_contract(contract, "grade"): return invalid
        actual, target = self.normalize(response, contract), self.normalize(expected, contract)
        if actual.status != "PASS" or target.status != "PASS" or len(actual.value or []) != len(target.value or []):
            return _failure(self.engine_type, "grade", "response and expected shapes must match")
        try: passed = all(_close(a, e, contract) for a, e in zip(actual.value, target.value))
        except ValueError as exc: return _failure(self.engine_type, "grade", str(exc))
        return AnswerEngineResult("PASS" if passed else "FAIL", self.engine_type, "grade", passed)


class NumericPairEngine(_NumericSequenceEngine):
    engine_type, arity = "numeric_pair", 2


class NumericVectorEngine(_NumericSequenceEngine):
    engine_type = "numeric_vector"


class MultipleChoiceEngine(_BaseEngine):
    engine_type = "multiple_choice"

    def _options(self, contract: AnswerContractV1) -> tuple[str, ...]:
        raw = contract.grading_contract.get("options")
        if not isinstance(raw, list) or len(raw) < 2:
            raise ValueError("at least two complete options are required")
        ids: list[str] = []
        correct = 0
        for option in raw:
            if not isinstance(option, Mapping) or not str(option.get("option_id", "")).strip() or not str(option.get("text", "")).strip():
                raise ValueError("each option requires option_id and text")
            ids.append(str(option["option_id"]))
            correct += option.get("correct") is True
        if len(ids) != len(set(ids)): raise ValueError("option identifiers must be unique")
        if correct != 1: raise ValueError("exactly one option must be correct")
        return tuple(ids)

    def normalize(self, answer: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._validate_contract(contract, "normalize"): return invalid
        try: option_ids = self._options(contract)
        except ValueError as exc: return _failure(self.engine_type, "normalize", str(exc))
        selected = answer.get("option_id", answer.get("correct_option_id")) if isinstance(answer, Mapping) else answer
        if not isinstance(selected, str) or selected not in option_ids:
            return _failure(self.engine_type, "normalize", "selection must reference a declared option")
        return AnswerEngineResult("PASS", self.engine_type, "normalize", selected)

    def grade(self, response: Any, expected: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._validate_contract(contract, "grade"): return invalid
        actual, target = self.normalize(response, contract), self.normalize(expected, contract)
        if actual.status != "PASS" or target.status != "PASS": return _failure(self.engine_type, "grade", "valid selections are required")
        passed = actual.value == target.value
        return AnswerEngineResult("PASS" if passed else "FAIL", self.engine_type, "grade", passed)


class AnswerEngineRegistry:
    """Immutable-by-convention registry with explicit disabled capabilities."""

    def __init__(self) -> None:
        self._engines: dict[str, AnswerEngine] = {}
        self._descriptors: dict[str, AnswerEngineDescriptor] = {}

    def register(self, descriptor: AnswerEngineDescriptor, engine: AnswerEngine | None = None) -> None:
        if descriptor.engine_type in self._descriptors: raise ValueError(f"duplicate engine: {descriptor.engine_type}")
        if descriptor.enabled != (engine is not None): raise ValueError("enabled descriptor and adapter must agree")
        if engine is not None and engine.engine_type != descriptor.engine_type: raise ValueError("descriptor and adapter type must agree")
        self._descriptors[descriptor.engine_type] = descriptor
        if engine is not None: self._engines[descriptor.engine_type] = engine

    def descriptor(self, engine_type: str) -> AnswerEngineDescriptor | None:
        return self._descriptors.get(engine_type)

    def lookup(self, engine_type: str) -> AnswerEngineResult:
        descriptor = self._descriptors.get(engine_type)
        if descriptor is None: return _failure(engine_type, "lookup", "engine is not registered", "UNSUPPORTED")
        if not descriptor.enabled: return _failure(engine_type, "lookup", descriptor.reason, "UNSUPPORTED")
        return AnswerEngineResult("SUPPORTED", engine_type, "lookup", self._engines[engine_type])

    def support_decision(self, contract: AnswerContractV1) -> SupportDecisionV1:
        result = self.lookup(contract.engine_type)
        supported = result.status == "SUPPORTED"
        return SupportDecisionV1(
            decision_id=f"answer-engine:{contract.answer_contract_id}",
            contract_identity=contract.answer_contract_id,
            engine_type=contract.engine_type,
            status="SUPPORTED" if supported else "UNSUPPORTED",
            reason="registered enabled answer engine" if supported else result.reasons[0],
        )

    def normalize(self, answer: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        found = self.lookup(contract.engine_type)
        return found.value.normalize(answer, contract) if found.status == "SUPPORTED" else _replace_operation(found, "normalize")

    def derive(self, derivation_input: Mapping[str, Any], contract: AnswerContractV1) -> AnswerEngineResult:
        found = self.lookup(contract.engine_type)
        return found.value.derive(derivation_input, contract) if found.status == "SUPPORTED" else _replace_operation(found, "derive")

    def grade(self, response: Any, expected: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        found = self.lookup(contract.engine_type)
        return found.value.grade(response, expected, contract) if found.status == "SUPPORTED" else _replace_operation(found, "grade")


def build_default_registry() -> AnswerEngineRegistry:
    registry = AnswerEngineRegistry()
    adapters: tuple[AnswerEngine, ...] = (NumericScalarEngine(), NumericPairEngine(), NumericVectorEngine(), MultipleChoiceEngine())
    for adapter in adapters:
        registry.register(AnswerEngineDescriptor(adapter.engine_type, True, "implemented and validated"), adapter)
    for engine_type in DISABLED_ENGINE_TYPES:
        registry.register(AnswerEngineDescriptor(engine_type, False, "registered capability is not yet validated"))
    return registry
