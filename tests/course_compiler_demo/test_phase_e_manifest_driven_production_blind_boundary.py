import ast
import json
from pathlib import Path

import pytest

from tools.course_compiler_demo.phase_e_production import candidate_generator, independent_deriver
from tools.course_compiler_demo.phase_e_production.common import sha256_file, write_json
from tools.course_compiler_demo.phase_e_production.golden_comparator import GoldenComparisonError, compare_to_benchmark
from tools.course_compiler_demo.phase_e_production.golden_replay import (
    build_derivation_packet,
    build_generation_packet,
    create_precomparison_seal,
    create_split_snapshots,
    golden_index_entry,
    load_replay_state_without_unseal,
    run_one_record,
)
from tools.course_compiler_demo.phase_e_production.sealed_benchmark_store import (
    SealedBenchmarkAccessError,
    load_sealed_benchmark,
)

ROOT = Path(__file__).resolve().parents[2]
PHASE_E = ROOT / "tools/course_compiler_demo/phase_e_production"
CANARY = "CANARY_BENCHMARK_ONLY_7391"


def sample_row(answer_type="numeric"):
    question_type = "multiple_choice" if answer_type == "multiple_choice" else "numeric_tolerance"
    contract = (
        {"representation": "complete_option", "correct_option_id": "B"}
        if answer_type == "multiple_choice"
        else {"parts": [{"label": "R", "expected_value": 999, "unit": "N"}]}
    )
    return {
        "manifest_uuid": "row-0001",
        "ordinal": 1,
        "family_identifier": "Force Systems",
        "destination_canonical_path": "curriculum/statics/questions/STATICS_FORCE_SYSTEMS/001.json",
        "ledger_identity": {"ledger_id": "ledger-v1", "ordinal": 1},
        "signed_procedure": {"procedure_id": "proc-force-v1", "signature": "signed"},
        "procedure_id": "proc-force-v1",
        "procedure_sha256": "abc123",
        "generation_family": "given_components_two_forces",
        "difficulty": 1,
        "question_type": question_type,
        "answer_type": answer_type,
        "answer_parts_contract": contract,
        "tolerance_policy": {"absolute": 1.0},
        "permitted_failure_signals": ["axis_confusion", "unclassified"],
        "prompt_constraints": "Use text only and state sign convention.",
        "primitive_input_data": "One supplied component vector: F1=<10,0> N.",
        "diagram_policy": {"diagram_required": False},
        "uniqueness_constraints": ["avoid exact duplicate prompts"],
    }


def sample_benchmark(answer_type="numeric"):
    expected = {"type": "multiple_choice", "correct_option_id": "A"} if answer_type == "multiple_choice" else {"type": "numeric", "value": 10.0, "unit": "N"}
    return {
        "benchmark_identifier": "bench-0001",
        "source_path": "external/benchmarks/bench-0001.json",
        "source_sha256": "source-sha",
        "manifest_uuid": "row-0001",
        "ordinal": 1,
        "procedure_id": "proc-force-v1",
        "procedure_sha256": "abc123",
        "question_type": "multiple_choice" if answer_type == "multiple_choice" else "numeric_tolerance",
        "answer_type": answer_type,
        "benchmark_prompt": "This sealed benchmark prompt contains F1=<10,0> N and must not enter generation.",
        "expected_answer": expected,
        "worked_solution": ["sealed worked solution"],
        "correct_option_id": "A" if answer_type == "multiple_choice" else None,
        "answer_bearing_parameters": {"sealed_value": 10},
        "benchmark_canary": CANARY,
    }


def _walk_text(root: Path) -> str:
    chunks = []
    for path in sorted(root.rglob("*.json")):
        chunks.append(path.read_text())
    return "\n".join(chunks)


def test_static_import_boundaries_exclude_sealed_store_and_comparator():
    forbidden = {
        "candidate_generator.py": {"sealed_benchmark_store", "golden_comparator"},
        "independent_deriver.py": {"sealed_benchmark_store", "golden_comparator", "candidate_generator"},
    }
    for filename, forbidden_modules in forbidden.items():
        tree = ast.parse((PHASE_E / filename).read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.rsplit(".", 1)[-1] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.rsplit(".", 1)[-1])
        assert not (imported & forbidden_modules)


def test_generator_and_derivation_packets_exclude_benchmark_values():
    row = sample_row("multiple_choice")
    benchmark = sample_benchmark("multiple_choice")
    generation_packet = build_generation_packet(row, generation_seed="seed")
    candidate = candidate_generator.generate_candidate(generation_packet)
    derivation_packet = build_derivation_packet(candidate, row)

    serialized_generation = json.dumps(generation_packet, sort_keys=True)
    serialized_derivation = json.dumps(derivation_packet, sort_keys=True)
    for prohibited in [
        benchmark["benchmark_prompt"],
        "sealed worked solution",
        CANARY,
        "sealed_value",
        "correct_option_id\": \"B",
    ]:
        assert prohibited not in serialized_generation
        assert prohibited not in serialized_derivation
    assert json.dumps(benchmark["expected_answer"], sort_keys=True) not in serialized_generation
    assert generation_packet["blind_boundary_certification"] == {
        "benchmark_prompt_present": False,
        "benchmark_answer_present": False,
        "benchmark_solution_present": False,
        "benchmark_correct_option_present": False,
        "benchmark_answer_parameters_present": False,
        "sealed_benchmark_access": False,
    }
    assert derivation_packet["blind_boundary_certification"]["generator_final_answer_function_used"] is False


def test_nested_benchmark_fields_are_rejected_in_generator_and_deriver_packets():
    generation_packet = build_generation_packet(sample_row(), generation_seed="seed")
    generation_packet["nested"] = {"expected_answer": {"value": 10}}
    with pytest.raises(ValueError, match="expected_answer"):
        candidate_generator.validate_generation_packet(generation_packet)

    candidate = candidate_generator.generate_candidate(build_generation_packet(sample_row(), generation_seed="seed"))
    derivation_packet = build_derivation_packet(candidate, sample_row())
    derivation_packet["nested"] = {"worked_solution": ["sealed"]}
    with pytest.raises(ValueError, match="worked_solution"):
        independent_deriver.validate_derivation_packet(derivation_packet)


def test_golden_benchmark_index_contains_only_safe_fields(tmp_path):
    benchmark = sample_benchmark()
    entry = golden_index_entry(benchmark, "sealed_benchmarks/bench-0001.json")
    serialized = json.dumps(entry, sort_keys=True)
    assert "benchmark_prompt" not in serialized
    assert "expected_answer" not in serialized
    assert "worked_solution" not in serialized
    assert "correct_option" not in serialized
    assert CANARY not in serialized


def test_unauthorized_benchmark_access_is_logged_and_rejected(tmp_path):
    dispatch = tmp_path / "dispatch"
    sealed = dispatch / "sealed_benchmarks/bench-0001.json"
    write_json(sealed, {"benchmark_identifier": "bench-0001", "expected_answer": {"value": 10}, "benchmark_canary": CANARY})
    log_path = tmp_path / "access.json"

    with pytest.raises(SealedBenchmarkAccessError):
        load_sealed_benchmark(
            store_root=dispatch / "sealed_benchmarks",
            benchmark_identifier="bench-0001",
            sealed_benchmark_path=sealed,
            reader_component="candidate_generator",
            access_reason="should fail",
            log_path=log_path,
        )
    log = json.loads(log_path.read_text())
    assert log[-1]["outcome"] == "rejected_candidate_generator_access"
    assert CANARY not in json.dumps(log)


def test_comparator_rejects_premature_access_before_seal(tmp_path):
    dispatch = tmp_path / "dispatch/RUN"
    snapshot = create_split_snapshots(dispatch_dir=dispatch, row=sample_row(), benchmark=sample_benchmark())
    record = tmp_path / "runs/RUN/row-0001"
    with pytest.raises(GoldenComparisonError, match="missing generated_candidate"):
        compare_to_benchmark(record_dir=record, dispatch_dir=dispatch, benchmark_index_entry=snapshot["index_entry"])


def test_candidate_and_derivation_mutation_after_seal_are_rejected(tmp_path):
    row = sample_row()
    benchmark = sample_benchmark()
    dispatch = tmp_path / "dispatch/RUN"
    snapshot = create_split_snapshots(dispatch_dir=dispatch, row=row, benchmark=benchmark)
    record = tmp_path / "runs/RUN/row-0001"
    generation_packet = build_generation_packet(row, generation_seed="seed")
    candidate = candidate_generator.generate_candidate(generation_packet)
    write_json(record / "generation/generation_input_manifest.json", generation_packet)
    write_json(record / "generation/generated_candidate.json", candidate)
    derivation_packet = build_derivation_packet(candidate, row)
    write_json(record / "derivation/derivation_input_manifest.json", derivation_packet)
    write_json(record / "derivation/independent_derivation.json", independent_deriver.derive_answer(derivation_packet))
    create_precomparison_seal(record)

    candidate["prompt"] = "mutated after seal"
    write_json(record / "generation/generated_candidate.json", candidate)
    with pytest.raises(GoldenComparisonError, match="candidate hash mismatch"):
        compare_to_benchmark(record_dir=record, dispatch_dir=dispatch, benchmark_index_entry=snapshot["index_entry"])

    candidate = candidate_generator.generate_candidate(generation_packet)
    write_json(record / "generation/generated_candidate.json", candidate)
    derivation_packet = build_derivation_packet(candidate, row)
    derivation = independent_deriver.derive_answer(derivation_packet)
    derivation["normalized_answer"] = {"type": "numeric", "value": -1, "unit": "N"}
    write_json(record / "derivation/independent_derivation.json", derivation)
    with pytest.raises(GoldenComparisonError, match="derivation hash mismatch"):
        compare_to_benchmark(record_dir=record, dispatch_dir=dispatch, benchmark_index_entry=snapshot["index_entry"])


def test_full_replay_canary_first_appears_during_authorized_comparison(tmp_path):
    result = run_one_record(production_root=tmp_path, run_id="RUN", row=sample_row(), benchmark=sample_benchmark())
    record = tmp_path / "runs/RUN/row-0001"
    dispatch = tmp_path / "dispatch/RUN"

    precomparison_text = "\n".join(
        [
            (record / "generation/generation_input_manifest.json").read_text(),
            (record / "generation/generated_candidate.json").read_text(),
            (record / "derivation/derivation_input_manifest.json").read_text(),
            (record / "derivation/independent_derivation.json").read_text(),
            (record / "precomparison/pre_unseal_duplicate_result.json").read_text(),
        ]
    )
    assert CANARY not in precomparison_text
    assert CANARY not in (dispatch / "golden_benchmark_index.json").read_text()
    assert CANARY in (record / "comparison/golden_comparison.json").read_text()
    assert result["comparison"]["benchmark_reader_component"] == "golden_comparator"
    assert result["comparison"]["answer_agreement"] is True
    access_log = json.loads((record / "comparison/benchmark_access_log.json").read_text())
    assert access_log[-1]["outcome"] == "authorized_comparator_access"
    assert result["comparison"]["candidate_postcomparison_sha256"] == result["precomparison_seal"]["candidate_sha256"]
    assert result["comparison"]["derivation_postcomparison_sha256"] == result["precomparison_seal"]["derivation_sha256"]


def test_restart_state_keeps_sealed_benchmark_out_of_general_state(tmp_path):
    run_one_record(production_root=tmp_path, run_id="RUN", row=sample_row(), benchmark=sample_benchmark())
    state = load_replay_state_without_unseal(production_root=tmp_path, run_id="RUN", record_identifier="row-0001")
    serialized = json.dumps(state, sort_keys=True)
    benchmark = sample_benchmark()
    assert benchmark["benchmark_prompt"] not in serialized
    assert benchmark["worked_solution"][0] not in serialized
    assert "sealed_value" not in serialized
    assert CANARY not in serialized
    assert state["golden_benchmark_index"][0]["sealed_benchmark_path"] == "sealed_benchmarks/bench-0001.json"
    assert state["benchmark_unsealed"] is True


def test_unseal_timestamps_are_written_and_do_not_change_candidate_hashes(tmp_path):
    row = sample_row()
    benchmark = sample_benchmark()
    dispatch = tmp_path / "dispatch/RUN"
    snapshot = create_split_snapshots(dispatch_dir=dispatch, row=row, benchmark=benchmark)
    record = tmp_path / "runs/RUN/row-0001"
    generation_packet = build_generation_packet(row, generation_seed="seed")
    candidate = candidate_generator.generate_candidate(generation_packet)
    write_json(record / "generation/generation_input_manifest.json", generation_packet)
    candidate_sha = write_json(record / "generation/generated_candidate.json", candidate)
    derivation_packet = build_derivation_packet(candidate, row)
    write_json(record / "derivation/derivation_input_manifest.json", derivation_packet)
    derivation_sha = write_json(record / "derivation/independent_derivation.json", independent_deriver.derive_answer(derivation_packet))
    seal = create_precomparison_seal(record)
    assert "benchmark_unseal_timestamp" not in seal

    comparison = compare_to_benchmark(record_dir=record, dispatch_dir=dispatch, benchmark_index_entry=snapshot["index_entry"])
    reopened_seal = json.loads((record / "precomparison/precomparison_seal.json").read_text())
    assert reopened_seal["benchmark_unseal_timestamp"].endswith("Z")
    assert reopened_seal["benchmark_access_timestamp"].endswith("Z")
    assert reopened_seal["comparator_start_timestamp"].endswith("Z")
    assert reopened_seal["comparator_completion_timestamp"].endswith("Z")
    assert reopened_seal["candidate_precomparison_sha256"] == candidate_sha
    assert reopened_seal["candidate_postcomparison_sha256"] == candidate_sha
    assert reopened_seal["derivation_precomparison_sha256"] == derivation_sha
    assert reopened_seal["derivation_postcomparison_sha256"] == derivation_sha
    assert comparison["candidate_mutated_after_unseal"] is False
    assert comparison["derivation_mutated_after_unseal"] is False


def test_pre_unseal_duplicate_excludes_assigned_benchmark_and_exact_wording_warns(tmp_path):
    benchmark = sample_benchmark()
    row = sample_row()
    result = run_one_record(production_root=tmp_path, run_id="RUN", row=row, benchmark=benchmark)
    record = tmp_path / "runs/RUN/row-0001"
    duplicate = json.loads((record / "precomparison/pre_unseal_duplicate_result.json").read_text())
    assert duplicate["assigned_benchmark_excluded"] is True
    assert result["comparison"]["benchmark_comparison_result"] == "PASS"
    assert "BENCHMARK_EXACT_WORDING_MATCH_LEAKAGE_REVIEW" not in result["comparison"]["warnings"]

    # Create an exact benchmark wording match after sealing to prove the comparator classifies it.
    dispatch = tmp_path / "dispatch/RUN2"
    snapshot = create_split_snapshots(dispatch_dir=dispatch, row=row, benchmark=benchmark)
    record2 = tmp_path / "runs/RUN2/row-0001"
    generation_packet = build_generation_packet(row, generation_seed="seed")
    candidate = candidate_generator.generate_candidate(generation_packet)
    candidate["prompt"] = benchmark["benchmark_prompt"]
    write_json(record2 / "generation/generation_input_manifest.json", generation_packet)
    write_json(record2 / "generation/generated_candidate.json", candidate)
    derivation_packet = build_derivation_packet(candidate, row)
    write_json(record2 / "derivation/derivation_input_manifest.json", derivation_packet)
    write_json(record2 / "derivation/independent_derivation.json", independent_deriver.derive_answer(derivation_packet))
    create_precomparison_seal(record2)
    comparison = compare_to_benchmark(record_dir=record2, dispatch_dir=dispatch, benchmark_index_entry=snapshot["index_entry"])
    assert "BENCHMARK_EXACT_WORDING_MATCH_LEAKAGE_REVIEW" in comparison["warnings"]
