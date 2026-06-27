# AxiomIQ Curriculum Intelligence Compiler Post-MVP Roadmap

## Current Published State

The current published state is a non-live AxiomIQ Curriculum Intelligence Compiler math demo MVP on `main`. It includes a local math document input, source interpretation, math topic and micro-skill extraction, practice module packaging, practice assessment packaging, performance tracking preview, validation reporting, demo reporting, content gap reporting, an operator README, an expected-output manifest, and a repeatable smoke test.

All learning outputs are `demo_unverified`. The MVP does not update operational Alpha readiness or mastery. The MVP does not contact any database. The MVP does not promote canonical curriculum.

## Frozen MVP Checkpoint

The frozen MVP checkpoint is:

```text
v0.1.0-math-demo-mvp -> c7837b3eb9afff6cebca9536311844abe382a737
```

That tag represents the completed math demo MVP before post-MVP stabilization documentation. It must remain fixed and must not be moved or recreated.

## What the MVP Proves

The MVP proves that the compiler lane can run as a local, non-live pipeline from a math source document to structured curriculum intelligence outputs. It demonstrates:

- Source loading and interpretation for a sample Algebra I document.
- Topic and micro-skill candidate extraction.
- Demo practice module packaging.
- Demo practice assessment packaging.
- Demo performance tracking preview generation.
- Demo content gap reporting.
- Validation and human-readable reporting.
- A smoke-testable operator workflow.
- Non-Live boundary language and `demo_unverified` labeling across generated learning outputs.

## Non-Live Boundary

This project remains a Non-Live demo lane. It does not contact production databases, hosted databases, local databases, student data stores, live APIs, operational Alpha procedures, operational Alpha questions, readiness files, mastery files, grading files, or routing files.

The compiler output is not canonical curriculum. It is not production-ready content. It does not update operational Alpha readiness or mastery. It does not represent reviewed instructional material. All generated learning outputs are `demo_unverified` until a separate review, approval, and production-readiness process exists.

## Must-Do Before External Demo

- Prepare an external demo package that explains the run command, smoke-test command, output folder, and expected result in one operator-facing path.
- Add a concise demo script or walkthrough that helps a viewer understand what each generated artifact proves.
- Freeze a known-good external demo output folder separate from ad hoc local test outputs.
- Confirm the smoke test passes from a clean clone using only documented commands.
- Review all public-facing wording for Non-Live, `demo_unverified`, no database contact, and no operational Alpha update boundaries.
- Add a short troubleshooting section for missing Python, wrong working directory, malformed input path, or unexpected dirty worktree.

## Should-Do Next

- Harden the expected-output manifest so it can distinguish schema regressions from harmless report wording changes.
- Add focused regression checks around key package fields, status labels, and report markers.
- Add a script option for temporary output directories so smoke tests can run without leaving generated files behind.
- Add a lightweight changelog for demo-lane milestones.
- Add a small architecture note describing the current pipeline stages and file ownership boundaries.

## Product Hardening

- Formalize schemas for every emitted package and report summary.
- Separate validation into structural validation, boundary validation, content-quality validation, and operator-readiness validation.
- Add deterministic run metadata so outputs can be compared safely across runs.
- Add test fixtures for multiple math source shapes, including thin sources and malformed documents.
- Add explicit error codes for missing input, unsupported subject, invalid mode, failed validation, and incomplete packaging.
- Improve logging so operators can diagnose failures without reading source code.

## Multi-Subject Expansion

Multi-subject work should wait until the math demo lane is stable. Expansion should proceed by isolated slices, each with its own sample input, expected-output manifest, smoke test, and boundary review.

Recommended order:

- Physics demo slice using the existing sample input as a constrained second subject.
- Additional math source shapes before broad subject expansion.
- Science course document patterns after physics proves reusable abstractions.
- Humanities or writing-heavy documents only after extraction confidence and evidence modeling improve.

No subject expansion should imply canonical curriculum or live readiness.

## Validation and Quality Gates

Every future stage should preserve these gates:

- Worktree clean before starting.
- Changes isolated to the authorized lane.
- No backend, frontend, migration, canonical content, operational Alpha, grading, routing, readiness, or mastery files touched unless separately authorized.
- No database contact.
- All learning outputs retain `demo_unverified`.
- Smoke test exits `0`.
- Expected-output manifest remains valid JSON.
- Reports include Non-Live and no operational Alpha readiness or mastery update language.
- MVP tag remains fixed at the frozen checkpoint.

## UX / Operator Experience

The next operator experience goal is a clean external demo path. An operator should be able to clone the repository, read one guide, run one command, run one smoke test, and understand the output set without chat history.

Useful additions include:

- A one-page external demo checklist.
- Cleaner smoke-test console output.
- Optional `--output` guidance for temporary or named demo runs.
- A report index that points to `demo_report.md`, `content_gap_report.md`, and `validation_report.json`.
- Better failure messages when expected files or markers are missing.

## Future Integration With AxiomIQ Alpha

Future integration with AxiomIQ Alpha must remain deferred until explicit authorization. Before any integration, the compiler needs reviewed content workflows, stronger schemas, human approval gates, privacy and rights checks, production readiness criteria, and a clear contract for how outputs would be consumed.

Any future Alpha integration must explicitly preserve operational safety:

- No direct readiness or mastery updates from demo outputs.
- No unreviewed generated content entering live learner workflows.
- No database writes without a dedicated integration design and approval.
- No canonical curriculum promotion without review and governance.

## Explicitly Deferred Work

- Production curriculum generation.
- Canonical curriculum promotion.
- Live operational Alpha readiness updates.
- Live operational Alpha mastery updates.
- Database writes or reads.
- Student data access.
- Hosted service integration.
- Broad subject support.
- Automated content approval.
- GitHub release creation.
- CI or deployment changes.

## Risk Register

- Boundary drift: Future work could accidentally imply live readiness or canonical status. Mitigation: keep `demo_unverified` and Non-Live checks in smoke tests.
- Output regression: Small code changes could alter required fields or report language. Mitigation: harden schemas and expected-output checks.
- Operator confusion: Demo outputs may look more production-ready than they are. Mitigation: improve operator docs and report boundary language.
- Over-expansion: Adding subjects too early could weaken the math lane. Mitigation: expand by small isolated slices with their own validation.
- Integration pressure: Future Alpha integration may be attempted before review gates exist. Mitigation: keep integration explicitly deferred until authorized.
- Generated-file noise: Smoke tests can leave output folders or caches. Mitigation: add cleanup options and keep commit scopes narrow.

## Recommended Next 5 Tasks

1. COURSE-COMPILER-ROADMAP-COMMIT-001
2. COURSE-COMPILER-EXTERNAL-DEMO-PACKAGE-001
3. COURSE-COMPILER-SCHEMA-HARDENING-001
4. COURSE-COMPILER-MULTI-DOCUMENT-INPUT-001
5. COURSE-COMPILER-PHYSICS-DEMO-SLICE-001
