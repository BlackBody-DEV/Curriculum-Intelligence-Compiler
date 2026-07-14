# Compiler Integration-Readiness File Ownership

## Boundary

This file ownership map applies only to `/Users/fanarichardson/Documents/AxiomIQ`.

`/Users/fanarichardson/adaptive-platform` remains read-only. No lane may stage, commit, push, copy compiler output into, or prepare changes inside adaptive-platform.

## Exclusive Ownership

| Lane | Task | Owned Paths | Notes |
|---|---|---|---|
| A | COMPILER-REAL-STATICS-SOURCE-PIPELINE-001 | `tools/course_compiler_demo/intake/`; `tools/course_compiler_demo/extract/`; `tools/course_compiler_demo/sample_inputs/real_statics/`; `reports/course_compiler_demo/integration_readiness/real_source/`; `tests/course_compiler_demo/test_real_source_pipeline*` | Existing intake and extraction modules are Lane A-owned for this sprint. Lane A is blocked until a real source is supplied. |
| B | COMPILER-PORTABLE-RELEASE-PACKAGE-CONTRACT-001 | `tools/course_compiler_demo/release_package/contracts/`; `tools/course_compiler_demo/release_package/manifest/`; `docs/course_compiler_demo/integration_readiness/package_contract/`; `tests/course_compiler_demo/test_release_package_contract*` | Owns contract and manifest definitions. |
| C | COMPILER-SEMANTIC-RELEASE-PACKAGE-VALIDATION-001 | `tools/course_compiler_demo/release_package/validate/`; `tests/course_compiler_demo/test_release_package_validation*`; `reports/course_compiler_demo/integration_readiness/validation/` | Reads Lane B contract; does not modify it unless separately authorized. |
| D | COMPILER-OFFLINE-REFERENCE-CONSUMER-001 | `tools/course_compiler_demo/reference_consumer/`; `tests/course_compiler_demo/test_reference_consumer*`; `reports/course_compiler_demo/integration_readiness/reference_consumer/` | Must not import adaptive-platform modules or read adaptive-platform at runtime. |
| E | COMPILER-STATICS-CONTENT-READINESS-14-001 | `reports/course_compiler_demo/integration_readiness/content_set/`; `docs/course_compiler_demo/integration_readiness/content_set/`; `tests/course_compiler_demo/test_integration_content_set*` | Records gaps without inventing reviewed content. |
| F | COMPILER-INTEGRATION-COMPATIBILITY-SCOPE-LOCK-001 | `docs/course_compiler_demo/integration_readiness/compatibility/`; `docs/course_compiler_demo/integration_readiness/scope_lock/`; `reports/course_compiler_demo/integration_readiness/compatibility/` | Uses adaptive-platform read-only inspection only. |
| G | COMPILER-INTEGRATION-REPRODUCTION-HARNESS-001 | `tools/course_compiler_demo/integration_readiness/`; `tests/course_compiler_demo/test_integration_readiness_reproduction*`; `reports/course_compiler_demo/integration_readiness/reproduction/`; `docs/course_compiler_demo/integration_readiness/release_qa/` | Uses existing fixtures until Lane A-D outputs land. |

## Conflict Rules

- No lane may use `git add .`.
- No lane may modify another lane's owned paths without a new explicit contract.
- Lane C and Lane D may begin early only against a versioned Lane B draft interface.
- Lane A may not modify Lane B package contract files.
- Lane E may not modify Lane A builders.
- Lane F may inspect adaptive-platform read-only but may not write reports there.
- Lane G may create harness interfaces but may not take ownership of Lane B/C/D implementation files.

## Current Conflicts

- No compiler-side file ownership conflict was found in the baseline inventory.
- Lane A has a release blocker: no real rights-cleared Statics source is currently available in the compiler repository.

