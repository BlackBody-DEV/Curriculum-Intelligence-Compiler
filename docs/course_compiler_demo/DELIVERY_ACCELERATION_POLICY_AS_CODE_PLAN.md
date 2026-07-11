# Delivery Acceleration Policy-as-Code Plan

## Purpose

This plan defines how the Curriculum Intelligence Compiler can replace repeated manual guardrail prose with reusable policy-as-code scaffolding.

The goal is faster delivery without weakening the non-live, no-copy, no-Alpha-write, no-DB-contact boundaries that have protected the compiler lane.

## Current Baseline

Current published baseline: 3af7a7f25a34bc08a2bd0502010a671392565721

The generation family import specification is published on main.

The procedure candidate import spec lane is closed out on main.

The question candidate import spec lane is closed out on main.

## Problem Statement

Compiler lane tasks now repeat the same safety language across readiness checks, closeouts, commit tasks, and push tasks. That repetition is useful, but it is slow and easy to drift.

A policy-as-code layer can centralize recurring non-live constraints while still allowing task-specific scope, evidence checks, and human review.

## What Remains Protected

The policy-as-code approach must preserve:

- no Alpha writes
- no adaptive-platform writes
- no operational Alpha touch
- no database contact
- no canonical promotion
- no student-visible output
- no live-deployable output
- no OCR unless separately authorized
- no parser implementation unless separately authorized
- no dependency addition unless separately authorized
- no MVP tag movement
- no source content copying
- no Alpha staging implementation

Alpha staging implementation remains parked as COURSE-COMPILER-PRODUCTION-STAGING-INTEGRATION-SCOPE-LOCK-001.

This task does not authorize Alpha staging implementation.

This task does not authorize writing into adaptive-platform.

This task does not authorize migrations, backend endpoints, frontend views, DB tables, or integration files in Alpha.

## Risk Tier Model

The first policy version defines three risk tiers:

1. docs_only
2. non_live_compiler_implementation
3. alpha_integration_scope_lock

The docs_only tier can create or update approved documentation and policy files. The non_live_compiler_implementation tier can touch isolated compiler-side tooling and non-live outputs only when explicitly authorized. The alpha_integration_scope_lock tier is specification-only and must not implement Alpha staging.

## Proposed Policy File

The initial policy file is `.axiomiq/policies/compiler_non_live_v1.yaml`.

It captures shared risk tiers, protected boundaries, default candidate values, required evidence fields, advisory Alpha state rules, and common forbidden zones.

## Proposed Task Contract Format

Future tasks should reference a policy id, risk tier, allowed files, forbidden files, required checks, expected dirty files, and final report schema.

The task contract should remain explicit enough for human governance while letting repetitive boundary language come from policy.

## Proposed Lane Runner

A later lane runner can read policy files and task contracts, then generate checklist scaffolds for:

- preflight checks
- content validation
- forbidden-zone scans
- boundary reports
- commit scope checks
- push readiness checks

This plan does not implement the lane runner.

## Docs-Only Finalize Flow

For docs-only lanes, the future flow should be:

1. verify baseline, branch, status, remote, and MVP tag
2. create only allowed documentation or policy files
3. run required string and forbidden-zone checks
4. report final dirty files
5. wait for separate commit authorization

## Non-Live Implementation Flow

For non-live compiler implementation lanes, the future flow should be:

1. verify policy and task contract
2. limit edits to isolated compiler-side paths
3. run deterministic local checks
4. reject backend, frontend, Alpha, database, canonical, student-visible, and live-deployable changes
5. preserve human_review_required and review_pending defaults unless separately authorized

## Alpha Integration Flow

Alpha integration must not begin from ordinary compiler implementation tasks.

Any Alpha integration must first pass through COURSE-COMPILER-PRODUCTION-STAGING-INTEGRATION-SCOPE-LOCK-001 as a scope-lock/spec-only lane opened by the main Alpha spline.

## CandidateBase Consolidation

Procedure candidates, question candidates, and generation family candidates share base fields: status, review_status, canonical_promotion_status, copying_allowed_now, student_visible, live_deployable, evidence refs, rights/privacy status, and human review requirements.

A future CandidateBase specification can consolidate these shared fields without changing existing non-live boundaries.

## Registry and Auto-Closeout Plan

A future registry can track task ids, policy ids, risk tiers, expected files, required checks, closeout requirements, commit status, and push status.

Auto-closeout should only draft closeout scaffolds. It must not commit, push, import, promote, or touch Alpha without explicit authorization.

## No Alpha Access Rule for Compiler-Only Lanes

Compiler-only lanes should use committed compiler-side census artifacts rather than current live Alpha files.

Alpha HEAD and worktree state can be recorded as advisory context when the compiler boundary is intact, but compiler tasks must not write into adaptive-platform or copy Alpha content.

## Migration Path From Current Workflow

1. Commit the initial compiler_non_live_v1 policy.
2. Add task templates that reference policy ids and risk tiers.
3. Convert repeated closeout, commit, push, and audit language into reusable policy snippets.
4. Keep task-specific allowed files and expected dirty files explicit.
5. Add a later read-only validator for policy/task-contract consistency.

## Immediate Next Tasks

1. COURSE-COMPILER-DELIVERY-ACCELERATION-POLICY-AS-CODE-COMMIT-001
2. COURSE-COMPILER-DELIVERY-ACCELERATION-POLICY-AS-CODE-PUSH-001
3. COURSE-COMPILER-DELIVERY-ACCELERATION-POLICY-AS-CODE-READINESS-AUDIT-001
4. COURSE-COMPILER-TASK-CONTRACT-TEMPLATE-001
5. COURSE-COMPILER-CANDIDATE-BASE-SPEC-001

## Do Not Do Yet

Do not implement the lane runner.

Do not modify compiler logic.

Do not modify intake engine code.

Do not implement importers.

Do not implement parsers.

Do not add dependencies.

Do not create new intake runs.

Do not process real source documents.

Do not modify final MVP demo outputs.

Do not import generation families, questions, or procedures.

Do not copy Alpha 2.0 content.

Do not generate live variants.

Do not modify Alpha 2.0.

Do not modify operational Alpha.

Do not write into adaptive-platform.

Do not start Alpha staging implementation.

Do not create Alpha migrations, backend endpoints, frontend views, DB tables, or integration files.

Do not create canonical content.

Do not create student-visible content.

Do not authorize OCR.

Do not contact any database.

Do not move or recreate the MVP tag.
