# Chemical Formula and Reaction Answer Engines

Version 1.0 supplies `chemical_formula` and `chemical_reaction` adapters for the universal `AnswerEngine` protocol. `build_chemistry_registry()` provides a lane-local registry; `register_chemistry_engines(registry)` is the synthesis hook for the shared registry. Every result identifies the actual engine, operation, status, value, and structured failure reasons. Invalid or unsupported inputs fail closed and never fall back to another answer type.

## Bounded support

Formula parsing validates all 118 element symbols, integer subscripts, nested parentheses/brackets (up to eight levels), and hydrate dot segments. It deterministically emits Hill-order formulas, independently counted atoms, empirical counts, and abridged-standard-weight molar masses. Contracts select `molecular_formula` (default), `empirical_formula`, or `molar_mass`.

Reaction parsing accepts one `->`, `→`, or `=` arrow, at most 12 species per side, positive integer coefficients, phase suffixes, and whitespace-delimited ` + ` separators. Exact rational Gaussian elimination derives a unique positive integer balance, reduces coefficients by their greatest common divisor, independently checks every element, and rejects underdetermined or impossible equations. `balanced_reaction` and `stoichiometric_ratio` grading use deterministic normalized coefficients.

Charge conservation is opt-in with `grading_contract.conserve_charge: true`. Charges use unambiguous caret notation (`Fe^2+`, `SO4^2-`) or a bare terminal sign for magnitude one. When declared, charge is included as an additional conservation row.

## Deliberate exclusions

This engine does not support isotope notation, fractional/zero/negative subscripts or coefficients, electrons as species, ambiguous compact charge notation such as `Fe3+`, redox half-reaction completion, reaction-condition inference, molecular drawings, stereochemistry, or unrestricted organic mechanisms. Formula equivalence compares composition, not molecular structure. A reaction must have a one-dimensional stoichiometric nullspace with all-positive coefficients no larger than 10,000.

## Independent derivation and proof

Formula derivation consumes only `{"formula": ...}` and recounts atoms. Reaction derivation consumes only `{"reaction": ...}` and solves the conservation system; it does not consume a generator answer. Focused tests contain exactly 50 valid formula parameter cases, 50 reaction/balancing parameter cases, and 25 malformed or impossible parameter cases, plus universal protocol, deterministic serialization, charge, empirical/molecular, molar-mass, and stoichiometric-ratio contract checks.
