"""Golden replay orchestration with blind generation boundaries."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .candidate_generator import generate_candidate
from .common import PROHIBITED_BENCHMARK_FIELDS, load_json, scan_for_values, sha256_file, write_json
from .golden_comparator import compare_to_benchmark
from .independent_deriver import derive_answer

MODE_IDENTIFIER = "PHASE_E_MANIFEST_DRIVEN_PRODUCTION"


class GoldenReplayError(ValueError):
    """Raised when replay cannot continue safely."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _strip_answer_values(answer_contract: Any) -> Any:
    contract = copy.deepcopy(answer_contract)
    if isinstance(contract, dict):
        for key in list(contract):
            if key in {"value", "expected_value", "correct_option", "correct_option_id", "answer_parameters"}:
                contract.pop(key)
            else:
                contract[key] = _strip_answer_values(contract[key])
    elif isinstance(contract, list):
        return [_strip_answer_values(item) for item in contract]
    return contract


def golden_index_entry(benchmark: dict[str, Any], sealed_relative_path: str) -> dict[str, Any]:
    entry = {
        "benchmark_identifier": benchmark["benchmark_identifier"],
        "source_path": benchmark["source_path"],
        "source_sha256": benchmark["source_sha256"],
        "manifest_uuid": benchmark["manifest_uuid"],
        "ordinal": benchmark["ordinal"],
        "procedure_id": benchmark["procedure_id"],
        "procedure_sha256": benchmark["procedure_sha256"],
        "question_type": benchmark["question_type"],
        "answer_type": benchmark["answer_type"],
        "sealed_benchmark_path": sealed_relative_path,
    }
    prohibited = sorted(PROHIBITED_BENCHMARK_FIELDS.intersection(entry))
    if prohibited:
        raise GoldenReplayError(f"golden index contains prohibited fields: {prohibited}")
    return entry


def build_generation_packet(row: dict[str, Any], *, generation_seed: str) -> dict[str, Any]:
    safe_row = copy.deepcopy(row)
    safe_row["answer_parts_contract"] = _strip_answer_values(safe_row.get("answer_parts_contract"))
    return {
        "packet_schema_version": "PHASE_E_GENERATION_PACKET_v0_1",
        "manifest_identity": {
            "manifest_uuid": safe_row["manifest_uuid"],
            "ordinal": safe_row["ordinal"],
            "family_identifier": safe_row["family_identifier"],
        },
        "ledger_identity": safe_row["ledger_identity"],
        "family_identity": safe_row["family_identifier"],
        "signed_procedure": safe_row["signed_procedure"],
        "procedure_hash": safe_row["procedure_sha256"],
        "generation_family_allocation": safe_row["generation_family"],
        "difficulty": safe_row["difficulty"],
        "question_type": safe_row["question_type"],
        "answer_type": safe_row["answer_type"],
        "answer_parts_shape": safe_row["answer_parts_contract"],
        "tolerance_policy": safe_row.get("tolerance_policy"),
        "permitted_failure_signals": safe_row["permitted_failure_signals"],
        "prompt_constraints": safe_row["prompt_constraints"],
        "primitive_input_data": safe_row["primitive_input_data"],
        "diagram_policy": safe_row["diagram_policy"],
        "uniqueness_constraints": safe_row.get("uniqueness_constraints", []),
        "destination_canonical_path": safe_row["destination_canonical_path"],
        "existing_record_disposition": safe_row["existing_record_disposition"],
        "adapter_identifier": safe_row["adapter_identifier"],
        "adapter_contract_version": safe_row["adapter_contract_version"],
        "adapter_metadata": safe_row.get("adapter_metadata", {}),
        "generation_seed": generation_seed,
        "manifest_row": safe_row,
        "blind_boundary_certification": {
            "benchmark_prompt_present": False,
            "benchmark_answer_present": False,
            "benchmark_solution_present": False,
            "benchmark_correct_option_present": False,
            "benchmark_answer_parameters_present": False,
            "sealed_benchmark_access": False,
        },
    }


def build_derivation_packet(candidate: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    derivation_candidate = copy.deepcopy(candidate)
    derivation_candidate.pop("expected_answer_proposal", None)
    return {
        "packet_schema_version": "PHASE_E_DERIVATION_PACKET_v0_1",
        "generated_candidate": derivation_candidate,
        "signed_procedure": row["signed_procedure"],
        "procedure_hash": row["procedure_sha256"],
        "declared_answer_contract": _strip_answer_values(row.get("answer_parts_contract")),
        "tolerance_policy": row.get("tolerance_policy"),
        "supplied_primitive_data_in_generated_question": row["primitive_input_data"],
        "blind_boundary_certification": {
            "benchmark_answer_present": False,
            "benchmark_prompt_present": False,
            "benchmark_solution_present": False,
            "benchmark_correct_option_present": False,
            "sealed_benchmark_access": False,
            "generator_final_answer_function_used": False,
        },
    }


def create_precomparison_seal(record_dir: Path) -> dict[str, Any]:
    generation_dir = record_dir / "generation"
    derivation_dir = record_dir / "derivation"
    seal = {
        "record_identifier": record_dir.name,
        "candidate_sha256": sha256_file(generation_dir / "generated_candidate.json"),
        "derivation_sha256": sha256_file(derivation_dir / "independent_derivation.json"),
        "generation_input_sha256_values": {
            "generation_input_manifest": sha256_file(generation_dir / "generation_input_manifest.json")
        },
        "derivation_input_sha256_values": {
            "derivation_input_manifest": sha256_file(derivation_dir / "derivation_input_manifest.json")
        },
        "generation_completion_timestamp": utc_now(),
        "derivation_completion_timestamp": utc_now(),
        "benchmark_unsealed": False,
        "candidate_immutable": True,
        "derivation_immutable": True,
    }
    write_json(record_dir / "precomparison" / "precomparison_seal.json", seal)
    return seal


def create_split_snapshots(*, dispatch_dir: Path, row: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    authority_dir = dispatch_dir / "authority_snapshot"
    sealed_dir = dispatch_dir / "sealed_benchmarks"
    safe_row = copy.deepcopy(row)
    safe_row["answer_parts_contract"] = _strip_answer_values(safe_row.get("answer_parts_contract"))
    authority = {
        "snapshot_label": "READ_ONLY_AUTHORITY_SNAPSHOT",
        "manifest_row": safe_row,
        "procedure_sha256": row["procedure_sha256"],
        "answer_shape_only": safe_row.get("answer_parts_contract"),
    }
    authority_sha = write_json(authority_dir / f"{row['manifest_uuid']}.json", authority)
    sealed_payload = {
        "benchmark_identifier": benchmark["benchmark_identifier"],
        "benchmark_prompt": benchmark["benchmark_prompt"],
        "expected_answer": benchmark["expected_answer"],
        "worked_solution": benchmark["worked_solution"],
        "correct_option_id": benchmark.get("correct_option_id"),
        "answer_bearing_parameters": benchmark.get("answer_bearing_parameters", {}),
        "review_notes": benchmark.get("review_notes", "sealed"),
        "validation_conclusions": benchmark.get("validation_conclusions", "sealed"),
        "benchmark_canary": benchmark["benchmark_canary"],
    }
    sealed_path = sealed_dir / f"{benchmark['benchmark_identifier']}.json"
    sealed_sha = write_json(sealed_path, sealed_payload)
    sealed_relative = str(sealed_path.relative_to(dispatch_dir))
    index_entry = golden_index_entry(benchmark, sealed_relative)
    index_path = dispatch_dir / "golden_benchmark_index.json"
    existing_index = load_json(index_path) if index_path.exists() else []
    existing_index = [entry for entry in existing_index if entry.get("benchmark_identifier") != index_entry["benchmark_identifier"]]
    existing_index.append(index_entry)
    write_json(index_path, existing_index)
    sealed_manifest_path = dispatch_dir / "sealed_benchmark_manifest.json"
    sealed_manifest = load_json(sealed_manifest_path) if sealed_manifest_path.exists() else {"sealed_benchmarks": []}
    sealed_manifest["sealed_benchmarks"] = [entry for entry in sealed_manifest["sealed_benchmarks"] if entry.get("benchmark_identifier") != benchmark["benchmark_identifier"]]
    sealed_manifest["sealed_benchmarks"].append(
        {
            "benchmark_identifier": benchmark["benchmark_identifier"],
            "sealed_benchmark_path": sealed_relative,
            "sealed_benchmark_sha256": sealed_sha,
        }
    )
    write_json(sealed_manifest_path, sealed_manifest)
    snapshot_manifest_path = dispatch_dir / "authority_snapshot_manifest.json"
    snapshot_manifest = load_json(snapshot_manifest_path) if snapshot_manifest_path.exists() else {"snapshots": []}
    snapshot_manifest["snapshots"] = [entry for entry in snapshot_manifest["snapshots"] if entry.get("manifest_uuid") != row["manifest_uuid"]]
    snapshot_manifest["snapshots"].append(
        {
            "snapshot_label": "READ_ONLY_AUTHORITY_SNAPSHOT",
            "manifest_uuid": row["manifest_uuid"],
            "path": str((authority_dir / f"{row['manifest_uuid']}.json").relative_to(dispatch_dir)),
            "sha256": authority_sha,
        }
    )
    write_json(snapshot_manifest_path, snapshot_manifest)
    return {"index_entry": index_entry, "authority_sha256": authority_sha, "sealed_sha256": sealed_sha}


def run_one_record(*, production_root: Path, run_id: str, row: dict[str, Any], benchmark: dict[str, Any]) -> dict[str, Any]:
    dispatch_dir = production_root / "dispatch" / run_id
    record_dir = production_root / "runs" / run_id / row["manifest_uuid"]
    snapshot = create_split_snapshots(dispatch_dir=dispatch_dir, row=row, benchmark=benchmark)
    generation_packet = build_generation_packet(row, generation_seed=f"{run_id}:{row['manifest_uuid']}")
    candidate = generate_candidate(generation_packet)
    write_json(record_dir / "generation" / "generation_input_manifest.json", generation_packet)
    write_json(record_dir / "generation" / "generated_candidate.json", candidate)
    derivation_packet = build_derivation_packet(candidate, row)
    derivation = derive_answer(derivation_packet)
    write_json(record_dir / "derivation" / "derivation_input_manifest.json", derivation_packet)
    write_json(record_dir / "derivation" / "independent_derivation.json", derivation)
    write_json(
        record_dir / "precomparison" / "pre_unseal_duplicate_result.json",
        {
            "assigned_benchmark_excluded": True,
            "pre_unseal_duplicate_result": "distinct_from_non_benchmark_records",
        },
    )
    seal = create_precomparison_seal(record_dir)
    canary_hits = scan_for_values(record_dir / "generation" / "generation_input_manifest.json", [benchmark["benchmark_canary"]])
    canary_hits += scan_for_values(record_dir / "derivation" / "derivation_input_manifest.json", [benchmark["benchmark_canary"]])
    canary_hits += scan_for_values(record_dir / "precomparison" / "precomparison_seal.json", [benchmark["benchmark_canary"]])
    if canary_hits:
        raise GoldenReplayError("benchmark canary leaked before comparison")
    comparison = compare_to_benchmark(
        record_dir=record_dir,
        dispatch_dir=dispatch_dir,
        benchmark_index_entry=snapshot["index_entry"],
    )
    return {
        "run_id": run_id,
        "record_identifier": row["manifest_uuid"],
        "precomparison_seal": seal,
        "comparison": comparison,
        "snapshot": snapshot,
    }


def load_replay_state_without_unseal(*, production_root: Path, run_id: str, record_identifier: str) -> dict[str, Any]:
    record_dir = production_root / "runs" / run_id / record_identifier
    dispatch_dir = production_root / "dispatch" / run_id
    return {
        "authority_snapshot_manifest": load_json(dispatch_dir / "authority_snapshot_manifest.json"),
        "golden_benchmark_index": load_json(dispatch_dir / "golden_benchmark_index.json"),
        "generated_candidate": load_json(record_dir / "generation" / "generated_candidate.json"),
        "independent_derivation": load_json(record_dir / "derivation" / "independent_derivation.json"),
        "generation_input_manifest": load_json(record_dir / "generation" / "generation_input_manifest.json"),
        "derivation_input_manifest": load_json(record_dir / "derivation" / "derivation_input_manifest.json"),
        "precomparison_seal": load_json(record_dir / "precomparison" / "precomparison_seal.json"),
        "benchmark_unsealed": load_json(record_dir / "precomparison" / "precomparison_seal.json").get("benchmark_unsealed", False),
    }
