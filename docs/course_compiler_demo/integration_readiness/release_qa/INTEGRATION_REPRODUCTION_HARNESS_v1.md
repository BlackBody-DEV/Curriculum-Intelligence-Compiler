# Integration Reproduction Harness v1

The integration reproduction harness proves deterministic replay for frozen compiler-side portable package fixtures. It validates a package, runs the offline reference consumer, compares repeat-run verdicts and ordering, proves package non-mutation, and emits zero-boundary-contact evidence.

This harness does not claim full compiler integration readiness. A real Statics source has not yet been selected or reproduced.

Required status distinction:

- `HARNESS_REPRODUCTION_CONFIRMED`
- `REAL_SOURCE_REPRODUCTION_NOT_RUN`
- `COMPILER_INTEGRATION_READINESS_NOT_YET_CONFIRMED`

## Processing Sequence

1. Verify package and output-path safety.
2. Capture input inventory, hashes, byte sizes, modes, and symlink metadata.
3. Invoke the semantic validator in memory.
4. Invoke the offline consumer in memory.
5. Normalize deterministic fields.
6. Repeat the complete run.
7. Compare verdicts, ordering, references, warnings, errors, manifest digest, and artifact digests.
8. Verify source package non-mutation.
9. Emit zero-boundary-contact evidence.
10. Aggregate the reproduction verdict.

## Clean-State Requirement

Fixture reproduction requires a clean compiler source state. During local test isolation, dirty-state handling may be exercised through narrowly scoped unit tests.

## Modes

- `fixture_reproduction`
- `existing_package_reproduction`
- `future_generated_package_reproduction`
