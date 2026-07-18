# Assessment Generation Contract v1

## Purpose

This contract defines deterministic, compiler-side assessment generation for non-live review candidates. It supports fixed, approved generation families that can produce multiple unique questions from a blueprint while preserving answer validation, duplicate rejection, and human review gates.

Generated assessments remain local compiler artifacts only:

- `compiler_non_live_review_pending`
- `eligible_for_alpha_import: false`
- `canonical_approved: false`
- `student_visible: false`
- `human_review_required: true`

## Contract Files

Schemas live under `tools/course_compiler_demo/schemas/`:

- `assessment_generation_family_v1.schema.json`
- `assessment_blueprint_v1.schema.json`
- `generated_question_v1.schema.json`
- `generated_assessment_v1.schema.json`
- `assessment_validation_report_v1.schema.json`
- `assessment_review_decisions_v1.schema.json`

The generator package lives under `tools/course_compiler_demo/assessment_generation/`.

## Fixed Registries

Family JSON may reference only fixed registry IDs for prompt builders, answer calculators, and solution builders. Family JSON cannot provide module paths, filesystem paths, callable names, template expressions, `eval`, `exec`, or dynamic imports.

Initial families:

- `GF_PHYSICS_NEWTON_SECOND_LAW_1D_V1`
- `GF_STATICS_VECTOR_COMPONENTS_2D_V1`

## Blueprint Rules

A blueprint must be `generation_ready` before generation. It must explicitly select subject, topic, micro-skill, question count, difficulty distribution, question type distribution, prerequisite policy, generation-family allocation, uniqueness policy, and non-live rights boundary.

Generation fails closed when a family attempts to use:

- an unselected topic
- an unselected micro-skill
- an unapproved prerequisite
- an unapproved procedure binding
- unsupported answer type or unit
- a downstream skill excluded by the blueprint

## Determinism

Generation uses local seeded randomness only. The same family, blueprint, and seed produce identical semantic output. A different seed produces valid variation when parameter space remains.

Each question records:

- `generation_seed`
- `generation_attempt`
- `exact_fingerprint`
- `structural_fingerprint`

## Deduplication

Exact fingerprints hash normalized prompt, parameter set, expected answer, and diagram specification when present.

Structural fingerprints hash family identity, reasoning sequence, difficulty, answer representation, and family-declared structural fields.

The generator compares against current-run fingerprints and optional filesystem-backed historical fingerprints. It does not scan arbitrary locations.

If parameter space is exhausted, the duplicate report records requested count, generated count, rejection counts, and `parameter_space_exhausted: true`.

## Answer Authority

The answer calculator is authoritative. Prompt builders never supply answers. Validation recomputes every answer from the parameter set and rejects mismatches, unsupported units, invalid tolerance, scope exclusions, and prompt answer leakage.

## Review

Review records support:

- `pending`
- `accepted`
- `rejected`
- `needs_revision`
- `regenerate`

Any mathematical edit sets `validation_invalidated: true`. Locked questions cannot be regenerated.

## Exports

Student exports omit expected answers and solution steps. Instructor exports include the answer key and solutions. All exports preserve noncanonical, non-live status and do not imply student publication.

## CLI

```bash
python3 tools/course_compiler_demo/run_assessment_generation.py \
  --family tools/course_compiler_demo/assessment_generation/families/apply_newtons_second_law_1d_v1.json \
  --blueprint reports/course_compiler_demo/internal_release/assessment_generation_contract_hardening/physics/assessment_blueprint.json \
  --output reports/course_compiler_demo/internal_release/assessment_generation_contract_hardening/physics
```

The CLI validates the family, validates the blueprint, generates requested slots, runs duplicate and answer checks, writes assessment artifacts, and exits nonzero when generation cannot satisfy the contract.
