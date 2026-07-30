"""Exact, dependency-free symbolic engines for a deliberately bounded grammar."""

from __future__ import annotations

import ast
from fractions import Fraction
from math import isqrt
from typing import Any, Mapping

from tools.course_compiler_demo.answer_engines.registry import (
    AnswerEngineDescriptor, AnswerEngineRegistry, AnswerEngineResult,
)
from tools.course_compiler_demo.universal_core import AnswerContractV1

Poly = dict[int, Fraction]
Rat = tuple[Poly, Poly]


def _fail(engine: str, operation: str, reason: str, status: str = "INVALID") -> AnswerEngineResult:
    return AnswerEngineResult(status, engine, operation, None, (reason,))


def _trim(p: Poly) -> Poly:
    return {k: v for k, v in p.items() if v}


def _add(a: Poly, b: Poly) -> Poly:
    out = dict(a)
    for degree, coefficient in b.items(): out[degree] = out.get(degree, Fraction()) + coefficient
    return _trim(out)


def _mul(a: Poly, b: Poly) -> Poly:
    out: Poly = {}
    for i, x in a.items():
        for j, y in b.items(): out[i + j] = out.get(i + j, Fraction()) + x * y
    return _trim(out)


def _scale(p: Poly, value: Fraction) -> Poly:
    return _trim({k: v * value for k, v in p.items()})


def _radd(a: Rat, b: Rat) -> Rat: return _add(_mul(a[0], b[1]), _mul(b[0], a[1])), _mul(a[1], b[1])
def _rmul(a: Rat, b: Rat) -> Rat: return _mul(a[0], b[0]), _mul(a[1], b[1])


def _parse(text: str, variable: str = "x") -> Rat:
    if not isinstance(text, str) or not text.strip() or len(text) > 500: raise ValueError("a bounded expression string is required")
    try: root = ast.parse(text.strip(), mode="eval").body
    except SyntaxError as exc: raise ValueError("malformed expression") from exc
    def walk(node: ast.AST) -> Rat:
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool): return (_trim({0: Fraction(node.value)}), {0: Fraction(1)})
        if isinstance(node, ast.Name) and node.id == variable: return ({1: Fraction(1)}, {0: Fraction(1)})
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            n, d = walk(node.operand); return (_scale(n, Fraction(-1)) if isinstance(node.op, ast.USub) else n, d)
        if isinstance(node, ast.BinOp):
            left, right = walk(node.left), walk(node.right)
            if isinstance(node.op, ast.Add): return _radd(left, right)
            if isinstance(node.op, ast.Sub): return _radd(left, (_scale(right[0], Fraction(-1)), right[1]))
            if isinstance(node.op, ast.Mult): return _rmul(left, right)
            if isinstance(node.op, ast.Div):
                if not right[0]: raise ValueError("division by zero")
                return _rmul(left, (right[1], right[0]))
            if isinstance(node.op, ast.Pow):
                if right[1] != {0: Fraction(1)} or set(right[0]) - {0}: raise ValueError("integer exponent required")
                exponent = right[0].get(0, Fraction())
                if exponent.denominator != 1 or not 0 <= exponent <= 12: raise ValueError("exponent must be an integer from 0 through 12")
                out: Rat = ({0: Fraction(1)}, {0: Fraction(1)})
                for _ in range(exponent.numerator): out = _rmul(out, left)
                return out
        raise ValueError("unsupported function or expression form")
    result = walk(root)
    if max(result[0] or {0}) > 20 or max(result[1] or {0}) > 20: raise ValueError("polynomial degree exceeds 20")
    return result


def _f(value: Fraction) -> str: return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
def _poly_value(p: Poly) -> list[list[Any]]: return [[degree, _f(p[degree])] for degree in sorted(p)]
def _equivalent(a: Rat, b: Rat) -> bool: return _mul(a[0], b[1]) == _mul(b[0], a[1])


def _restrictions(answer: Any) -> tuple[str, ...]:
    raw = answer.get("domain_restrictions", []) if isinstance(answer, Mapping) else []
    if not isinstance(raw, (list, tuple)) or any(isinstance(x, bool) for x in raw): raise ValueError("domain_restrictions must be a list")
    values: list[Fraction] = []
    for item in raw:
        try: values.append(Fraction(str(item)))
        except (ValueError, ZeroDivisionError) as exc: raise ValueError("domain restrictions must be rational constants") from exc
    return tuple(_f(x) for x in sorted(set(values)))


class SymbolicExpressionEngine:
    engine_type = "symbolic_expression"
    engine_id = "axiomiq.symbolic_expression"
    engine_version = "1.0"
    supported_answer_contracts = ("exact_expression", "derivative", "antiderivative")

    def _valid(self, contract: AnswerContractV1, operation: str) -> AnswerEngineResult | None:
        if not isinstance(contract, AnswerContractV1) or contract.engine_type != self.engine_type: return _fail(self.engine_type, operation, "answer contract does not match engine")
        return None

    def normalize(self, answer: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._valid(contract, "normalize"): return invalid
        expression = answer.get("expression") if isinstance(answer, Mapping) else answer
        variable = str(contract.normalization_contract.get("variable", "x"))
        if not variable.isidentifier(): return _fail(self.engine_type, "normalize", "variable must be an identifier")
        try:
            numerator, denominator = _parse(expression, variable)
            restrictions = _restrictions(answer)
        except (TypeError, ValueError) as exc: return _fail(self.engine_type, "normalize", str(exc))
        value = {"denominator": _poly_value(denominator), "domain_restrictions": list(restrictions), "numerator": _poly_value(numerator), "variable": variable}
        return AnswerEngineResult("PASS", self.engine_type, "normalize", value)

    def grade(self, response: Any, expected: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._valid(contract, "grade"): return invalid
        variable = str(contract.normalization_contract.get("variable", "x"))
        try:
            actual_expr = response.get("expression") if isinstance(response, Mapping) else response
            target_expr = expected.get("expression") if isinstance(expected, Mapping) else expected
            passed = _equivalent(_parse(actual_expr, variable), _parse(target_expr, variable)) and _restrictions(response) == _restrictions(expected)
        except (TypeError, ValueError) as exc: return _fail(self.engine_type, "grade", str(exc))
        return AnswerEngineResult("PASS" if passed else "FAIL", self.engine_type, "grade", passed)

    def derive(self, derivation_input: Mapping[str, Any], contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._valid(contract, "derive"): return invalid
        if not isinstance(derivation_input, Mapping): return _fail(self.engine_type, "derive", "derivation input must be a mapping")
        variable = str(contract.normalization_contract.get("variable", "x")); operation = derivation_input.get("operation")
        try:
            if operation == "recurrence_step":
                current=Fraction(str(derivation_input.get("current"))); increment=Fraction(str(derivation_input.get("increment")))
                result={0:current+increment}; denominator={0:Fraction(1)}
            else:
                numerator, denominator = _parse(derivation_input.get("expression"), variable)
                if denominator != {0: Fraction(1)}: raise ValueError("derivation currently requires a polynomial")
                if operation == "derivative": result = {d - 1: c * d for d, c in numerator.items() if d}
                elif operation == "antiderivative":
                    if max(numerator or {0}) >= 20: raise ValueError("antiderivative degree exceeds bound")
                    result = {d + 1: c / (d + 1) for d, c in numerator.items()}
                elif operation == "linear_root":
                    root=_solve_linear(numerator)[0]; result,denominator=_parse(str(root),variable)
                else: raise ValueError("operation must be derivative, antiderivative, linear_root, or recurrence_step")
        except (TypeError, ValueError) as exc: return _fail(self.engine_type, "derive", str(exc))
        value = {"denominator": _poly_value(denominator), "domain_restrictions": [], "numerator": _poly_value(result), "variable": variable}
        return AnswerEngineResult("PASS", self.engine_type, "derive", value)


def _solve_linear(poly: Poly) -> tuple[Fraction, ...]:
    if max(poly or {0}) > 1 or not poly.get(1): raise ValueError("equation must have one unique linear solution")
    return (-poly.get(0, Fraction()) / poly[1],)


def _linear_form(text: str, variables: tuple[str, ...]) -> tuple[list[Fraction], Fraction]:
    """Parse a linear expression as coefficients and constant."""
    try: root = ast.parse(text, mode="eval").body
    except (SyntaxError, TypeError) as exc: raise ValueError("malformed linear expression") from exc
    def walk(node: ast.AST) -> tuple[list[Fraction], Fraction]:
        if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool): return [Fraction()] * len(variables), Fraction(node.value)
        if isinstance(node, ast.Name) and node.id in variables:
            row = [Fraction()] * len(variables); row[variables.index(node.id)] = Fraction(1); return row, Fraction()
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            row, const = walk(node.operand); scale = -1 if isinstance(node.op, ast.USub) else 1
            return [scale*x for x in row], scale*const
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
            ar, ac = walk(node.left); br, bc = walk(node.right); scale = -1 if isinstance(node.op, ast.Sub) else 1
            return [x + scale*y for x, y in zip(ar, br)], ac + scale*bc
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mult, ast.Div)):
            ar, ac = walk(node.left); br, bc = walk(node.right)
            if any(ar) and any(br): raise ValueError("nonlinear system term")
            if isinstance(node.op, ast.Div):
                if any(br) or not bc: raise ValueError("division requires a nonzero integer constant")
                return [x/bc for x in ar], ac/bc
            if any(ar): return [x*bc for x in ar], ac*bc
            if any(br): return [x*ac for x in br], bc*ac
            return [Fraction()] * len(variables), ac*bc
        raise ValueError("unsupported linear-system expression")
    return walk(root)


def _solve_system(equations: list[str], variables: tuple[str, ...]) -> dict[str, str]:
    if not 1 <= len(variables) <= 3 or len(equations) != len(variables) or len(set(variables)) != len(variables): raise ValueError("a square system of one through three unique variables is required")
    matrix: list[list[Fraction]] = []
    for equation in equations:
        if not isinstance(equation, str) or equation.count("=") != 1: raise ValueError("each equation requires one equals sign")
        left, right = equation.split("="); lr, lc = _linear_form(left, variables); rr, rc = _linear_form(right, variables)
        matrix.append([x-y for x, y in zip(lr, rr)] + [rc-lc])
    n = len(variables)
    for column in range(n):
        pivot = next((row for row in range(column, n) if matrix[row][column]), None)
        if pivot is None: raise ValueError("system does not have one unique solution")
        matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
        divisor = matrix[column][column]; matrix[column] = [x/divisor for x in matrix[column]]
        for row in range(n):
            if row != column:
                factor = matrix[row][column]; matrix[row] = [x-factor*y for x, y in zip(matrix[row], matrix[column])]
    return {variable: _f(matrix[i][-1]) for i, variable in enumerate(variables)}


class EquationSystemEngine:
    engine_type = "equation_system"
    engine_id = "axiomiq.equation_system"
    engine_version = "1.0"
    supported_answer_contracts = ("linear_equation", "quadratic_equation", "linear_system")

    def _valid(self, contract: AnswerContractV1, operation: str) -> AnswerEngineResult | None:
        if not isinstance(contract, AnswerContractV1) or contract.engine_type != self.engine_type: return _fail(self.engine_type, operation, "answer contract does not match engine")
        return None

    def normalize(self, answer: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._valid(contract, "normalize"): return invalid
        raw = answer.get("solutions") if isinstance(answer, Mapping) else answer
        if not isinstance(raw, (list, tuple)): return _fail(self.engine_type, "normalize", "solutions must be a list")
        try:
            if raw and isinstance(raw[0], Mapping):
                rows = sorted(tuple((str(k), _f(Fraction(str(v)))) for k, v in sorted(row.items())) for row in raw)
                value: Any = [dict(row) for row in rows]
            else: value = [_f(x) for x in sorted({Fraction(str(item)) for item in raw})]
        except (ValueError, ZeroDivisionError): return _fail(self.engine_type, "normalize", "solutions must contain exact rational values")
        return AnswerEngineResult("PASS", self.engine_type, "normalize", value)

    def grade(self, response: Any, expected: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._valid(contract, "grade"): return invalid
        actual, target = self.normalize(response, contract), self.normalize(expected, contract)
        if actual.status != "PASS" or target.status != "PASS": return _fail(self.engine_type, "grade", "response and expected solution sets must be valid")
        passed = actual.value == target.value
        return AnswerEngineResult("PASS" if passed else "FAIL", self.engine_type, "grade", passed)

    def derive(self, derivation_input: Mapping[str, Any], contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._valid(contract, "derive"): return invalid
        if not isinstance(derivation_input, Mapping): return _fail(self.engine_type, "derive", "derivation input must be a mapping")
        try:
            if "equations" in derivation_input:
                equations = derivation_input["equations"]; variables = tuple(derivation_input.get("variables", ()))
                if not isinstance(equations, list) or not all(isinstance(v, str) and v.isidentifier() for v in variables): raise ValueError("equations list and identifier variables are required")
                return AnswerEngineResult("PASS", self.engine_type, "derive", [_solve_system(equations, variables)])
            equation = derivation_input.get("equation")
            if not isinstance(equation, str) or equation.count("=") != 1: raise ValueError("one equation with one equals sign is required")
            left, right = equation.split("="); a, b = _parse(left), _parse(right)
            if a[1] != {0: Fraction(1)} or b[1] != {0: Fraction(1)}: raise ValueError("equation derivation requires polynomials")
            polynomial = _add(a[0], _scale(b[0], Fraction(-1))); degree = max(polynomial or {0})
            if degree <= 1: solutions = _solve_linear(polynomial)
            elif degree == 2:
                aa, bb, cc = polynomial[2], polynomial.get(1, Fraction()), polynomial.get(0, Fraction())
                disc = bb * bb - 4 * aa * cc
                if disc < 0: solutions = ()
                else:
                    nroot, droot = isqrt(disc.numerator), isqrt(disc.denominator)
                    if nroot*nroot != disc.numerator or droot*droot != disc.denominator: raise ValueError("quadratic has unsupported irrational roots")
                    root = Fraction(nroot, droot); solutions = tuple(sorted({(-bb-root)/(2*aa), (-bb+root)/(2*aa)}))
            else: raise ValueError("only linear and quadratic equations are supported")
        except (TypeError, ValueError, ZeroDivisionError) as exc: return _fail(self.engine_type, "derive", str(exc))
        return AnswerEngineResult("PASS", self.engine_type, "derive", [_f(x) for x in solutions])


def register_symbolic_engines(registry: AnswerEngineRegistry) -> None:
    """Enable both adapters in a caller-owned registry without altering global defaults."""
    for engine in (SymbolicExpressionEngine(), EquationSystemEngine()):
        registry.register(AnswerEngineDescriptor(engine.engine_type, True, f"{engine.engine_id} {engine.engine_version}"), engine)
