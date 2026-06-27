# Demo Talk Track

## 30-Second Version

This is a prototype, non-live Curriculum Intelligence Compiler MVP. It takes a sample Algebra I source document and produces candidate curriculum structure, a practice package, an assessment package, a performance tracking preview, and a validation report. All generated learning outputs are `demo_unverified`.

## 2-Minute Version

The demo starts with a local math source document. The compiler interprets the document, extracts candidate topics and micro-skills, then packages those candidates into demo practice and assessment outputs. It also creates a performance tracking preview, a content gap report, a human-readable demo report, and a validation report.

The important boundary is that this is not live product behavior. It is not canonical curriculum, not production-ready, not student-ready, and not integrated with operational Alpha. It does not contact a database or update readiness or mastery.

## 5-Minute Walkthrough

1. Show the sample Algebra I input file.
2. Run the smoke test.
3. Open the final `demo_report.md`.
4. Point out the topic map and micro-skill map.
5. Show the practice package and assessment package summaries.
6. Explain the performance tracking preview as a local preview only.
7. Open `content_gap_report.md` and explain that the gaps are expected and useful.
8. Open `validation_report.json` and show the `pass` result.
9. Close with the Non-Live boundary and post-MVP roadmap.

## Technical Reviewer Version

This MVP is a local pipeline and output-contract proof. The strongest technical signals are the repeatable CLI, the smoke test, the expected-output manifest, the validation report, and the stable final demo output folder. The current implementation is intentionally narrow and should be judged as a staged compiler slice, not a production integration.

## Education / Curriculum Reviewer Version

This MVP turns source material into candidate curriculum. The key word is candidate: extracted topics, micro-skills, practice items, and assessment items are demo outputs that need review before any classroom use. The content gap report is the best place to discuss what is missing before instructional trust.

## Funder / Partner Version

This MVP demonstrates the product idea in a concrete way: a curriculum intelligence layer can read a course document and produce structured practice, assessment, tracking, and validation artifacts. The current version is non-live and intentionally safe; the value is in the direction and repeatability, not a claim of classroom readiness.

## Live Demo Sequence

1. Confirm repository, branch, and clean worktree.
2. Show the sample math input.
3. Run `python3 tools/course_compiler_demo/smoke_test_course_compiler_demo.py`.
4. Show the smoke test pass summary.
5. Open `reports/course_compiler_demo/final_math_demo_001/demo_report.md`.
6. Open `reports/course_compiler_demo/final_math_demo_001/validation_report.json`.
7. Open `reports/course_compiler_demo/final_math_demo_001/content_gap_report.md`.
8. Close with the roadmap and next tasks.

## Closing Statement

The demo proves the first local end-to-end compiler path. It is a prototype with `demo_unverified` learning outputs, clear validation, and explicit safety boundaries. The next work is to harden schemas, improve external demo packaging, add multi-document input, and expand carefully into a second subject slice.

## Safe Language

- prototype
- non-live
- demo_unverified
- candidate curriculum
- practice package
- assessment package
- performance tracking preview
- validation report

## Avoid Saying

- production-ready
- canonical
- mastery-certified
- student-ready
- live Alpha integrated
- database-backed
