# Question Candidate Import Specification

## Purpose

This specification defines how future Alpha 2.0 question-like material could be converted into non-live compiler question candidates.

It defines the import contract, review gates, safety boundaries, evidence requirements, rights/privacy gates, validation requirements, and closeout criteria for a later separately authorized task.

This specification does not authorize import.

## Current Baseline

Current published baseline: 53b574015cc6967461c203dc6a2f7cce0de9d75d

MVP tag remains fixed at c7837b3eb9afff6cebca9536311844abe382a737

Repository: BlackBody-DEV/Curriculum-Intelligence-Compiler

## Source Census Basis

The Alpha 2.0 reference census identified 80 prioritized reference candidates.

The Alpha 2.0 reference census identified 37 candidate_for_non_live_import entries.

The Alpha 2.0 reference census identified 31 requires_rights_review entries.

Every Alpha 2.0 census matrix entry has copying_allowed_now: false.

Relevant committed census artifacts:

- reports/course_compiler_demo/alpha2_reference_census_001/ALPHA2_REFERENCE_CENSUS_REPORT.md
- reports/course_compiler_demo/alpha2_reference_census_001/alpha2_reuse_matrix.json
- reports/course_compiler_demo/alpha2_reference_census_001/alpha2_candidate_file_inventory.json
- docs/course_compiler_demo/ALPHA2_REFERENCE_CENSUS_CLOSEOUT.md

The census is a reference-planning input only. It does not authorize copying or importing Alpha 2.0 content.

## Relationship to Procedure Candidate Import Spec

This question candidate import specification follows the same non-live, review-gated, non-importing posture established by:

- docs/course_compiler_demo/PROCEDURE_CANDIDATE_IMPORT_SPEC.md
- docs/course_compiler_demo/PROCEDURE_CANDIDATE_IMPORT_SPEC_CLOSEOUT.md

Question candidates may link to procedure candidates in a future dry-run, but procedure linkage does not authorize canonical promotion, student visibility, database writes, or operational Alpha integration.

## Scope

This specification covers future non-live question candidate records derived from question-like source patterns.

It defines:

- candidate structure
- required metadata
- required source evidence
- review gates
- rights and privacy gates
- procedure linkage gates
- answer and solution validation gates
- difficulty and failure-signal review gates
- generation family review gates
- diagram and image boundaries
- validation and audit expectations

## Explicit Non-Goals

This specification does not authorize import.

This specification does not authorize copying Alpha 2.0 question prompts.

This specification does not authorize copying Alpha 2.0 answers.

This specification does not authorize copying Alpha 2.0 solutions.

This specification does not authorize copying Alpha 2.0 diagrams.

This specification does not authorize copying Alpha 2.0 procedure bodies.

This specification does not authorize canonical promotion.

This specification does not authorize operational Alpha integration.

This specification does not authorize database writes.

This specification does not authorize student-visible delivery.

This specification does not authorize OCR.

## Allowed Source Classes

Allowed source classes for future planning only:

- safe_validation_pattern
- safe_audit_pattern
- candidate_for_non_live_import
- requires_rights_review after rights review clears future use
- requires_architect_review after architecture review clears future use

Allowed use means identifying structure, classification signals, review requirements, validation patterns, and candidate metadata. It does not mean copying source wording or importing question content.

## Disallowed Source Classes

Disallowed source classes:

- do_not_import
- sources with unresolved rights restrictions
- sources containing private student, family, company, or institutional data
- sources requiring OCR or diagram extraction before a separate OCR or image policy exists
- sources whose answer or solution cannot be reviewed
- sources whose procedure linkage cannot be established or marked review_required

## Question Candidate Definition

A question candidate is a non-live, review-required assessment or practice item candidate that may describe the target subject, topic, subtopic, micro-skill, linked procedure, question type, answer type, difficulty estimate, prompt summary, answer summary, solution pattern, failure signal candidates, generation family relationship, diagram requirement, source evidence, and review status.

A question candidate is not canonical.

A question candidate is not active.

A question candidate is not student-visible.

A question candidate is not production-ready.

A question candidate may not be promoted without separate answer validation, solution validation, micro-skill alignment review, procedure linkage review, rights review, pedagogical review, and human sign-off.

## Target Non-Live Output Shape

Future non-live question candidates must include at least:

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
- linked_procedure_guess
- question_type
- answer_type
- difficulty_estimate
- prompt_summary
- answer_summary
- solution_pattern_summary
- distractor_pattern_summary
- common_error_candidates
- failure_signal_candidates
- generation_family_guess
- diagram_required
- image_ref_placeholder
- evidence_refs
- rights_status
- privacy_status
- review_status
- micro_skill_alignment_status
- procedure_linkage_status
- answer_validation_status
- solution_validation_status
- difficulty_review_status
- generation_family_review_status
- rights_review_status
- canonical_promotion_status
- copying_allowed_now
- student_visible
- live_deployable
- created_by
- created_at
- notes

## Required Metadata

Required metadata must identify the candidate, source, guessed classification, linked procedure guess, question type, answer type, difficulty estimate, diagram requirement, review status, and boundary defaults.

Metadata must be enough to support review without copying full Alpha 2.0 question prompts, answers, solutions, diagrams, or procedure bodies.

## Required Evidence Fields

Every imported question candidate must preserve source evidence.

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

Evidence may identify where the question pattern came from, but must not copy full proprietary source wording.

## Rights and Privacy Gate

If rights status is unknown, restricted, source-derived, or unclear, the question candidate must be blocked from public-facing use and canonical promotion.

If the source contains private student, family, company, or institutional data, the candidate must be blocked until sanitized and explicitly approved.

The safest default is:

- analyze question structure
- classify micro-skills
- classify answer type
- classify difficulty
- generate original AxiomIQ wording later
- do not republish source wording
- keep candidate non-live and human_review_required

## Procedure Linkage Gate

Procedure linkage review must confirm that a question candidate either links to an appropriate reviewed procedure candidate or explicitly carries procedure_linkage_status as review_required.

No question candidate may advance if its linked procedure guess is unsupported, ambiguous, or inconsistent with the claimed micro-skill.

## Answer Validation Gate

Answer validation must confirm answer type, answer summary, expected answer structure, units where applicable, tolerance where applicable, and review evidence.

No answer may be copied from Alpha 2.0 into compiler output.

## Solution Validation Gate

Solution validation must confirm that solution_pattern_summary is sufficient for review while avoiding copied Alpha 2.0 solution text.

No full Alpha solution copied is allowed.

## Difficulty Review Gate

Difficulty review must confirm that difficulty_estimate is plausible for the target micro-skill, question type, answer type, required reasoning, and linked procedure.

Difficulty estimates remain review_pending until human review confirms them.

## Failure Signal Review Gate

Failure signal review must confirm that common_error_candidates and failure_signal_candidates are instructionally useful, tied to the micro-skill, and not merely copied from source wording.

Failure signals must remain candidates until reviewed.

## Generation Family Review Gate

Generation family review must confirm whether the question candidate can belong to a future generation family, whether variable fields are plausible, and whether invariants can be authored without copying source wording.

Generation family relationships remain guesses until reviewed.

## Pedagogical Review Gate

Pedagogical review must confirm conceptual clarity, learner-facing usefulness, assessment purpose, wording suitability, and alignment to the intended micro-skill.

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

The import pipeline may use Alpha 2.0 material to identify structure, metadata, micro-skill alignment, question type, answer type, difficulty pattern, failure-signal pattern, and review requirements.

If future import is authorized, imported candidates should prefer summarized structure and later AxiomIQ-authored wording.

## Diagram and Image Boundary

Diagram-dependent question candidates must be marked with diagram_required: true.

Image references must remain placeholders unless rights permit use.

No image should be copied into compiler output during import.

Diagram or image dependent questions require human review.

Diagram extraction and OCR are not authorized by this specification.

## Alpha 2.0 Boundary

Alpha 2.0 remains reference-only unless a later task explicitly authorizes a non-live dry-run.

Alpha 2.0 files must not be modified.

Alpha 2.0 question prompts, answers, solutions, diagrams, images, and procedure bodies must not be copied into compiler output.

## Non-Live Compiler Boundary

All question candidates must remain non-live, review-required, not active, not canonical, not student-visible, and not live-deployable.

Required default values for future non-live question candidates:

status: human_review_required
review_status: review_pending
canonical_promotion_status: not_authorized
copying_allowed_now: false
student_visible: false
live_deployable: false

## Canonical Promotion Boundary

Canonical promotion is not authorized.

No question candidate may become canonical, active, student-visible, or live-deployable without a separate task and completed answer validation, solution validation, micro-skill alignment review, procedure linkage review, rights review, pedagogical review, and human sign-off.

## Import Eligibility Matrix

| Reuse Classification | Eligible for Immediate Import | Allowed Use | Required Review | Risk Level | Recommended Action |
| --- | --- | --- | --- | --- | --- |
| safe_validation_pattern | No | Reference validation structure only | Architect and validation review | Medium | Use to design validation checks in a later spec |
| safe_audit_pattern | No | Reference audit workflow structure only | Architect and audit review | Medium | Use to design audit gates in a later spec |
| candidate_for_non_live_import | No | Candidate scoping for non-live question import | Rights, privacy, answer, solution, procedure linkage, pedagogical, and human review | High | Create a dry-run import spec before any implementation |
| requires_rights_review | No | Reference only until rights are resolved | Rights and privacy review first | High | Block from import until cleared |
| requires_architect_review | No | Architecture planning only | Architect review first | High | Block from import until architecture is approved |
| do_not_import | No | None beyond risk awareness | Human confirmation of exclusion | High | Do not import |

## Review Status Lifecycle

Suggested review states:

1. review_pending
2. evidence_checked
3. rights_privacy_checked
4. procedure_linkage_pending
5. answer_validation_pending
6. solution_validation_pending
7. difficulty_review_pending
8. generation_family_review_pending
9. pedagogy_review_pending
10. human_signoff_pending
11. approved_for_non_live_dry_run
12. blocked

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
- linked_procedure_guess is present or procedure_linkage_status is review_required
- answer_validation_status is present
- solution_validation_status is present
- difficulty_review_status is present
- generation_family_review_status is present
- no full Alpha question prompt copied
- no full Alpha answer copied
- no full Alpha solution copied
- no full Alpha diagram copied
- no DB contact
- no operational Alpha contact
- no canonical promotion

## Audit Requirements

Future audits must confirm the candidate file set, source evidence, rights/privacy status, review status, non-live defaults, no copied Alpha wording, no copied diagrams, no DB contact, no operational Alpha contact, no canonical promotion, and no student-visible output.

## Example Candidate Record Shape

```json
{
  "candidate_id": "question_candidate_example_001",
  "candidate_type": "question_candidate",
  "status": "human_review_required",
  "source_origin": "alpha2_reference_census",
  "source_file_path": "reference-only",
  "source_artifact_type": "question_like_reference",
  "subject_guess": "MATHEMATICS",
  "topic_guess": "review_required",
  "subtopic_guess": "review_required",
  "micro_skill_guess": "review_required",
  "linked_procedure_guess": "review_required",
  "question_type": "review_required",
  "answer_type": "review_required",
  "difficulty_estimate": "review_required",
  "prompt_summary": "summarized structure only",
  "answer_summary": "summarized structure only",
  "solution_pattern_summary": "summarized structure only",
  "distractor_pattern_summary": "review_required",
  "common_error_candidates": [],
  "failure_signal_candidates": [],
  "generation_family_guess": "review_required",
  "diagram_required": false,
  "image_ref_placeholder": null,
  "evidence_refs": [],
  "rights_status": "review_required",
  "privacy_status": "review_required",
  "review_status": "review_pending",
  "micro_skill_alignment_status": "review_required",
  "procedure_linkage_status": "review_required",
  "answer_validation_status": "review_required",
  "solution_validation_status": "review_required",
  "difficulty_review_status": "review_required",
  "generation_family_review_status": "review_required",
  "rights_review_status": "review_required",
  "canonical_promotion_status": "not_authorized",
  "copying_allowed_now": false,
  "student_visible": false,
  "live_deployable": false,
  "created_by": "future_authorized_task",
  "created_at": "future_timestamp",
  "notes": "No import authorized by this specification."
}
```

## Failure and Block Conditions

Block future candidate creation or advancement if:

- rights status is unknown, restricted, source-derived, or unclear
- privacy status is unresolved
- source evidence is missing
- micro-skill alignment is unsupported
- linked procedure is missing without review_required status
- answer validation is missing
- solution validation is missing
- difficulty review is missing
- generation family review is missing
- a full Alpha question prompt is copied
- a full Alpha answer is copied
- a full Alpha solution is copied
- a diagram or image is copied
- database contact occurs
- operational Alpha contact occurs
- canonical promotion is attempted
- student-visible delivery is attempted
- OCR is required

## Recommended Future Implementation Tasks

1. COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-SPEC-COMMIT-001
2. COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-SPEC-PUSH-001
3. COURSE-COMPILER-GENERATION-FAMILY-IMPORT-SPEC-001
4. COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-DRY-RUN-SPEC-001
5. COURSE-COMPILER-QUESTION-CANDIDATE-VALIDATION-SPEC-001
6. COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-DRY-RUN-SPEC-001
7. COURSE-COMPILER-ACEF-REVIEW-PRESENTATION-PACKAGE-001
8. COURSE-COMPILER-INGEST-PDF-TEXT-ONLY-SPEC-001
9. COURSE-COMPILER-IMAGE-DIAGRAM-METADATA-SPEC-001
10. COURSE-COMPILER-OCR-RISK-AND-EVALUATION-SPEC-001

## Do Not Do Yet

Do not import Alpha 2.0 questions.

Do not copy Alpha 2.0 question prompts.

Do not copy Alpha 2.0 answers.

Do not copy Alpha 2.0 solutions.

Do not copy Alpha 2.0 diagrams.

Do not create canonical questions.

Do not create student-visible questions.

Do not implement the import pipeline.

Do not connect to any database.

Do not modify operational Alpha.

Do not implement OCR.

Do not implement PDF, DOCX, spreadsheet, slide, image, ZIP, folder, or LMS ingestion.
