# Curriculum Intake Engine Feature Spec

## Feature Name

Curriculum Intake Engine

## Status

Documentation-only feature specification. Implementation is not authorized in this task.

Default compiler artifact status: `human_review_required`.

No compiler output becomes active without human review.

## Purpose

The Curriculum Intake Engine will define a controlled intake workflow for subject-related curriculum artifacts before they enter compiler processing. It will preserve original source artifacts, organize compiler outputs by intake run, and produce ACEF-aligned review scaffolds that help human reviewers decide what can later become useful to AxiomIQ.

## Problem Being Solved

The current demo proves a local math document-to-practice pipeline, but it does not yet define a durable intake model for real curriculum artifacts. Before implementation expands, the repository needs a clear feature contract for:

- where new source artifacts are placed,
- how originals are preserved,
- how intake runs are identified,
- where compiler outputs are written,
- how ACEF alignment is scaffolded,
- how review status is represented,
- and how the workflow prevents accidental canonical promotion.

## Core Workflow

1. An operator places source material into `incoming/`.
2. The intake engine assigns an `intake_id`.
3. The original source artifact is copied or recorded under `original_artifacts/` without mutation.
4. The engine creates an `intake_record.json` describing source identity, provenance, file type, operator notes, and processing intent.
5. The engine creates an isolated run folder under `compiler_output/intake_runs/`.
6. The compiler produces structured outputs inside the intake run folder.
7. The engine emits `acef_package_scaffold.json` with ACEF linkage placeholders and `human_review_required` status.
8. A reviewer inspects the output using `review_before_commit` policy before anything is committed, promoted, or used in downstream work.

## Required Folder Model

The first implementation should use this model:

```text
incoming/
original_artifacts/
compiler_output/
compiler_output/intake_runs/
tools/course_compiler_demo/intake/
```

This feature spec does not create those folders. It only defines their intended responsibilities.

## Folder Responsibilities

- `incoming/`: operator drop zone for new curriculum artifacts awaiting intake.
- `original_artifacts/`: preservation area for unmodified source files and metadata references.
- `compiler_output/`: top-level container for generated compiler artifacts.
- `compiler_output/intake_runs/`: per-run output folders keyed by `intake_id`.
- `tools/course_compiler_demo/intake/`: future implementation location for intake-specific local tooling.

## Intake Record

Each intake run should create an `intake_record.json` containing, at minimum:

- `intake_id`
- source filename and source path
- original artifact preservation path
- detected file type
- source subject guess
- operator-supplied subject, course, or use-mode hints
- intake timestamp
- artifact status set to `human_review_required`
- review policy set to `review_before_commit`
- non-live boundary flags
- no DB contact confirmation
- no operational Alpha contact confirmation

The `intake_id` should be stable enough to link all generated artifacts from the same run without relying on filenames alone.

## ACEF Alignment

The intake engine must align with the ACEF rule that content is useful only when it can be traced through the required curriculum chain.

A question is only useful to AxiomIQ if it is linked to:

```text
Subject → Topic → Subtopic → Micro-skill → Procedure → Question
```

A procedure is only useful to AxiomIQ if it is linked to:

```text
Subject → Topic → Subtopic → Micro-skill
```

The intake engine should not claim that these links are complete merely because the compiler detected candidate material. Compiler output should be treated as candidate scaffolding until human review confirms the chain.

## ACEF Status Policy

Every generated intake artifact should default to:

```text
human_review_required
```

No compiler output becomes active without human review.

The first implementation should avoid status names that imply approval, activation, canonical status, live readiness, or mastery impact. Acceptable early statuses include:

- `human_review_required`
- `review_ready`
- `review_blocked`
- `rejected_by_review`
- `approved_for_demo_only`

Canonical, production, or operational status names are out of scope for the first implementation.

## ACEF Package Scaffold

Each intake run should produce an `acef_package_scaffold.json` with an explicit package identifier such as:

```text
ACEF_PACKAGE_v0_1
```

The scaffold should organize candidate data around the ACEF chain:

- subject candidates
- topic candidates
- subtopic candidates
- micro-skill candidates
- procedure candidates
- question candidates
- evidence references
- missing-link warnings
- review notes
- status: `human_review_required`
- policy: `review_before_commit`

The scaffold is not canonical curriculum. It is a structured review aid.

## Procedure and Question Priority

The intake engine should support both procedure-first and question-first textbook extraction priority.

Procedure-first priority means the compiler should identify explanatory steps, worked examples, or procedural descriptions before linking related questions.

Question-first priority means the compiler should identify practice questions, assessment items, or exercises before linking them back to required procedures and micro-skills.

Both paths must converge on the ACEF chains. A question without `Subject → Topic → Subtopic → Micro-skill → Procedure → Question` linkage remains `human_review_required`. A procedure without `Subject → Topic → Subtopic → Micro-skill` linkage remains `human_review_required`.

## Textbook Extraction Focus

The first intake engine should focus on textbook-like source artifacts where procedures and questions may appear near each other but still require careful linkage. The intake record should preserve page, section, heading, and local evidence references when available.

Extraction should favor reviewability over completeness. Missing links should be explicit rather than silently inferred.

## Original Artifact Policy

Original document preservation is mandatory. Intake processing must not overwrite, normalize, redact, split, or rewrite the original source artifact in place.

The future `original_artifacts/` area should keep the original file or a traceable preserved copy. Compiler outputs should reference the preserved original through `intake_id`, source path, checksum if available, and evidence references.

## Output Organization Policy

Compiler outputs should be organized by intake run under `compiler_output/intake_runs/`. A run folder should be uniquely associated with one `intake_id`.

Generated outputs may include:

- `intake_record.json`
- `source_document.json`
- `source_interpretation.json`
- `acef_package_scaffold.json`
- extracted candidate packages
- validation reports
- review checklists

Outputs should remain separate from original artifacts and should not be committed until reviewed under `review_before_commit`.

## Non-Live Boundary

This feature is non-live. No database contact is allowed. No operational Alpha contact is allowed. No canonical promotion is allowed.

The intake engine must not touch backend application code, frontend application code, migrations, production seed files, canonical content files, operational Alpha procedure files, operational Alpha question files, grading files, routing files, readiness files, or mastery files unless a future task explicitly authorizes that work.

## First Implementation Scope

The first implementation should be local and file-based only. It should:

- detect files in `incoming/`,
- create an `intake_id`,
- preserve originals under `original_artifacts/`,
- create `intake_record.json`,
- create a run folder under `compiler_output/intake_runs/`,
- emit `acef_package_scaffold.json`,
- set generated artifact status to `human_review_required`,
- enforce `review_before_commit`,
- and avoid any database or operational Alpha contact.

## First Test Case

The first test case should use a small textbook-like math source containing both procedural explanation and practice questions.

Expected result:

- one `intake_id`,
- one preserved original artifact reference,
- one `intake_record.json`,
- one `acef_package_scaffold.json`,
- procedure candidates,
- question candidates,
- explicit missing-link warnings,
- all generated artifacts marked `human_review_required`,
- no DB contact,
- no operational Alpha contact,
- no canonical promotion.

## Success Criteria

- Intake run is reproducible from local files.
- Original artifact remains preserved and unmodified.
- `intake_id` links the record, preserved artifact, and outputs.
- `intake_record.json` is valid JSON.
- `acef_package_scaffold.json` is valid JSON.
- ACEF chains are represented explicitly.
- Missing ACEF links are visible to reviewers.
- All compiler-generated artifacts default to `human_review_required`.
- `review_before_commit` is enforced as policy.
- No database contact occurs.
- No operational Alpha contact occurs.
- No canonical promotion occurs.

## Explicit Non-Goals

- Implementing the intake engine in this task.
- Creating `incoming/`.
- Creating `original_artifacts/`.
- Creating `compiler_output/`.
- Modifying compiler code.
- Modifying final demo outputs.
- Connecting to any database.
- Touching operational Alpha.
- Promoting canonical curriculum.
- Activating generated procedures or questions.
- Updating readiness or mastery.

## Future Expansion

Future versions may add checksum capture, multi-file intake bundles, richer textbook section detection, page-level evidence mapping, human review UI support, batch validation, and tighter schema enforcement.

Any future expansion must preserve original document preservation, `human_review_required` defaults, `review_before_commit`, no DB contact unless explicitly authorized, no operational Alpha contact unless explicitly authorized, and no canonical promotion without human governance.

## Recommended Next Implementation Task

COURSE-COMPILER-INTAKE-FEATURE-SPEC-COMMIT-001
