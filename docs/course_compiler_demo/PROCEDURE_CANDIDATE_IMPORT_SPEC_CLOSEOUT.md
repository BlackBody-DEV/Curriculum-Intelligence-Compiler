# Procedure Candidate Import Specification Closeout Report

## Final Verdict

Final verdict: PROCEDURE_CANDIDATE_IMPORT_SPEC_AUDIT_READY

The Procedure Candidate Import Specification lane is audit-ready after review-gate remediation. The lane remains documentation-only, non-importing, non-live, non-canonical, no-DB, no-operational-Alpha, and no-OCR.

## Published Baseline

Current published baseline: ca93621b65aac11fddbb6e95002f949070193b5a

Previous baseline for the initial published specification: e3b13cae3e127490464b7dc0294f4cc904099bb2

Alpha2 reference census closeout baseline: 4b824ac471595d76ab865ba52987eda4aa9ebf2d

## Repository State

Repository: BlackBody-DEV/Curriculum-Intelligence-Compiler

Branch: main

The procedure candidate import specification is spec-only.

## MVP Tag Status

MVP tag remains fixed at c7837b3eb9afff6cebca9536311844abe382a737

The MVP tag was not moved, recreated, or pushed as part of this closeout task.

## Alpha 2.0 Census Basis

The Alpha 2.0 reference census identified 80 prioritized reference candidates.

The Alpha 2.0 reference census identified 37 candidate_for_non_live_import entries.

The Alpha 2.0 reference census identified 31 requires_rights_review entries.

Every Alpha 2.0 census matrix entry has copying_allowed_now: false.

No Alpha 2.0 files were modified.

No Alpha 2.0 files were copied into the compiler.

No Alpha 2.0 content was imported.

## Specification Scope

The procedure candidate import specification defines a future, separately authorized, non-live planning contract for procedure candidate import.

It documents candidate shape, metadata, evidence requirements, review gates, validation requirements, audit requirements, and boundary conditions.

## What Was Specified

The specification defines how future non-live procedure candidates would be described, reviewed, and blocked from live use unless separate review and authorization occur.

It specifies required metadata, source evidence, rights/privacy controls, mathematical review, pedagogical review, review status, and default safety values.

## What Was Not Authorized

The procedure candidate import specification does not authorize import.

The procedure candidate import specification does not authorize copying Alpha 2.0 procedure bodies.

The procedure candidate import specification does not authorize copying Alpha 2.0 question prompts.

The procedure candidate import specification does not authorize copying Alpha 2.0 solutions.

The procedure candidate import specification does not authorize canonical promotion.

The procedure candidate import specification does not authorize operational Alpha integration.

The procedure candidate import specification does not authorize database writes.

The procedure candidate import specification does not authorize student-visible delivery.

The procedure candidate import specification does not authorize OCR.

## Procedure Candidate Definition

A procedure candidate is a non-live, review-required instructional object that may describe the concept, variables, formulas, steps, worked-example pattern, common errors, failure signals, source evidence, and review status for a target micro-skill.

A procedure candidate is not canonical.

A procedure candidate is not active.

A procedure candidate is not student-visible.

A procedure candidate is not production-ready.

A procedure candidate may not be promoted without separate mathematical, pedagogical, rights, and human review.

## Target Non-Live Output Shape

Future non-live procedure candidates should preserve structure, classification, evidence, review status, and default boundary fields.

The target output shape is intended for review staging only, not canonical curriculum, live application behavior, student delivery, or operational Alpha integration.

## Required Default Values

Required default values for future non-live procedure candidates:

status: human_review_required
review_status: review_pending
canonical_promotion_status: not_authorized
copying_allowed_now: false
student_visible: false
live_deployable: false

## Metadata and Evidence Requirements

Required metadata includes candidate identity, source origin, source file path, source artifact type, subject/topic/subtopic guesses, micro-skill guess, rights status, privacy status, and review status.

Required evidence includes source_file_sha256, source_heading_or_key, extraction_method, confidence, reviewer_required, and enough source reference context to support review without copying protected source wording.

## Rights and Privacy Gate

Rights and privacy review is required before any future non-live procedure candidate can advance.

Unknown, restricted, source-derived, or unclear rights status blocks public-facing use and canonical promotion.

Private student, family, institutional, or company data must be blocked until sanitized and explicitly approved.

## Review Gate Requirements

Required procedure candidate review gates:

1. schema validation
2. source evidence validation
3. rights/privacy validation
4. micro-skill alignment review
5. formula correctness review
6. step completeness review
7. worked-example computation review
8. common-error/failure-signal review
9. pedagogical clarity review
10. human sign-off

These gates are required before any future non-live procedure candidate could be considered for review advancement.

## Source Wording Boundary

The import pipeline must not copy full procedure bodies.

The import pipeline must not copy full worked examples.

The import pipeline must not copy textbook-derived explanations.

The import pipeline must not copy full solution text.

Imported candidates should prefer summarized structure and later AxiomIQ-authored wording.

## Import Eligibility Boundary

The specification identifies candidate_for_non_live_import and requires_rights_review as planning classifications only.

No classification is eligible for immediate live import, canonical promotion, operational Alpha use, or student-visible delivery.

## Validation Requirements

Future validation must confirm that all candidates are human_review_required, copying_allowed_now is false, student_visible is false, live_deployable is false, canonical_promotion_status is not_authorized, no DB contact occurred, no operational Alpha contact occurred, and no canonical promotion occurred.

## Audit History

COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-SPEC-001
Result: pass
Summary: Created the non-live procedure candidate import specification.

COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-SPEC-COMMIT-001
Commit: e3b13cae3e127490464b7dc0294f4cc904099bb2

COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-SPEC-PUSH-001
Result: pushed to main.

COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-SPEC-READINESS-AUDIT-001
Result: PROCEDURE_CANDIDATE_IMPORT_SPEC_AUDIT_NO_GO
Reason: required review-gate phrases were missing verbatim.

COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-SPEC-REVIEW-GATE-REMEDIATION-001
Result: PROCEDURE_CANDIDATE_IMPORT_SPEC_REVIEW_GATE_REMEDIATION_READY
Summary: Added the exact required review-gate phrase list.

COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-SPEC-REVIEW-GATE-REMEDIATION-COMMIT-001
Commit: ca93621b65aac11fddbb6e95002f949070193b5a

COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-SPEC-REVIEW-GATE-REMEDIATION-PUSH-001
Result: pushed to main.

COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-SPEC-READINESS-AUDIT-002
Result: PROCEDURE_CANDIDATE_IMPORT_SPEC_AUDIT_READY

## Non-Live Boundary

No procedure import was performed.

No active or canonical promotion was performed.

No database contact occurred.

No operational Alpha contact occurred.

## Human Review Boundary

All future candidates remain human_review_required until separate mathematical, pedagogical, rights/privacy, and human review gates are satisfied under a separately authorized task.

## OCR Boundary

This milestone does not authorize OCR.

OCR implementation was not authorized.

## What This Milestone Means

This milestone means the compiler now has a reviewed specification for future non-live procedure candidate import planning.

## What This Milestone Does Not Mean

This milestone does not mean procedure import has been implemented.

This milestone does not mean Alpha 2.0 procedure content has been copied.

This milestone does not mean Alpha 2.0 procedure content is rights-cleared.

This milestone does not mean any procedure candidate is canonical.

This milestone does not mean any procedure candidate is student-visible.

This milestone does not authorize operational Alpha integration.

This milestone does not authorize database writes.

This milestone does not authorize OCR, PDF parsing, DOCX parsing, or corpus ingestion implementation.

## Known Limitations

The milestone is specification-only and does not include a dry-run importer, validation implementation, rights review implementation, parser implementation, or candidate data generation.

## Remaining Risks

Future work must still resolve rights status, privacy status, source wording boundaries, mathematical correctness, pedagogical clarity, failure-signal quality, and human approval before any candidate can advance.

No parser was implemented.

No dependency was added.

## Recommended Next Tasks

1. COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-SPEC-CLOSEOUT-COMMIT-001
2. COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-SPEC-CLOSEOUT-PUSH-001
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
