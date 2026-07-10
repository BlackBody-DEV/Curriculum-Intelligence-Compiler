# Generation Family Import Specification

## Purpose

This specification defines how future Alpha 2.0 generation-family-like material could be converted into non-live compiler generation family candidates.

It is a planning and safety contract only. This specification does not authorize import.

## Current Baseline

Current published baseline: 6dfe37550f2b1bd879044b668a8a439c745c56c7

MVP tag remains fixed at c7837b3eb9afff6cebca9536311844abe382a737

## Source Census Basis

This specification uses only committed compiler-side census artifacts:

- reports/course_compiler_demo/alpha2_reference_census_001/ALPHA2_REFERENCE_CENSUS_REPORT.md
- reports/course_compiler_demo/alpha2_reference_census_001/alpha2_reuse_matrix.json
- reports/course_compiler_demo/alpha2_reference_census_001/alpha2_candidate_file_inventory.json
- docs/course_compiler_demo/ALPHA2_REFERENCE_CENSUS_CLOSEOUT.md

The Alpha 2.0 reference census identified 80 prioritized reference candidates.

The Alpha 2.0 reference census identified 37 candidate_for_non_live_import entries.

The Alpha 2.0 reference census identified 31 requires_rights_review entries.

Every Alpha 2.0 census matrix entry has copying_allowed_now: false.

Current live Alpha 2.0 files are not source material for this task. Alpha 2.0 HEAD and worktree state are advisory only when the compiler boundary is intact and no Alpha content is copied/imported.

## Relationship to Procedure Candidate Import Spec

Generation family candidates may reference linked procedure guesses, but they do not import procedures, copy procedure bodies, or authorize procedure promotion. Procedure linkage remains review_required until separately validated.

## Relationship to Question Candidate Import Spec

Generation family candidates may reference linked question candidate guesses, but they do not import questions, copy question prompts, copy answers, copy solutions, or generate live question variants. Question linkage remains review_required until separately validated.

## Scope

This specification defines a future non-live candidate contract for generation family planning, metadata, evidence, rights/privacy review, linkage review, validation, audit, and future task sequencing.

## Explicit Non-Goals

This specification does not authorize import.

This specification does not authorize copying Alpha 2.0 generation text or full template wording.

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

This specification does not authorize Alpha staging implementation.

This specification does not authorize writing into adaptive-platform.

## Allowed Source Classes

Allowed source classes are committed compiler-side census summaries, reuse classifications, file inventories, and metadata-only references that identify where a possible pattern may exist without copying source wording.

Allowed use is limited to identifying structure, metadata, micro-skill alignment, parameter patterns, answer type, difficulty pattern, failure-signal pattern, and review requirements.

## Disallowed Source Classes

Disallowed source classes include live Alpha files, proprietary full generation templates, full question prompts, full answers, full solution text, diagrams, images, procedure bodies, private student/family/company/institutional data, and any operational Alpha database or service.

## Generation Family Candidate Definition

A generation family candidate is a non-live, review-required template-pattern candidate that may describe a family of related practice or assessment questions for a target micro-skill.

A generation family candidate may describe the target subject, topic, subtopic, micro-skill, linked procedure, linked question candidates, question type, answer type, invariant concept, variable parameters, parameter constraints, allowed variation dimensions, disallowed variation dimensions, difficulty band, prompt pattern summary, answer pattern summary, solution pattern summary, distractor pattern summary, common error candidates, failure signal candidates, diagram requirement, source evidence, and review status.

A generation family candidate is not canonical.

A generation family candidate is not active.

A generation family candidate is not student-visible.

A generation family candidate is not production-ready.

A generation family candidate may not be promoted without separate parameter validation, answer pattern validation, solution pattern validation, micro-skill alignment review, procedure linkage review, question linkage review, rights review, pedagogical review, and human sign-off.

## Target Non-Live Output Shape

Future non-live generation family candidates must support at least:

- family_id
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
- linked_question_candidate_guesses
- question_type
- answer_type
- family_name
- family_summary
- invariant_concept
- variable_parameters
- parameter_constraints
- allowed_variation_dimensions
- disallowed_variation_dimensions
- prompt_pattern_summary
- answer_pattern_summary
- solution_pattern_summary
- distractor_pattern_summary
- common_error_candidates
- failure_signal_candidates
- difficulty_band
- coverage_goal
- diagram_required
- image_ref_placeholder
- evidence_refs
- rights_status
- privacy_status
- review_status
- micro_skill_alignment_status
- procedure_linkage_status
- question_linkage_status
- parameter_validation_status
- answer_pattern_validation_status
- solution_pattern_validation_status
- difficulty_review_status
- coverage_review_status
- failure_signal_review_status
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

Each candidate must retain metadata sufficient to support non-live review, later validation, audit repeatability, and source-boundary enforcement.

Required default values:

status: human_review_required
review_status: review_pending
canonical_promotion_status: not_authorized
copying_allowed_now: false
student_visible: false
live_deployable: false

## Required Evidence Fields

Every imported generation family candidate must preserve source evidence.

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

Evidence may identify where the generation pattern came from, but must not copy full proprietary source wording.

## Rights and Privacy Gate

If rights status is unknown, restricted, source-derived, or unclear, the generation family candidate must be blocked from public-facing use and canonical promotion.

If the source contains private student, family, company, or institutional data, the candidate must be blocked until sanitized and explicitly approved.

The safest default is:

- analyze generation structure
- classify micro-skills
- classify parameter patterns
- classify answer type
- classify difficulty and coverage
- generate original AxiomIQ wording later
- do not republish source wording
- keep candidate non-live and human_review_required

## Procedure Linkage Gate

Procedure linkage review is required before a candidate may advance. linked_procedure_guess may be recorded as a hypothesis, but procedure_linkage_status must remain review_required until validated.

## Question Linkage Gate

Question linkage review is required before a candidate may advance. linked_question_candidate_guesses may describe possible relationships, but question_linkage_status must remain review_required until validated.

## Parameter and Variant Boundary

Generation family candidates may describe variable parameters and allowed variation dimensions.

Generation family candidates must not generate live variants during import.

Generation family candidates must not produce student-visible questions during import.

Generation family candidates must not claim that generated variants are mathematically correct until reviewed.

Parameter ranges must be validated before future generation.

Answer patterns must be validated before future generation.

Solution patterns must be validated before future generation.

Diagram-dependent variants must require human review.

## Answer Pattern Boundary

Answer pattern summaries may describe answer type and expected validation needs. They must not copy full Alpha answers, and answer pattern validation is required before future generation.

## Solution Pattern Boundary

Solution pattern summaries may describe reasoning structure at a high level. They must not copy full solution text or textbook-derived explanations, and solution pattern validation is required before future generation.

## Difficulty and Coverage Review Gate

Difficulty and coverage review must confirm whether the candidate's difficulty_band and coverage_goal fit the target micro-skill and intended practice or assessment use.

## Failure Signal Review Gate

Failure signal review must confirm that failure_signal_candidates are pedagogically meaningful, bounded, and compatible with the compiler's allowed diagnostic signal policy.

## Diagram and Image Boundary

Diagram-dependent generation family candidates must be marked with diagram_required: true.

Image references must remain placeholders unless rights permit use.

No image should be copied into compiler output during import.

Diagram or image dependent generation families require human review.

Diagram extraction and OCR are not authorized by this specification.

## Alpha 2.0 Boundary

No Alpha 2.0 files may be modified by this specification lane.

No Alpha 2.0 files may be copied into the compiler.

No Alpha 2.0 content may be imported.

No operational Alpha integration is authorized.

No adaptive-platform write is authorized.

The import pipeline must not copy full generation templates from Alpha 2.0 into compiler output.

The import pipeline must not copy full question prompts.

The import pipeline must not copy full answers.

The import pipeline must not copy full solution text.

The import pipeline must not copy textbook-derived explanations.

The import pipeline must not copy diagrams or images.

The import pipeline must not copy Alpha 2.0 procedure bodies.

The import pipeline may use Alpha 2.0 material to identify structure, metadata, micro-skill alignment, parameter patterns, answer type, difficulty pattern, failure-signal pattern, and review requirements.

If future import is authorized, imported candidates should prefer summarized structure and later AxiomIQ-authored wording.

## Non-Live Compiler Boundary

Generation family candidates remain non-live, human_review_required, review_pending, not_authorized for canonical promotion, not student-visible, and not live-deployable.

## Canonical Promotion Boundary

Canonical promotion is not authorized. Active or canonical generation family records require separate future authorization, validation, review, and human sign-off.

## Import Eligibility Matrix

| Reuse Classification | Eligible for Immediate Import | Allowed Use | Required Review | Risk Level | Recommended Action |
| --- | --- | --- | --- | --- | --- |
| safe_validation_pattern | No | Metadata-only validation pattern planning | schema, evidence, rights/privacy, human review | low | Keep non-live and summarize structure only |
| safe_audit_pattern | No | Metadata-only audit pattern planning | schema, evidence, rights/privacy, human review | low | Keep non-live and summarize structure only |
| candidate_for_non_live_import | No | Future candidate planning only | full generation family review gates | medium | Use only after separate dry-run spec |
| requires_rights_review | No | Rights triage only | rights/privacy and human sign-off | high | Block from use until rights are cleared |
| requires_architect_review | No | Architecture triage only | architect and human review | high | Block until architecture ruling |
| do_not_import | No | Exclusion documentation only | none for import; audit record only | high | Do not import |

## Review Status Lifecycle

The default lifecycle is review_pending, human_review_required, review_required for linkage and validation fields, and not_authorized for canonical promotion. A later lane may define additional statuses, but this specification does not authorize status advancement.

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
- linked_question_candidate_guesses are present or question_linkage_status is review_required
- parameter_validation_status is present
- answer_pattern_validation_status is present
- solution_pattern_validation_status is present
- difficulty_review_status is present
- coverage_review_status is present
- failure_signal_review_status is present
- generation_family_review_status is present
- no full Alpha generation template copied
- no full Alpha question prompt copied
- no full Alpha answer copied
- no full Alpha solution copied
- no full Alpha diagram copied
- no full Alpha procedure body copied
- no DB contact
- no operational Alpha contact
- no canonical promotion
- no Alpha staging implementation
- no adaptive-platform write

## Audit Requirements

Required generation family candidate review gates:

1. schema validation
2. source evidence validation
3. rights/privacy validation
4. micro-skill alignment review
5. procedure linkage review
6. question linkage review
7. parameter/variant validation
8. answer pattern validation
9. solution pattern validation
10. difficulty and coverage review
11. failure signal review
12. diagram/image review when applicable
13. pedagogical clarity review
14. human sign-off

## Example Candidate Record Shape

```json
{
  "family_id": "GENFAM_REVIEW_REQUIRED_001",
  "candidate_type": "generation_family_candidate",
  "status": "human_review_required",
  "source_origin": "compiler_side_alpha2_reference_census",
  "source_file_path": "reports/course_compiler_demo/alpha2_reference_census_001/alpha2_reuse_matrix.json",
  "source_artifact_type": "census_reference",
  "subject_guess": "MATHEMATICS_OR_STATICS_REVIEW_REQUIRED",
  "topic_guess": "review_required",
  "subtopic_guess": "review_required",
  "micro_skill_guess": "review_required",
  "linked_procedure_guess": "review_required",
  "linked_question_candidate_guesses": [],
  "question_type": "review_required",
  "answer_type": "review_required",
  "family_name": "Review Required Generation Pattern",
  "family_summary": "Summarized structure only; no source wording copied.",
  "invariant_concept": "review_required",
  "variable_parameters": [],
  "parameter_constraints": [],
  "allowed_variation_dimensions": [],
  "disallowed_variation_dimensions": [],
  "prompt_pattern_summary": "review_required",
  "answer_pattern_summary": "review_required",
  "solution_pattern_summary": "review_required",
  "distractor_pattern_summary": "review_required",
  "common_error_candidates": [],
  "failure_signal_candidates": [],
  "difficulty_band": "review_required",
  "coverage_goal": "review_required",
  "diagram_required": false,
  "image_ref_placeholder": null,
  "evidence_refs": [],
  "rights_status": "review_required",
  "privacy_status": "review_required",
  "review_status": "review_pending",
  "micro_skill_alignment_status": "review_required",
  "procedure_linkage_status": "review_required",
  "question_linkage_status": "review_required",
  "parameter_validation_status": "review_required",
  "answer_pattern_validation_status": "review_required",
  "solution_pattern_validation_status": "review_required",
  "difficulty_review_status": "review_required",
  "coverage_review_status": "review_required",
  "failure_signal_review_status": "review_required",
  "generation_family_review_status": "review_required",
  "rights_review_status": "review_required",
  "canonical_promotion_status": "not_authorized",
  "copying_allowed_now": false,
  "student_visible": false,
  "live_deployable": false,
  "created_by": "future_authorized_import_dry_run",
  "created_at": "future_task",
  "notes": "Non-live placeholder example; not imported."
}
```

## Failure and Block Conditions

Block the candidate if source evidence is missing, rights/privacy status is unclear, full source wording is copied, Alpha content is imported, operational Alpha is touched, database contact occurs, any student-visible or live-deployable flag is true, canonical promotion is claimed, parameter validation is missing, answer pattern validation is missing, solution pattern validation is missing, or human review is absent.

## Recommended Future Implementation Tasks

1. COURSE-COMPILER-GENERATION-FAMILY-IMPORT-SPEC-COMMIT-001
2. COURSE-COMPILER-GENERATION-FAMILY-IMPORT-SPEC-PUSH-001
3. COURSE-COMPILER-GENERATION-FAMILY-IMPORT-SPEC-READINESS-AUDIT-001
4. COURSE-COMPILER-GENERATION-FAMILY-IMPORT-SPEC-CLOSEOUT-001
5. COURSE-COMPILER-PROCEDURE-CANDIDATE-IMPORT-DRY-RUN-SPEC-001
6. COURSE-COMPILER-QUESTION-CANDIDATE-IMPORT-DRY-RUN-SPEC-001
7. COURSE-COMPILER-GENERATION-FAMILY-IMPORT-DRY-RUN-SPEC-001
8. COURSE-COMPILER-PROCEDURE-CANDIDATE-VALIDATION-SPEC-001
9. COURSE-COMPILER-QUESTION-CANDIDATE-VALIDATION-SPEC-001
10. COURSE-COMPILER-ACEF-REVIEW-PRESENTATION-PACKAGE-001

## Do Not Do Yet

Do not import Alpha 2.0 generation families.

Do not copy Alpha 2.0 generation templates.

Do not copy Alpha 2.0 question prompts.

Do not copy Alpha 2.0 answers.

Do not copy Alpha 2.0 solutions.

Do not copy Alpha 2.0 diagrams.

Do not copy Alpha 2.0 procedure bodies.

Do not create canonical generation families.

Do not create student-visible questions.

Do not generate live variants.

Do not implement the import pipeline.

Do not connect to any database.

Do not modify operational Alpha.

Do not implement OCR.

Do not implement PDF, DOCX, spreadsheet, slide, image, ZIP, folder, or LMS ingestion.

Do not start Alpha staging implementation.

Do not write into adaptive-platform.

Do not create migrations, backend endpoints, frontend views, DB tables, or integration files in Alpha.
