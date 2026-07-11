# Task Contract Specification v1

## Purpose

This document defines the first compiler-side task contract specification for AxiomIQ Curriculum Intelligence Compiler lanes.

The task contract is intended to reduce repeated manual governance prose by referencing reusable policy and structured allowed-path rules.

## Current Baseline

Current published baseline: 2dfe5a1fb9d3198d34c53e987419233a308bb1b7

## Relationship to compiler_non_live_v1

The active policy reference is compiler_non_live_v1.

Task contracts should reference `.axiomiq/policies/compiler_non_live_v1.yaml` and inherit its protected boundaries unless an explicitly authorized future policy permits otherwise.

## Why This Exists

Compiler lane prompts currently repeat long guardrail blocks for every specification, audit, closeout, commit, and push task. A declarative task contract can keep the guardrails intact while making task scope easier to review and automate later.

## Risk Classes

Supported risk classes are:

- docs_only
- non_live_compiler_implementation
- alpha_integration_scope_lock

Docs-only contracts are limited to approved documentation, report, schema, and policy files. Non-live compiler implementation contracts are limited to isolated compiler-side tooling and non-live outputs. Alpha scope-lock contracts are specification-only and must not implement Alpha staging.

## Required Top-Level Fields

Task contracts must include:

- task_id
- repository
- risk_class
- baseline
- policy_refs
- allowed_paths
- actions
- source_snapshot
- safety_flags
- report

## Baseline Rules

The baseline object records how to verify repository state before task execution.

Supported baseline modes:

- exact_commit
- current_synced_main

Baseline fields:

- mode
- expected_head
- branch

## Policy References

policy_refs must include compiler_non_live_v1 for current compiler-side lanes.

Future policy versions may be introduced by separate governance tasks, but this specification only defines the v1 reference model.

## Allowed Paths

allowed_paths lists every file or directory the task may create or update.

Any file outside allowed_paths must be treated as out of scope unless a newer authorized task contract explicitly expands the path list.

## Protected Boundaries

Task contracts inherit protected boundaries from compiler_non_live_v1, including no Alpha write, no adaptive-platform write, no operational Alpha touch, no database contact, no canonical promotion, no student-visible output, no live-deployable output, no OCR, no unauthorized parser implementation, no unauthorized dependency addition, no MVP tag move, no source content copying, and no Alpha staging implementation.

## Source Snapshot Rules

source_snapshot records the task's source basis.

Fields:

- snapshot_id
- source_type
- live_alpha_access

The default compiler-only value is:

```yaml
live_alpha_access: forbidden
```

Other possible values are advisory_only and current_required. current_required should be reserved for separately authorized lanes.

## Alpha Advisory Rule

For compiler documentation/specification audits, Alpha HEAD and worktree state may be advisory when the compiler boundary is intact and the task uses committed compiler-side artifacts instead of current live Alpha files.

Advisory Alpha state never authorizes Alpha writes, Alpha content copying, operational Alpha integration, adaptive-platform writes, or database contact.

## Action Model

Supported actions are:

- create_or_update_files
- validate
- commit
- push
- audit
- closeout

A task contract must list only the actions explicitly authorized for that task.

## Safety Flags

Safety flags are explicit booleans. Normal compiler docs-only tasks set all of these to false:

```yaml
allow_alpha_write: false
allow_adaptive_platform_write: false
allow_database_contact: false
allow_canonical_promotion: false
allow_student_visible_output: false
allow_live_deployable_output: false
allow_ocr: false
allow_parser_implementation: false
allow_dependency_addition: false
allow_mvp_tag_move: false
```

## Report Model

The report object records whether a final report is required, the report format, and the recommended next task.

Supported report formats:

- codex_task_report
- codex_commit_report
- codex_push_report
- codex_readiness_audit_report

## Docs-Only Task Contract Example

```yaml
task_id: EXAMPLE-DOCS-ONLY-TASK-001
repository: Curriculum-Intelligence-Compiler
risk_class: docs_only
baseline:
  mode: exact_commit
  expected_head: example_head
  branch: main
policy_refs:
  - compiler_non_live_v1
allowed_paths:
  - docs/course_compiler_demo/example.md
actions:
  - create_or_update_files
  - validate
  - commit
  - push
source_snapshot:
  snapshot_id: committed_compiler_artifacts
  source_type: compiler_side
  live_alpha_access: forbidden
safety_flags:
  allow_alpha_write: false
  allow_adaptive_platform_write: false
  allow_database_contact: false
  allow_canonical_promotion: false
  allow_student_visible_output: false
  allow_live_deployable_output: false
  allow_ocr: false
  allow_parser_implementation: false
  allow_dependency_addition: false
  allow_mvp_tag_move: false
report:
  required: true
  format: codex_task_report
  recommended_next_task: EXAMPLE-DOCS-ONLY-TASK-COMMIT-001
```

## Non-Live Implementation Task Contract Example

```yaml
task_id: EXAMPLE-NON-LIVE-IMPLEMENTATION-001
repository: Curriculum-Intelligence-Compiler
risk_class: non_live_compiler_implementation
baseline:
  mode: exact_commit
  expected_head: example_head
  branch: main
policy_refs:
  - compiler_non_live_v1
allowed_paths:
  - tools/course_compiler_demo/example_module.py
  - reports/course_compiler_demo/example_output/
actions:
  - create_or_update_files
  - validate
source_snapshot:
  snapshot_id: committed_compiler_artifacts
  source_type: compiler_side
  live_alpha_access: forbidden
safety_flags:
  allow_alpha_write: false
  allow_adaptive_platform_write: false
  allow_database_contact: false
  allow_canonical_promotion: false
  allow_student_visible_output: false
  allow_live_deployable_output: false
  allow_ocr: false
  allow_parser_implementation: false
  allow_dependency_addition: false
  allow_mvp_tag_move: false
report:
  required: true
  format: codex_task_report
  recommended_next_task: EXAMPLE-NON-LIVE-IMPLEMENTATION-COMMIT-001
```

## Alpha Scope-Lock Task Contract Example

```yaml
task_id: EXAMPLE-ALPHA-SCOPE-LOCK-001
repository: Curriculum-Intelligence-Compiler
risk_class: alpha_integration_scope_lock
baseline:
  mode: current_synced_main
  expected_head: remote_main
  branch: main
policy_refs:
  - compiler_non_live_v1
allowed_paths:
  - docs/course_compiler_demo/example_alpha_scope_lock.md
actions:
  - create_or_update_files
  - validate
  - closeout
source_snapshot:
  snapshot_id: scope_lock_only
  source_type: compiler_side
  live_alpha_access: advisory_only
safety_flags:
  allow_alpha_write: false
  allow_adaptive_platform_write: false
  allow_database_contact: false
  allow_canonical_promotion: false
  allow_student_visible_output: false
  allow_live_deployable_output: false
  allow_ocr: false
  allow_parser_implementation: false
  allow_dependency_addition: false
  allow_mvp_tag_move: false
report:
  required: true
  format: codex_task_report
  recommended_next_task: EXAMPLE-ALPHA-SCOPE-LOCK-COMMIT-001
```

## Validation Expectations

Validation should confirm required fields, risk_class, repository, baseline mode, compiler_non_live_v1 policy reference, allowed paths, supported actions, source snapshot behavior, safety flags, and report model.

Validation must also verify that task results remain inside allowed paths and do not violate protected boundaries.

## What This Does Not Implement

This task contract specification does not implement a lane runner.

This task contract specification does not authorize Alpha staging implementation.

This task contract specification does not authorize writing into adaptive-platform.

This task contract specification does not authorize migrations, backend endpoints, frontend views, DB tables, or integration files in Alpha.

This task contract specification does not authorize parser implementation, OCR, importers, DB contact, canonical promotion, or student-visible delivery.

## Recommended Next Tasks

1. COURSE-COMPILER-TASK-CONTRACT-SPEC-COMMIT-001
2. COURSE-COMPILER-TASK-CONTRACT-SPEC-PUSH-001
3. COURSE-COMPILER-TASK-CONTRACT-SPEC-READINESS-AUDIT-001
4. COURSE-COMPILER-TASK-CONTRACT-TEMPLATE-001
5. COURSE-COMPILER-CANDIDATE-BASE-SPEC-001

## Do Not Do Yet

Do not implement a lane runner.

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
