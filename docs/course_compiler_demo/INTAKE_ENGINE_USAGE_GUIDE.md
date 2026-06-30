# Curriculum Intake Engine Usage Guide

## What This Tool Does

The Curriculum Intake Engine is a non-live local tool for processing curriculum source files through the Course Compiler Demo lane. It takes supported files from `incoming/`, creates an intake record, runs the existing compiler pipeline, moves the original document into `original_artifacts/`, organizes generated outputs under `compiler_output/intake_runs/<intake_id>/`, and writes ACEF review scaffolds for human review.

Outputs are review scaffolds, not active curriculum. ACEF artifacts default to `human_review_required`. The tool does not contact a database. The tool does not update operational Alpha. The tool does not promote canonical curriculum.

## Where To Put Input Documents

Put input files in:

```text
incoming/
```

Each supported file is processed as a local intake item. After processing, the original file should no longer remain in `incoming/`; it is moved to `original_artifacts/`.

## Supported Input Formats

The current intake engine supports:

- `.txt`
- `.md`

Unsupported formats are left in `incoming/` and reported by the command. PDF, DOCX, OCR, and production textbook extraction are not implemented yet.

## How To Run The Intake Engine

From the repository root:

```bash
python3 tools/course_compiler_demo/intake/intake_engine.py
```

The no-argument command uses these defaults:

- input folder: `incoming/`
- original artifact folder: `original_artifacts/`
- output root: `compiler_output/`
- subject: `MATHEMATICS`
- mode: `student_practice`

## What Happens During Processing

For each supported input file, the intake engine:

1. assigns an `intake_id`,
2. runs the existing Course Compiler Demo pipeline,
3. writes compiler outputs to `compiler_output/intake_runs/<intake_id>/`,
4. moves the original file to `original_artifacts/`,
5. writes `intake_record.json`,
6. creates ACEF scaffold JSON files,
7. copies subject-oriented scaffold artifacts under `compiler_output/math/`,
8. marks review artifacts as `human_review_required`.

## Where The Original Document Goes

Original files are moved to:

```text
original_artifacts/
```

The archive filename includes the `intake_id` so the original source can be traced back to its intake run. The original artifact path is recorded in `intake_record.json`.

## Where Extracted Outputs Go

Run outputs are written to:

```text
compiler_output/intake_runs/<intake_id>/
```

That folder contains `intake_record.json`, the existing compiler output set, reports, validation output, and ACEF scaffolds.

## Where ACEF Scaffolds Go

ACEF run scaffolds are written inside the intake run folder:

```text
compiler_output/intake_runs/<intake_id>/
```

ACEF subject staging outputs are written to:

```text
compiler_output/math/
```

The current staging folders are:

- `compiler_output/math/packages/`
- `compiler_output/math/procedures/`
- `compiler_output/math/questions/`
- `compiler_output/math/generation_families/`
- `compiler_output/math/validation/`

## Folder Map

```text
incoming/
original_artifacts/
compiler_output/
compiler_output/intake_runs/
compiler_output/math/
compiler_output/math/packages/
compiler_output/math/procedures/
compiler_output/math/questions/
compiler_output/math/generation_families/
compiler_output/math/validation/
tools/course_compiler_demo/intake/
```

## Example: Processing A Math Homework File

```bash
cd /Users/fanarichardson/Documents/AxiomIQ

cp path/to/my_document.txt incoming/

python3 tools/course_compiler_demo/intake/intake_engine.py

find original_artifacts -maxdepth 2 -type f | sort
find compiler_output/intake_runs -maxdepth 3 -type f | sort
```

After processing:

- `incoming/` should no longer contain the processed file.
- `original_artifacts/` should contain the archived source document.
- `compiler_output/intake_runs/<intake_id>/` should contain `intake_record.json`, compiler outputs, and ACEF scaffolds.
- `compiler_output/math/` should contain subject-oriented staging artifacts.

## How To Inspect Results

Start with:

```text
compiler_output/intake_runs/<intake_id>/intake_record.json
compiler_output/intake_runs/<intake_id>/validation_report.json
compiler_output/intake_runs/<intake_id>/demo_report.md
compiler_output/intake_runs/<intake_id>/acef_package_scaffold.json
```

Then inspect the ACEF procedure, question, generation family, and validation scaffold files. Treat every generated learning artifact as requiring human review.

## How To Read intake_record.json

`intake_record.json` is the run-level ledger. It records:

- `intake_id`
- original filename
- original artifact archive path
- original input path
- compiler output path
- detected file type
- detected subject
- detected document type
- processing mode
- rights and privacy status
- `db_contact`
- `operational_alpha_contact`
- `human_review_required`

For this non-live lane, `db_contact` and `operational_alpha_contact` should be `false`.

## How To Read acef_package_scaffold.json

`acef_package_scaffold.json` is the package-level review scaffold. It is not active curriculum. It summarizes the ACEF package candidate, references generated procedure/question/generation-family/validation scaffolds, lists known gaps, and preserves the promotion recommendation:

```text
review_before_commit
```

The expected package status is:

```text
human_review_required
```

## What human_review_required Means

`human_review_required` means the artifact was generated by the local compiler and must be reviewed before it can be trusted, committed into a reviewed content lane, promoted, shown to students, or used by any live system.

No compiler output becomes active without human review.

## What demo_unverified Means

`demo_unverified` means the artifact belongs to the non-live demo compiler lane. It is useful for demonstrating the pipeline and inspecting candidate structure, but it is not canonical curriculum and is not production-ready content.

## What Not To Do

- Do not claim intake outputs are active curriculum.
- Do not claim intake outputs are canonical.
- Do not claim intake outputs are production-ready.
- Do not claim intake outputs are student-visible.
- Do not claim intake outputs update operational Alpha readiness or mastery.
- Do not connect the intake engine to any database.
- Do not place unsupported source formats into production expectations.
- Do not manually edit generated output into reviewed status.

## Troubleshooting

- If no files are processed, confirm supported `.txt` or `.md` files exist in `incoming/`.
- If unsupported files are reported, convert them to `.txt` or `.md` for this first version.
- If an original file is missing from `incoming/` after a run, check `original_artifacts/`.
- If an intake run folder is missing, check the terminal output for errors.
- If JSON inspection fails, rerun JSON validation on the specific file before using the output.
- If the worktree contains generated output you do not intend to commit, review the task scope before staging.

## Current Limitations

- Supports only `.txt` and `.md`.
- Does not implement PDF, DOCX, OCR, or textbook extraction.
- Does not perform human review.
- Does not promote canonical curriculum.
- Does not contact a database.
- Does not update operational Alpha.
- ACEF outputs are scaffold-level and `human_review_required`.

## Next Planned Improvements

- Add safer temporary or dry-run modes for operator testing.
- Add richer intake validation summaries.
- Add multi-document intake bundles.
- Add stricter ACEF schema validation.
- Add review workflow documentation.
- Add future support for textbook extraction only after explicit authorization.

## ACEF Review Chain

ACEF is the target exchange format for AxiomIQ review. Useful outputs must preserve this chain:

```text
Subject → Topic → Subtopic → Micro-skill → Procedure → Question
```

A procedure is only useful if linked to Subject → Topic → Subtopic → Micro-skill.

A question is only useful if linked to Subject → Topic → Subtopic → Micro-skill → Procedure → Question.

No compiler output becomes active without human review.
