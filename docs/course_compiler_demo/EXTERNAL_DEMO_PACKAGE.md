# AxiomIQ Curriculum Intelligence Compiler External Demo Package

## Demo Status

This is a non-live MVP for the AxiomIQ Curriculum Intelligence Compiler. It is published in `BlackBody-DEV/Curriculum-Intelligence-Compiler` on `main`.

All learning outputs are `demo_unverified`. This is not canonical curriculum. This is not production-ready content. This does not update operational Alpha readiness or mastery. No database contact is required. No operational Alpha integration is present.

## One-Sentence Summary

The demo shows a local compiler pipeline that turns a sample Algebra I source document into candidate curriculum structure, practice packaging, assessment packaging, performance tracking preview, validation reporting, and demo-ready summaries.

## What This MVP Proves

- A single math source document can move through a repeatable local compiler pipeline.
- The pipeline can identify candidate topics and micro-skills from a source.
- The pipeline can package demo practice items and demo assessment items.
- The pipeline can produce a performance tracking preview without touching live readiness or mastery.
- The pipeline can generate validation and content gap reports that preserve the Non-Live boundary.
- Another operator can run and smoke-test the demo without relying on chat history.

## Demo Input

The demo input is:

```text
tools/course_compiler_demo/sample_inputs/math_demo_input.txt
```

It is a local sample Algebra I document used to demonstrate math-first source interpretation, extraction, packaging, reporting, and validation.

## End-to-End Pipeline

1. Load the local source document.
2. Interpret source type, subject, course level, primary use, and feature flags.
3. Extract candidate topics and micro-skills.
4. Build practice targets, assessment targets, and performance tracking targets.
5. Generate demo practice, assessment, and performance tracking packages.
6. Generate validation, demo, and content gap reports.
7. Preserve `demo_unverified` status and Non-Live boundary language across learning outputs.

## Generated Outputs

The final demo output folder is:

```text
reports/course_compiler_demo/final_math_demo_001/
```

Key outputs include:

- `demo_report.md`: human-readable demo summary.
- `content_gap_report.md`: human-readable content gap summary.
- `validation_report.json`: machine-readable validation result and boundary checks.
- `curriculum_extraction_package.json`: topics, micro-skills, targets, and gaps.
- `practice_module_package.json`: demo practice package.
- `practice_assessment_package.json`: demo assessment package.
- `performance_tracking_package.json`: demo performance tracking preview.

## Final Demo Results

- topics extracted: 2
- micro-skills extracted: 6
- practice items generated: 6
- assessment items generated: 6
- content gaps reported: 5
- validation result: pass

## Validation Result

The final `validation_report.json` reports `overall_result` as `pass`. It also confirms no missing files, no required field errors, `demo_unverified` labeling, no database contact, and no backend, frontend, or operational Alpha touch reported by the demo validation layer.

## How To Run The Demo

From the repository root:

```bash
python3 tools/course_compiler_demo/run_course_compiler_demo.py \
  --input tools/course_compiler_demo/sample_inputs/math_demo_input.txt \
  --subject MATHEMATICS \
  --mode student_practice \
  --output reports/course_compiler_demo/latest
```

## How To Run The Smoke Test

From the repository root:

```bash
python3 tools/course_compiler_demo/smoke_test_course_compiler_demo.py
```

The smoke test writes a temporary verification run to:

```text
reports/course_compiler_demo/smoke_test_run/
```

Before committing, remove generated smoke-test output if it exists.

## What To Show During A Demo

- Open `docs/course_compiler_demo/OPERATOR_README.md` to show the operator path.
- Open the sample input at `tools/course_compiler_demo/sample_inputs/math_demo_input.txt`.
- Run the smoke test and show its pass summary.
- Open `reports/course_compiler_demo/final_math_demo_001/demo_report.md`.
- Open `reports/course_compiler_demo/final_math_demo_001/validation_report.json`.
- Open `reports/course_compiler_demo/final_math_demo_001/content_gap_report.md`.
- Point to the generated package JSON files only as supporting technical artifacts.

## What To Say During A Demo

This MVP proves the local shape of the compiler: it can read a math source, infer candidate curriculum structure, produce demo practice and assessment packages, preview performance tracking, and validate the output package. It is intentionally non-live and keeps all learning outputs marked `demo_unverified`.

## What Not To Claim

- Do not claim this is production-ready.
- Do not claim this is canonical curriculum.
- Do not claim this updates operational Alpha readiness or mastery.
- Do not claim this is student-ready.
- Do not claim this is database-backed.
- Do not claim this has live operational Alpha integration.
- Do not claim generated content has been human-reviewed for classroom use.

## Non-Live Boundary

This is a Non-Live local demo package. The MVP does not contact any database, student data store, hosted service, or live API. It does not touch operational Alpha files. It does not modify backend or frontend application code. It does not promote canonical curriculum. It does not update readiness or mastery.

## Known Limitations

- The current input is a narrow Algebra I sample.
- Extraction is rule-based and demo-oriented.
- Practice and assessment content is source-derived and unreviewed.
- Performance tracking is a preview, not learner-state tracking.
- Content gaps are expected because reviewed procedures and reviewed question banks are not part of the MVP.
- Multi-document input and multi-subject support are post-MVP work.

## Post-MVP Roadmap

The roadmap is documented in:

```text
docs/course_compiler_demo/POST_MVP_ROADMAP.md
```

The next planned lanes are external demo packaging, schema hardening, multi-document input, and a physics demo slice.

## Suggested Audience-Specific Framing

- Technical reviewer: focus on pipeline shape, output contracts, smoke test, validation report, and isolation boundaries.
- Education or curriculum reviewer: focus on candidate topics, micro-skills, practice package, assessment package, and content gaps.
- Funder or partner: focus on the product concept, demo proof, repeatable run path, and what remains before classroom or platform use.
- Internal operator: focus on commands, paths, expected outputs, and checks.

## Demo Success Criteria

- Correct repository and `main` branch are checked out.
- MVP tag exists and remains fixed.
- Worktree is clean before the demo.
- Smoke test passes.
- Final demo report exists.
- Validation result is `pass`.
- Outputs are marked `demo_unverified`.
- No database contact is required or performed.
- No operational Alpha contact or integration is present.

## Appendix: Key Paths

- Operator README: `docs/course_compiler_demo/OPERATOR_README.md`
- Roadmap: `docs/course_compiler_demo/POST_MVP_ROADMAP.md`
- Talk track: `docs/course_compiler_demo/DEMO_TALK_TRACK.md`
- Checklist: `docs/course_compiler_demo/EXTERNAL_DEMO_CHECKLIST.md`
- FAQ: `docs/course_compiler_demo/EXTERNAL_DEMO_FAQ.md`
- Sample input: `tools/course_compiler_demo/sample_inputs/math_demo_input.txt`
- Demo CLI: `tools/course_compiler_demo/run_course_compiler_demo.py`
- Smoke test: `tools/course_compiler_demo/smoke_test_course_compiler_demo.py`
- Final demo report: `reports/course_compiler_demo/final_math_demo_001/demo_report.md`
- Content gap report: `reports/course_compiler_demo/final_math_demo_001/content_gap_report.md`
- Validation report: `reports/course_compiler_demo/final_math_demo_001/validation_report.json`
