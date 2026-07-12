# Docs-Only Contract Validator

## Purpose

`tools/course_compiler_demo/validate_docs_only_contract.py` is a minimal local validator for docs-only compiler task contracts.

It checks whether a contract follows the non-live docs-only boundary described by `compiler_non_live_v1`, `task_contract_v1`, and the docs-only finalize contract intent.

## Usage

Run:

```bash
python3 tools/course_compiler_demo/validate_docs_only_contract.py .axiomiq/task_contracts/docs_only_finalize_v1.json
```

Expected success marker:

```text
DOCS_ONLY_CONTRACT_VALID
```

Expected failure marker:

```text
DOCS_ONLY_CONTRACT_INVALID
```

## Checks

The validator checks:

- valid JSON
- required task-contract fields
- `risk_class` is `docs_only`
- `repository` is `Curriculum-Intelligence-Compiler`
- `policy_refs` includes `compiler_non_live_v1`
- `source_snapshot.live_alpha_access` is `forbidden`
- all required safety flags are `false`
- allowed paths stay within compiler-side docs, policy, schema, and task-contract paths
- actions are docs-only safe
- report model is present

## Non-Live Boundary

This validator does not implement a lane runner.

This validator does not perform commits or pushes automatically from a contract.

This validator does not execute task actions.

This validator does not authorize Alpha staging implementation, adaptive-platform writes, database contact, canonical promotion, student-visible delivery, live deployable output, OCR, parser implementation, importers, or dependency additions.

## Allowed Scope

The validator is intended for docs-only compiler contracts whose allowed paths are limited to:

- `docs/course_compiler_demo/`
- `reports/course_compiler_demo/`
- `.axiomiq/policies/`
- `.axiomiq/schemas/`
- `.axiomiq/task_contracts/`

## Tests

Run:

```bash
python3 -m pytest tests/course_compiler_demo/test_validate_docs_only_contract.py
```

The tests cover the published docs-only finalize contract and representative unsafe contract mutations.
