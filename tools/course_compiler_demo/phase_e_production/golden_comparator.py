"""Golden benchmark comparison for sealed Phase E replay."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .common import load_json, sha256_file, write_json
from .sealed_benchmark_store import load_sealed_benchmark


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class GoldenComparisonError(ValueError):
    """Raised when a golden comparison cannot safely unseal."""


def _require_hash(path: Path, expected: str, label: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise GoldenComparisonError(f"{label} hash mismatch: {actual} != {expected}")


def compare_to_benchmark(
    *,
    record_dir: Path,
    dispatch_dir: Path,
    benchmark_index_entry: dict[str, Any],
    access_reason: str = "post_precomparison_seal_comparison",
) -> dict[str, Any]:
    generation_dir = record_dir / "generation"
    derivation_dir = record_dir / "derivation"
    comparison_dir = record_dir / "comparison"
    precomparison_dir = record_dir / "precomparison"
    candidate_path = generation_dir / "generated_candidate.json"
    derivation_path = derivation_dir / "independent_derivation.json"
    generation_manifest_path = generation_dir / "generation_input_manifest.json"
    derivation_manifest_path = derivation_dir / "derivation_input_manifest.json"
    seal_path = precomparison_dir / "precomparison_seal.json"
    comparator_start_timestamp = utc_now()
    for path in (candidate_path, derivation_path, generation_manifest_path, derivation_manifest_path, seal_path):
        if not path.exists():
            raise GoldenComparisonError(f"premature comparator access rejected; missing {path.name}")
    seal = load_json(seal_path)
    if seal.get("benchmark_unsealed") is not False:
        raise GoldenComparisonError("benchmark already unsealed")
    _require_hash(candidate_path, seal["candidate_sha256"], "candidate")
    _require_hash(derivation_path, seal["derivation_sha256"], "derivation")
    benchmark_unseal_timestamp = utc_now()
    benchmark = load_sealed_benchmark(
        store_root=dispatch_dir / "sealed_benchmarks",
        benchmark_identifier=benchmark_index_entry["benchmark_identifier"],
        sealed_benchmark_path=dispatch_dir / benchmark_index_entry["sealed_benchmark_path"],
        reader_component="golden_comparator",
        access_reason=access_reason,
        log_path=comparison_dir / "benchmark_access_log.json",
    )
    candidate = load_json(candidate_path)
    derivation = load_json(derivation_path)
    exact_wording = candidate.get("prompt") == benchmark.get("benchmark_prompt")
    answer_agrees = derivation.get("normalized_answer") == benchmark.get("expected_answer")
    warnings = []
    if exact_wording:
        warnings.append("BENCHMARK_EXACT_WORDING_MATCH_LEAKAGE_REVIEW")
    comparator_completion_timestamp = utc_now()
    candidate_postcomparison_sha256 = sha256_file(candidate_path)
    derivation_postcomparison_sha256 = sha256_file(derivation_path)
    result = {
        "comparison_schema_version": "PHASE_E_GOLDEN_COMPARISON_v0_1",
        "benchmark_identifier": benchmark_index_entry["benchmark_identifier"],
        "benchmark_reader_component": "golden_comparator",
        "comparator_start_timestamp": comparator_start_timestamp,
        "benchmark_unseal_timestamp": benchmark_unseal_timestamp,
        "benchmark_access_timestamp": benchmark_unseal_timestamp,
        "comparator_completion_timestamp": comparator_completion_timestamp,
        "candidate_precomparison_sha256": seal["candidate_sha256"],
        "derivation_precomparison_sha256": seal["derivation_sha256"],
        "candidate_sha256": seal["candidate_sha256"],
        "derivation_sha256": seal["derivation_sha256"],
        "benchmark_unsealed": True,
        "answer_agreement": answer_agrees,
        "benchmark_comparison_result": "PASS" if answer_agrees else "MISMATCH",
        "exact_wording_match": exact_wording,
        "warnings": warnings,
        "benchmark_canary_observed_by_comparator": benchmark.get("benchmark_canary"),
        "candidate_postcomparison_sha256": candidate_postcomparison_sha256,
        "derivation_postcomparison_sha256": derivation_postcomparison_sha256,
        "candidate_mutated_after_unseal": candidate_postcomparison_sha256 != seal["candidate_sha256"],
        "derivation_mutated_after_unseal": derivation_postcomparison_sha256 != seal["derivation_sha256"],
    }
    result_sha = write_json(comparison_dir / "golden_comparison.json", result)
    result["comparison_output_sha256"] = result_sha
    write_json(comparison_dir / "golden_comparison.json", result)
    updated_seal = dict(seal)
    updated_seal.update(
        {
            "benchmark_unsealed": True,
            "benchmark_unseal_timestamp": benchmark_unseal_timestamp,
            "benchmark_access_timestamp": benchmark_unseal_timestamp,
            "comparator_start_timestamp": comparator_start_timestamp,
            "comparator_completion_timestamp": comparator_completion_timestamp,
            "comparison_output_sha256": sha256_file(comparison_dir / "golden_comparison.json"),
            "candidate_precomparison_sha256": seal["candidate_sha256"],
            "candidate_postcomparison_sha256": result["candidate_postcomparison_sha256"],
            "derivation_precomparison_sha256": seal["derivation_sha256"],
            "derivation_postcomparison_sha256": result["derivation_postcomparison_sha256"],
            "candidate_mutated_after_unseal": result["candidate_mutated_after_unseal"],
            "derivation_mutated_after_unseal": result["derivation_mutated_after_unseal"],
        }
    )
    write_json(seal_path, updated_seal)
    return result
