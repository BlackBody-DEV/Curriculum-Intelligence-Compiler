# Ingest File Type Roadmap

## Executive Summary

This roadmap defines a staged, non-live path for expanding the Curriculum Intelligence Compiler intake layer beyond the current .txt and .md workflow.

Current published baseline: 1c9aa148d21e5a1a24c48673f560d33aeb05acc8.

MVP tag remains fixed at c7837b3eb9afff6cebca9536311844abe382a737.

No new file parser is authorized by this roadmap task.

No database contact is authorized.

No operational Alpha contact is authorized.

No canonical promotion is authorized.

## Current Supported Intake State

Current implemented intake support is limited to .txt and .md.

The current system has preserved original artifacts, intake run outputs, subject staging outputs, and ACEF scaffold outputs.

The ACEF scaffold layer is complete for the current three committed intake runs.

## Roadmap Goal

The goal is to safely plan support for PDFs, DOCX files, slide decks, spreadsheets, CSV files, HTML exports, images, folders, zip archives, LMS exports, textbook chapters, textbook groups, course packets, question banks, homework archives, and practice exam collections.

The roadmap is a planning artifact only. It does not implement parsers, install dependencies, process new files, or authorize production use.

## Governing Principles

File type expansion must be staged, observable, reviewable, non-live, and rights-aware.

Every new ingestion capability must preserve source evidence and must default to human_review_required or review_pending output.

The safe default is to analyze structure, classify skills, generate original AxiomIQ practice, and avoid republishing source wording.

## File Type Expansion Matrix

| File Type | Use Case | Expected Extractable Content | Recommended Parser Strategy | Rights/Privacy Risk | Implementation Difficulty | Recommended Phase | Validation Needs | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| .txt | Plain text homework, notes, simple prompts | Text blocks, headings by convention, question-like lines | Existing text reader, improve metadata and evidence refs | Low to medium | Low | Phase 1 | Source document, interpretation, rights/privacy labels | Implemented baseline |
| .md | Structured notes and authored examples | Headings, lists, tables by markdown convention, code fences | Existing markdown-as-text reader, add structure preservation | Low to medium | Low | Phase 1 | Section refs, feature flags, rights/privacy labels | Implemented baseline |
| .pdf | Textbook chapters, packets, worksheets | Text, pages, headings when detectable | Text-based PDF extraction only at first | High | High | Phase 2 | Page refs, extraction quality, rights labels | Planned |
| .docx | Teacher docs, syllabi, worksheets | Headings, paragraphs, lists, tables, metadata | DOCX text extraction with section references | Medium to high | Medium | Phase 3 | Section refs, table checks, privacy labels | Planned |
| .pptx | Slide decks and lesson materials | Slide text, speaker notes, titles | Slide text extraction with slide refs | Medium | Medium | Phase 5 | Slide refs, image placeholder handling | Planned |
| .xlsx | Curriculum maps, rubrics, question banks | Sheets, rows, columns, tables, schedules | Structured workbook reader with sheet census | High if student data present | Medium | Phase 4 | Sheet refs, privacy screening, schema checks | Planned |
| .csv | Topic maps, question banks, rubric exports | Rows, columns, headers | Structured CSV reader with header inference | High if student data present | Low to medium | Phase 4 | Header validation, privacy screening | Planned |
| .html | LMS exports, web pages, saved lessons | Headings, paragraphs, links, tables | Sanitized HTML text extraction | Medium to high | Medium | Phase 6 | Link refs, source URL/path refs, rights labels | Planned |
| .png/.jpg | Diagrams, screenshots, scanned pages | Metadata, dimensions, optional placeholders | Metadata-first, no OCR initially | High | Medium to high | Phase 7 | image_ref placeholders, human review flags | Planned |
| folder | Course packet, textbook group, mixed corpus | File inventory, detected formats, likely types | Corpus census before parsing | Medium to high | Medium | Phase 8 | File manifest, skipped/processed counts | Planned |
| .zip | LMS export, packet archive, homework archive | Archive inventory and contained files | Safe extraction to quarantine then census | High | High | Phase 8 | Archive manifest, zip safety checks | Planned |
| LMS export | Course export package | Modules, pages, assignments, files | Vendor-specific census before parsing | High | High | Phase 9 | Privacy review, rights labels, manifest | Planned |

## Phase 0 Current State

The current state supports local non-live intake for .txt and .md examples.

Outputs include preserved original artifacts, intake run directories, subject staging outputs, and ACEF scaffold outputs.

## Phase 1 Text and Markdown Stabilization

Phase 1: stabilize .txt and .md intake.

This phase should improve source evidence references, rights_status, privacy_status, unsupported format behavior, and batch summaries for the existing implemented text workflow.

## Phase 2 PDF Intake

Phase 2: add PDF text extraction for text-based PDFs only.

PDF support should begin with text-based PDFs only.

Scanned PDFs and OCR should be deferred.

PDF extraction must preserve source page references.

PDF extraction must not republish protected textbook wording into student-facing outputs.

PDF extraction outputs should remain human_review_required or review_pending until reviewed.

Textbook-scale PDF ingestion should begin as source inventory, topic mapping, and candidate extraction, not student-facing publication.

## Phase 3 DOCX Intake

Phase 3: add DOCX text extraction.

DOCX support should extract headings, paragraphs, lists, tables when feasible, and document metadata.

DOCX ingestion must preserve source section references where available.

Private student or instructor documents must be rights-labeled and privacy-labeled before extraction.

DOCX content must not become canonical or student-visible without review.

## Phase 4 Spreadsheet and CSV Intake

Phase 4: add CSV/XLSX structured table intake.

CSV and XLSX intake should support structured curriculum tables, question banks, rubrics, grade-free performance templates, syllabus schedules, and topic maps.

Spreadsheet intake must distinguish curriculum structure from student private data.

If a spreadsheet contains real student grades, names, IDs, or private performance data, processing must stop or require explicit sanitized approval.

## Phase 5 Slide Deck Intake

Phase 5: add PPTX slide text extraction.

Slide deck intake should preserve slide numbers, titles, speaker notes when available, and image placeholder metadata.

Slide images and diagrams should remain review-required and should not be converted into student-facing content without separate authorization.

## Phase 6 HTML and Web Export Intake

Phase 6: add HTML export intake.

HTML intake should support saved lessons, LMS pages, web exports, headings, paragraphs, lists, tables, and links while preserving source file or URL references.

Sanitization and privacy review should happen before extraction output is used for any demo or review packet.

## Phase 7 Image and Diagram Intake

Phase 7: add image/diagram handling as metadata or placeholders only.

Image intake should be metadata-first.

Diagram extraction and OCR are deferred.

Images may be registered as source artifacts with image_ref placeholders.

No image should be copied into student-facing output unless rights permit.

Diagram-dependent questions should be flagged as requiring human review.

## Phase 8 Folder and ZIP Corpus Intake

Phase 8: add folder and ZIP corpus census.

Folder and ZIP ingestion should begin as corpus census only.

The first corpus output should list files, detected formats, likely document types, subject guesses, rights/privacy status, and recommended processing order.

Corpus ingestion must not immediately create canonical curriculum.

Corpus ingestion must not publish source-derived questions.

## Phase 9 LMS Export Intake

Phase 9: add LMS export intake.

LMS export intake should start with vendor-neutral archive census and privacy screening. Vendor-specific parsing should be specified only after sample-safe exports are reviewed.

## Rights and Privacy Gate

Every input must receive rights_status and privacy_status before extraction.

Unknown rights status blocks public-facing use.

Private student data blocks hackathon/demo processing unless sanitized and explicitly approved.

Private company data blocks public demo and cross-customer reuse.

The safe default is to analyze structure, classify skills, generate original AxiomIQ practice, and avoid republishing source wording.

## Source Evidence Requirements

Every extracted claim, topic, skill, candidate procedure, candidate question, and validation report should preserve source evidence references.

Evidence references should use the most specific stable locator available, such as page, section, slide, sheet row, HTML heading, image filename, archive member path, or folder path.

## Unsupported Format Behavior

Unsupported formats should not crash the intake engine.

Unsupported formats should produce a blocked_unsupported_format or skipped_unsupported_format record.

Unsupported files should remain preserved or explicitly skipped according to the intake policy.

The batch summary should report processed_count, skipped_count, and failed_count.

## Parser Dependency Policy

Parser dependencies must be introduced only through separately authorized implementation tasks.

Each new dependency should be justified by file type, license, security posture, local-only behavior, and deterministic output requirements.

No dependency is added by this roadmap.

## Validation Requirements

Future validation checks for each new file type should include:
- input file registered
- source_document created
- source_interpretation created
- feature flags created
- rights_status present
- privacy_status present
- processing recommendation present
- source evidence references preserved
- unsupported formats skipped safely
- no DB contact
- no operational Alpha contact
- no canonical promotion
- all outputs non-live and review-required

## Non-Live Boundary

File type expansion must remain non-live.

File type expansion must not write to the live database.

File type expansion must not alter operational Alpha.

File type expansion must not serve unreviewed content to students.

File type expansion must not promote candidates into canonical content without separate authorization.

## Human Review Boundary

All extracted content, source interpretation, topic maps, procedure candidates, question candidates, generation families, packages, and validation reports should remain human_review_required or review_pending until reviewed.

Human review is required before canonical promotion, live deployment, student visibility, or external reuse.

## Risks

Major risks include copyright exposure, private student data exposure, OCR errors, parser instability, lossy table extraction, slide/image context loss, archive safety issues, and accidental promotion of unreviewed source-derived content.

## Recommended Implementation Sequence

1. COURSE-COMPILER-INGEST-FILE-TYPE-ROADMAP-COMMIT-001
2. COURSE-COMPILER-INGEST-FILE-TYPE-ROADMAP-PUSH-001
3. COURSE-COMPILER-INGEST-TXT-MD-STABILIZATION-001
4. COURSE-COMPILER-INGEST-PDF-TEXT-ONLY-SPEC-001
5. COURSE-COMPILER-INGEST-DOCX-SPEC-001
6. COURSE-COMPILER-CORPUS-CENSUS-SPEC-001
7. COURSE-COMPILER-TEXTBOOK-PROCEDURE-QUESTION-EXTRACTION-V0-1-SPEC-001

## Explicit Non-Goals

This roadmap does not implement file parsers, install dependencies, process PDFs, process DOCX files, process images, run intake on new inputs, create intake runs, modify demo outputs, or authorize canonical promotion.

## Do Not Do Yet

Do not add parser dependencies.

Do not process PDFs, DOCX files, images, zip archives, LMS exports, textbook packets, or new folders.

Do not run intake on new inputs.

Do not create a new intake run.

Do not contact any database.

Do not touch operational Alpha.

Do not promote candidates into canonical content.
