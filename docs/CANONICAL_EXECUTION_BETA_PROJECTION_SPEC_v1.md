# Canonical Execution and Beta Projection Planning v1

## Boundary

This compiler capability produces external, database-neutral review packages. It does not execute canonical promotion. It does not read or write a database, call a Beta service, modify the adaptive platform, or create student-visible state.

Every artifact carries these invariants:

- `noncanonical=true`
- `human_review_required=true`
- `student_visible=false`
- `database_write=false`
- `promotion_authorized=false`
- `canonical_write=false`
- `beta_import_live=false`

The `proposed-question-*` and `proposed-revision-*` identifiers are planning identities. They are not canonical IDs and convey no authority.

## Input contract

Each candidate must already have passed canonical-promotion preparation review and must provide a source system, source identity, source revision, content SHA-256, preparation identity, and source lineage. The accepted review action is exactly `ACCEPT_FOR_PROMOTION_REVIEW` with `eligible=true`.

The Beta package is validated by the existing compiler Beta dry-run import contract. Every Beta question must resolve to exactly one projection candidate. Assessment staging can reference only questions in that validated Beta package.

## Identity, revisions, and lineage

Proposed identity is a deterministic digest of the contract version, source system, and source identity. Proposed revision is a deterministic digest of proposed identity, source revision, content hash, and parent proposed revision.

Reprojecting unchanged source state produces `REPROJECT_NOOP` and preserves the prior proposed revision. A new source revision must explicitly name the current prior proposed revision. Reusing a source revision with changed content, using stale lineage, or submitting duplicate candidates fails the entire plan before artifacts are written.

Source lineage is copied and extended; input objects are not mutated. The persisted manifest seals every artifact and a semantic plan hash. Reopening verifies both byte hashes and the semantic hash.

## Staging and rollback

The planner emits:

- an external projection plan and proposed packages;
- a validated-but-not-imported Beta stage;
- assessment promotion-review staging;
- operator state with review-only controls;
- a reverse-ordered rollback plan for external staged revisions.

Rollback contains no SQL, canonical-store command, executable import instruction, or live action. Operator controls expose review, return, reject, and reopen only. Promote, import, publish, and database-write controls are explicitly unavailable.
