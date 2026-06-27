# External Demo Checklist

## Before The Demo

- Use the correct repo: `BlackBody-DEV/Curriculum-Intelligence-Compiler`.
- Confirm you are on `main`.
- Confirm the worktree is clean.
- Confirm current `main` has been pushed.
- Confirm the MVP tag exists.
- Confirm the smoke test passes.
- Confirm the final demo report exists.
- Confirm `validation_report.json` reports `pass`.
- Confirm all learning outputs are `demo_unverified`.
- Confirm no DB contact is required.
- Confirm no operational Alpha contact is present.

## Repo / Branch / Tag Checks

```bash
git rev-parse HEAD
git branch --show-current
git status --short --untracked-files=all
git remote -v
git rev-list -n 1 v0.1.0-math-demo-mvp
```

Expected:

- Branch is `main`.
- Worktree is clean.
- Origin is `https://github.com/BlackBody-DEV/Curriculum-Intelligence-Compiler.git`.
- `v0.1.0-math-demo-mvp` exists and remains fixed at `c7837b3eb9afff6cebca9536311844abe382a737`.

## Smoke Test

Run:

```bash
python3 tools/course_compiler_demo/smoke_test_course_compiler_demo.py
```

Expected:

- Smoke test exits `0`.
- Validation result is `pass` or `pass_with_warnings`.
- Topic count is at least 1.
- Micro-skill count is at least 3.
- Practice item count is at least 1.
- Assessment item count is at least 1.
- No backend, frontend, or operational Alpha contact is reported.

## Files To Open

- `docs/course_compiler_demo/EXTERNAL_DEMO_PACKAGE.md`
- `docs/course_compiler_demo/DEMO_TALK_TRACK.md`
- `docs/course_compiler_demo/OPERATOR_README.md`
- `tools/course_compiler_demo/sample_inputs/math_demo_input.txt`
- `reports/course_compiler_demo/final_math_demo_001/demo_report.md`
- `reports/course_compiler_demo/final_math_demo_001/validation_report.json`
- `reports/course_compiler_demo/final_math_demo_001/content_gap_report.md`

## Demo Flow

1. State the Non-Live boundary.
2. Show the sample input.
3. Run the smoke test.
4. Show the final demo report.
5. Explain topics and micro-skills.
6. Explain practice and assessment package summaries.
7. Explain the performance tracking preview.
8. Explain content gaps.
9. Show validation result.
10. Close with roadmap and next tasks.

## Questions To Be Ready For

- What does the compiler read?
- What makes a topic or micro-skill a candidate?
- Are the generated practice and assessment items reviewed?
- Does this update readiness or mastery?
- Does this connect to a database?
- What would be required before classroom use?
- What changes for multi-document input?
- What changes for non-math subjects?

## Safety Boundaries

- This is a non-live MVP.
- All learning outputs are `demo_unverified`.
- This is not canonical curriculum.
- This is not production-ready content.
- This does not update operational Alpha readiness or mastery.
- No database contact is required.
- No operational Alpha integration is present.
- No student data is used.

## After The Demo

- Remove generated smoke-test output if it was created and should not be committed:

```bash
rm -rf reports/course_compiler_demo/smoke_test_run
```

- Confirm the worktree status before any commit:

```bash
git status --short --untracked-files=all
```

## Go / No-Go Checklist

- Go: correct repo.
- Go: clean worktree.
- Go: current main pushed.
- Go: MVP tag exists and is fixed.
- Go: smoke test passes.
- Go: final demo report exists.
- Go: validation result is pass.
- Go: all outputs are `demo_unverified`.
- Go: no DB contact.
- Go: no operational Alpha contact.
- No-Go: dirty worktree with unexpected files.
- No-Go: missing final demo report.
- No-Go: validation does not pass.
- No-Go: MVP tag is missing or moved.
- No-Go: any claim of production-ready, canonical, student-ready, or live Alpha integrated output.
