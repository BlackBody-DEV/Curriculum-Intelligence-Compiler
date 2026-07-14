# Semantic Validator CLI v1

## Command

```bash
python3 -m tools.course_compiler_demo.release_package.validate.validate_release_package \
  --package tools/course_compiler_demo/release_package/golden_packages/minimal_valid \
  --output reports/course_compiler_demo/integration_readiness/validation/minimal_valid
```

## Options

- `--package <package-root>`: package directory containing `manifest.json`
- `--output <compiler-owned-output-directory>`: report destination
- `--no-write`: print the structured result and write no files

## Output Rules

Without `--no-write`, the validator writes only:

- `validation_result.json`
- `validation_report.md`

The output path must stay inside the compiler repository, must not overlap the package being validated, must not overlap frozen fixtures, and must not resolve under any adaptive-platform path.

## Fixture Verdicts

- `minimal_valid`: `accept`
- `normal_multi_artifact`: `accept`
- `known_nonblocking_gaps`: `accept_with_warnings`
- `deliberately_invalid`: `reject`
- `safety_boundary_violation`: `reject`

Rejected fixture reports are rejection evidence only.

## Future Offline Consumer Interface

The offline reference consumer should treat the structured validator result as its gate input. It may proceed only for `accept` or `accept_with_warnings`, and it must preserve warnings in any dry-run plan.
