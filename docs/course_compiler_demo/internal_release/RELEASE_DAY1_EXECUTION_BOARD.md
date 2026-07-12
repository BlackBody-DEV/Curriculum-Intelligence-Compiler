# Release Day 1 Execution Board

## Current Objective

Deliver one controlled internal Statics vertical slice by July 19, 2026.

## Locked Procedure Set

Reference:

docs/course_compiler_demo/internal_release/RELEASE_DAY1_STATICS_PROCEDURE_SET_LOCK.md

## Current Blockers

1. compiler-to-Alpha controlled package import path is not proven
2. learner session for a release package is not proven
3. release-package grading/failure-signal/readiness persistence is not proven
4. prerequisite procedure gaps exist but are not Day 1 blockers unless Day 2 proof requires them
5. Alpha internal_loading_at_section draft is classified outside Day 1 release path

## Day 1 Critical Path

1. COMPILER-PACKAGE-BOUNDARY-PROBE-001
2. ALPHA-INTERNAL-VERTICAL-SLICE-GAP-AUDIT-001
3. RELEASE-DAY1-ONE-MICRO-SKILL-PROOF-TARGET-001
4. RELEASE-DAY1-CONTENT-BATCH-0-SEED-PACKET-001
5. RELEASE-DAY1-INTEGRATION-OWNER-BOARD-001

## Execution Board Table

| task ID | owner | repository | allowed paths | dependencies | parallelizable | acceptance criteria | permission boundary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| COMPILER-PACKAGE-BOUNDARY-PROBE-001 | Compiler Pod | /Users/fanarichardson/Documents/AxiomIQ | reports/course_compiler_demo/release_day1_probe/**; tools/course_compiler_demo/**; tests/course_compiler_demo/** | clean compiler repo | yes | prove existing compiler can produce or simulate a non-live package to import-boundary shape for one locked release micro-skill, or list smallest missing task | compiler-side only; no Alpha writes |
| ALPHA-INTERNAL-VERTICAL-SLICE-GAP-AUDIT-001 | Application Pod | /Users/fanarichardson/adaptive-platform | read-only | internal_loading draft classified outside Day 1 release path | yes | exact gap list from controlled import/staging to learner session, grading, failure signals, persistence, and performance retrieval | read-only; no DB mutation; no migrations |
| RELEASE-DAY1-ONE-MICRO-SKILL-PROOF-TARGET-001 | Architect + Compiler/Application Pods | report-only | report-only | package-boundary probe + vertical-slice gap audit | no | selected Day 2 proof target from locked release set, preferably vector_components_2d or resultant_magnitude unless evidence selects another | no repo write unless later prompt authorizes |
| RELEASE-DAY1-CONTENT-BATCH-0-SEED-PACKET-001 | Content Pod | pending target chosen by proof task | exact path pending proof target | proof target selected | yes after target selection | procedure, question seeds, generation family, answer logic, failure signals, review status, and known limitations for the proof micro-skill | exact-path content only; no canonical/student-visible promotion |
| RELEASE-DAY1-INTEGRATION-OWNER-BOARD-001 | Architect | compiler report path unless Alpha spline authorizes otherwise | docs-only release board/report path | Day 1 board lock | yes | integration owner, shared interfaces, branch rules, four-hour integration checkpoints, and file ownership map | docs-only unless Alpha spline authorizes implementation |

## Deferred Items

- OCR
- universal parser work
- all-98 procedure completion
- public release
- instructor dashboards
- generalized orchestration infrastructure
- Alpha staging implementation unless opened through an authorized release integration contract
