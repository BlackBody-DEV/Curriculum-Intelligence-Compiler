# Offline Consumer CLI v1

Run in no-write mode:

```bash
python3 -m tools.course_compiler_demo.reference_consumer.consume_release_package \
  --package tools/course_compiler_demo/release_package/golden_packages/minimal_valid \
  --output reports/course_compiler_demo/integration_readiness/reference_consumer/minimal_valid \
  --no-write
```

Run in report-writing mode:

```bash
python3 -m tools.course_compiler_demo.reference_consumer.consume_release_package \
  --package tools/course_compiler_demo/release_package/golden_packages/minimal_valid \
  --output reports/course_compiler_demo/integration_readiness/reference_consumer/minimal_valid
```

No-write mode performs the permitted workflow, prints structured JSON to stdout, writes no files, creates no cache, and mutates no package artifact.

Report-writing mode writes only:

- `consumer_result.json`
- `consumer_report.md`
- `dry_run_import_plan.json`
- `artifact_enumeration.json`
- `reference_resolution.json`

Output paths must remain inside the compiler repository and must not overlap source packages, frozen fixtures, frozen contract paths, frozen validator paths, or adaptive-platform paths.
