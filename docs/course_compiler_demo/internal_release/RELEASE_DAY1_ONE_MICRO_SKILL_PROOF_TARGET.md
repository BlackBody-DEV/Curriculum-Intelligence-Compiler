# Release Day 1 One-Micro-Skill Proof Target

## Final Target

vector_components_2d

## Rationale

`vector_components_2d` is selected as the Day 2 one-micro-skill proof target because:

- it is graph-confirmed
- it is procedure-backed
- it is first in the locked learner sequence
- it was the selected proof target in the compiler package-boundary probe
- it is narrow enough for a Day 2 end-to-end proof
- it supports simple question seeds, grading, and failure-signal validation

This target keeps the Day 2 proof focused on the release-critical bridge from compiler package shape into an internal Alpha practice loop, without expanding into broader Statics coverage or all-Phase-D completion.

## Required Day 2 Proof Package

The Day 2 proof package must include:

- package_id
- selected_micro_skill_code: vector_components_2d
- subject/topic/subtopic
- procedure candidate or procedure reference
- question candidate or question seed
- generation family candidate or generation-family seed
- evidence_refs
- rights_status
- privacy_status
- review_status
- canonical_promotion_status: not_authorized
- copying_allowed_now: false
- student_visible: false
- live_deployable: false
- answer logic
- grading expectation
- failure-signal mapping
- known limitations

The package may be simulated only where explicitly authorized, but it must preserve the release boundary: no canonical promotion, no live/public exposure, no student-visible publishing, and no operational Alpha write unless a later task explicitly authorizes that action.

## Required Alpha Binding Proof

The Day 2 proof must demonstrate this chain:

1. controlled package import/staging
2. package review/approval gate
3. practice module opening
4. learner route/rendering
5. answer submission
6. grading/evaluation
7. failure signal generation/display
8. readiness/progress persistence
9. performance retrieval
10. package smoke path

## Current Release Blockers

- actual Statics release package emitter is not implemented
- `vector_components_2d` question seed and generation family are placeholders
- controlled Alpha package import/staging is partial
- package-specific review/approval gate is partial
- package-to-practice runtime bridge is not proven
- package-specific grading/failure-signal/progress persistence path is not proven

## Day 2 Minimum Success Criteria

Day 2 succeeds only if an internal authenticated user can open a `vector_components_2d` practice module sourced from the proof package, submit an answer, receive grading and a failure signal, and produce persistent retrievable performance data.

## Non-Goals

- no public release
- no canonical promotion
- no general student-visible publishing
- no multi-skill package requirement
- no OCR
- no universal parser work
- no all-98-procedure completion
- no broad dashboard work

## Recommended Next Tasks

1. RELEASE-DAY1-VECTOR-COMPONENTS-SEED-PACKET-001
2. ALPHA-CONTROLLED-PACKAGE-IMPORT-STAGING-001
3. ALPHA-RELEASE-PACKAGE-REVIEW-GATE-001
4. ALPHA-RELEASE-PACKAGE-PRACTICE-MODULE-OPENING-001
5. ALPHA-RELEASE-PACKAGE-ANSWER-SUBMISSION-BINDING-001
6. ALPHA-RELEASE-PACKAGE-GRADING-ADAPTER-001
7. ALPHA-RELEASE-PACKAGE-FAILURE-SIGNAL-BINDING-001
8. ALPHA-RELEASE-PACKAGE-PROGRESS-PERSISTENCE-BINDING-001
9. ALPHA-RELEASE-PACKAGE-PERFORMANCE-RETRIEVAL-001
10. ALPHA-RELEASE-PACKAGE-SMOKE-PATH-001
