# Docs-Only Finalize Contract v1

## Purpose

The docs-only finalize contract defines a reusable compact governance pattern for low-risk documentation-only work in the Curriculum Intelligence Compiler repository. It describes how a docs-only lane should create or update approved compiler-side documentation, policy, schema, or task-contract artifacts, validate the result, commit, push, and emit one final report.

## Current Baseline

Current published baseline: 53363fbf4d5c0a18e4c201e3acd1ee3b6a6eba70

This baseline is the expected synchronized `main` state for the first version of this contract.

## Relationship to compiler_non_live_v1

The active policy reference is compiler_non_live_v1.

This contract inherits the non-live compiler boundary from that policy. It keeps docs-only tasks inside compiler-side governance artifacts and does not authorize operational Alpha work, database contact, live deployment, canonical promotion, or student-visible delivery.

## Relationship to task_contract_v1

The active task contract schema is task_contract_v1.

The JSON contract at `.axiomiq/task_contracts/docs_only_finalize_v1.json` is shaped to use only fields allowed by `task_contract_v1.schema.json`. It is a concrete reusable contract instance for documentation-only finalize lanes.

## Why This Exists

The docs-only finalize contract is intended to reduce repeated manual governance prose for low-risk documentation tasks.

Many compiler documentation lanes repeat the same sequence: create a scoped documentation artifact, validate path boundaries, commit, push, and report. This contract makes that shape explicit without expanding authority or changing implementation behavior.

## Intended Docs-Only Flow

1. Confirm the compiler repository is on clean, synchronized `main`.
2. Confirm the MVP tag has not moved.
3. Create or update only approved documentation, policy, schema, or task-contract files.
4. Validate JSON, required text, allowed paths, and forbidden-zone boundaries.
5. Commit only the approved files.
6. Push only the current `main` branch when the remote is still compatible.
7. Emit one final task, commit, or push report as required by the lane.

## Allowed Use

The docs-only finalize contract should be used only for documentation, policy, schema, and task-contract artifacts inside the compiler repo.

Allowed examples include:

- `docs/course_compiler_demo/*.md`
- `.axiomiq/policies/*.yaml`
- `.axiomiq/schemas/*.json`
- `.axiomiq/task_contracts/*.json`

## Disallowed Use

The docs-only finalize contract should not be used for non-live compiler implementation, import adapters, validators, source processing, parser work, Alpha integration, DB migrations, or student-facing features.

It is also not appropriate for tasks that need new dependencies, OCR, source ingestion, generated intake runs, canonical promotion, backend/frontend changes, deployment changes, or any operational Alpha touch.

## Contract Fields

The contract uses these top-level fields from `task_contract_v1`:

- `task_id`
- `repository`
- `risk_class`
- `baseline`
- `policy_refs`
- `allowed_paths`
- `actions`
- `source_snapshot`
- `safety_flags`
- `report`

The contract sets `risk_class` to `docs_only` and restricts actions to create or update approved files, validate, commit, and push.

## Allowed Paths

Allowed paths are limited to compiler-side docs, policy, schema, and task-contract artifacts:

- `docs/course_compiler_demo/*.md`
- `.axiomiq/policies/*.yaml`
- `.axiomiq/schemas/*.json`
- `.axiomiq/task_contracts/*.json`

These path patterns are examples and must still be narrowed by each executable task to the exact files approved for that lane.

## Source Snapshot Rule

The contract uses `committed_compiler_side_artifacts_only` as the source snapshot rule. That means the task may rely on committed compiler-side policy, schema, and documentation artifacts.

It does not authorize live Alpha lookup, live content import, or copying operational Alpha files into the compiler repository.

## Alpha Advisory and No-Access Rule

Live Alpha access is forbidden in this contract.

Alpha repository state may be mentioned only as external context if a future task explicitly requires an advisory check. This contract does not authorize Alpha staging implementation, Alpha file modification, adaptive-platform writes, or copying Alpha content.

## Safety Flags

All safety flags are false:

- `allow_alpha_write: false`
- `allow_adaptive_platform_write: false`
- `allow_database_contact: false`
- `allow_canonical_promotion: false`
- `allow_student_visible_output: false`
- `allow_live_deployable_output: false`
- `allow_ocr: false`
- `allow_parser_implementation: false`
- `allow_dependency_addition: false`
- `allow_mvp_tag_move: false`

These defaults preserve the compiler's non-live, non-operational boundary.

## Validation Expectations

Docs-only finalize tasks should validate:

- repository baseline and branch
- clean worktree before task start
- MVP tag target
- allowed file scope
- JSON validity for contract or schema files
- required documentation language
- forbidden-zone absence
- final dirty files before commit
- clean worktree after commit and push when those actions are authorized

## Commit and Push Behavior

The contract describes a compact flow that includes commit and push actions, but each concrete task must still authorize those actions explicitly.

When commit is authorized, stage exact approved paths only. When push is authorized, push only `main`, never force push, never push tags unless a separate task authorizes that action.

## Report Behavior

The report model requires a final Codex report. The contract instance uses `codex_task_report` and recommends `COURSE-COMPILER-DOCS-ONLY-FINALIZE-CONTRACT-COMMIT-001` as the next task for this initial documentation lane.

Future lanes may use task, commit, push, or readiness-audit report formats as allowed by `task_contract_v1`.

## What This Replaces

The docs-only finalize contract replaces repeated manual create, commit, push, audit, closeout, closeout-commit, and closeout-push prompts for low-risk documentation lanes after a runner exists.

It is intended to let routine documentation lanes use reusable policy and allowed-path rules rather than restating every governance boundary from scratch.

## What This Does Not Implement

The docs-only finalize contract is not a lane runner.

The docs-only finalize contract does not implement automation.

The docs-only finalize contract does not authorize Alpha staging implementation.

The docs-only finalize contract does not authorize writing into adaptive-platform.

The docs-only finalize contract does not authorize migrations, backend endpoints, frontend views, DB tables, or integration files in Alpha.

The docs-only finalize contract does not authorize parser implementation, OCR, importers, DB contact, canonical promotion, student-visible delivery, or live deployable output.

## Future Runner Requirements

A future runner would need to:

- load and validate `task_contract_v1` contracts
- compare requested file changes to exact allowed paths
- enforce safety flags before execution
- validate clean baseline and remote synchronization
- run configured checks
- stage exact paths only
- block protected paths
- emit structured reports

Until a runner exists, this contract is advisory and must not be treated as executable automation.

## Recommended Next Tasks

1. COURSE-COMPILER-DOCS-ONLY-FINALIZE-CONTRACT-COMMIT-001
2. COURSE-COMPILER-DOCS-ONLY-FINALIZE-CONTRACT-PUSH-001
3. COURSE-COMPILER-DOCS-ONLY-FINALIZE-CONTRACT-READINESS-AUDIT-001
4. COURSE-COMPILER-LOW-RISK-DOCS-RUNNER-DESIGN-001
5. COURSE-COMPILER-TASK-CONTRACT-VALIDATOR-SPEC-001

## Do Not Do Yet

Do not implement a lane runner.

Do not implement automation.

Do not implement importers, parsers, OCR, dependency changes, source processing, Alpha staging, database access, canonical promotion, student-visible delivery, or live deployable output.
