import pytest

from tools.course_compiler_demo.answer_engines.registry import AnswerEngineRegistry
from tools.course_compiler_demo.answer_engines.symbolic import (
    EquationSystemEngine, SymbolicExpressionEngine, register_symbolic_engines,
)
from tools.course_compiler_demo.universal_core import AnswerContractV1


def contract(kind):
    return AnswerContractV1(f"contract:{kind}", kind, {}, {"variable": "x"})


@pytest.mark.parametrize("left,right", [
    (f"(x+{n})*(x-{n})", f"x**2-{n*n}") for n in range(1, 26)
] + [(f"{n}*(x+1)", f"{n}*x+{n}") for n in range(1, 26)])
def test_fifty_symbolic_equivalences(left, right):
    result = SymbolicExpressionEngine().grade(left, right, contract("symbolic_expression"))
    assert result.status == "PASS" and result.value is True


@pytest.mark.parametrize("equation,solutions", [(f"{n}*x+{n}=0", ["-1"]) for n in range(1, 14)] + [
    (f"x**2-{n*n}=0", [f"-{n}", f"{n}"]) for n in range(1, 13)
])
def test_twenty_five_equation_cases(equation, solutions):
    result = EquationSystemEngine().derive({"equation": equation}, contract("equation_system"))
    assert result.status == "PASS" and result.value == solutions


@pytest.mark.parametrize("answer", [
    "sin(x)", "cos(x)", "sqrt(x)", "x**-1", "x**13", "x//2", "x%2", "x if x else 0",
    "True", "1.2", "y+1", "x[0]", "lambda: x", "__import__('os')", "x and 1", "[x]", "{x}",
    "x << 1", "x @ x", "x == 1", "", "(", "1/0", "x**(x)", "x**(1/2)",
])
def test_twenty_five_adversarial_forms_fail_closed(answer):
    result = SymbolicExpressionEngine().normalize(answer, contract("symbolic_expression"))
    assert result.status == "INVALID" and result.value is None and result.reasons


def test_domain_restrictions_are_preserved_and_required_for_equivalence():
    engine = SymbolicExpressionEngine(); c = contract("symbolic_expression")
    normalized = engine.normalize({"expression": "(x**2-1)/(x-1)", "domain_restrictions": [1]}, c)
    assert normalized.status == "PASS" and normalized.value["domain_restrictions"] == ["1"]
    assert engine.grade({"expression": "(x**2-1)/(x-1)", "domain_restrictions": [1]}, {"expression": "x+1", "domain_restrictions": []}, c).status == "FAIL"


def test_derivative_and_antiderivative_are_independently_derived():
    engine = SymbolicExpressionEngine(); c = contract("symbolic_expression")
    assert engine.derive({"operation": "derivative", "expression": "3*x**2+2*x+7"}, c).value["numerator"] == [[0, "2"], [1, "6"]]
    assert engine.derive({"operation": "antiderivative", "expression": "6*x+2"}, c).value["numerator"] == [[1, "2"], [2, "3"]]


def test_small_linear_system_and_solution_set_ordering():
    engine = EquationSystemEngine(); c = contract("equation_system")
    result = engine.derive({"equations": ["x+y=5", "x-y=1"], "variables": ["x", "y"]}, c)
    assert result.value == [{"x": "3", "y": "2"}]
    assert engine.grade([2, 1], [1, 2], c).status == "PASS"


def test_registry_registration_and_actual_engine_identity():
    registry = AnswerEngineRegistry(); register_symbolic_engines(registry)
    for kind in ("symbolic_expression", "equation_system"):
        assert registry.lookup(kind).status == "SUPPORTED"
        assert registry.support_decision(contract(kind)).status == "SUPPORTED"
        assert registry.normalize("x+1" if kind == "symbolic_expression" else [1], contract(kind)).engine_type == kind


def test_deterministic_normalization_under_reordering():
    engine = SymbolicExpressionEngine(); c = contract("symbolic_expression")
    values = [engine.normalize(expr, c).to_dict() for expr in ("x+2+x", "2+x+x", "x+x+2")]
    assert values[0] == values[1] == values[2]
