"""Bounded, dependency-free chemical formula and reaction answer engines."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import reduce
from math import gcd, isfinite
import re
from typing import Any, Mapping

from tools.course_compiler_demo.answer_engines.registry import (
    AnswerEngineDescriptor, AnswerEngineRegistry, AnswerEngineResult,
)
from tools.course_compiler_demo.universal_core import AnswerContractV1


ENGINE_VERSION = "1.0"
# IUPAC symbols through oganesson. Atomic weights are conventional abridged values.
_SYMBOLS = "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og".split()
_ELEMENTS = frozenset(_SYMBOLS)
_WEIGHTS = dict(zip(_SYMBOLS, [
    1.008,4.0026,6.94,9.0122,10.81,12.011,14.007,15.999,18.998,20.180,
    22.990,24.305,26.982,28.085,30.974,32.06,35.45,39.948,39.098,40.078,
    44.956,47.867,50.942,51.996,54.938,55.845,58.933,58.693,63.546,65.38,
    69.723,72.630,74.922,78.971,79.904,83.798,85.468,87.62,88.906,91.224,
    92.906,95.95,98,101.07,102.91,106.42,107.87,112.41,114.82,118.71,
    121.76,127.60,126.90,131.29,132.91,137.33,138.91,140.12,140.91,144.24,
    145,150.36,151.96,157.25,158.93,162.50,164.93,167.26,168.93,173.05,
    174.97,178.49,180.95,183.84,186.21,190.23,192.22,195.08,196.97,200.59,
    204.38,207.2,208.98,209,210,222,223,226,227,232.04,231.04,238.03,
    237,244,243,247,247,251,252,257,258,259,266,267,268,269,270,269,
    281,282,285,286,289,290,293,294,294
]))
_PHASE = re.compile(r"\((?:aq|s|l|g)\)$", re.I)


class ChemistryError(ValueError):
    """A structured, student-safe rejection of an unsupported chemistry input."""


def _failure(engine: str, operation: str, reason: str, status: str = "INVALID") -> AnswerEngineResult:
    return AnswerEngineResult(status, engine, operation, None, (reason,))


def _contract(contract: Any, engine: str, operation: str) -> AnswerEngineResult | None:
    if not isinstance(contract, AnswerContractV1) or contract.engine_type != engine:
        return _failure(engine, operation, "answer contract does not match engine")
    return None


def _merge(target: dict[str, int], source: Mapping[str, int], multiplier: int = 1) -> None:
    for symbol, count in source.items():
        target[symbol] = target.get(symbol, 0) + count * multiplier


def parse_formula(text: str) -> dict[str, int]:
    """Parse a neutral formula with (), [] and bounded hydrate-dot segments."""
    if not isinstance(text, str) or not text.strip():
        raise ChemistryError("formula must be a nonempty string")
    formula = _PHASE.sub("", text.strip()).replace("·", ".")
    if len(formula) > 200 or any(c.isspace() for c in formula):
        raise ChemistryError("formula is outside the bounded syntax")
    total: dict[str, int] = {}
    for segment_index, segment in enumerate(formula.split(".")):
        if not segment:
            raise ChemistryError("empty hydrate segment")
        match = re.match(r"([1-9][0-9]*)(?=[A-Z[(])", segment)
        if match and segment_index == 0:
            raise ChemistryError("a standalone formula cannot have a leading coefficient")
        multiplier = int(match.group(1)) if match else 1
        if multiplier > 10_000:
            raise ChemistryError("count exceeds bounded limit")
        body = segment[match.end():] if match else segment
        stack: list[dict[str, int]] = [{}]
        closers: list[str] = []
        i = 0
        while i < len(body):
            char = body[i]
            if char in "([":
                if len(stack) >= 9:
                    raise ChemistryError("group nesting exceeds bounded limit")
                stack.append({}); closers.append(")" if char == "(" else "]"); i += 1
            elif char in ")]":
                if not closers or char != closers.pop():
                    raise ChemistryError("mismatched group delimiter")
                group = stack.pop(); i += 1
                number = re.match(r"[0-9]+", body[i:])
                factor = int(number.group()) if number else 1
                if (number and number.group().startswith("0")) or factor < 1 or factor > 10_000 or not group:
                    raise ChemistryError("invalid group count")
                i += len(number.group()) if number else 0
                _merge(stack[-1], group, factor)
            elif char.isupper():
                symbol_match = re.match(r"[A-Z][a-z]?", body[i:])
                assert symbol_match
                symbol = symbol_match.group(); i += len(symbol)
                if symbol not in _ELEMENTS:
                    raise ChemistryError(f"unknown element symbol: {symbol}")
                number = re.match(r"[0-9]+", body[i:])
                count = int(number.group()) if number else 1
                if (number and number.group().startswith("0")) or count < 1 or count > 10_000:
                    raise ChemistryError("invalid element count")
                i += len(number.group()) if number else 0
                stack[-1][symbol] = stack[-1].get(symbol, 0) + count
            else:
                raise ChemistryError(f"unexpected formula token: {char}")
        if closers:
            raise ChemistryError("unclosed group delimiter")
        _merge(total, stack[0], multiplier)
    if not total or sum(total.values()) > 100_000:
        raise ChemistryError("formula atom count exceeds bounded limit")
    return dict(sorted(total.items()))


def empirical_counts(counts: Mapping[str, int]) -> dict[str, int]:
    divisor = reduce(gcd, counts.values())
    return {key: value // divisor for key, value in sorted(counts.items())}


def canonical_formula(counts: Mapping[str, int]) -> str:
    keys = list(counts)
    order = (["C"] if "C" in counts else []) + (["H"] if "C" in counts and "H" in counts else [])
    order += sorted(key for key in keys if key not in order)
    return "".join(key + (str(counts[key]) if counts[key] != 1 else "") for key in order)


def molar_mass(counts: Mapping[str, int]) -> float:
    return round(sum(_WEIGHTS[symbol] * count for symbol, count in counts.items()), 6)


@dataclass(frozen=True)
class Species:
    formula: str
    counts: dict[str, int]
    charge: int = 0


def parse_species(text: str) -> Species:
    raw = _PHASE.sub("", text.strip())
    charge = 0
    match = re.search(r"\^([1-9][0-9]*)?([+-])$", raw)
    if match:
        charge = (int(match.group(1)) if match.group(1) else 1) * (1 if match.group(2) == "+" else -1)
        raw = raw[:match.start()]
    elif raw.endswith(("+", "-")):
        charge = 1 if raw[-1] == "+" else -1; raw = raw[:-1]
    return Species(canonical_formula(parse_formula(raw)), parse_formula(raw), charge)


def _split_side(side: str) -> list[tuple[int, Species]]:
    # A plus separator must have surrounding whitespace, avoiding ionic charge signs.
    pieces = re.split(r"\s+\+\s+", side.strip())
    if not pieces or any(not piece for piece in pieces) or len(pieces) > 12:
        raise ChemistryError("reaction side is invalid or exceeds 12 species")
    result = []
    for piece in pieces:
        match = re.match(r"([1-9][0-9]*)\s*(?=[A-Z[(])", piece)
        coefficient = int(match.group(1)) if match else 1
        if coefficient > 10_000:
            raise ChemistryError("coefficient exceeds bounded limit")
        result.append((coefficient, parse_species(piece[match.end():] if match else piece)))
    return result


def parse_reaction(text: str) -> tuple[list[tuple[int, Species]], list[tuple[int, Species]]]:
    if not isinstance(text, str) or len(text) > 1000:
        raise ChemistryError("reaction must be a bounded string")
    arrows = re.findall(r"(?:->|→|=)", text)
    if len(arrows) != 1:
        raise ChemistryError("reaction requires exactly one arrow")
    left, right = re.split(r"(?:->|→|=)", text)
    return _split_side(left), _split_side(right)


def _vectors(reaction, conserve_charge: bool):
    left, right = reaction
    elements = sorted({e for _, species in left + right for e in species.counts})
    rows = []
    for element in elements:
        rows.append([Fraction(sign * species.counts.get(element, 0)) for sign, side in ((1, left), (-1, right)) for _, species in side])
    if conserve_charge:
        rows.append([Fraction(sign * species.charge) for sign, side in ((1, left), (-1, right)) for _, species in side])
    return rows


def balance_reaction(text: str, conserve_charge: bool = False) -> tuple[int, ...]:
    reaction = parse_reaction(text); rows = _vectors(reaction, conserve_charge)
    columns = len(rows[0]); matrix = [row[:] for row in rows]; pivots = []; r = 0
    for c in range(columns):
        pivot = next((i for i in range(r, len(matrix)) if matrix[i][c]), None)
        if pivot is None: continue
        matrix[r], matrix[pivot] = matrix[pivot], matrix[r]
        scale = matrix[r][c]; matrix[r] = [x / scale for x in matrix[r]]
        for i in range(len(matrix)):
            if i != r and matrix[i][c]:
                factor = matrix[i][c]; matrix[i] = [a - factor * b for a, b in zip(matrix[i], matrix[r])]
        pivots.append(c); r += 1
        if r == len(matrix): break
    free = [c for c in range(columns) if c not in pivots]
    if len(free) != 1:
        raise ChemistryError("reaction has no unique bounded stoichiometric balance")
    solution = [Fraction(0) for _ in range(columns)]; solution[free[0]] = 1
    for row_index in range(len(pivots) - 1, -1, -1):
        pivot = pivots[row_index]
        solution[pivot] = -sum(matrix[row_index][j] * solution[j] for j in free)
    lcm = 1
    for value in solution: lcm = lcm * value.denominator // gcd(lcm, value.denominator)
    integers = [int(value * lcm) for value in solution]
    if all(value < 0 for value in integers): integers = [-value for value in integers]
    if any(value <= 0 for value in integers):
        raise ChemistryError("reaction cannot be balanced with positive coefficients")
    divisor = reduce(gcd, integers); normalized = tuple(value // divisor for value in integers)
    if max(normalized) > 10_000:
        raise ChemistryError("balanced coefficients exceed bounded limit")
    return normalized


def _reaction_value(text: str, conserve_charge: bool) -> dict[str, Any]:
    left, right = parse_reaction(text)
    supplied = tuple(coef for coef, _ in left + right)
    balanced = balance_reaction(text, conserve_charge)
    divisor = reduce(gcd, supplied)
    supplied_normal = tuple(value // divisor for value in supplied)
    if supplied_normal != balanced:
        raise ChemistryError("supplied reaction coefficients do not conserve atoms and declared charge")
    split = len(left)
    species = [item.formula for _, item in left + right]
    rendered = " + ".join((str(c) if c != 1 else "") + s for c, s in zip(balanced[:split], species[:split]))
    rendered += " -> " + " + ".join((str(c) if c != 1 else "") + s for c, s in zip(balanced[split:], species[split:]))
    return {"coefficients": list(balanced), "reaction": rendered, "split_index": split}


class ChemicalFormulaEngine:
    engine_type = "chemical_formula"
    engine_id = "axiomiq.chemical_formula"
    engine_version = ENGINE_VERSION

    def normalize(self, answer: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := _contract(contract, self.engine_type, "normalize"): return invalid
        try:
            raw = answer.get("formula") if isinstance(answer, Mapping) else answer
            counts = parse_formula(raw)
            mode = contract.grading_contract.get("mode", "molecular_formula")
            if mode not in {"molecular_formula", "empirical_formula", "molar_mass"}:
                return _failure(self.engine_type, "normalize", "unsupported formula grading mode", "UNSUPPORTED")
            normalized = empirical_counts(counts) if mode == "empirical_formula" else counts
            value = {"atom_counts": normalized, "formula": canonical_formula(normalized), "molar_mass": molar_mass(counts)}
            return AnswerEngineResult("PASS", self.engine_type, "normalize", value)
        except (ChemistryError, TypeError) as exc: return _failure(self.engine_type, "normalize", str(exc))

    def derive(self, derivation_input: Mapping[str, Any], contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := _contract(contract, self.engine_type, "derive"): return invalid
        if not isinstance(derivation_input, Mapping) or "formula" not in derivation_input:
            return _failure(self.engine_type, "derive", "formula derivation input is required")
        result = self.normalize({"formula": derivation_input["formula"]}, contract)
        return AnswerEngineResult(result.status, result.engine_type, "derive", result.value, result.reasons)

    def grade(self, response: Any, expected: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := _contract(contract, self.engine_type, "grade"): return invalid
        actual, target = self.normalize(response, contract), self.normalize(expected, contract)
        if actual.status != "PASS" or target.status != "PASS": return _failure(self.engine_type, "grade", "response and expected formula must be valid")
        if contract.grading_contract.get("mode") == "molar_mass":
            tolerance = float(contract.grading_contract.get("absolute_tolerance", 0.001))
            passed = abs(actual.value["molar_mass"] - target.value["molar_mass"]) <= tolerance
        else: passed = actual.value["atom_counts"] == target.value["atom_counts"]
        return AnswerEngineResult("PASS" if passed else "FAIL", self.engine_type, "grade", passed)


class ChemicalReactionEngine:
    engine_type = "chemical_reaction"
    engine_id = "axiomiq.chemical_reaction"
    engine_version = ENGINE_VERSION

    def _charge(self, contract): return contract.grading_contract.get("conserve_charge", False) is True

    def normalize(self, answer: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := _contract(contract, self.engine_type, "normalize"): return invalid
        try:
            raw = answer.get("reaction") if isinstance(answer, Mapping) else answer
            value = _reaction_value(raw, self._charge(contract))
            return AnswerEngineResult("PASS", self.engine_type, "normalize", value)
        except (ChemistryError, TypeError) as exc: return _failure(self.engine_type, "normalize", str(exc))

    def derive(self, derivation_input: Mapping[str, Any], contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := _contract(contract, self.engine_type, "derive"): return invalid
        if not isinstance(derivation_input, Mapping) or "reaction" not in derivation_input:
            return _failure(self.engine_type, "derive", "reaction derivation input is required")
        try:
            raw = derivation_input["reaction"]; left, right = parse_reaction(raw)
            balanced = balance_reaction(raw, self._charge(contract)); species = [s.formula for _, s in left + right]; split = len(left)
            rendered = " + ".join((str(c) if c != 1 else "") + s for c, s in zip(balanced[:split], species[:split])) + " -> " + " + ".join((str(c) if c != 1 else "") + s for c, s in zip(balanced[split:], species[split:]))
            return AnswerEngineResult("PASS", self.engine_type, "derive", {"coefficients": list(balanced), "reaction": rendered, "split_index": split})
        except (ChemistryError, TypeError) as exc: return _failure(self.engine_type, "derive", str(exc))

    def grade(self, response: Any, expected: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := _contract(contract, self.engine_type, "grade"): return invalid
        actual, target = self.normalize(response, contract), self.normalize(expected, contract)
        if actual.status != "PASS" or target.status != "PASS": return _failure(self.engine_type, "grade", "response and expected reaction must be valid")
        mode = contract.grading_contract.get("mode", "balanced_reaction")
        if mode not in {"balanced_reaction", "stoichiometric_ratio"}: return _failure(self.engine_type, "grade", "unsupported reaction grading mode", "UNSUPPORTED")
        passed = actual.value["reaction"] == target.value["reaction"] if mode == "balanced_reaction" else actual.value["coefficients"] == target.value["coefficients"]
        return AnswerEngineResult("PASS" if passed else "FAIL", self.engine_type, "grade", passed)


def register_chemistry_engines(registry: AnswerEngineRegistry) -> AnswerEngineRegistry:
    """Register both engines into a registry that does not already declare them."""
    for engine in (ChemicalFormulaEngine(), ChemicalReactionEngine()):
        registry.register(AnswerEngineDescriptor(engine.engine_type, True, f"chemistry engine {ENGINE_VERSION}"), engine)
    return registry


def build_chemistry_registry() -> AnswerEngineRegistry:
    return register_chemistry_engines(AnswerEngineRegistry())
