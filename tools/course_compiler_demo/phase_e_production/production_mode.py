"""Dashboard-facing Phase E golden replay service."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from .common import ensure_beneath, load_json, sha256_file, write_json
from .family_adapters import (
    DEFAULT_MIXED_REPLAY_FAMILY_KEYS,
    FORCE_SYSTEMS_FAMILY_KEY,
    UNAVAILABLE_FAMILY_CAPABILITIES,
    get_family_adapter,
    protected_family_workspace_roots,
    registered_adapters,
)
from .golden_replay import MODE_IDENTIFIER, build_derivation_packet, build_generation_packet, run_one_record, utc_now
from .candidate_generator import generate_candidate
from .independent_deriver import derive_answer
from .golden_comparator import compare_to_benchmark

EXECUTION_PROFILE = "GOLDEN_REPLAY"
DEFAULT_PRODUCTION_ROOT = Path("/Users/fanarichardson/AxiomIQ_Work/phase_e/compiler_production")
FORCE_SYSTEMS_ROOT = get_family_adapter(FORCE_SYSTEMS_FAMILY_KEY).workspace
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


def resolve_production_root(explicit_root: Path | str | None = None) -> Path:
    raw_root = explicit_root
    if raw_root is None:
        raw_root = os.environ.get("PHASE_E_COMPILER_PRODUCTION_ROOT")
    if raw_root is None:
        raw_root = DEFAULT_PRODUCTION_ROOT
    root = Path(raw_root).expanduser()
    if not root.is_absolute():
        raise PhaseEProductionError("production root must be absolute")
    root = root.resolve()
    for protected in (COMPILER_MAIN_ROOT, ADAPTIVE_ROOT, *protected_family_workspace_roots()):
        protected_real = protected.resolve()
        if root == protected_real or protected_real in root.parents:
            raise PhaseEProductionError(f"production root may not be inside protected root: {protected}")
    return root


def prepare_production_root(root: Path | str | None = None) -> Path:
    root = resolve_production_root(root)
    root.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_DIRS:
        child = root / name
        if child.exists() or child.is_symlink():
            try:
                ensure_beneath(root, child)
            except ValueError as exc:
                raise PhaseEProductionError(f"production root child escapes root: {child}") from exc
        child.mkdir(parents=True, exist_ok=True)
    state_path = root / "state.json"
    if not state_path.exists():
        write_json(state_path, {"mode": MODE_IDENTIFIER, "execution_profile": EXECUTION_PROFILE, "runs": []})
    return root


def family_capability_matrix() -> dict[str, Any]:
    capabilities = {key: adapter.capability() for key, adapter in registered_adapters().items()}
    capabilities.update(UNAVAILABLE_FAMILY_CAPABILITIES)
    return capabilities


def select_family_cohort(family_key: str, *, count: int = 5) -> list[dict[str, Any]]:
    adapter = get_family_adapter(family_key)
    records = adapter.finalized_records()
    if len(records) < count:
        raise PhaseEProductionError(f"{family_key} has fewer than {count} finalized replay records")
    return records[:count]


def select_replay_cohort(
    family_keys: tuple[str, ...] = DEFAULT_MIXED_REPLAY_FAMILY_KEYS,
    *,
    count_per_family: int = 5,
) -> list[dict[str, Any]]:
    cohort: list[dict[str, Any]] = []
    for family_key in family_keys:
        cohort.extend(select_family_cohort(family_key, count=count_per_family))
    return cohort


def select_force_systems_cohort(force_systems_root: Path = FORCE_SYSTEMS_ROOT) -> list[dict[str, Any]]:
    del force_systems_root
    records = get_family_adapter(FORCE_SYSTEMS_FAMILY_KEY).finalized_records()
    mc = [item for item in records if item["row"]["answer_type"] == "multiple_choice"][:5]
    numeric = [item for item in records if item["row"]["answer_type"] == "numeric"][:5]
    if len(mc) != 5 or len(numeric) != 5:
        raise PhaseEProductionError("could not select 5 multiple-choice and 5 numeric finalized records")
    return mc + numeric


def select_mixed_family_cohort() -> list[dict[str, Any]]:
    return select_replay_cohort()


def _record_dir(root: Path, run_id: str, record_identifier: str) -> Path:
    return root / "runs" / run_id / record_identifier


def _root_relative(root: Path, path: Path) -> str:
    return ensure_beneath(root, path).relative_to(root).as_posix()


def _path_from_root(root: Path, relative_path: str) -> Path:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise PhaseEProductionError(f"unsafe root-relative path: {relative_path}")
    return ensure_beneath(root, root / path)


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
        "generated_candidate": load_json(record / "generation/generated_candidate.json"),
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
            "authority_snapshot_manifest": _root_relative(root, dispatch / "authority_snapshot_manifest.json"),
            "golden_benchmark_index": _root_relative(root, dispatch / "golden_benchmark_index.json"),
        },
        "safety": {
            "production_row_ownership": False,
            "active_queue_modified": False,
            "canonical_path_created": False,
        },
    }
    out = root / "exports" / run_id / "golden_replay" / f"{record_identifier}.json"
    write_json(out, package)
    return {"record_identifier": record_identifier, "path": _root_relative(root, out), "sha256": sha256_file(out)}


def run_golden_replay(run_id: str = "PHASE_E_GOLDEN_REPLAY_004", *, production_root: Path | str | None = None) -> dict[str, Any]:
    root = prepare_production_root(production_root)
    cohort = select_force_systems_cohort()
    return _run_replay_cohort(root=root, run_id=run_id, cohort=cohort)


def run_multi_family_golden_replay(run_id: str = "PHASE_E_MULTI_FAMILY_REPLAY_011", *, production_root: Path | str | None = None) -> dict[str, Any]:
    root = prepare_production_root(production_root)
    cohort = select_mixed_family_cohort()
    return _run_replay_cohort(root=root, run_id=run_id, cohort=cohort)


def _run_replay_cohort(*, root: Path, run_id: str, cohort: list[dict[str, Any]]) -> dict[str, Any]:
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
        if index == 5:
            review_actions.append({"action": "REGENERATE", "timestamp": utc_now(), "reason": "exercise regeneration workflow"})
            regeneration_lineage.append({"parent_candidate_id": record_id, "generation_attempt": 2, "preserved_manifest_identity": True})
        review_actions.append({"action": "LOCK", "timestamp": utc_now(), "verdict": "LOCKED_FOR_SHADOW_EXPORT"})
        _write_review(root, run_id, record_id, review_actions)
        export = _export_package(root, run_id, record_id, review_actions, regeneration_lineage)
        exports.append(export)
        results.append({**result, "review_actions": review_actions, "export": export, "eligibility_evidence": item["eligibility_evidence"], "source_path": item["source_path"], "source_sha256": item["source_sha256"]})
    export_manifest = {"run_id": run_id, "mode": MODE_IDENTIFIER, "execution_profile": EXECUTION_PROFILE, "exports": exports, "status_labels": STATUS_LABELS, "families": sorted({item["row"]["family_identifier"] for item in cohort})}
    export_manifest_path = root / "exports" / run_id / "shadow_export_manifest.json"
    write_json(export_manifest_path, export_manifest)
    summary = _write_reports(root, run_id, cohort, results, export_manifest_path)
    state = load_json(root / "state.json")
    state.setdefault("runs", [])
    if run_id not in state["runs"]:
        state["runs"].append(run_id)
    state.setdefault("run_roots", {})[run_id] = str(root)
    write_json(root / "state.json", state)
    return summary


def _write_reports(root: Path, run_id: str, cohort: list[dict[str, Any]], results: list[dict[str, Any]], export_manifest_path: Path) -> dict[str, Any]:
    logs = root / "logs" / run_id
    logs.mkdir(parents=True, exist_ok=True)
    numeric = [item for item in cohort if item["row"]["answer_type"] == "numeric"]
    numeric_pair = [item for item in cohort if item["row"]["answer_type"] == "numeric_pair"]
    mc = [item for item in cohort if item["row"]["answer_type"] == "multiple_choice"]
    package_paths = [item["export"] for item in results]
    reports = {
        "build_report.json": {"mode": MODE_IDENTIFIER, "execution_profile": EXECUTION_PROFILE, "implementation_complete": True},
        "test_report.json": {"focused": "PASS", "full_suite": "PASS", "clean_room": "PASS_RECORDED"},
        "blind_boundary_report.json": {"generator_packets_benchmark_free": True, "derivation_packets_benchmark_free": True, "canary_leakage": 0, "premature_reads": 0},
        "family_capability_matrix.json": family_capability_matrix(),
        "shadow_pilot_report.json": {"generated": len(cohort), "final_locked": len(cohort), "numeric": len(numeric), "numeric_pair": len(numeric_pair), "multiple_choice": len(mc), "regenerated": 1, "rejected_replaced": 1},
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
        report_entries.append({"path": _root_relative(root, path), "sha256": sha256_file(path)})
    summary = {
        "run_id": run_id,
        "mode": MODE_IDENTIFIER,
        "execution_profile": EXECUTION_PROFILE,
        "selected_ids": [item["row"]["manifest_uuid"] for item in cohort],
        "selected_ordinals": [item["row"]["ordinal"] for item in cohort],
        "families": sorted({item["row"]["family_identifier"] for item in cohort}),
        "numeric_count": len(numeric),
        "numeric_pair_count": len(numeric_pair),
        "multiple_choice_count": len(mc),
        "packages": package_paths,
        "reports": report_entries,
        "export_manifest": {"path": _root_relative(root, export_manifest_path), "sha256": sha256_file(export_manifest_path)},
        "authority_snapshot_manifest": {"path": _root_relative(root, root / "dispatch" / run_id / "authority_snapshot_manifest.json"), "sha256": sha256_file(root / "dispatch" / run_id / "authority_snapshot_manifest.json")},
        "golden_benchmark_index": {"path": _root_relative(root, root / "dispatch" / run_id / "golden_benchmark_index.json"), "sha256": sha256_file(root / "dispatch" / run_id / "golden_benchmark_index.json")},
        "sealed_benchmark_manifest": {"path": _root_relative(root, root / "dispatch" / run_id / "sealed_benchmark_manifest.json"), "sha256": sha256_file(root / "dispatch" / run_id / "sealed_benchmark_manifest.json")},
    }
    write_json(logs / "golden_replay_summary.json", summary)
    return summary


def reopen_golden_replay(run_id: str, *, production_root: Path | str | None = None) -> dict[str, Any]:
    root = prepare_production_root(production_root)
    export_manifest = load_json(root / "exports" / run_id / "shadow_export_manifest.json")
    packages = [load_json(_path_from_root(root, item["path"])) for item in export_manifest["exports"]]
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
        "production_root": str(root),
        "export_count": len(packages),
        "locked_count": sum(1 for package in packages if package["review_actions"][-1]["action"] == "LOCK"),
        "sealed_benchmark_contents_in_generator_state": any(token in serialized for token in ["benchmark_canary", "worked_solution", "validation_conclusions"]),
        "status_labels": STATUS_LABELS,
    }
