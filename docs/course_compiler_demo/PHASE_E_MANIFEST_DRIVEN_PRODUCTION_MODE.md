# Phase E Manifest-Driven Production Mode

This task-branch implementation adds the blind-boundary foundation for `PHASE_E_MANIFEST_DRIVEN_PRODUCTION` golden replay. It remains non-live, noncanonical, external-output-only, and human-review-required.

## Multi-Family Adapter Boundary

The replay engine now resolves family-specific authority through a registered adapter contract before any universal replay step runs. The adapter is responsible for manifest and ledger identity, procedure authority, answer-contract shape, failure-signal allowance, primitive-data extraction, diagram policy, duplicate-inventory scope, and existing-record disposition.

Implemented adapters:

- `ForceSystemsFamilyAdapter`
- `VectorOperationsFamilyAdapter`

Unknown families fail closed. `moments_and_couples` remains in the capability matrix as an authority family with no finalized immutable replay records yet, so it is not a replay gate until records exist.

Universal replay code consumes the adapter-produced row packet and must not silently inherit another family’s procedure, answer contract, failure-signal mapping, or duplicate inventory.

## Runtime Separation

The replay boundary is split across three runtime components:

- `candidate_generator.py` constructs candidate questions from sanitized generation packets.
- `independent_deriver.py` derives answers from finalized candidates without importing generator final-answer logic.
- `golden_comparator.py` is the first component permitted to unseal benchmark contents.

Sealed benchmark reads are isolated in `sealed_benchmark_store.py`. Static tests verify that the generator and deriver do not import the sealed store or comparator.

## Split Snapshots

Each replay run creates separate dispatch areas:

- `dispatch/<run_id>/authority_snapshot/` contains only generation-safe authority.
- `dispatch/<run_id>/sealed_benchmarks/` contains benchmark prompts, expected answers, worked solutions, correct options, and canaries.
- `dispatch/<run_id>/golden_benchmark_index.json` contains only identity, path, hash, manifest, procedure, and contract metadata.

The golden benchmark index intentionally excludes benchmark prompts, answers, worked solutions, correct options, answer-bearing parameters, review conclusions, and canaries.

## Precomparison Seal

Before any benchmark unseal, the runner persists:

- `generation/generated_candidate.json`
- `generation/generation_input_manifest.json`
- `derivation/independent_derivation.json`
- `derivation/derivation_input_manifest.json`
- `precomparison/precomparison_seal.json`

The seal records candidate and derivation hashes and marks both as immutable. The comparator revalidates these hashes before reading a sealed benchmark. Post-seal mutation blocks comparison.

## Benchmark Access

Every sealed benchmark access attempt is logged. Authorized comparator reads are recorded separately from rejected generator, deriver, premature comparator, path escape, and unknown-identifier attempts. Benchmark canaries are tested to remain absent from precomparison artifacts and to appear only during authorized comparison output.

## Operational Root

Phase E replay artifacts are written only under a resolved external production root. Root selection is centralized and uses this precedence:

1. explicit function or controller argument
2. controller configuration
3. `PHASE_E_COMPILER_PRODUCTION_ROOT`
4. default external root

The resolved root must be absolute, realpath-normalized, writable for write operations, and outside the compiler repository, adaptive-platform, and the active Force Systems workspace. Preexisting child directories are checked for symlink escape before writes begin.

Dashboard replay persists the root selected for each run, so reopen and restart paths use the original run root instead of re-reading the current environment. Export manifests store package paths relative to the resolved root so copied clean-room roots can reopen without falling back to absolute paths from the original machine location.

## Duplicate Separation

Pre-unseal duplicate analysis excludes the assigned benchmark and compares only against non-benchmark records and other replay candidates. Benchmark comparison occurs only after unseal. Exact benchmark wording matches produce a leakage-review warning rather than automatic success.

## Scope Limit

This implementation proves only the blind-boundary foundation for golden replay and adapter-driven multi-family replay over finalized immutable records. It does not prove real production throughput, ownership of unlanded rows, replacement of existing authoring lanes, canonical promotion, live-platform readiness, or Alpha 2.0 launch gating.
