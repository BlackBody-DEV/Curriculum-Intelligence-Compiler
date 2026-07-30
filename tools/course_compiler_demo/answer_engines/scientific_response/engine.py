"""Deterministic grading for bounded scientific responses and explicit rubrics."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Mapping, Sequence

from tools.course_compiler_demo.answer_engines.registry import (
    AnswerEngineDescriptor, AnswerEngineRegistry, AnswerEngineResult,
)
from tools.course_compiler_demo.universal_core import AnswerContractV1


ENGINE_VERSION = "1.0"
_FIELDS = frozenset({"concepts", "relationships", "quantities", "causal_sequence", "evidence"})


class StructuredResponseError(ValueError):
    pass


def _failure(engine: str, operation: str, reason: str, status: str = "INVALID") -> AnswerEngineResult:
    return AnswerEngineResult(status, engine, operation, None, (reason,))


def _validate_contract(contract: Any, engine: str, operation: str) -> AnswerEngineResult | None:
    if not isinstance(contract, AnswerContractV1) or contract.engine_type != engine:
        return _failure(engine, operation, "answer contract does not match engine")
    return None


def _token(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StructuredResponseError("structured terms must be nonempty strings")
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    if not normalized or len(normalized) > 120:
        raise StructuredResponseError("structured term is outside bounded syntax")
    return normalized


def _synonym_map(spec: Any) -> dict[str, str]:
    if spec is None: return {}
    if not isinstance(spec, Mapping):
        raise StructuredResponseError("permitted_synonyms must be an object")
    result: dict[str, str] = {}
    for canonical, aliases in spec.items():
        key = _token(canonical)
        values = aliases if isinstance(aliases, (list, tuple)) else [aliases]
        result[key] = key
        for alias in values:
            alias_key = _token(alias)
            if alias_key in result and result[alias_key] != key:
                raise StructuredResponseError("a synonym cannot map to multiple concepts")
            result[alias_key] = key
    return result


def _canonical(value: Any, synonyms: Mapping[str, str]) -> str:
    term = _token(value)
    return synonyms.get(term, term)


def _list(value: Any, field: str) -> list[Any]:
    if value is None: return []
    if not isinstance(value, (list, tuple)) or isinstance(value, (str, bytes)):
        raise StructuredResponseError(f"{field} must be an ordered array")
    if len(value) > 100:
        raise StructuredResponseError(f"{field} exceeds bounded item limit")
    return list(value)


def _relationship(value: Any, synonyms: Mapping[str, str]) -> tuple[str, str, str]:
    if isinstance(value, Mapping):
        if set(value) != {"source", "relation", "target"}:
            raise StructuredResponseError("relationship requires source, relation, and target")
        return tuple(_canonical(value[key], synonyms) for key in ("source", "relation", "target"))  # type: ignore[return-value]
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return tuple(_canonical(item, synonyms) for item in value)  # type: ignore[return-value]
    raise StructuredResponseError("relationship must be an explicit three-part structure")


def _quantity(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not {"name", "value", "unit"}.issubset(value):
        raise StructuredResponseError("quantity requires name, finite value, and unit")
    raw = value["value"]
    if isinstance(raw, bool): raise StructuredResponseError("quantity value must be numeric")
    try: number = float(raw)
    except (TypeError, ValueError): raise StructuredResponseError("quantity value must be numeric")
    if not math.isfinite(number): raise StructuredResponseError("quantity value must be finite")
    return {"name": _token(value["name"]), "unit": _token(value["unit"]), "value": number}


def normalize_response(response: Any, spec: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and canonicalize explicit fields; unrestricted prose is rejected."""
    if not isinstance(response, Mapping):
        raise StructuredResponseError("freeform prose is unsupported; a structured response object is required")
    unknown = set(response) - _FIELDS
    if unknown:
        raise StructuredResponseError(f"unsupported response fields: {', '.join(sorted(map(str, unknown)))}")
    synonyms = _synonym_map(spec.get("permitted_synonyms"))
    concepts = sorted(set(_canonical(item, synonyms) for item in _list(response.get("concepts"), "concepts")))
    relationships = sorted(set(_relationship(item, synonyms) for item in _list(response.get("relationships"), "relationships")))
    quantities = sorted((_quantity(item) for item in _list(response.get("quantities"), "quantities")), key=lambda item: (item["name"], item["unit"], item["value"]))
    sequence = [_canonical(item, synonyms) for item in _list(response.get("causal_sequence"), "causal_sequence")]
    evidence = sorted(set(_canonical(item, synonyms) for item in _list(response.get("evidence"), "evidence")))
    if not any((concepts, relationships, quantities, sequence, evidence)):
        raise StructuredResponseError("structured response must contain at least one supported item")
    return {
        "causal_sequence": sequence, "concepts": concepts, "evidence": evidence,
        "quantities": quantities,
        "relationships": [{"relation": r, "source": s, "target": t} for s, r, t in relationships],
    }


def _required_terms(values: Any, synonyms: Mapping[str, str], field: str) -> list[str]:
    return sorted(set(_canonical(value, synonyms) for value in _list(values, field)))


def _requirements(spec: Mapping[str, Any]) -> dict[str, Any]:
    synonyms = _synonym_map(spec.get("permitted_synonyms"))
    concepts = _required_terms(spec.get("required_concepts"), synonyms, "required_concepts")
    relationships = sorted(set(_relationship(item, synonyms) for item in _list(spec.get("required_relationships"), "required_relationships")))
    contradictions = _required_terms(spec.get("forbidden_contradictions"), synonyms, "forbidden_contradictions")
    sequence = [_canonical(item, synonyms) for item in _list(spec.get("required_causal_sequence"), "required_causal_sequence")]
    evidence_threshold = spec.get("minimum_evidence_threshold", 0)
    if isinstance(evidence_threshold, bool) or not isinstance(evidence_threshold, int) or evidence_threshold < 0:
        raise StructuredResponseError("minimum_evidence_threshold must be a nonnegative integer")
    quantities = [_quantity(item) for item in _list(spec.get("required_quantities"), "required_quantities")]
    return {"concepts": concepts, "relationships": relationships, "contradictions": contradictions,
            "sequence": sequence, "evidence_threshold": evidence_threshold, "quantities": quantities}


def _sequence_present(required: Sequence[str], actual: Sequence[str]) -> bool:
    if not required: return True
    cursor = iter(actual)
    return all(any(candidate == term for candidate in cursor) for term in required)


def _quantity_matches(required: Mapping[str, Any], actual: Sequence[Mapping[str, Any]], spec: Mapping[str, Any]) -> bool:
    tolerance = spec.get("quantity_absolute_tolerance", 0.0)
    if isinstance(tolerance, bool): raise StructuredResponseError("quantity tolerance must be nonnegative")
    try: tolerance = float(tolerance)
    except (TypeError, ValueError): raise StructuredResponseError("quantity tolerance must be nonnegative")
    if not math.isfinite(tolerance) or tolerance < 0: raise StructuredResponseError("quantity tolerance must be nonnegative")
    return any(item["name"] == required["name"] and item["unit"] == required["unit"] and abs(item["value"] - required["value"]) <= tolerance for item in actual)


def _weights(spec: Mapping[str, Any], rubric: bool) -> dict[str, float]:
    defaults = {"concepts": 1.0, "relationships": 1.0, "quantities": 1.0, "causal_sequence": 1.0, "evidence": 1.0}
    raw = spec.get("partial_credit_rules", spec.get("weights", {}))
    if raw is None: raw = {}
    if not isinstance(raw, Mapping): raise StructuredResponseError("partial_credit_rules must be an object")
    for key, value in raw.items():
        if key not in defaults: raise StructuredResponseError(f"unsupported partial-credit category: {key}")
        if isinstance(value, Mapping): value = value.get("points")
        if isinstance(value, bool): raise StructuredResponseError("partial-credit points must be nonnegative")
        try: number = float(value)
        except (TypeError, ValueError): raise StructuredResponseError("partial-credit points must be nonnegative")
        if not math.isfinite(number) or number < 0: raise StructuredResponseError("partial-credit points must be nonnegative")
        defaults[key] = number
    return defaults


def grade_response(response: dict[str, Any], spec: Mapping[str, Any], rubric: bool) -> dict[str, Any]:
    requirements = _requirements(spec); weights = _weights(spec, rubric)
    actual_concepts = set(response["concepts"]); actual_evidence = set(response["evidence"])
    actual_relationships = {(item["source"], item["relation"], item["target"]) for item in response["relationships"]}
    matched_concepts = [item for item in requirements["concepts"] if item in actual_concepts]
    matched_relationships = [item for item in requirements["relationships"] if item in actual_relationships]
    matched_quantities = [item for item in requirements["quantities"] if _quantity_matches(item, response["quantities"], spec)]
    sequence_pass = _sequence_present(requirements["sequence"], response["causal_sequence"])
    evidence_count = len(actual_evidence); evidence_pass = evidence_count >= requirements["evidence_threshold"]
    contradictions = sorted(set(requirements["contradictions"]) & (actual_concepts | actual_evidence | set(response["causal_sequence"])))
    earned = 0.0; possible = 0.0
    categories = (
        ("concepts", len(matched_concepts), len(requirements["concepts"])),
        ("relationships", len(matched_relationships), len(requirements["relationships"])),
        ("quantities", len(matched_quantities), len(requirements["quantities"])),
        ("causal_sequence", int(sequence_pass), int(bool(requirements["sequence"]))),
        ("evidence", int(evidence_pass), int(requirements["evidence_threshold"] > 0)),
    )
    breakdown = {}
    for name, matched, required in categories:
        if required:
            possible += weights[name]; points = weights[name] * matched / required; earned += points
        else: points = 0.0
        breakdown[name] = {"matched": matched, "required": required, "points": round(points, 6)}
    if not possible: raise StructuredResponseError("grading contract must declare at least one requirement")
    score = round(earned / possible, 6)
    threshold = spec.get("passing_score", 1.0 if not rubric else 0.7)
    if isinstance(threshold, bool): raise StructuredResponseError("passing_score must be between zero and one")
    try: threshold = float(threshold)
    except (TypeError, ValueError): raise StructuredResponseError("passing_score must be between zero and one")
    if not 0 <= threshold <= 1: raise StructuredResponseError("passing_score must be between zero and one")
    passed = score >= threshold and not contradictions
    return {"breakdown": breakdown, "contradictions": contradictions, "passed": passed,
            "possible_points": round(possible, 6), "score": score,
            "total_points": round(earned, 6)}


class _StructuredEngine:
    engine_type = ""
    engine_id = ""
    engine_version = ENGINE_VERSION
    rubric = False

    def normalize(self, answer: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := _validate_contract(contract, self.engine_type, "normalize"): return invalid
        try: value = normalize_response(answer, contract.grading_contract)
        except StructuredResponseError as exc: return _failure(self.engine_type, "normalize", str(exc))
        return AnswerEngineResult("PASS", self.engine_type, "normalize", value)

    def derive(self, derivation_input: Mapping[str, Any], contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := _validate_contract(contract, self.engine_type, "derive"): return invalid
        if not isinstance(derivation_input, Mapping) or "structured_response" not in derivation_input:
            return _failure(self.engine_type, "derive", "structured_response derivation input is required")
        result = self.normalize(derivation_input["structured_response"], contract)
        return AnswerEngineResult(result.status, result.engine_type, "derive", result.value, result.reasons)

    def grade(self, response: Any, expected: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := _validate_contract(contract, self.engine_type, "grade"): return invalid
        normalized = self.normalize(response, contract)
        if normalized.status != "PASS": return _failure(self.engine_type, "grade", normalized.reasons[0])
        try: value = grade_response(normalized.value, contract.grading_contract, self.rubric)
        except StructuredResponseError as exc: return _failure(self.engine_type, "grade", str(exc), "UNSUPPORTED")
        return AnswerEngineResult("PASS" if value["passed"] else "FAIL", self.engine_type, "grade", value)


class ScientificStructuredResponseEngine(_StructuredEngine):
    engine_type = "scientific_structured_response"
    engine_id = "axiomiq.scientific_structured_response"


class RubricScoredExplanationEngine(_StructuredEngine):
    engine_type = "rubric_scored_explanation"
    engine_id = "axiomiq.rubric_scored_explanation"
    rubric = True


def register_scientific_response_engines(registry: AnswerEngineRegistry) -> AnswerEngineRegistry:
    for engine in (ScientificStructuredResponseEngine(), RubricScoredExplanationEngine()):
        registry.register(AnswerEngineDescriptor(engine.engine_type, True, f"scientific response engine {ENGINE_VERSION}"), engine)
    return registry


def build_scientific_response_registry() -> AnswerEngineRegistry:
    return register_scientific_response_engines(AnswerEngineRegistry())
