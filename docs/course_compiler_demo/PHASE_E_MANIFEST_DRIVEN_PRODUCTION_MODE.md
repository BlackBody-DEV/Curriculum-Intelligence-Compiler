# Phase E Manifest-Driven Production Mode

This task-branch implementation adds the blind-boundary foundation for `PHASE_E_MANIFEST_DRIVEN_PRODUCTION` golden replay. It remains non-live, noncanonical, external-output-only, and human-review-required.

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

## Duplicate Separation

Pre-unseal duplicate analysis excludes the assigned benchmark and compares only against non-benchmark records and other replay candidates. Benchmark comparison occurs only after unseal. Exact benchmark wording matches produce a leakage-review warning rather than automatic success.

## Scope Limit

This implementation proves only the blind-boundary foundation for golden replay. It does not prove real production throughput, next-family generalization, replacement of existing authoring lanes, canonical promotion, live-platform readiness, or Alpha 2.0 launch gating.
