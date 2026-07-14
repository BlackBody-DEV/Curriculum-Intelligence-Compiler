# Semantic Validation Rule Catalog v1

## Rule IDs

- `CONTRACT_VERSION`: verifies `compiler_release_package_v1` and version `1.0.0`.
- `JSON_PARSE`: verifies manifest JSON can be read.
- `STRUCTURAL_SCHEMA`: verifies required manifest and artifact descriptor fields.
- `ARTIFACT_INVENTORY`: verifies declared artifacts exist, package files are declared, required categories exist, media types are supported, and artifact JSON parses.
- `PATH_CONTAINMENT`: rejects absolute paths, parent traversal, backslashes, package escapes, and unsafe symlinks.
- `IDENTIFIER_UNIQUENESS`: rejects duplicate artifact, source, procedure, question, generation-family, signal, performance, review, and validation identifiers.
- `REFERENCE_INTEGRITY`: verifies source references, artifact dependencies, manifest artifact lists, and dependency cycles.
- `PROVENANCE`: requires source provenance and source references for instructional artifacts.
- `PROCEDURE_QUESTION_LINKAGE`: rejects orphan question candidates and missing answer/origin fields.
- `GENERATION_FAMILY_LINKAGE`: rejects orphan or live-enabled generation family candidates and duplicate parameter definitions.
- `SIGNAL_POLICY`: permits only approved compiler-side signal categories and rejects runtime execution claims.
- `REVIEW_STATE`: requires non-live candidate and human-review-required status.
- `RIGHTS_SAFETY`: verifies rights/privacy status and rejects protected-source payload markers.
- `SAFETY_BOUNDARY`: enforces non-live, non-canonical, no database, no adaptive-platform, no runtime-route, no learner-state mutation, and no student-visible flags.
- `INTEGRITY`: verifies artifact SHA-256, byte sizes, and manifest integrity checksum.
- `DETERMINISM`: verifies repeatable canonical serialization, manifest digest reproduction, and deterministic artifact ordering.
- `KNOWN_GAPS`: classifies declared gaps and permits only nonblocking declared gaps as warnings.

## Severity Model

Errors reject a package. Warnings are allowed only for declared nonblocking gaps and produce `accept_with_warnings`.

## Known-Gap Classes

- `nonblocking_declared`: warning only when promotion remains `hold_for_human_review`
- `blocking_content`: reject
- `blocking_reference`: reject
- `blocking_safety`: reject
- `blocking_integrity`: reject
- `blocking_rights`: reject
