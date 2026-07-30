import json

import pytest

from tools.course_compiler_demo.answer_engines.registry import AnswerEngine
from tools.course_compiler_demo.answer_engines.chemistry import (
    ChemicalFormulaEngine, ChemicalReactionEngine, balance_reaction,
    build_chemistry_registry, parse_formula, parse_reaction,
)
from tools.course_compiler_demo.universal_core import AnswerContractV1


def contract(engine, grading=None):
    return AnswerContractV1(f"contract:{engine}", engine, grading or {})


FORMULAS = [
    "H2O", "CO2", "NaCl", "NH3", "CH4", "O2", "N2", "HCl", "H2SO4", "HNO3",
    "NaOH", "KOH", "CaCO3", "Na2CO3", "NaHCO3", "C6H12O6", "C2H5OH", "C3H8", "C4H10", "C8H18",
    "Fe2O3", "Fe3O4", "CuSO4", "ZnCl2", "AgNO3", "KMnO4", "K2Cr2O7", "Al2(SO4)3", "Ca(OH)2", "Mg(OH)2",
    "(NH4)2SO4", "NH4NO3", "Ca3(PO4)2", "Na3PO4", "Mg3(PO4)2", "K4[Fe(CN)6]", "Fe(NO3)3", "Pb(NO3)2", "BaCl2", "Li2O",
    "P4O10", "SO2", "SO3", "N2O5", "Cl2O7", "C12H22O11", "CuSO4·5H2O", "CoCl2.6H2O", "CaSO4·2H2O", "Al2O3",
]


@pytest.mark.parametrize("formula", FORMULAS)
def test_50_formula_proofs_parse_normalize_and_independently_verify_atoms(formula):
    engine = ChemicalFormulaEngine(); answer_contract = contract("chemical_formula")
    direct = parse_formula(formula)
    normalized = engine.normalize(formula, answer_contract)
    derived = engine.derive({"formula": formula, "generator_answer": "must-not-be-read"}, answer_contract)
    assert normalized.status == derived.status == "PASS"
    assert normalized.value["atom_counts"] == direct == derived.value["atom_counts"]
    assert sum(direct.values()) > 0 and normalized.engine_type == "chemical_formula"


REACTIONS = [
    ("H2 + O2 -> H2O", (2,1,2)), ("N2 + H2 -> NH3", (1,3,2)),
    ("Fe + O2 -> Fe2O3", (4,3,2)), ("Al + O2 -> Al2O3", (4,3,2)),
    ("Na + Cl2 -> NaCl", (2,1,2)), ("K + Br2 -> KBr", (2,1,2)),
    ("Mg + HCl -> MgCl2 + H2", (1,2,1,1)), ("Zn + HCl -> ZnCl2 + H2", (1,2,1,1)),
    ("C3H8 + O2 -> CO2 + H2O", (1,5,3,4)), ("C2H6 + O2 -> CO2 + H2O", (2,7,4,6)),
    ("CH4 + O2 -> CO2 + H2O", (1,2,1,2)), ("C2H5OH + O2 -> CO2 + H2O", (1,3,2,3)),
    ("NaOH + HCl -> NaCl + H2O", (1,1,1,1)), ("H2SO4 + NaOH -> Na2SO4 + H2O", (1,2,1,2)),
    ("CaCO3 -> CaO + CO2", (1,1,1)), ("KClO3 -> KCl + O2", (2,2,3)),
    ("H2O2 -> H2O + O2", (2,2,1)), ("N2O5 + H2O -> HNO3", (1,1,2)),
    ("P4 + O2 -> P4O10", (1,5,1)), ("SO2 + O2 -> SO3", (2,1,2)),
    ("Fe2O3 + CO -> Fe + CO2", (1,3,2,3)), ("CuO + H2 -> Cu + H2O", (1,1,1,1)),
    ("AgNO3 + NaCl -> AgCl + NaNO3", (1,1,1,1)),
    ("BaCl2 + Na2SO4 -> BaSO4 + NaCl", (1,1,1,2)),
    ("Ca3(PO4)2 + H2SO4 -> CaSO4 + H3PO4", (1,3,3,2)),
]


@pytest.mark.parametrize("reaction,expected", REACTIONS)
@pytest.mark.parametrize("representation", ["bare", "scaled"])
def test_50_reaction_proofs_balance_conserve_atoms_and_normalize(reaction, expected, representation):
    left, right = parse_reaction(reaction); split = len(left)
    derived = balance_reaction(reaction)
    assert derived == expected
    for element in {e for _, s in left + right for e in s.counts}:
        assert sum(c*s.counts.get(element, 0) for c, (_, s) in zip(derived[:split], left)) == sum(c*s.counts.get(element, 0) for c, (_, s) in zip(derived[split:], right))
    species = [s.formula for _, s in left + right]
    factor = 1 if representation == "bare" else 3
    rendered = " + ".join(f"{factor*c if factor*c != 1 else ''}{s}" for c,s in zip(derived[:split],species[:split])) + " -> " + " + ".join(f"{factor*c if factor*c != 1 else ''}{s}" for c,s in zip(derived[split:],species[split:]))
    normalized = ChemicalReactionEngine().normalize(rendered, contract("chemical_reaction"))
    assert normalized.status == "PASS" and normalized.value["coefficients"] == list(expected)


MALFORMED_FORMULAS = [
    "", "2", "Xx2", "h2O", "H0", "H02", "Na(Cl", "Na]Cl[", "()2", "H2..O",
    "H2 O", "Na+Cl", "C-1H4", "Fe(OH]3", "[NaCl", "NaCl]", "10001H2O",
]
IMPOSSIBLE_REACTIONS = [
    "H2 O2", "H2 ->", "-> H2O", "H2 -> H2 -> H2", "H2 + O2 -> CO2",
    "H2 -> H2 + O2", "NaCl -> Na + KCl", "C -> CO2 + CO",
]


@pytest.mark.parametrize("bad", MALFORMED_FORMULAS)
def test_malformed_formula_proofs_fail_closed(bad):
    result = ChemicalFormulaEngine().normalize(bad, contract("chemical_formula"))
    assert result.status == "INVALID" and result.value is None and result.reasons


@pytest.mark.parametrize("bad", IMPOSSIBLE_REACTIONS)
def test_malformed_or_impossible_reaction_proofs_fail_closed(bad):
    result = ChemicalReactionEngine().derive({"reaction": bad}, contract("chemical_reaction"))
    assert result.status == "INVALID" and result.value is None and result.reasons


def test_empirical_molecular_molar_mass_and_stoichiometric_contracts():
    formula = ChemicalFormulaEngine()
    assert formula.grade("C6H12O6", "CH2O", contract("chemical_formula", {"mode": "empirical_formula"})).status == "PASS"
    assert formula.grade("C6H12O6", "CH2O", contract("chemical_formula", {"mode": "molecular_formula"})).status == "FAIL"
    assert formula.normalize("H2O", contract("chemical_formula", {"mode": "molar_mass"})).value["molar_mass"] == 18.015
    reaction = ChemicalReactionEngine(); ratio = contract("chemical_reaction", {"mode": "stoichiometric_ratio"})
    assert reaction.grade("2H2 + O2 -> 2H2O", "4H2 + 2O2 -> 4H2O", ratio).status == "PASS"


def test_charge_conservation_is_enforced_only_when_declared():
    charged = contract("chemical_reaction", {"conserve_charge": True})
    derived = ChemicalReactionEngine().derive({"reaction": "Fe^2+ + Ce^4+ -> Fe^3+ + Ce^3+"}, charged)
    assert derived.status == "PASS" and derived.value["coefficients"] == [1,1,1,1]
    impossible = ChemicalReactionEngine().derive({"reaction": "Fe^2+ -> Fe^3+"}, charged)
    assert impossible.status == "INVALID"


def test_universal_protocol_registry_support_failure_reasons_and_determinism():
    registry = build_chemistry_registry()
    for name in ("chemical_formula", "chemical_reaction"):
        found = registry.lookup(name)
        assert found.status == "SUPPORTED" and isinstance(found.value, AnswerEngine)
        assert registry.support_decision(contract(name)).status == "SUPPORTED"
    formula_contract = contract("chemical_formula")
    first = registry.normalize("OH2", formula_contract).to_dict()
    second = registry.normalize({"formula": "H2O"}, formula_contract).to_dict()
    assert first == second
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(second, sort_keys=True, separators=(",", ":"))
    wrong = ChemicalFormulaEngine().normalize("H2O", contract("numeric_scalar"))
    assert wrong.status == "INVALID" and wrong.engine_type == "chemical_formula"
    unsupported = ChemicalFormulaEngine().normalize("H2O", contract("chemical_formula", {"mode": "molecular_drawing"}))
    assert unsupported.status == "UNSUPPORTED" and unsupported.value is None
