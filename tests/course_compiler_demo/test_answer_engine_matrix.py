import json

import pytest

from tools.course_compiler_demo.answer_engines.matrix import MatrixAnswerEngine, register_matrix_engine
from tools.course_compiler_demo.answer_engines.registry import AnswerEngine, AnswerEngineRegistry
from tools.course_compiler_demo.universal_core import AnswerContractV1


def contract(kind="matrix", **grading):
    return AnswerContractV1("contract:matrix", "matrix", {"answer_kind": kind, **grading})


ENGINE = MatrixAnswerEngine()


@pytest.mark.parametrize("seed", range(40))
def test_exact_matrix_equality_cases(seed):
    matrix = [[seed, f"{seed + 1}/2"], [-seed, seed + 2]]
    normalized = ENGINE.normalize(matrix, contract())
    assert normalized.status == "PASS"
    assert ENGINE.grade(matrix, normalized.value, contract()).status == "PASS"


@pytest.mark.parametrize("seed", range(15))
def test_declared_tolerance_scalar_cases(seed):
    spec = contract("scalar", absolute_tolerance=0.01)
    assert ENGINE.grade(seed + 0.005, seed, spec).status == "PASS"


DERIVATIONS = [
    ({"operation": "addition", "left": [[1, 2], [3, 4]], "right": [[5, 6], [7, 8]]}, contract(), [[6, 8], [10, 12]]),
    ({"operation": "addition", "left": [["1/2"]], "right": [["1/3"]]}, contract(), [["5/6"]]),
    ({"operation": "scalar_multiplication", "scalar": 3, "matrix": [[1, -2]]}, contract(), [[3, -6]]),
    ({"operation": "scalar_multiplication", "scalar": "1/2", "matrix": [[1, 3]]}, contract(), [["1/2", "3/2"]]),
    ({"operation": "multiplication", "left": [[1, 2]], "right": [[3], [4]]}, contract(), [[11]]),
    ({"operation": "multiplication", "left": [[1, 0], [0, 1]], "right": [[2, 3], [4, 5]]}, contract(), [[2, 3], [4, 5]]),
    ({"operation": "determinant", "matrix": [[1]]}, contract("scalar"), 1),
    ({"operation": "determinant", "matrix": [[1, 2], [3, 4]]}, contract("scalar"), -2),
    ({"operation": "determinant", "matrix": [[1, 2, 3], [0, 4, 5], [0, 0, 6]]}, contract("scalar"), 24),
    ({"operation": "inverse", "matrix": [[1, 0], [0, 1]]}, contract("inverse"), [[1, 0], [0, 1]]),
    ({"operation": "inverse", "matrix": [[2, 0], [0, 4]]}, contract("inverse"), [["1/2", 0], [0, "1/4"]]),
    ({"operation": "rref", "matrix": [[1, 2], [2, 4]]}, contract("rref"), [[1, 2], [0, 0]]),
    ({"operation": "rref", "matrix": [[0, 1], [1, 0]]}, contract("rref"), [[1, 0], [0, 1]]),
    ({"operation": "solve", "coefficients": [[1, 0], [0, 1]], "constants": [3, 4]}, contract("solution_vector"), [3, 4]),
    ({"operation": "solve", "coefficients": [[2, 1], [1, -1]], "constants": [5, 1]}, contract("solution_vector"), [2, 1]),
    ({"operation": "solve", "coefficients": [[1]] , "constants": ["2/3"]}, contract("solution_vector"), ["2/3"]),
    ({"operation": "eigenvalues", "matrix": [[7]]}, contract("eigenvalues"), [7]),
    ({"operation": "eigenvalues", "matrix": [[2, 0], [0, 3]]}, contract("eigenvalues"), [2, 3]),
    ({"operation": "eigenvalues", "matrix": [[0, 1], [1, 0]]}, contract("eigenvalues"), [-1, 1]),
    ({"operation": "eigenvalues", "matrix": [[4, 1], [0, 4]]}, contract("eigenvalues"), [4, 4]),
]


@pytest.mark.parametrize("derivation,spec,expected", DERIVATIONS)
def test_independent_derivation_cases(derivation, spec, expected):
    result = ENGINE.derive(derivation, spec)
    assert result.status == "PASS"
    assert result.operation == "derive"
    assert ENGINE.grade(result.value, expected, spec).status == "PASS"


INVALID_CASES = [
    ("normalize", [], contract()),
    ("normalize", [[1], [1, 2]], contract()),
    ("normalize", [1, 2], contract()),
    ("normalize", [[True]], contract()),
    ("normalize", [[float("inf")]], contract()),
    ("normalize", [[float("nan")]], contract()),
    ("normalize", [["x"]], contract()),
    ("normalize", [[1] * 7], contract()),
    ("normalize", [[1]] * 7, contract()),
    ("normalize", [[1]], contract("unknown")),
    ("derive", {"operation": "addition", "left": [[1]], "right": [[1, 2]]}, contract()),
    ("derive", {"operation": "multiplication", "left": [[1, 2]], "right": [[1, 2]]}, contract()),
    ("derive", {"operation": "determinant", "matrix": [[1, 2]]}, contract("scalar")),
    ("derive", {"operation": "inverse", "matrix": [[1, 2], [2, 4]]}, contract("inverse")),
    ("derive", {"operation": "solve", "coefficients": [[1, 0], [0, 1]], "constants": [1]}, contract("solution_vector")),
    ("derive", {"operation": "solve", "coefficients": [[1, 1], [2, 2]], "constants": [1, 2]}, contract("solution_vector")),
    ("derive", {"operation": "eigenvalues", "matrix": [[0, -1], [1, 0]]}, contract("eigenvalues")),
    ("derive", {"operation": "eigenvalues", "matrix": [[1, 1], [1, 0]]}, contract("eigenvalues")),
    ("derive", {"operation": "eigenvalues", "matrix": [[1, 0, 0], [0, 2, 0], [0, 0, 3]]}, contract("eigenvalues")),
    ("derive", {"operation": "mystery"}, contract()),
    ("derive", None, contract()),
    ("grade", [[1]], contract(absolute_tolerance=-1)),
    ("grade", [[1]], contract(absolute_tolerance="bad")),
    ("normalize", {"value": None}, contract()),
    ("normalize", [], contract("solution_vector")),
]


@pytest.mark.parametrize("operation,payload,spec", INVALID_CASES)
def test_invalid_shapes_and_unsupported_cases(operation, payload, spec):
    if operation == "derive":
        result = ENGINE.derive(payload, spec)
    elif operation == "grade":
        result = ENGINE.grade([[1]], [[1]], spec)
    else:
        result = ENGINE.normalize(payload, spec)
    assert result.status in {"INVALID", "UNSUPPORTED"}
    assert result.engine_type == "matrix"
    assert result.reasons


def test_protocol_registration_support_and_no_fallback():
    assert isinstance(ENGINE, AnswerEngine)
    registry = AnswerEngineRegistry()
    register_matrix_engine(registry)
    assert registry.lookup("matrix").status == "SUPPORTED"
    assert registry.support_decision(contract()).status == "SUPPORTED"
    assert registry.lookup("numeric_scalar").status == "UNSUPPORTED"


def test_deterministic_normalization_and_serialization():
    first = ENGINE.normalize([["2/4", -0.0], [3, "4.50"]], contract()).to_dict()
    second = ENGINE.normalize([["1/2", 0], ["3", "9/2"]], contract()).to_dict()
    assert first == second
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(second, sort_keys=True, separators=(",", ":"))


def test_contract_mismatch_fails_closed():
    wrong = AnswerContractV1("wrong", "numeric_scalar", {})
    assert ENGINE.normalize([[1]], wrong).status == "INVALID"
    assert ENGINE.derive({"operation": "determinant", "matrix": [[1]]}, wrong).status == "INVALID"
    assert ENGINE.grade([[1]], [[1]], wrong).status == "INVALID"
