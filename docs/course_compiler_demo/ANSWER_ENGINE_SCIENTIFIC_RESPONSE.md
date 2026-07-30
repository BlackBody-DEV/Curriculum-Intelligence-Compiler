# Scientific Structured-Response and Rubric Engines

Version 1.0 implements `scientific_structured_response` and `rubric_scored_explanation` under the universal `AnswerEngine` protocol. `build_scientific_response_registry()` creates a lane-local registry, while `register_scientific_response_engines(registry)` is the conflict-free synthesis hook. Results always identify the actual engine and contain deterministic status, value, and failure reasons; neither engine falls back to another answer type.

## Accepted response contract

Responses must be objects containing only explicit `concepts`, `relationships`, `quantities`, `causal_sequence`, and `evidence` arrays. Relationships require `source`, `relation`, and `target`; quantities require a finite numeric `value`, `name`, and `unit`. Case, whitespace, punctuation, synonyms, collection order, and duplicate items normalize deterministically. Causal sequence intentionally preserves order.

The grading contract declares `required_concepts`, `required_relationships`, `permitted_synonyms`, `required_quantities`, `quantity_absolute_tolerance`, `forbidden_contradictions`, `required_causal_sequence`, `minimum_evidence_threshold`, and optionally `passing_score`. Rubric scoring also accepts nonnegative per-category points in `partial_credit_rules`. Scores, point totals, category breakdowns, contradictions, and the pass decision are serialized deterministically. Any declared contradiction overrides an otherwise passing score.

## Limits and fail-closed behavior

This is deterministic checklist and relationship grading, not semantic essay assessment. Freeform strings, extra prose fields, implicit relationships, undeclared units, non-finite quantities, malformed rubric rules, ambiguous synonyms, and contracts without requirements fail closed. Synonyms are permitted only when explicitly declared. Evidence items are identifiers or short labels; their truth or quality is not inferred. Required causal terms must occur as an ordered subsequence, while concept and relationship collection order has no grading effect.

Independent derivation consumes only `structured_response`; generator-answer state is ignored. Focused proof covers exactly 50 structured-response cases and 50 rubric cases, plus deterministic partial credit, contradiction override, ordering independence, unit/quantity checks, evidence thresholds, causal ordering, freeform rejection, universal registry support, and stable JSON serialization.
