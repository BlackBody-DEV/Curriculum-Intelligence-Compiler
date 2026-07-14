# Reproduction Result Contract v1

Each package reproduction result records:

- harness and dependency versions
- mode and package identity
- repeat count
- input inventory digest
- artifact digests
- validator and consumer verdicts
- dry-run plan statuses
- deterministic fields compared
- volatile fields excluded
- manifest and artifact digest matches
- artifact, dependency, reference, error, and warning ordering matches
- package non-mutation confirmation
- boundary evidence
- reproduction verdict
- blockers and warnings

Allowed reproduction verdicts:

- `reproduced`
- `reproduced_with_expected_warnings`
- `reproduced_expected_rejection`
- `not_reproduced`
- `harness_error`
- `generation_unavailable`

Volatile fields include timestamps and path observability fields. Deterministic fields include package identity, contract and version, verdicts, inventory, references, dependency order, classifications, known gaps, warnings, errors, checksums, plan status, prohibited-operation declarations, and boundary booleans.
