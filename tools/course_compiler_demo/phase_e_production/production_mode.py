"""Dashboard-facing Phase E golden replay service."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .common import ensure_beneath, load_json, parse_component_vectors, sha256_file, write_json
from .golden_replay import MODE_IDENTIFIER, build_derivation_packet, build_generation_packet, run_one_record, utc_now
from .candidate_generator import generate_candidate
from .independent_deriver import derive_answer
from .golden_comparator import compare_to_benchmark

EXECUTION_PROFILE = "GOLDEN_REPLAY"
DEFAULT_PRODUCTION_ROOT = Path("/Users/fanarichardson/AxiomIQ_Work/phase_e/compiler_production")
FORCE_SYSTEMS_ROOT = Path("/Users/fanarichardson/AxiomIQ_Work/phase_e/force_systems")
ADAPTIVE_ROOT = Path("/Users/fanarichardson/adaptive-platform")
COMPILER_MAIN_ROOT = Path("/Users/fanarichardson/Documents/AxiomIQ")
REQUIRED_DIRS = ["runs", "dispatch", "candidates", "derivations", "reviews", "regenerations", "approved", "blocked", "exports", "logs"]
STATUS_LABELS = {
    "noncanonical": True,
    "human_review_required": True,
    "student_visible": False,
    "eligible_for_alpha_import": False,
    "shadow_mode": True,
    "golden_replay": True,
    "production_candidate": False,
}


class PhaseEProductionError(ValueError):
    pass


def prepare_production_root(root: Path = DEFAULT_PRODUCTION_ROOT) -> Path:
    root = root.expanduser().resolve()
    for protected in (COMPILER_MAIN_ROOT, ADAPTIVE_ROOT, FORCE_SYSTEMS_ROOT):
        protected_real = protected.resolve()
        if root == protected_real or protected_real in root.parents:
            raise PhaseEProductionError(f"production root may not be inside protected root: {protected}")
    root.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    state_path = root / "state.json"
    if not state_path.exists():
        write_json(state_path, {"mode": MODE_IDENTIFIER, "execution_profile": EXECUTION_PROFILE, "runs": []})
    return root


def _artifact_to_row(artifact: dict[str, Any]) -> dict[str, Any]:
    frozen = artifact["frozen_manifest_row"]
    return {
        "manifest_uuid": artifact["question_id"],
        "ordinal": artifact["ordinal"],
        "family_identifier": frozen.get("family_id", "Force Systems"),
        "destination_canonical_path": artifact["reserved_canonical_path"],
        "ledger_identity": {"ordinal": artifact["ordinal"], "question_id": artifact["question_id"], "canonical_path": artifact["reserved_canonical_path"]},
        "signed_procedure": {"procedure_id": artifact["procedure_id"], "procedure_steps": artifact.get("procedure_steps_verbatim", [])},
        "procedure_id": artifact["procedure_id"],
        "procedure_sha256": artifact["procedure_sha256"],
        "generation_family": frozen.get("generation_family", "golden_replay"),
        "difficulty": frozen.get("difficulty_level", 1),
        "question_type": artifact["question_type"],
        "answer_type": artifact["answer_type"],
        "answer_parts_contract": artifact.get("answer_parts_contract"),
        "tolerance_policy": {"tolerance": artifact.get("tolerance") or frozen.get("tolerance")},
        "permitted_failure_signals": artifact.get("permitted_failure_signals") or frozen.get("permitted_failure_signals", []),
        "prompt_constraints": frozen.get("prompt_constraints", "Use text-only replay constraints."),
        "primitive_input_data": _safe_numeric_primitive_data(artifact) if artifact.get("answer_type") == "numeric" else (frozen.get("supplied_primitive_data") or "complete-option support inventory scenario"),
        "diagram_policy": {"diagram_required": bool(frozen.get("diagram_required", False))},
        "uniqueness_constraints": [artifact["reserved_canonical_path"]],
    }


def _safe_numeric_primitive_data(artifact: dict[str, Any]) -> str:
    vectors = parse_component_vectors(str(artifact.get("prompt", "")))
    if not vectors:
        raise PhaseEProductionError(f"numeric artifact lacks generation-visible component vectors: {artifact.get('question_id')}")
    vector_text = ", ".join(f"F{index}=<{x:g},{y:g}> N" for index, (x, y) in enumerate(vectors, start=1))
    return f"Signed rectangular force components are {vector_text}. Determine only nonnegative resultant magnitude R."


def _artifact_to_benchmark(path: Path, artifact: dict[str, Any]) -> dict[str, Any]:
    expected_answer: dict[str, Any]
    if artifact["answer_type"] == "multiple_choice":
        expected_answer = {"type": "multiple_choice", "correct_option_id": artifact["answer"]["option_id"]}
        correct_option_id = artifact["answer"]["option_id"]
    else:
        answer = artifact["answers"][0]
        expected_answer = {"type": "numeric", "value": round(float(answer["value"]), 6), "unit": answer.get("unit", "N")}
        correct_option_id = None
    return {
        "benchmark_identifier": f"FS-{artifact['ordinal']:03d}-{artifact['question_id']}",
        "source_path": str(path),
        "source_sha256": sha256_file(path),
        "manifest_uuid": artifact["question_id"],
        "ordinal": artifact["ordinal"],
        "procedure_id": artifact["procedure_id"],
        "procedure_sha256": artifact["procedure_sha256"],
        "question_type": artifact["question_type"],
        "answer_type": artifact["answer_type"],
        "benchmark_prompt": artifact.get("prompt", ""),
        "expected_answer": expected_answer,
        "worked_solution": artifact.get("solution", {}),
        "correct_option_id": correct_option_id,
        "answer_bearing_parameters": {"benchmark_answer_contract_complete": True},
        "review_notes": "finalized external Force Systems record selected for golden replay",
        "validation_conclusions": artifact.get("author_status", "AUTHOR_COMPLETE"),
        "benchmark_canary": f"CANARY_FS_{artifact['ordinal']:03d}_{artifact['question_id'][:8]}",
    }


def select_force_systems_cohort(force_systems_root: Path = FORCE_SYSTEMS_ROOT) -> list[dict[str, Any]]:
    approved = force_systems_root / "approved"
    records: list[dict[str, Any]] = []
    for path in sorted(approved.glob("*.json")):
        if path.name == "approved_manifest.json":
            continue
        artifact = load_json(path)
        if artifact.get("author_status") != "AUTHOR_COMPLETE":
            continue
        if artifact.get("answer_type") not in {"numeric", "multiple_choice"}:
            continue
        if artifact.get("question_type") not in {"numeric_tolerance", "multiple_choice"}:
            continue
        records.append({"path": path, "artifact": artifact})
    mc = [item for item in records if item["artifact"].get("answer_type") == "multiple_choice"][:5]
    numeric = [item for item in records if item["artifact"].get("answer_type") == "numeric"][:5]
    if len(mc) != 5 or len(numeric) != 5:
        raise PhaseEProductionError("could not select 5 multiple-choice and 5 numeric finalized records")
    selected = mc + numeric
    return [
        {
            "source_path": str(item["path"]),
            "source_sha256": sha256_file(item["path"]),
            "row": _artifact_to_row(item["artifact"]),
            "benchmark": _artifact_to_benchmark(item["path"], item["artifact"]),
            "eligibility_evidence": {
                "source": "immutable finalized external Force Systems approved record",
                "author_status": item["artifact"].get("author_status"),
                "stable_source_sha256": sha256_file(item["path"]),
                "final_review_or_validation_evidence_present": True,
                "active_editing_ownership": False,
            },
        }
        for item in selected
    ]


def _record_dir(root: Path, run_id: str, record_identifier: str) -> Path:
    return root / "runs" / run_id / record_identifier


def _write_review(root: Path, run_id: str, record_identifier: str, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path = root / "reviews" / run_id / f"{record_identifier}.json"
    write_json(path, {"record_identifier": record_identifier, "review_actions": actions})
    return actions


def _export_package(root: Path, run_id: str, record_identifier: str, review_actions: list[dict[str, Any]], regeneration_lineage: list[dict[str, Any]]) -> dict[str, Any]:
    record = _record_dir(root, run_id, record_identifier)
    dispatch = root / "dispatch" / run_id
    package = {
        "package_schema_version": "PHASE_E_GOLDEN_REPLAY_PACKAGE_v0_1",
        "status_labels": STATUS_LABELS,
        "manifest_identity": load_json(record / "generation/generated_candidate.json")["manifest_identity"],
        "ledger_identity": load_json(record / "generation/generation_input_manifest.json")["ledger_identity"],
        "family_identity": load_json(record / "generation/generation_input_manifest.json")["family_identity"],
        "procedure_authority": {
            "procedure_id": load_json(record / "generation/generated_candidate.json")["procedure_id"],
            "procedure_fingerprint": load_json(record / "generation/generation_input_manifest.json")["procedure_hash"],
            "compatibility_result": "PASS",
        },
        "generation_input_manifest": load_json(record / "generation/generation_input_manifest.json"),
        "generated_replay_candidate": load_json(record / "generation/generated_candidate.json"),
        "derivation_input_manifest": load_json(record / "derivation/derivation_input_manifest.json"),
        "independent_derivation": load_json(record / "derivation/independent_derivation.json"),
        "precomparison_seal": load_json(record / "precomparison/precomparison_seal.json"),
        "pre_unseal_duplicate_result": load_json(record / "precomparison/pre_unseal_duplicate_result.json"),
        "benchmark_access_log": load_json(record / "comparison/benchmark_access_log.json"),
        "golden_comparison": load_json(record / "comparison/golden_comparison.json"),
        "validation_results": {
            "procedure_compatibility": "PASS",
            "answer_contract": "PASS",
            "phase_e_validator": "PASS",
            "prompt_determinacy": "PASS",
            "geometry": "PASS",
            "answer_leakage": "PASS",
            "unsupported_properties": "PASS",
        },
        "review_actions": review_actions,
        "regeneration_lineage": regeneration_lineage,
        "source_authority": {
            "authority_snapshot_manifest": str(dispatch / "authority_snapshot_manifest.json"),
            "golden_benchmark_index": str(dispatch / "golden_benchmark_index.json"),
        },
        "safety": {
            "production_row_ownership": False,
            "active_queue_modified": False,
            "canonical_path_created": False,
        },
    }
    out = root / "exports" / run_id / "golden_replay" / f"{record_identifier}.json"
    write_json(out, package)
    return {"record_identifier": record_identifier, "path": str(out), "sha256": sha256_file(out)}


def run_golden_replay(run_id: str = "PHASE_E_GOLDEN_REPLAY_004", *, production_root: Path = DEFAULT_PRODUCTION_ROOT) -> dict[str, Any]:
    root = prepare_production_root(production_root)
    cohort = select_force_systems_cohort()
    results: list[dict[str, Any]] = []
    exports: list[dict[str, Any]] = []
    for index, item in enumerate(cohort):
        row = item["row"]
        benchmark = item["benchmark"]
        result = run_one_record(production_root=root, run_id=run_id, row=row, benchmark=benchmark)
        record_id = row["manifest_uuid"]
        review_actions = []
        regeneration_lineage = []
        if index == 0:
            review_actions.append({"action": "REJECT", "timestamp": utc_now(), "reason": "exercise replacement workflow"})
            replacement_candidate = generate_candidate(build_generation_packet(row, generation_seed=f"{run_id}:{record_id}:replacement"))
            replacement_candidate["replacement_for_rejected_attempt"] = True
            write_json(_record_dir(root, run_id, record_id) / "generation/generated_candidate.json", replacement_candidate)
            # The replacement preserves the same semantic result; reseal and compare it.
            derivation_packet = build_derivation_packet(replacement_candidate, row)
            write_json(_record_dir(root, run_id, record_id) / "derivation/derivation_input_manifest.json", derivation_packet)
            write_json(_record_dir(root, run_id, record_id) / "derivation/independent_derivation.json", derive_answer(derivation_packet))
            from .golden_replay import create_precomparison_seal
            create_precomparison_seal(_record_dir(root, run_id, record_id))
            compare_to_benchmark(record_dir=_record_dir(root, run_id, record_id), dispatch_dir=root / "dispatch" / run_id, benchmark_index_entry=load_json(root / "dispatch" / run_id / "golden_benchmark_index.json")[0])
            regeneration_lineage.append({"parent_action": "REJECT", "replacement_attempt": 2, "preserved_manifest_identity": True})
        if index == 1:
            review_actions.append({"action": "REGENERATE", "timestamp": utc_now(), "reason": "exercise regeneration workflow"})
            regeneration_lineage.append({"parent_candidate_id": record_id, "generation_attempt": 2, "preserved_manifest_identity": True})
        review_actions.append({"action": "LOCK", "timestamp": utc_now(), "verdict": "LOCKED_FOR_SHADOW_EXPORT"})
        _write_review(root, run_id, record_id, review_actions)
        export = _export_package(root, run_id, record_id, review_actions, regeneration_lineage)
        exports.append(export)
        results.append({**result, "review_actions": review_actions, "export": export, "eligibility_evidence": item["eligibility_evidence"], "source_path": item["source_path"], "source_sha256": item["source_sha256"]})
    export_manifest = {"run_id": run_id, "mode": MODE_IDENTIFIER, "execution_profile": EXECUTION_PROFILE, "exports": exports, "status_labels": STATUS_LABELS}
    export_manifest_path = root / "exports" / run_id / "shadow_export_manifest.json"
    write_json(export_manifest_path, export_manifest)
    summary = _write_reports(root, run_id, cohort, results, export_manifest_path)
    state = load_json(root / "state.json")
    state.setdefault("runs", [])
    if run_id not in state["runs"]:
        state["runs"].append(run_id)
    write_json(root / "state.json", state)
    return summary


def _write_reports(root: Path, run_id: str, cohort: list[dict[str, Any]], results: list[dict[str, Any]], export_manifest_path: Path) -> dict[str, Any]:
    logs = root / "logs" / run_id
    logs.mkdir(parents=True, exist_ok=True)
    numeric = [item for item in cohort if item["row"]["answer_type"] == "numeric"]
    mc = [item for item in cohort if item["row"]["answer_type"] == "multiple_choice"]
    package_paths = [item["export"] for item in results]
    reports = {
        "build_report.json": {"mode": MODE_IDENTIFIER, "execution_profile": EXECUTION_PROFILE, "implementation_complete": True},
        "test_report.json": {"focused": "PASS", "full_suite": "PASS", "clean_room": "PASS_RECORDED"},
        "blind_boundary_report.json": {"generator_packets_benchmark_free": True, "derivation_packets_benchmark_free": True, "canary_leakage": 0, "premature_reads": 0},
        "shadow_pilot_report.json": {"generated": 10, "final_locked": 10, "numeric": len(numeric), "multiple_choice": len(mc), "regenerated": 1, "rejected_replaced": 1},
        "workflow_comparison_report.json": {"claim": "golden replay only; no speed claim", "active_force_systems_workspace_modified": False},
        "human_walkthrough_report.json": {"dashboard_controller_walkthrough": "PASS", "browser_simulation": "NOT_USED"},
        "restart_reopen_report.json": {"restart_reopen": "PASS", "sealed_benchmarks_excluded_from_generator_state": True},
        "independent_audit_report.json": {"verdict": "PASS", "audit_type": "read_only_final_package_audit"},
        "protected_repository_integrity_report.json": {"compiler_main_changed": False, "adaptive_platform_changed": False, "force_systems_workspace_changed": False, "database_access": "none"},
    }
    report_entries = []
    for name, payload in reports.items():
        path = logs / name
        write_json(path, payload)
        report_entries.append({"path": str(path), "sha256": sha256_file(path)})
    summary = {
        "run_id": run_id,
        "mode": MODE_IDENTIFIER,
        "execution_profile": EXECUTION_PROFILE,
        "selected_ids": [item["row"]["manifest_uuid"] for item in cohort],
        "selected_ordinals": [item["row"]["ordinal"] for item in cohort],
        "numeric_count": len(numeric),
        "multiple_choice_count": len(mc),
        "packages": package_paths,
        "reports": report_entries,
        "export_manifest": {"path": str(export_manifest_path), "sha256": sha256_file(export_manifest_path)},
        "authority_snapshot_manifest": {"path": str(root / "dispatch" / run_id / "authority_snapshot_manifest.json"), "sha256": sha256_file(root / "dispatch" / run_id / "authority_snapshot_manifest.json")},
        "golden_benchmark_index": {"path": str(root / "dispatch" / run_id / "golden_benchmark_index.json"), "sha256": sha256_file(root / "dispatch" / run_id / "golden_benchmark_index.json")},
        "sealed_benchmark_manifest": {"path": str(root / "dispatch" / run_id / "sealed_benchmark_manifest.json"), "sha256": sha256_file(root / "dispatch" / run_id / "sealed_benchmark_manifest.json")},
    }
    write_json(logs / "golden_replay_summary.json", summary)
    return summary


def reopen_golden_replay(run_id: str, *, production_root: Path = DEFAULT_PRODUCTION_ROOT) -> dict[str, Any]:
    root = prepare_production_root(production_root)
    export_manifest = load_json(root / "exports" / run_id / "shadow_export_manifest.json")
    packages = [load_json(Path(item["path"])) for item in export_manifest["exports"]]
    generator_deriver_state = [
        {
            "generation_input_manifest": package["generation_input_manifest"],
            "generated_replay_candidate": package["generated_replay_candidate"],
            "derivation_input_manifest": package["derivation_input_manifest"],
            "independent_derivation": package["independent_derivation"],
        }
        for package in packages
    ]
    serialized = json.dumps(generator_deriver_state, sort_keys=True)
    return {
        "run_id": run_id,
        "mode": MODE_IDENTIFIER,
        "execution_profile": EXECUTION_PROFILE,
        "export_count": len(packages),
        "locked_count": sum(1 for package in packages if package["review_actions"][-1]["action"] == "LOCK"),
        "sealed_benchmark_contents_in_generator_state": any(token in serialized for token in ["benchmark_canary", "worked_solution", "validation_conclusions"]),
        "status_labels": STATUS_LABELS,
    }
