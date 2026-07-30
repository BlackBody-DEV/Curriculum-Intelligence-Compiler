# Matrix and Linear-System Answer Engine

The `matrix` engine is a bounded, deterministic `AnswerEngine` implementation. It records `matrix` as the actual engine type and never falls back to another answer capability. Synthesis can enable it with `register_matrix_engine(registry)`.

## Contract

`engine_type` must be `matrix`. The grading contract selects `answer_kind`: `matrix` (default), `scalar`, `inverse`, `rref`, `solution_vector`, or `eigenvalues`. Optional `absolute_tolerance`/`absolute` and `relative_tolerance`/`relative` values must be finite and nonnegative. With zero or omitted tolerances, comparison is exact.

Inputs use nonempty rectangular nested sequences, bounded to 6 rows and 6 columns. Entries may be integers, finite decimal numbers, or rational strings such as `-3/5`. Normalization emits reduced rationals as integers or `numerator/denominator` strings, so serialization is stable and exact. Eigenvalue order is canonical; solution-vector order remains significant.

## Independent derivation

`derive` recomputes answers from source operands and does not consume a generator-provided answer. Supported operations are:

- `addition`: `left`, `right`
- `scalar_multiplication`: `matrix`, `scalar`
- `multiplication`: `left`, `right`
- `determinant`: square `matrix`
- `inverse`: nonsingular square `matrix`
- `rref`: `matrix`
- `solve`: square `coefficients` and matching `constants`, with one unique solution
- `eigenvalues`: 1x1 or 2x2 `matrix` with rational real eigenvalues

Gaussian elimination uses exact rational arithmetic for determinants, inverse verification, RREF, and linear-system solutions. Matrix grading validates shape before component comparison. An inverse may be independently derived and then graded against a proposed inverse; multiplication can additionally be derived to verify the identity product.

## Fail-closed boundary

The engine rejects ragged, empty, oversized, nonnumeric, nonfinite, or incompatible matrices. It reports structured `INVALID` or `UNSUPPORTED` reasons for singular inverses, non-unique systems, non-square determinant inputs, complex/irrational or larger eigenvalue cases, unknown answer kinds, and unknown derivation operations. It does not approximate an unsupported symbolic result and does not route it to scalar, vector, multiple-choice, or any other engine.
