# Universal Curriculum Compiler Core

The universal core is the stable, dependency-free boundary between source intake,
curriculum synthesis, generation, validation, assessment compilation, and AxiomIQ
Beta export. All public names have a `V1` suffix and serialize to deterministic,
sorted, compact JSON through `to_json()`.

## Ownership boundary

The compiler owns curriculum and question production. It does not own student
attempts, scores, mastery, progress, adaptive assignment, or performance analytics.
Those fields are rejected recursively, including inside extension-like mappings.
Beta receives content packages only; no export grants canonical authority or activates
content.

## Hierarchy and evidence

`CurriculumNodeV1` supports Domain → Subject → Course → Unit → Topic → Subtopic →
Micro-skill → Procedure → Generation Family → Question → Assessment.
`CurriculumRelationshipV1` represents containment, prerequisites, alignment, and
implementation links. Package construction rejects dangling relationship endpoints.

Source evidence and review state travel with nodes, relationships, proposed mappings,
and packages. `CanonicalMappingCandidateV1` is deliberately proposal-only:
`canonical_authority` must remain false.

## Strictness and compatibility

`from_dict()` rejects unknown keys, missing constructor-required fields, unsupported
enums, blank identities, and forbidden performance data. Schema objects use
`additionalProperties: false`; their version is fixed at `1.0`. New incompatible
shapes require a new version instead of changing V1 semantics.

The four integration schemas are under `schemas/course_compiler_demo/`:

- universal curriculum package
- generation manifest
- assessment blueprint
- Beta export package

Callers should import contracts from `tools.course_compiler_demo.universal_core`, not
from internal modules.
