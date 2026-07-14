# Semantic Release Package Validation v1

## Purpose

The semantic validator checks portable compiler release packages that use `compiler_release_package_v1` version `1.0.0`.

The validator is compiler-side only. It is not an adaptive-platform importer, does not contact a database, does not create runtime routes, and does not perform learner-loop work.

## Architecture

Validation runs in deterministic stages:

1. package discovery
2. JSON parsing
3. structural schema checks
4. manifest and artifact inventory checks
5. path and containment checks
6. identifier uniqueness checks
7. internal reference checks
8. source-provenance checks
9. procedure-question linkage checks
10. generation-family linkage checks
11. signal-policy checks
12. review-state checks
13. rights and safety checks
14. integrity and checksum checks
15. deterministic-manifest checks
16. known-gap classification
17. final verdict aggregation

## Verdicts

- `accept`: no errors or warnings
- `accept_with_warnings`: no errors and at least one declared nonblocking warning
- `reject`: one or more validation errors
- `validator_error`: validator invocation or output-path error

## Result Shape

The result includes package metadata, per-stage statuses, ordered errors, ordered warnings, rule results, artifact results, and boundary evidence. Every error and warning includes a rule id, severity, message, scope, field/path, evidence, and recommended action.

## Boundaries

The validator never mutates the package being checked. Report-writing mode writes only `validation_result.json` and `validation_report.md` to a caller-supplied compiler-owned output directory.
