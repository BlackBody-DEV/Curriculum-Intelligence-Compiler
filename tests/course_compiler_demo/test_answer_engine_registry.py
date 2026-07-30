import json

import pytest

from tools.course_compiler_demo.answer_engines import build_default_registry
from tools.course_compiler_demo.answer_engines.registry import DISABLED_ENGINE_TYPES, ENABLED_ENGINE_TYPES
from tools.course_compiler_demo.universal_core import AnswerContractV1


def contract(engine, grading=None):
    return AnswerContractV1(f"contract:{engine}", engine, grading or {})


def mc_contract(options=None):
    return contract("multiple_choice", {"options": options or [
        {"option_id": "A", "text": "one", "correct": True},
        {"option_id": "B", "text": "two", "correct": False},
    ]})


def test_registry_lookup_and_support_decision():
    registry = build_default_registry()
    for name in ENABLED_ENGINE_TYPES:
        assert registry.lookup(name).status == "SUPPORTED"
        assert registry.support_decision(contract(name)).status == "SUPPORTED"


def test_unknown_engine_is_rejected_without_fallback():
    registry = build_default_registry()
    unknown = contract("not_real")
    assert registry.lookup("not_real").status == "UNSUPPORTED"
    assert registry.normalize(1, unknown).status == "UNSUPPORTED"
    assert registry.grade(1, 1, unknown).status == "UNSUPPORTED"


@pytest.mark.parametrize("name", DISABLED_ENGINE_TYPES)
def test_registered_disabled_engines_fail_closed(name):
    registry = build_default_registry()
    answer_contract = contract(name)
    assert registry.descriptor(name).enabled is False
    assert registry.support_decision(answer_contract).status == "UNSUPPORTED"
    assert registry.derive({"independently_derived_answer": 1}, answer_contract).status == "UNSUPPORTED"


def test_numeric_scalar_independent_derivation_and_tolerance_grading():
    registry = build_default_registry()
    answer_contract = contract("numeric_scalar", {"absolute_tolerance": 0.05, "relative_tolerance": 0})
    derived = registry.derive({"independently_derived_answer": {"value": "2.50"}}, answer_contract)
    assert derived.status == "PASS" and derived.operation == "derive" and derived.value == 2.5
    assert registry.grade(2.54, derived.value, answer_contract).status == "PASS"
    assert registry.grade(2.56, derived.value, answer_contract).status == "FAIL"


def test_numeric_pair_preserves_order_and_requires_exact_arity():
    registry = build_default_registry()
    answer_contract = contract("numeric_pair")
    assert registry.normalize([4, -3], answer_contract).value == [4.0, -3.0]
    assert registry.grade([-3, 4], [4, -3], answer_contract).status == "FAIL"
    assert registry.normalize([1], answer_contract).status == "INVALID"
    assert registry.normalize([1, 2, 3], answer_contract).status == "INVALID"


def test_vector_component_normalization_and_shape_matching():
    registry = build_default_registry()
    answer_contract = contract("numeric_vector", {"absolute": 0.001})
    normalized = registry.normalize({"values": [{"value": "1"}, {"value": 2.0}, 3]}, answer_contract)
    assert normalized.value == [1.0, 2.0, 3.0]
    assert registry.grade([1, 2], [1, 2, 3], answer_contract).status == "INVALID"


def test_multiple_choice_completeness_and_exactly_one_correct():
    registry = build_default_registry()
    assert registry.grade("A", {"correct_option_id": "A"}, mc_contract()).status == "PASS"
    incomplete = mc_contract([{"option_id": "A", "text": "", "correct": True}, {"option_id": "B", "text": "b"}])
    assert registry.normalize("A", incomplete).status == "INVALID"
    two_correct = mc_contract([{"option_id": "A", "text": "a", "correct": True}, {"option_id": "B", "text": "b", "correct": True}])
    assert registry.normalize("A", two_correct).status == "INVALID"


def test_engine_results_are_deterministic_and_json_stable():
    registry = build_default_registry()
    answer_contract = contract("numeric_vector")
    first = registry.normalize([1, "2.0", 3.5], answer_contract).to_dict()
    second = registry.normalize([1, "2.0", 3.5], answer_contract).to_dict()
    assert first == second
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(second, sort_keys=True, separators=(",", ":"))


@pytest.mark.parametrize("bad", [True, "not-a-number", float("inf"), float("nan")])
def test_numeric_values_fail_closed(bad):
    assert build_default_registry().normalize(bad, contract("numeric_scalar")).status == "INVALID"


def test_negative_or_invalid_tolerance_fails_closed():
    registry = build_default_registry()
    assert registry.grade(1, 1, contract("numeric_scalar", {"absolute": -1})).status == "INVALID"


def test_engine_contract_mismatch_is_rejected():
    engine = build_default_registry().lookup("numeric_scalar").value
    assert engine.normalize(1, contract("numeric_pair")).status == "INVALID"
