# Universal Answer-Engine Registry

The version 1 registry provides one explicit decision point for answer-contract support, normalization, independent derivation, and grading. It is compiler-only: it stores no attempts, scores, mastery, or student identity.

## Enabled engines

`numeric_scalar`, `numeric_pair`, `numeric_vector`, and `multiple_choice` have working deterministic adapters. Numeric engines reject booleans, nonnumeric values, infinities, and NaN. Pair and vector values preserve component order. Grading applies nonnegative absolute and relative tolerances component by component. Multiple-choice contracts require at least two complete, uniquely identified options and exactly one option marked correct.

Independent derivation accepts only an `independently_derived_answer` supplied by a separate derivation path. It never reads a generator's expected answer or silently reconstructs one from generator state.

## Disabled engines

The registry includes disabled descriptors for `symbolic_expression`, `equation_system`, `matrix`, `proof_logic`, `code_execution`, `graph_diagram`, `scientific_structured_response`, `chemical_reaction`, and `rubric_scored_explanation`. Lookup and every operation return a structured `UNSUPPORTED` result. Unknown engine names behave the same way; there is no numeric or multiple-choice fallback.

## Public usage

Create the standard registry with `build_default_registry()`. Pass an `AnswerContractV1` to `support_decision`, `normalize`, `derive`, or `grade`. Results contain `status`, `engine_type`, `operation`, `value`, and `reasons`. Call `to_dict()` for deterministic JSON-ready output. A passing support decision only means the answer shape has a validated engine; it grants no canonical, publication, assessment, or student-visible authority.
