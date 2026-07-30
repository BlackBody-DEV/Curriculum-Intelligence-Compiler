"""Exact, deterministic matrix grading with bounded independent derivations."""

from __future__ import annotations

from fractions import Fraction
import math
from typing import Any, Mapping, Sequence

from tools.course_compiler_demo.answer_engines.registry import (
    AnswerEngineDescriptor,
    AnswerEngineRegistry,
    AnswerEngineResult,
)
from tools.course_compiler_demo.universal_core import AnswerContractV1


Number = Fraction
Matrix = list[list[Number]]
MAX_DIMENSION = 6


def _failure(operation: str, reason: str, status: str = "INVALID") -> AnswerEngineResult:
    return AnswerEngineResult(status, "matrix", operation, None, (reason,))


def _number(value: Any) -> Number:
    if isinstance(value, bool):
        raise ValueError("boolean is not a matrix number")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("matrix numbers must be finite")
        return Fraction(str(value))
    if isinstance(value, str):
        try:
            result = Fraction(value.strip())
        except (ValueError, ZeroDivisionError):
            raise ValueError("matrix numbers must be integers, decimals, or rationals") from None
        return result
    raise ValueError("matrix numbers must be integers, decimals, or rationals")


def _matrix(value: Any, *, square: bool = False) -> Matrix:
    if isinstance(value, Mapping):
        value = value.get("matrix", value.get("value"))
    if not isinstance(value, (list, tuple)) or not value or len(value) > MAX_DIMENSION:
        raise ValueError(f"matrix must have 1 to {MAX_DIMENSION} rows")
    if any(not isinstance(row, (list, tuple)) for row in value):
        raise ValueError("matrix rows must be ordered sequences")
    width = len(value[0])
    if width < 1 or width > MAX_DIMENSION or any(len(row) != width for row in value):
        raise ValueError("matrix must be nonempty, rectangular, and bounded")
    result = [[_number(item) for item in row] for row in value]
    if square and len(result) != width:
        raise ValueError("operation requires a square matrix")
    return result


def _canonical_number(value: Number) -> int | str:
    return value.numerator if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _canonical_matrix(value: Matrix) -> list[list[int | str]]:
    return [[_canonical_number(item) for item in row] for row in value]


def _determinant(matrix: Matrix) -> Number:
    work = [row[:] for row in matrix]
    result = Fraction(1)
    for column in range(len(work)):
        pivot = next((row for row in range(column, len(work)) if work[row][column]), None)
        if pivot is None:
            return Fraction(0)
        if pivot != column:
            work[column], work[pivot] = work[pivot], work[column]
            result = -result
        pivot_value = work[column][column]
        result *= pivot_value
        for row in range(column + 1, len(work)):
            factor = work[row][column] / pivot_value
            for col in range(column + 1, len(work)):
                work[row][col] -= factor * work[column][col]
    return result


def _rref(matrix: Matrix) -> tuple[Matrix, tuple[int, ...]]:
    work = [row[:] for row in matrix]
    pivot_row = 0
    pivots: list[int] = []
    for column in range(len(work[0])):
        pivot = next((row for row in range(pivot_row, len(work)) if work[row][column]), None)
        if pivot is None:
            continue
        work[pivot_row], work[pivot] = work[pivot], work[pivot_row]
        scale = work[pivot_row][column]
        work[pivot_row] = [item / scale for item in work[pivot_row]]
        for row in range(len(work)):
            if row != pivot_row and work[row][column]:
                factor = work[row][column]
                work[row] = [a - factor * b for a, b in zip(work[row], work[pivot_row])]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(work):
            break
    return work, tuple(pivots)


def _inverse(matrix: Matrix) -> Matrix:
    size = len(matrix)
    augmented = [row[:] + [Fraction(i == j) for j in range(size)] for i, row in enumerate(matrix)]
    reduced, pivots = _rref(augmented)
    if pivots[:size] != tuple(range(size)):
        raise ValueError("matrix is singular and has no inverse")
    return [row[size:] for row in reduced]


def _multiply(left: Matrix, right: Matrix) -> Matrix:
    if len(left[0]) != len(right):
        raise ValueError("matrix multiplication dimensions are incompatible")
    return [[sum((left[i][k] * right[k][j] for k in range(len(right))), Fraction())
             for j in range(len(right[0]))] for i in range(len(left))]


def _tolerances(contract: AnswerContractV1) -> tuple[float, float]:
    spec = contract.grading_contract
    try:
        absolute = float(spec.get("absolute_tolerance", spec.get("absolute", 0)))
        relative = float(spec.get("relative_tolerance", spec.get("relative", 0)))
    except (TypeError, ValueError):
        raise ValueError("tolerances must be finite nonnegative numbers") from None
    if not math.isfinite(absolute) or not math.isfinite(relative) or absolute < 0 or relative < 0:
        raise ValueError("tolerances must be finite nonnegative numbers")
    return absolute, relative


def _close(actual: Number, expected: Number, tolerances: tuple[float, float]) -> bool:
    absolute, relative = tolerances
    if not absolute and not relative:
        return actual == expected
    a, e = float(actual), float(expected)
    return abs(a - e) <= max(absolute, relative * abs(e))


class MatrixAnswerEngine:
    """AnswerEngine adapter for matrices and uniquely solvable linear systems."""

    engine_type = "matrix"
    engine_id = "axiomiq.matrix"
    engine_version = "1.0.0"
    supported_answer_contracts = ("matrix",)

    def _contract_error(self, contract: AnswerContractV1, operation: str) -> AnswerEngineResult | None:
        if not isinstance(contract, AnswerContractV1) or contract.engine_type != self.engine_type:
            return _failure(operation, "answer contract does not match matrix engine")
        return None

    def normalize(self, answer: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._contract_error(contract, "normalize"):
            return invalid
        kind = contract.grading_contract.get("answer_kind", "matrix")
        try:
            if kind in ("matrix", "inverse", "rref"):
                value: Any = _canonical_matrix(_matrix(answer))
            elif kind == "scalar":
                raw = answer.get("value") if isinstance(answer, Mapping) else answer
                value = _canonical_number(_number(raw))
            elif kind in ("solution_vector", "eigenvalues"):
                raw = answer.get("values", answer.get("value")) if isinstance(answer, Mapping) else answer
                if not isinstance(raw, (list, tuple)) or not raw or len(raw) > MAX_DIMENSION:
                    raise ValueError("answer requires a bounded nonempty numeric vector")
                numbers = [_number(item) for item in raw]
                if kind == "eigenvalues":
                    numbers.sort()
                value = [_canonical_number(item) for item in numbers]
            else:
                return _failure("normalize", f"unsupported matrix answer kind: {kind}", "UNSUPPORTED")
        except ValueError as exc:
            return _failure("normalize", str(exc))
        return AnswerEngineResult("PASS", self.engine_type, "normalize", value)

    def derive(self, derivation_input: Mapping[str, Any], contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._contract_error(contract, "derive"):
            return invalid
        if not isinstance(derivation_input, Mapping):
            return _failure("derive", "derivation input must be a mapping")
        operation = derivation_input.get("operation")
        try:
            if operation == "addition":
                left, right = _matrix(derivation_input.get("left")), _matrix(derivation_input.get("right"))
                if (len(left), len(left[0])) != (len(right), len(right[0])):
                    raise ValueError("matrix addition requires equal shapes")
                raw: Any = [[a + b for a, b in zip(lrow, rrow)] for lrow, rrow in zip(left, right)]
            elif operation == "scalar_multiplication":
                matrix, scalar = _matrix(derivation_input.get("matrix")), _number(derivation_input.get("scalar"))
                raw = [[scalar * item for item in row] for row in matrix]
            elif operation == "multiplication":
                raw = _multiply(_matrix(derivation_input.get("left")), _matrix(derivation_input.get("right")))
            elif operation == "determinant":
                raw = _determinant(_matrix(derivation_input.get("matrix"), square=True))
            elif operation == "inverse":
                raw = _inverse(_matrix(derivation_input.get("matrix"), square=True))
            elif operation == "rref":
                raw = _rref(_matrix(derivation_input.get("matrix")))[0]
            elif operation == "solve":
                coefficients = _matrix(derivation_input.get("coefficients"), square=True)
                constants = derivation_input.get("constants")
                if not isinstance(constants, (list, tuple)) or len(constants) != len(coefficients):
                    raise ValueError("linear system constants must match coefficient rows")
                augmented = [row + [_number(constants[i])] for i, row in enumerate(coefficients)]
                reduced, pivots = _rref(augmented)
                if pivots[:len(coefficients)] != tuple(range(len(coefficients))):
                    raise ValueError("linear system must have one unique solution")
                raw = [row[-1] for row in reduced]
            elif operation == "eigenvalues":
                matrix = _matrix(derivation_input.get("matrix"), square=True)
                if len(matrix) == 1:
                    raw = [matrix[0][0]]
                elif len(matrix) == 2:
                    trace = matrix[0][0] + matrix[1][1]
                    discriminant = trace * trace - 4 * _determinant(matrix)
                    root = math.isqrt(discriminant.numerator)
                    denominator_root = math.isqrt(discriminant.denominator)
                    if root * root != discriminant.numerator or denominator_root * denominator_root != discriminant.denominator:
                        raise ValueError("only rational real eigenvalues are supported")
                    square_root = Fraction(root, denominator_root)
                    raw = [(trace - square_root) / 2, (trace + square_root) / 2]
                else:
                    raise ValueError("eigenvalue derivation is bounded to 1x1 and 2x2 matrices")
            else:
                return _failure("derive", f"unsupported matrix derivation operation: {operation}", "UNSUPPORTED")
        except (ValueError, TypeError) as exc:
            return _failure("derive", str(exc))
        normalized = self.normalize(raw, contract)
        return AnswerEngineResult(normalized.status, self.engine_type, "derive", normalized.value, normalized.reasons)

    def grade(self, response: Any, expected: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._contract_error(contract, "grade"):
            return invalid
        actual, target = self.normalize(response, contract), self.normalize(expected, contract)
        if actual.status != "PASS" or target.status != "PASS":
            reasons = actual.reasons + target.reasons
            return _failure("grade", "; ".join(reasons) or "answers must be valid")
        try:
            tolerances = _tolerances(contract)
            kind = contract.grading_contract.get("answer_kind", "matrix")
            if kind in ("matrix", "inverse", "rref"):
                if len(actual.value) != len(target.value) or any(len(a) != len(e) for a, e in zip(actual.value, target.value)):
                    passed = False
                else:
                    passed = all(_close(_number(a), _number(e), tolerances)
                                 for arow, erow in zip(actual.value, target.value) for a, e in zip(arow, erow))
            elif kind == "scalar":
                passed = _close(_number(actual.value), _number(target.value), tolerances)
            else:
                passed = len(actual.value) == len(target.value) and all(
                    _close(_number(a), _number(e), tolerances) for a, e in zip(actual.value, target.value))
        except ValueError as exc:
            return _failure("grade", str(exc))
        return AnswerEngineResult("PASS" if passed else "FAIL", self.engine_type, "grade", passed)


def register_matrix_engine(registry: AnswerEngineRegistry) -> None:
    """Register this lane's engine in a registry during synthesis wiring."""

    engine = MatrixAnswerEngine()
    registry.register(AnswerEngineDescriptor(engine.engine_type, True, "implemented and validated"), engine)
