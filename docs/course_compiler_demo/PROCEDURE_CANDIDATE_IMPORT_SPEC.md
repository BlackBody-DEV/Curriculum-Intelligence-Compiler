# Procedure Candidate Import Specification

## Purpose

This specification defines how future Alpha 2.0 procedure-like reference material could be converted into non-live compiler procedure candidates.

This specification does not authorize import.

This specification defines contracts, review gates, safety boundaries, evidence requirements, rights/privacy gates, validation requirements, audit requirements, and closeout criteria for a later separately authorized task.

## Current Baseline

Current published baseline: 4b824ac471595d76ab865ba52987eda4aa9ebf2d

MVP tag remains fixed at c7837b3eb9afff6cebca9536311844abe382a737.

## Source Census Basis

The Alpha 2.0 reference census identified 80 prioritized reference candidates.

The Alpha 2.0 reference census identified 37 candidate_for_non_live_import entries.

The Alpha 2.0 reference census identified 31 requires_rights_review entries.

Every Alpha 2.0 census matrix entry has copying_allowed_now: false.

The source census is advisory only. It does not grant rights, canonical approval, import approval, student delivery approval, or operational Alpha integration approval.

## Scope

This specification covers a future non-live procedure candidate import design.

It describes how a future dry-run importer should identify structure, metadata, source evidence, micro-skill alignment, validation needs, and review requirements without copying protected source wording into compiler outputs.

## Explicit Non-Goals

This specification does not authorize import.

This specification does not authorize copying Alpha 2.0 procedure bodies.

This specification does not authorize copying Alpha 2.0 question prompts.

This specification does not authorize copying Alpha 2.0 solutions.

This specification does not authorize canonical promotion.

This specification does not authorize operational Alpha integration.

This specification does not authorize database writes.

This specification does not authorize student-visible delivery.

This specification does not authorize OCR, parser implementation, dependency installation, or real source document processing.

## Allowed Source Classes

Allowed source classes for a later specification may include:

- Alpha 2.0 census entries classified as candidate_for_non_live_import.
- Alpha 2.0 census entries classified as safe_validation_pattern, for validation structure only.
- Alpha 2.0 census entries classified as safe_audit_pattern, for audit workflow structure only.
- Entries that include source evidence, path metadata, hash identity, and review-required status.

Allowed use remains structural and advisory unless a later task explicitly authorizes a non-live import dry run.

## Disallowed Source Classes

Disallowed source classes include:

- Entries classified as do_not_import.
- Entries with unknown, restricted, private, or unclear rights status unless blocked from public-facing use and canonical promotion.
- Entries containing private student, family, company, or institutional data unless sanitized and explicitly approved.
- Any full Alpha 2.0 procedure body, full worked example, full question prompt, full solution, or textbook-derived explanation.
- Any material intended for immediate canonical, live, production, operational Alpha, or student-visible use.

## Procedure Candidate Definition

A procedure candidate is a non-live, review-required instructional object that may describe the concept, variables, formulas, steps, worked-example pattern, common errors, failure signals, source evidence, and review status for a target micro-skill.

A procedure candidate is not canonical.

A procedure candidate is not active.

A procedure candidate is not student-visible.

A procedure candidate is not production-ready.

A procedure candidate may not be promoted without separate mathematical, pedagogical, rights, and human review.

## Target Non-Live Output Shape

A future non-live procedure candidate record should include at least:

- candidate_id
- candidate_type
- status
- source_origin
- source_file_path
- source_artifact_type
- subject_guess
- topic_guess
- subtopic_guess
- micro_skill_guess
- procedure_title
- concept_summary
- formula_refs
- variables
- procedure_steps_summary
- worked_example_pattern_summary
- common_error_candidates
- failure_signal_candidates
- evidence_refs
- rights_status
- privacy_status
- review_status
- mathematical_review_status
- pedagogical_review_status
- rights_review_status
- canonical_promotion_status
- copying_allowed_now
- student_visible
- live_deployable
- created_by
- created_at
- notes

Required default values:

- status: human_review_required
- review_status: review_pending
- canonical_promotion_status: not_authorized
- copying_allowed_now: false
- student_visible: false
- live_deployable: false

## Required Metadata

Required metadata includes source path, source hash, source artifact type, subject guess, topic guess, subtopic guess, micro-skill guess, creation metadata, and review status.

Metadata must be sufficient to trace a candidate back to census evidence without copying full source content into compiler outputs.

## Required Evidence Fields

Every imported procedure candidate must preserve source evidence.

Minimum evidence fields:

- source_repo_root
- source_file_path
- source_file_sha256
- source_artifact_type
- source_heading_or_key
- source_reference_note
- extraction_method
- confidence
- reviewer_required

Evidence may identify where the idea came from, but must not copy full proprietary source wording.

## Rights and Privacy Gate

If rights status is unknown, restricted, source-derived, or unclear, the candidate must be blocked from public-facing use and canonical promotion.

If the source contains private student, family, company, or institutional data, the candidate must be blocked until sanitized and explicitly approved.

The safest default is:

- analyze structure
- classify micro-skills
- generate original AxiomIQ wording later
- do not republish source wording
- keep candidate non-live and human_review_required

## Mathematical Review Gate

Mathematical review must confirm formula correctness, variable definitions, step logic, worked-example computation, final-answer consistency, and failure-signal validity.

No candidate may move beyond review_pending until mathematical review is explicitly passed.

## Pedagogical Review Gate

Pedagogical review must confirm conceptual clarity, step sequencing, learner-facing usefulness, accessibility of language, and alignment to the intended micro-skill.

Pedagogical review must also confirm that common-error and failure-signal candidates are useful for instruction rather than merely descriptive.

## Procedure Preservation Gate

The import process must preserve enough structural information to support review while avoiding verbatim transfer of protected source wording.

Procedure preservation means preserving source evidence, step categories, formula references, variable roles, and review notes. It does not mean copying source-authored procedure prose.

## Source Wording Boundary

The import pipeline must not copy full procedure bodies from Alpha 2.0 into compiler output.

The import pipeline must not copy full worked examples.

The import pipeline must not copy textbook-derived explanations.

The import pipeline must not copy full solution text.

The import pipeline may use Alpha 2.0 material to identify structure, metadata, micro-skill alignment, validation patterns, and review requirements.

If future import is authorized, imported candidates should prefer summarized structure and later AxiomIQ-authored wording.

## Alpha 2.0 Boundary

Alpha 2.0 reference material remains reference-only unless a future task explicitly authorizes a non-live import dry run.

The Alpha 2.0 repository must not be modified.

Operational Alpha must not be modified.

Alpha 2.0 material must not be copied into canonical content or served to students.

## Non-Live Compiler Boundary

All procedure candidates must remain non-live.

Future outputs must be local, review-required, not student-visible, not live-deployable, and not production-ready.

No database contact is authorized.

## Canonical Promotion Boundary

canonical_promotion_status: not_authorized

Canonical promotion requires a separate task, explicit authorization, mathematical review, pedagogical review, rights review, privacy review, and human sign-off.

No candidate created under this specification may be active, canonical, student-visible, or live-deployable.

## Import Eligibility Matrix

| Reuse Classification | Eligible for Immediate Import | Allowed Use | Required Review | Risk Level | Recommended Action |
| --- | --- | --- | --- | --- | --- |
| safe_validation_pattern | No | Reference validation structure only | Architect and validation review | Medium | Use to design validation checks in a later spec |
| safe_audit_pattern | No | Reference audit workflow structure only | Architect and audit review | Medium | Use to design audit gates in a later spec |
| candidate_for_non_live_import | No | Candidate scoping for non-live procedure import | Rights, privacy, mathematical, pedagogical, and human review | High | Create a dry-run import spec before any implementation |
| requires_rights_review | No | Reference only until rights are resolved | Rights and privacy review first | High | Block from import until cleared |
| requires_architect_review | No | Architecture planning only | Architect review first | High | Block from import until architecture is approved |
| do_not_import | No | None beyond risk awareness | Human confirmation of exclusion | High | Do not import |

## Review Status Lifecycle

Suggested review states:

1. review_pending
2. evidence_checked
3. rights_privacy_checked
4. math_review_pending
5. pedagogy_review_pending
6. human_signoff_pending
7. approved_for_non_live_dry_run
8. blocked

No lifecycle state authorizes canonical promotion or student-visible delivery.

## Validation Requirements

Future implementation validation must check:

- all candidates are human_review_required
- copying_allowed_now is false
- student_visible is false
- live_deployable is false
- canonical_promotion_status is not_authorized
- rights_status is present
- privacy_status is present
- source evidence is present
- micro_skill_guess is present or review_required
- no full Alpha procedure body copied
- no full source question prompt copied
- no full solution copied
- no DB contact
- no operational Alpha contact
- no canonical promotion

## Audit Requirements

Every future dry-run import task must produce an audit report that lists candidate counts, blocked counts, rights-risk counts, review status counts, validation failures, and explicit boundary checks.

The audit must verify that no source body, full prompt, or full solution text was copied.

The audit must verify that every candidate remains non-live, review-required, not canonical, not active, not student-visible, and not live-deployable.

## Example Candidate Record Shape

```json
{
  "candidate_id": "PROC_CANDIDATE_EXAMPLE_001",
  "candidate_type": "procedure_candidate",
  "status": "human_review_required",
  "source_origin": "alpha2_reference_census",
  "source_file_path": "path/from/census.json",
  "source_artifact_type": "procedure_pattern",
  "subject_guess": "UNKNOWN",
  "topic_guess": "review_required",
  "subtopic_guess": "review_required",
  "micro_skill_guess": "review_required",
  "procedure_title": "review_required",
  "concept_summary": "summary_to_be_authored",
  "formula_refs": [],
  "variables": [],
  "procedure_steps_summary": [],
  "worked_example_pattern_summary": "summary_to_be_authored",
  "common_error_candidates": [],
  "failure_signal_candidates": [],
  "evidence_refs": [],
  "rights_status": "unknown",
  "privacy_status": "unknown",
  "review_status": "review_pending",
  "mathematical_review_status": "review_pending",
  "pedagogical_review_status": "review_pending",
  "rights_review_status": "review_pending",
  "canonical_promotion_status": "not_authorized",
  "copying_allowed_now": false,
  "student_visible": false,
  "live_deployable": false,
  "created_by": "course_compiler_non_live_import_dry_run",
  "created_at": "to_be_generated",
  "notes": "No source wording copied."
}
```

## Failure and Block Conditions

Block a candidate if:

- source evidence is missing
- source hash is missing
- rights status is unknown, restricted, source-derived, or unclear
- privacy status is unknown or risky
- micro-skill alignment is not reviewable
- formula correctness cannot be verified
- procedure steps are incomplete or incoherent
- worked-example computation is not verified
- full Alpha procedure body is copied
- full source question prompt is copied
- full solution text is copied
- student_visible is true
- live_deployable is true
- canonical_promotion_status is anything other than not_authorized
- database contact occurs
- operational Alpha contact occurs

## Recommended Future Implementation Tasks

1. COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-SPEC-COMMIT-001
2. COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-SPEC-PUSH-001
3. COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-SPEC-001
4. COURSE-COMPILER-GENERATION-FAMILY-IMPORT-SPEC-001
5. COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-DRY-RUN-SPEC-001
6. COURSE-COMPILER-PROCEDURE-CANDIDATE-VALIDATION-SPEC-001
7. COURSE-COMPILER-ACEF-REVIEW-PRESENTATION-PACKAGE-001
8. COURSE-COMPILER-INGEST-PDF-TEXT-ONLY-SPEC-001
9. COURSE-COMPILER-IMAGE-DIAGRAM-METADATA-SPEC-001
10. COURSE-COMPILER-OCR-RISK-AND-EVALUATION-SPEC-001

## Do Not Do Yet

Do not import Alpha 2.0 procedures.

Do not copy Alpha 2.0 procedure bodies.

Do not copy Alpha 2.0 question prompts.

Do not copy Alpha 2.0 solutions.

Do not create canonical procedures.

Do not create student-visible procedures.

Do not implement the import pipeline.

Do not connect to any database.

Do not modify operational Alpha.

Do not implement OCR.

Do not implement PDF, DOCX, spreadsheet, slide, image, ZIP, folder, or LMS ingestion.
