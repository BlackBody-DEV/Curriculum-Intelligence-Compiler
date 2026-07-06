# TXT and MD Intake Stabilization Report

## Final Result

TXT_MD_STABILIZATION_READY.

The current .txt and .md intake path was inspected, smoke-tested with synthetic temporary files, and minimally stabilized for clearer review metadata.

## Baseline

Current baseline: 5cc4d10d7844c5974815cc20865b52781980efc3.

MVP tag remains fixed at c7837b3eb9afff6cebca9536311844abe382a737.

## Repository State

Branch: main.

Repository: BlackBody-DEV/Curriculum-Intelligence-Compiler.

Current implemented intake support remains limited to .txt and .md.

The current system has preserved original artifacts, intake run outputs, subject staging outputs, and ACEF scaffold outputs.

The ACEF scaffold layer remains complete for the current three committed intake runs.

## Current TXT Support

.txt files are accepted by the current supported path.

Uppercase .TXT suffixes are accepted because suffix detection is case-insensitive.

Synthetic .txt smoke input was processed successfully through the non-live intake engine.

## Current MD Support

.md files are accepted by the current supported path.

Uppercase .MD suffixes are accepted because suffix detection is case-insensitive.

Synthetic .md smoke input was processed successfully through the non-live intake engine.

## Unsupported Format Behavior

Unsupported formats do not crash the batch intake path.

Synthetic unsupported .pdf input was not parsed as a compiler source.

Unsupported files are reported in the batch summary with status: skipped_unsupported_format.

No PDF parser was implemented.

No DOCX parser was implemented.

No OCR was implemented.

No parser dependency was added.

## Empty Input Behavior

Empty .txt input does not crash the current intake path.

Synthetic empty .txt input was processed through the current non-live path and retained review-required output status.

## Rights and Privacy Metadata

rights_status is present on produced source records and source interpretations.

privacy_status is present on produced source records and source interpretations.

input_format is present on produced source records and source interpretations.

## Source Reference Preservation

Source records preserve file_path.

Intake records preserve input_path, original_filename, original_artifact_path, and compiler_output_path.

Batch summaries preserve incoming_path and per-file processed or skipped references.

## Non-Live Boundary

All outputs remain non-live and review-required.

TXT and MD intake stabilization does not authorize live delivery.

TXT and MD intake stabilization does not authorize canonical promotion.

TXT and MD intake stabilization does not authorize operational Alpha integration.

TXT and MD intake stabilization does not authorize database writes.

TXT and MD intake stabilization is only a local compiler hardening step before future file type expansion.

No output claims production readiness.

No output claims canonical readiness.

No output claims live readiness.

## Human Review Boundary

All generated compiler and intake outputs remain demo_unverified, processed_non_live, human_review_required, or otherwise review-required according to their existing schema.

No compiler output becomes active without human review.

## Commands Run

- git rev-parse HEAD
- git branch --show-current
- git status --short --untracked-files=all
- git remote -v
- git rev-list -n 1 v0.1.0-math-demo-mvp
- find tools/course_compiler_demo -maxdepth 5 -type f
- find docs/course_compiler_demo -maxdepth 1 -type f
- find reports/course_compiler_demo -maxdepth 3 -type f
- sed inspections of intake_engine.py, intake_registry.py, artifact_router.py, input_loader.py, source_registry.py, run_course_compiler_demo.py, and smoke_test_course_compiler_demo.py
- synthetic temporary intake smoke using .txt, .md, .TXT, .MD, empty .txt, and unsupported .pdf files
- python3 -m py_compile tools/course_compiler_demo/run_course_compiler_demo.py tools/course_compiler_demo/intake/intake_engine.py
- python3 tools/course_compiler_demo/smoke_test_course_compiler_demo.py

## Smoke Test Results

Synthetic TXT/MD stabilization smoke result: pass.

Existing MVP smoke test result: pass.

Synthetic temporary inputs were created outside the repository and were not committed.

The existing smoke-test output was transient and removed after the test.

## Files Changed

- tools/course_compiler_demo/intake/intake_engine.py
- tools/course_compiler_demo/run_course_compiler_demo.py
- reports/course_compiler_demo/txt_md_stabilization_001/TXT_MD_STABILIZATION_REPORT.md

## Known Gaps

The current intake path remains limited to .txt and .md.

PDF, DOCX, OCR, image, spreadsheet, slide, HTML, folder, ZIP, and LMS export parsing remain future work.

Empty input is non-crashing, but it still requires human review because meaningful curriculum extraction is not guaranteed.

No new real source document was processed.

No new committed intake run was created.

No final demo output was modified.

No database contact occurred.

No operational Alpha contact occurred.

No canonical promotion was performed.

## Recommended Next Tasks

1. COURSE-COMPILER-INGEST-TXT-MD-STABILIZATION-COMMIT-001
2. COURSE-COMPILER-INGEST-TXT-MD-STABILIZATION-PUSH-001
3. COURSE-COMPILER-INGEST-PDF-TEXT-ONLY-SPEC-001
4. COURSE-COMPILER-INGEST-DOCX-SPEC-001
5. COURSE-COMPILER-CORPUS-CENSUS-SPEC-001

## Do Not Do Yet

Do not implement PDF parsing.

Do not implement DOCX parsing.

Do not implement OCR.

Do not add parser dependencies.

Do not run intake on real source documents.

Do not create production content.

Do not promote any output into canonical content.

Do not connect this workflow to operational Alpha.

Do not write to any database.
