# Question Candidate Import Specification Closeout Report

## Final Verdict

Final verdict: QUESTION_CANDIDATE_IMPORT_SPEC_AUDIT_READY

The Question Candidate Import Specification lane is closed as an audit-ready, documentation-only planning milestone.

## Published Baseline

Current published baseline: 55d14e76104b261442f10d8717e010ed21362f88

## Repository State

Repository: BlackBody-DEV/Curriculum-Intelligence-Compiler

The closeout is based on the committed compiler-side question candidate import specification and prior compiler-side census artifacts. The closeout does not depend on live Alpha 2.0 files.

## MVP Tag Status

MVP tag remains fixed at c7837b3eb9afff6cebca9536311844abe382a737

The MVP tag was not moved, recreated, or pushed by this closeout task.

## Alpha 2.0 Advisory Governance

Alpha 2.0 HEAD and worktree state are advisory for compiler documentation/spec audits when the compiler boundary is intact and no Alpha content was copied/imported.

No Alpha 2.0 files were modified by the compiler task.

No Alpha 2.0 files were copied into the compiler.

No Alpha 2.0 content was imported.

No question import was performed.

No question prompt was copied.

No answer was copied.

No solution was copied.

No diagram was copied.

No parser was implemented.

No dependency was added.

No database contact occurred.

No operational Alpha contact occurred.

No active or canonical promotion was performed.

Future Alpha integration is parked as COURSE-COMPILER-PRODUCTION-STAGING-INTEGRATION-SCOPE-LOCK-001. That lane must be opened by the main Alpha spline as scope-lock/spec-only before any implementation.

## Alpha 2.0 Census Basis

The Alpha 2.0 reference census identified 80 prioritized reference candidates.

The Alpha 2.0 reference census identified 37 candidate_for_non_live_import entries.

The Alpha 2.0 reference census identified 31 requires_rights_review entries.

Every Alpha 2.0 census matrix entry has copying_allowed_now: false.

## Specification Scope

The question candidate import specification is spec-only.

It defines future non-live question candidate planning boundaries for possible later import dry-runs, validation, and review workflows.

## What Was Specified

The specification defines candidate metadata, evidence requirements, non-live defaults, rights/privacy boundaries, procedure linkage expectations, answer and solution validation gates, review gates, source wording limits, diagram and image limits, import eligibility classifications, validation expectations, and follow-on task sequencing.

## What Was Not Authorized

The question candidate import specification does not authorize import.

The question candidate import specification does not authorize copying Alpha 2.0 question prompts.

The question candidate import specification does not authorize copying Alpha 2.0 answers.

The question candidate import specification does not authorize copying Alpha 2.0 solutions.

The question candidate import specification does not authorize copying Alpha 2.0 diagrams.

The question candidate import specification does not authorize copying Alpha 2.0 procedure bodies.

The question candidate import specification does not authorize canonical promotion.

The question candidate import specification does not authorize operational Alpha integration.

The question candidate import specification does not authorize database writes.

The question candidate import specification does not authorize student-visible delivery.

The question candidate import specification does not authorize OCR.

## Question Candidate Definition

A question candidate is a non-live, review-required assessment or practice item candidate that may describe the target subject, topic, subtopic, micro-skill, linked procedure, question type, answer type, difficulty estimate, prompt summary, answer summary, solution pattern, failure signal candidates, generation family relationship, diagram requirement, source evidence, and review status.

A question candidate is not canonical.

A question candidate is not active.

A question candidate is not student-visible.

A question candidate is not production-ready.

A question candidate may not be promoted without separate answer validation, solution validation, micro-skill alignment review, procedure linkage review, rights review, pedagogical review, and human sign-off.

## Target Non-Live Output Shape

Future non-live question candidates may include candidate_id, candidate_type, source_origin, source_file_path, subject_guess, topic_guess, subtopic_guess, micro_skill_guess, linked_procedure_guess, question_type, answer_type, difficulty_estimate, prompt_summary, answer_summary, solution_pattern_summary, failure_signal_candidates, generation_family_guess, diagram_required, image_ref_placeholder, evidence_refs, rights_status, privacy_status, answer_validation_status, solution_validation_status, and generation_family_review_status.

## Required Default Values

Required default values for future non-live question candidates:

status: human_review_required
review_status: review_pending
canonical_promotion_status: not_authorized
copying_allowed_now: false
student_visible: false
live_deployable: false

## Metadata and Evidence Requirements

Candidate records must preserve source evidence without copying protected source content. Evidence should include source_repo_root, source_file_sha256, source_artifact_type, source_heading_or_key, source_reference_note, extraction_method, confidence, and reviewer_required.

## Rights and Privacy Gate

Rights/privacy validation is mandatory before any future candidate can advance. Rights review must preserve copying_allowed_now: false until a separate human review authorizes a different status.

## Procedure Linkage Gate

Procedure linkage review is mandatory. Candidate linkage must remain a guess until a reviewer confirms the subject, topic, subtopic, micro-skill, and linked procedure relationship.

## Answer and Solution Validation Gates

Answer validation is mandatory.

Solution validation is mandatory.

No future candidate may be promoted without separate verification of answer correctness and solution reasoning.

## Review Gate Requirements

Required question candidate review gates:

1. schema validation
2. source evidence validation
3. rights/privacy validation
4. micro-skill alignment review
5. procedure linkage review
6. answer validation
7. solution validation
8. difficulty review
9. failure signal review
10. generation family review
11. diagram/image review when applicable
12. pedagogical clarity review
13. human sign-off

## Source Wording Boundary

The import pipeline must not copy full question prompts from Alpha 2.0 into compiler output.

The import pipeline must not copy full answers.

The import pipeline must not copy full solution text.

The import pipeline must not copy textbook-derived explanations.

The import pipeline must not copy diagrams or images.

Imported candidates should prefer summarized structure and later AxiomIQ-authored wording.

## Diagram and Image Boundary

Diagram-dependent question candidates must be marked with diagram_required: true.

Image references must remain placeholders unless rights permit use.

No image should be copied into compiler output during import.

Diagram or image dependent questions require human review.

Diagram extraction and OCR are not authorized by this specification.

## Import Eligibility Boundary

Import eligibility is non-live and review-bound. Reuse classifications such as candidate_for_non_live_import, requires_rights_review, requires_architect_review, and do_not_import are planning labels only.

No classification authorizes copying, activation, canonical promotion, or student-visible delivery.

## Validation Requirements

Future validation must preserve safe_validation_pattern and safe_audit_pattern checks, including no full Alpha question prompt copied, no full Alpha answer copied, no full Alpha solution copied, no full Alpha diagram copied, no DB contact, no operational Alpha contact, and no canonical promotion.

## Audit History

COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-SPEC-001
Result: pass
Summary: Created the non-live question candidate import specification.

COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-SPEC-COMMIT-001
Commit: 55d14e76104b261442f10d8717e010ed21362f88

COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-SPEC-PUSH-001
Result: pushed to main.

COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-SPEC-READINESS-AUDIT-001
Result: QUESTION_CANDIDATE_IMPORT_SPEC_AUDIT_NO_GO
Reason: Alpha 2.0 worktree was dirty.

COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-SPEC-ALPHA-STATE-RECONCILIATION-001
Result: QUESTION_CANDIDATE_IMPORT_SPEC_ALPHA_STATE_CLASSIFIED
Summary: Classified Alpha state as external Alpha work lane.

QUESTION-CANDIDATE-IMPORT-SPEC-ALPHA-HEAD-DRIFT-RULING-001
Result: QUESTION_CANDIDATE_IMPORT_SPEC_ALPHA_HEAD_DRIFT_ADVISORY_READY
Summary: Ruled Alpha exact HEAD drift advisory when Alpha is clean and compiler boundary is intact.

COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-SPEC-READINESS-AUDIT-002
Result: QUESTION_CANDIDATE_IMPORT_SPEC_AUDIT_NO_GO
Reason: Alpha exact HEAD mismatch only.

COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-SPEC-READINESS-AUDIT-003
Result: QUESTION_CANDIDATE_IMPORT_SPEC_AUDIT_NO_GO
Reason: Alpha worktree dirty only.

QUESTION-CANDIDATE-IMPORT-SPEC-ALPHA-WORKTREE-DRIFT-RULING-001
Result: QUESTION_CANDIDATE_IMPORT_SPEC_ALPHA_WORKTREE_DRIFT_ADVISORY_READY
Summary: Ruled Alpha HEAD and worktree state advisory for compiler documentation/spec audits when compiler boundary is intact and no Alpha content was copied/imported.

COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-SPEC-READINESS-AUDIT-004
Result: QUESTION_CANDIDATE_IMPORT_SPEC_AUDIT_READY

## Non-Live Boundary

All future question candidates remain non-live, human_review_required, review_pending, not_authorized for canonical promotion, not student-visible, and not live-deployable unless a later authorized lane changes those states after review.

## Human Review Boundary

Human review is mandatory before any future candidate advances beyond planning status. Human sign-off is required after schema validation, evidence validation, rights/privacy validation, procedure linkage review, answer validation, solution validation, difficulty review, failure signal review, generation family review, diagram/image review when applicable, and pedagogical clarity review.

## OCR Boundary

This milestone does not authorize OCR.

OCR, diagram extraction, and image copying remain out of scope until a separate OCR risk and evaluation lane is authorized.

## Future Alpha Integration Boundary

This milestone does not authorize operational Alpha integration.

This milestone does not authorize COURSE-COMPILER-PRODUCTION-STAGING-INTEGRATION-SCOPE-LOCK-001.

Any future Alpha integration must begin as scope-lock/spec-only from the main Alpha spline before implementation.

## What This Milestone Means

This milestone means the compiler now has a reviewed specification for future non-live question candidate import planning.

It establishes a safe planning boundary for question candidate metadata, evidence, validation, and review requirements.

## What This Milestone Does Not Mean

This milestone does not mean question import has been implemented.

This milestone does not mean Alpha 2.0 question prompts have been copied.

This milestone does not mean Alpha 2.0 answers, solutions, or diagrams have been copied.

This milestone does not mean Alpha 2.0 question content is rights-cleared.

This milestone does not mean any question candidate is canonical.

This milestone does not mean any question candidate is student-visible.

This milestone does not authorize operational Alpha integration.

This milestone does not authorize database writes.

This milestone does not authorize OCR, PDF parsing, DOCX parsing, or corpus ingestion implementation.

This milestone does not authorize COURSE-COMPILER-PRODUCTION-STAGING-INTEGRATION-SCOPE-LOCK-001.

## Known Limitations

The closeout is documentation-only. No import pipeline exists. No question candidates were generated. No Alpha content was copied. No live or production pathway was created.

## Remaining Risks

Future work must still handle rights review, privacy review, source evidence quality, answer correctness, solution correctness, diagram dependency, failure signal quality, generation family alignment, and human sign-off before any candidate can advance.

## Recommended Next Tasks

1. COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-SPEC-CLOSEOUT-COMMIT-001
2. COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-SPEC-CLOSEOUT-PUSH-001
3. COURSE-COMPILER-GENERATION-FAMILY-IMPORT-SPEC-001
4. COURSE-COMPILER-GENERATION-FAMILY-IMPORT-SPEC-COMMIT-001
5. COURSE-COMPILER-GENERATION-FAMILY-IMPORT-SPEC-PUSH-001
6. COURSE-COMPILER-GENERATION-FAMILY-IMPORT-SPEC-READINESS-AUDIT-001
7. COURSE-COMPILER-GENERATION-FAMILY-IMPORT-SPEC-CLOSEOUT-001
8. COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-DRY-RUN-SPEC-001
9. COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-DRY-RUN-SPEC-001
10. COURSE-COMPILER-ACEF-REVIEW-PRESENTATION-PACKAGE-001

## Do Not Do Yet

Do not import Alpha 2.0 questions.

Do not copy Alpha 2.0 question prompts.

Do not copy Alpha 2.0 answers.

Do not copy Alpha 2.0 solutions.

Do not copy Alpha 2.0 diagrams.

Do not copy Alpha 2.0 procedure bodies.

Do not create canonical questions.

Do not create student-visible questions.

Do not implement the import pipeline.

Do not connect to any database.

Do not modify operational Alpha.

Do not implement OCR.

Do not implement PDF, DOCX, spreadsheet, slide, image, ZIP, folder, or LMS ingestion.

Do not start Alpha staging implementation.

Do not write into adaptive-platform.

Do not create migrations, backend endpoints, frontend views, DB tables, or integration files in Alpha.
