import json

import pytest

from tools.course_compiler_demo.answer_engines.registry import AnswerEngine
from tools.course_compiler_demo.answer_engines.scientific_response import (
    RubricScoredExplanationEngine, ScientificStructuredResponseEngine,
    build_scientific_response_registry,
)
from tools.course_compiler_demo.universal_core import AnswerContractV1


def contract(engine, grading):
    return AnswerContractV1(f"contract:{engine}", engine, grading)


BASE_SPEC = {
    "required_concepts": ["force", "acceleration"],
    "required_relationships": [{"source": "net force", "relation": "causes", "target": "acceleration"}],
    "permitted_synonyms": {"force": ["net force", "resultant force"], "acceleration": ["rate of velocity change"]},
    "required_quantities": [{"name": "acceleration", "value": 2, "unit": "m/s^2"}],
    "forbidden_contradictions": ["constant velocity"],
    "required_causal_sequence": ["force", "acceleration"],
    "minimum_evidence_threshold": 2,
    "quantity_absolute_tolerance": 0.01,
}


def full_response(index=0):
    concepts = ["rate of velocity change", "resultant force"]
    if index % 2: concepts.reverse()
    relationships = [{"target": "acceleration", "relation": "causes", "source": "net force"}]
    evidence = [f"measurement {index}", "free body diagram"]
    return {"concepts": concepts, "relationships": relationships,
            "quantities": [{"unit": "m/s^2", "value": 2 + (index % 3) * .001, "name": "acceleration"}],
            "causal_sequence": ["force", "acceleration"], "evidence": evidence}


@pytest.mark.parametrize("case", range(50))
def test_50_scientific_structured_response_proofs(case):
    engine = ScientificStructuredResponseEngine(); answer_contract = contract(engine.engine_type, BASE_SPEC)
    response = full_response(case)
    normalized = engine.normalize(response, answer_contract)
    derived = engine.derive({"structured_response": response, "generator_answer": "unread"}, answer_contract)
    graded = engine.grade(response, None, answer_contract)
    assert normalized.status == derived.status == graded.status == "PASS"
    assert normalized.value == derived.value
    assert graded.value["score"] == 1.0 and graded.value["contradictions"] == []
    assert graded.engine_type == "scientific_structured_response"


RUBRIC_SPEC = {
    **BASE_SPEC,
    "partial_credit_rules": {"concepts": 4, "relationships": 2, "quantities": 2, "causal_sequence": 1, "evidence": 1},
    "passing_score": 0.6,
}


@pytest.mark.parametrize("case", range(50))
def test_50_rubric_partial_credit_proofs_are_exact_and_deterministic(case):
    engine = RubricScoredExplanationEngine(); answer_contract = contract(engine.engine_type, RUBRIC_SPEC)
    count = case % 5
    response = {"concepts": ["force"] if count >= 1 else ["irrelevant observation"], "relationships": [], "quantities": [],
                "causal_sequence": ["force", "acceleration"] if count >= 4 else [],
                "evidence": ["trial one", "trial two"] if count >= 3 else (["trial one"] if count >= 2 else [])}
    if count >= 2: response["concepts"].append("acceleration")
    if count >= 3: response["relationships"].append({"source": "force", "relation": "causes", "target": "acceleration"})
    first = engine.grade(response, {}, answer_contract)
    second = engine.grade(dict(reversed(list(response.items()))), None, answer_contract)
    assert first.to_dict() == second.to_dict()
    assert 0 <= first.value["score"] <= 1 and first.value["total_points"] <= first.value["possible_points"] == 10
    expected_concept_points = 0 if count == 0 else (2 if count == 1 else 4)
    assert first.value["breakdown"]["concepts"]["points"] == expected_concept_points


def test_contradiction_detection_overrides_otherwise_complete_answer():
    response = full_response(); response["concepts"].append("constant velocity")
    result = ScientificStructuredResponseEngine().grade(response, None, contract("scientific_structured_response", BASE_SPEC))
    assert result.status == "FAIL" and result.value["score"] == 1.0
    assert result.value["contradictions"] == ["constant_velocity"] and result.value["passed"] is False


def test_concept_and_relationship_matching_are_order_independent():
    engine = ScientificStructuredResponseEngine(); answer_contract = contract(engine.engine_type, BASE_SPEC)
    first = full_response(0); second = full_response(1)
    second["evidence"] = list(reversed(first["evidence"]))
    second["quantities"] = list(reversed(first["quantities"]))
    assert engine.normalize(first, answer_contract).to_dict() == engine.normalize(second, answer_contract).to_dict()
    assert engine.grade(first, None, answer_contract).value == engine.grade(second, None, answer_contract).value


@pytest.mark.parametrize("freeform", [
    "Force causes acceleration because F=ma.", "A thoughtful scientific paragraph.", "", 42,
    ["force", "acceleration"], {"essay": "Force causes acceleration"},
])
def test_unsupported_freeform_responses_fail_closed(freeform):
    engine = ScientificStructuredResponseEngine()
    result = engine.normalize(freeform, contract(engine.engine_type, BASE_SPEC))
    assert result.status == "INVALID" and result.value is None and result.reasons


def test_required_units_evidence_threshold_sequence_and_relationships():
    engine = ScientificStructuredResponseEngine(); answer_contract = contract(engine.engine_type, BASE_SPEC)
    bad_unit = full_response(); bad_unit["quantities"][0]["unit"] = "km/s^2"
    assert engine.grade(bad_unit, None, answer_contract).status == "FAIL"
    low_evidence = full_response(); low_evidence["evidence"] = ["one trial"]
    assert engine.grade(low_evidence, None, answer_contract).status == "FAIL"
    reversed_cause = full_response(); reversed_cause["causal_sequence"].reverse()
    assert engine.grade(reversed_cause, None, answer_contract).status == "FAIL"
    missing_relationship = full_response(); missing_relationship["relationships"] = []
    assert engine.grade(missing_relationship, None, answer_contract).status == "FAIL"


def test_universal_protocol_registry_fail_closed_and_stable_serialization():
    registry = build_scientific_response_registry()
    for name in ("scientific_structured_response", "rubric_scored_explanation"):
        found = registry.lookup(name)
        assert found.status == "SUPPORTED" and isinstance(found.value, AnswerEngine)
        assert registry.support_decision(contract(name, BASE_SPEC)).status == "SUPPORTED"
    response = full_response(); answer_contract = contract("scientific_structured_response", BASE_SPEC)
    first = registry.normalize(response, answer_contract).to_dict(); second = registry.normalize(response, answer_contract).to_dict()
    assert first == second
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(second, sort_keys=True, separators=(",", ":"))
    mismatch = ScientificStructuredResponseEngine().normalize(response, contract("numeric_scalar", BASE_SPEC))
    assert mismatch.status == "INVALID" and mismatch.engine_type == "scientific_structured_response"
    no_requirements = contract("scientific_structured_response", {})
    unsupported = ScientificStructuredResponseEngine().grade({"concepts": ["force"]}, None, no_requirements)
    assert unsupported.status == "UNSUPPORTED" and unsupported.value is None


def test_malformed_contracts_and_responses_are_rejected():
    engine = RubricScoredExplanationEngine()
    bad_specs = [
        {**RUBRIC_SPEC, "minimum_evidence_threshold": -1},
        {**RUBRIC_SPEC, "passing_score": 2},
        {**RUBRIC_SPEC, "partial_credit_rules": {"concepts": -1}},
        {**RUBRIC_SPEC, "permitted_synonyms": {"force": ["x"], "acceleration": ["x"]}},
    ]
    for spec in bad_specs:
        assert engine.grade(full_response(), None, contract(engine.engine_type, spec)).status in {"INVALID", "UNSUPPORTED"}
    malformed = {"concepts": "force", "relationships": [], "quantities": [], "causal_sequence": [], "evidence": []}
    assert engine.normalize(malformed, contract(engine.engine_type, RUBRIC_SPEC)).status == "INVALID"
