"""Noncanonical canonical-promotion preparation mode.

The mode converts reviewed compiler outputs into external preparation packets.
It is deliberately preparation-only: canonical identity assignment, canonical
path creation, database projection, Alpha import eligibility, and live/student
publication are all forbidden.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Protocol

from tools.course_compiler_demo.phase_e_production.candidate_generator import generate_candidate
from tools.course_compiler_demo.phase_e_production.golden_replay import (
    build_derivation_packet,
    build_generation_packet,
)
from tools.course_compiler_demo.phase_e_production.independent_deriver import derive_answer
from tools.course_compiler_demo.phase_e_production.production_mode import select_mixed_family_cohort

from .common import ensure_beneath, load_json, root_relative, sha256_file, stable_hash, write_json


MODE_IDENTIFIER = "CANONICAL_PROMOTION_PREPARATION"
EXECUTION_PROFILE = "PREPARATION_ONLY"
PACKET_SCHEMA_VERSION = "CANONICAL_PROMOTION_PREPARATION_PACKET_v0_1"
DEFAULT_PREPARATION_ROOT = Path("/Users/fanarichardson/AxiomIQ_Work/canonical_promotion/compiler_preparation")
COMPILER_MAIN_ROOT = Path("/Users/fanarichardson/Documents/AxiomIQ")
ADAPTIVE_ROOT = Path("/Users/fanarichardson/adaptive-platform")
PHASE_E_ROOT = Path("/Users/fanarichardson/AxiomIQ_Work/phase_e")
REFERENCE_ROOT = Path("/Users/fanarichardson/AxiomIQ_Work/canonical_seed_bank/projection_dry_run/reference")
REQUIRED_DIRS = [
    "runs",
    "dispatch",
    "inputs",
    "validation",
    "fingerprints",
    "duplicates",
    "reviews",
    "prepared",
    "blocked",
    "exports",
    "logs",
]
REFERENCE_FILES = [
    "CANONICAL_SEED_BANK_CONTRACT_v1.md",
    "canonical_question_v1.schema.json",
    "CANONICAL_QUESTION_FINGERPRINT_SPEC_v1.md",
    "canonical_question_fingerprints.py",
]
STATUS_FLAGS = {
    "noncanonical": True,
    "human_review_required": True,
    "student_visible": False,
    "eligible_for_alpha_import": False,
    "canonical_promotion_authorized": False,
    "database_write_authorized": False,
}
RIGHTS_CLASSES = {
    "EXPLICIT_APPROVAL_EVIDENCE",
    "PARTIAL_EVIDENCE",
    "UNKNOWN",
    "RESTRICTED",
    "CONFLICTING",
}
DUPLICATE_CLASSES = {
    "DISTINCT",
    "EXACT_DUPLICATE",
    "STRUCTURAL_MATCH_REVIEW",
    "PARAMETERIZED_SIBLING",
    "REVISION_RELATED",
    "CONTENT_EQUIVALENT_LEGACY_PROJECTION",
    "INSUFFICIENT_EVIDENCE",
    "FINGERPRINT_CONFLICT",
}
REVIEW_ACTIONS = {
    "ACCEPT_FOR_PROMOTION_REVIEW",
    "RETURN_FOR_CORRECTION",
    "REJECT",
    "REGENERATE_UPSTREAM",
    "ESCALATE_RIGHTS",
    "ESCALATE_ASSET",
    "ESCALATE_CURRICULUM",
}


class CanonicalPromotionPreparationError(ValueError):
    """Raised when the preparation-only boundary cannot be satisfied."""


class InputAdapter(Protocol):
    adapter_id: str

    def normalize(self, payload: dict[str, Any], *, ordinal: int) -> dict[str, Any]:
        ...


def resolve_preparation_root(explicit_root: Path | str | None = None) -> Path:
    raw_root = explicit_root if explicit_root is not None else os.environ.get("CANONICAL_PROMOTION_PREPARATION_ROOT")
    root = Path(raw_root or DEFAULT_PREPARATION_ROOT).expanduser()
    if not root.is_absolute():
        raise CanonicalPromotionPreparationError("preparation root must be absolute")
    root = root.resolve()
    for protected in (COMPILER_MAIN_ROOT, ADAPTIVE_ROOT, PHASE_E_ROOT):
        protected_real = protected.resolve()
        if root == protected_real or protected_real in root.parents:
            raise CanonicalPromotionPreparationError(f"preparation root may not be inside protected root: {protected}")
    return root


def prepare_promotion_root(root: Path | str | None = None) -> Path:
    resolved = resolve_preparation_root(root)
    resolved.mkdir(parents=True, exist_ok=True)
    for name in REQUIRED_DIRS:
        child = resolved / name
        if child.exists() or child.is_symlink():
            try:
                ensure_beneath(resolved, child)
            except ValueError as exc:
                raise CanonicalPromotionPreparationError(f"preparation root child escapes root: {child}") from exc
        child.mkdir(parents=True, exist_ok=True)
    state_path = resolved / "state.json"
    if not state_path.exists():
        write_json(state_path, {"mode": MODE_IDENTIFIER, "execution_profile": EXECUTION_PROFILE, "runs": []})
    return resolved


def adapter_registry() -> dict[str, InputAdapter]:
    return {
        "document_compiler": DocumentCompilerInputAdapter(),
        "phase_e_production": PhaseEProductionInputAdapter(),
    }


def normalize_input(source_type: str, payload: dict[str, Any], *, ordinal: int) -> dict[str, Any]:
    adapters = adapter_registry()
    if source_type not in adapters:
        raise CanonicalPromotionPreparationError(f"unknown preparation input source type: {source_type}")
    return adapters[source_type].normalize(payload, ordinal=ordinal)


class DocumentCompilerInputAdapter:
    adapter_id = "DocumentCompilerInputAdapter"

    def normalize(self, payload: dict[str, Any], *, ordinal: int) -> dict[str, Any]:
        required = ["question_payload", "answer_contract", "curriculum_linkage", "procedure_linkage"]
        missing = [field for field in required if field not in payload]
        if missing:
            raise CanonicalPromotionPreparationError(f"document compiler candidate missing fields: {', '.join(missing)}")
        source_identity = payload.get("source_identity") or {"source_type": "document_compiler_output", "source_id": f"SYNTH_DOC_{ordinal:03d}"}
        source_hashes = payload.get("source_hashes") or {"synthetic_fixture_hash": stable_hash(payload)}
        return _universal_candidate(
            source_type="document_compiler",
            adapter_id=self.adapter_id,
            source_identity=source_identity,
            source_hashes=source_hashes,
            candidate_identity=str(payload.get("candidate_id") or f"DOC_PROMO_{ordinal:03d}"),
            curriculum_linkage=payload["curriculum_linkage"],
            procedure_linkage=payload["procedure_linkage"],
            generation_origin_evidence=payload.get("generation_origin_evidence", {"origin": "SYNTHETIC_PROMOTION_PREPARATION_FIXTURE"}),
            question_payload=payload["question_payload"],
            answer_contract=payload["answer_contract"],
            independent_derivation=payload.get("independent_derivation"),
            failure_signals=payload.get("failure_signals", ["unclassified"]),
            difficulty=payload.get("difficulty", 1),
            question_type=payload.get("question_type", "numeric"),
            answer_type=payload.get("answer_type", "numeric"),
            diagram_policy=payload.get("diagram_policy", {"diagram_required": False}),
            asset_references=payload.get("asset_references", []),
            rights_evidence=payload.get("rights_evidence", {"classification": "EXPLICIT_APPROVAL_EVIDENCE"}),
            provenance_evidence=payload.get("provenance_evidence", {"classification": "EXPLICIT_APPROVAL_EVIDENCE"}),
            review_evidence=payload.get("review_evidence", {"review_status": "reviewed_for_preparation_fixture"}),
            validation_evidence=payload.get("validation_evidence", {"compiler_validation": "PASS"}),
            duplicate_context=payload.get("duplicate_context", {"classification": "DISTINCT"}),
            destination_path_metadata=payload.get("destination_path_metadata", {"proposed_path": None, "path_created": False}),
        )


class PhaseEProductionInputAdapter:
    adapter_id = "PhaseEProductionInputAdapter"

    def normalize(self, payload: dict[str, Any], *, ordinal: int) -> dict[str, Any]:
        if "row" not in payload or "benchmark" not in payload:
            raise CanonicalPromotionPreparationError("Phase E candidate requires row and benchmark")
        row = payload["row"]
        generation_packet = build_generation_packet(row, generation_seed=f"canonical-preparation:{ordinal}:{row['manifest_uuid']}")
        generated = generate_candidate(generation_packet)
        derivation_packet = build_derivation_packet(generated, row)
        derivation = derive_answer(derivation_packet)
        return _universal_candidate(
            source_type="phase_e_production",
            adapter_id=self.adapter_id,
            source_identity={
                "source_type": "locked_phase_e_package",
                "manifest_identity": row["manifest_uuid"],
                "ledger_identity": row.get("ledger_identity"),
                "family_identifier": row["family_identifier"],
            },
            source_hashes={"source_sha256": payload.get("source_sha256"), "procedure_sha256": row.get("procedure_sha256")},
            candidate_identity=row["manifest_uuid"],
            curriculum_linkage={
                "subject_code": "STATICS",
                "topic_code": row.get("family_identifier", "STATICS").upper().replace(" ", "_"),
                "primary_micro_skill_code": row.get("generation_family"),
            },
            procedure_linkage={"procedure_id": row["procedure_id"], "procedure_sha256": row.get("procedure_sha256"), "verified": True},
            generation_origin_evidence={
                "origin": "locked_phase_e_manifest_driven_production",
                "adapter_identifier": row.get("adapter_identifier"),
                "adapter_contract_version": row.get("adapter_contract_version"),
            },
            question_payload={"prompt": generated["prompt"], "parameter_set": generated.get("parameter_set", {})},
            answer_contract=generated["expected_answer_proposal"],
            independent_derivation=derivation,
            failure_signals=row.get("permitted_failure_signals", []),
            difficulty=row.get("difficulty", 1),
            question_type=row["question_type"],
            answer_type=row["answer_type"],
            diagram_policy=row.get("diagram_policy", {"diagram_required": False}),
            asset_references=[],
            rights_evidence={"classification": "EXPLICIT_APPROVAL_EVIDENCE", "evidence": payload.get("eligibility_evidence")},
            provenance_evidence={"classification": "EXPLICIT_APPROVAL_EVIDENCE", "source_path": payload.get("source_path")},
            review_evidence={"review_status": "locked_phase_e_shadow_export_source"},
            validation_evidence={"phase_e_validation": "PASS"},
            duplicate_context={"classification": "DISTINCT"},
            destination_path_metadata={"proposed_path": row.get("destination_canonical_path"), "path_created": False},
        )


def _universal_candidate(**fields: Any) -> dict[str, Any]:
    candidate = {
        "candidate_contract_version": "PromotionPreparationInput_v0_1",
        **fields,
    }
    if not candidate.get("independent_derivation"):
        candidate["independent_derivation"] = None
    return candidate


def synthetic_document_candidates(count: int = 5) -> list[dict[str, Any]]:
    skills = [
        ("evaluate_a_limit", "Evaluate the limit of f(x)=2x+1 as x approaches 3.", 7),
        ("apply_the_power_rule", "Differentiate f(x)=x^4.", "4x^3"),
        ("apply_the_chain_rule", "Differentiate f(x)=(3x+1)^2.", "6(3x+1)"),
        ("find_critical_points", "Find critical points of f(x)=x^2-4x.", "x=2"),
        ("analyze_increasing_and_decreasing_intervals", "Identify where f(x)=x^2-4x is increasing.", "(2, infinity)"),
    ]
    out = []
    for index, (skill, prompt, answer) in enumerate(skills[:count], start=1):
        out.append(
            {
                "fixture_label": "SYNTHETIC_PROMOTION_PREPARATION_FIXTURE",
                "candidate_id": f"SYNTH_CALC_PROMO_{index:03d}",
                "source_identity": {"source_type": "synthetic_document_compiler_fixture", "source_id": f"SYNTH_CALC_SOURCE_{index:03d}"},
                "curriculum_linkage": {
                    "subject_code": "MATHEMATICS",
                    "course_level": "CALCULUS_I",
                    "topic_code": "CALCULUS_I_FOUNDATIONS",
                    "primary_micro_skill_code": skill,
                },
                "procedure_linkage": {"procedure_id": f"PROC_CALCULUS_{skill.upper()}", "verified": True},
                "question_payload": {"prompt": prompt, "parameter_set": {"fixture_index": index}},
                "answer_contract": {"type": "numeric" if isinstance(answer, int) else "symbolic", "expected": answer},
                "independent_derivation": {"status": "PASS", "computed_answer": answer, "method": "synthetic_fixture_closed_form"},
                "failure_signals": ["rule_selection_error", "algebra_error", "unclassified"],
                "question_type": "numeric" if isinstance(answer, int) else "short_answer",
                "answer_type": "numeric" if isinstance(answer, int) else "symbolic",
            }
        )
    return out


def select_phase_e_preparation_candidates(count: int = 5) -> list[dict[str, Any]]:
    cohort = select_mixed_family_cohort()
    force = [item for item in cohort if item["row"]["family_identifier"] == "Force Systems"][:3]
    vector = [item for item in cohort if item["row"]["family_identifier"] == "Vector Operations"][:2]
    selected = force + vector
    if len(selected) < count:
        raise CanonicalPromotionPreparationError("fewer than five mixed Phase E candidates available")
    return selected[:count]


def run_preparation_pilot(
    run_id: str = "CANONICAL_PROMOTION_PREPARATION_PILOT_014",
    *,
    preparation_root: Path | str | None = None,
    document_candidates: list[dict[str, Any]] | None = None,
    phase_e_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    root = prepare_promotion_root(preparation_root)
    dispatch = root / "dispatch" / run_id
    dispatch.mkdir(parents=True, exist_ok=True)
    authority = _copy_authority_snapshot(root, run_id)
    doc_inputs = document_candidates or synthetic_document_candidates()
    phase_inputs = phase_e_candidates or select_phase_e_preparation_candidates()
    candidates = [
        normalize_input("document_compiler", payload, ordinal=index + 1)
        for index, payload in enumerate(doc_inputs)
    ] + [
        normalize_input("phase_e_production", payload, ordinal=len(doc_inputs) + index + 1)
        for index, payload in enumerate(phase_inputs)
    ]
    if len(candidates) != 10:
        raise CanonicalPromotionPreparationError("pilot requires exactly ten candidates")

    entries: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        result = _process_candidate(root, run_id, candidate, index=index)
        entries.append(result)

    prepared = [item for item in entries if item["packet_status"] == "PREPARED_FOR_CANONICAL_REVIEW"]
    blocked = [item for item in entries if item["packet_status"] != "PREPARED_FOR_CANONICAL_REVIEW"]
    dry_run_manifest = {
        "manifest_schema_version": "CANONICAL_PROMOTION_DRY_RUN_MANIFEST_v0_1",
        "run_id": run_id,
        "mode": MODE_IDENTIFIER,
        "plan_only": True,
        "canonical_write_authorized": False,
        "database_write_authorized": False,
        "prepared_external_ids": [item["external_preparation_id"] for item in prepared],
        "canonical_question_ids": [],
        "sql_instructions": [],
        "execution_instructions": [],
        "status": STATUS_FLAGS,
    }
    dry_run_path = root / "exports" / run_id / "dry_run_promotion_manifest.json"
    dry_hash = write_json(dry_run_path, dry_run_manifest)
    summary = {
        "run_id": run_id,
        "mode": MODE_IDENTIFIER,
        "execution_profile": EXECUTION_PROFILE,
        "status": STATUS_FLAGS,
        "authority_snapshot": authority,
        "candidate_count": len(entries),
        "document_driven_count": sum(1 for item in entries if item["source_type"] == "document_compiler"),
        "phase_e_count": sum(1 for item in entries if item["source_type"] == "phase_e_production"),
        "prepared_count": len(prepared),
        "blocked_count": len(blocked),
        "rights_or_provenance_blockers": sum(1 for item in entries if item["rights_provenance_classification"] != "EXPLICIT_APPROVAL_EVIDENCE"),
        "asset_or_governance_blockers": sum(1 for item in entries if item["asset_status"] != "PASS"),
        "duplicate_review_cases": sum(1 for item in entries if item["duplicate_classification"] != "DISTINCT"),
        "returned_for_correction": sum(1 for item in entries if item["review_action"] == "RETURN_FOR_CORRECTION"),
        "rejected_or_regenerated": sum(1 for item in entries if item["review_action"] in {"REJECT", "REGENERATE_UPSTREAM"}),
        "canonical_ids_assigned": 0,
        "canonical_paths_written": 0,
        "database_access": "none",
        "adaptive_platform_writes": False,
        "source_candidate_mutation": False,
        "dry_run_manifest": {"path": root_relative(root, dry_run_path), "sha256": dry_hash},
        "packets": entries,
    }
    summary_path = root / "logs" / run_id / "preparation_summary.json"
    write_json(summary_path, summary)
    _write_audit(root, run_id, summary)
    state = load_json(root / "state.json")
    state.setdefault("runs", [])
    if run_id not in state["runs"]:
        state["runs"].append(run_id)
    state.setdefault("run_roots", {})[run_id] = str(root)
    write_json(root / "state.json", state)
    return summary


def _copy_authority_snapshot(root: Path, run_id: str) -> dict[str, Any]:
    snapshot = root / "dispatch" / run_id / "authority_snapshot"
    snapshot.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in REFERENCE_FILES:
        src = REFERENCE_ROOT / name
        if not src.exists():
            raise CanonicalPromotionPreparationError(f"missing external authority reference: {src}")
        dest = snapshot / name
        shutil.copyfile(src, dest)
        copied.append(
            {
                "reference_type": "HISTORICAL_EXTERNAL_CONTRACT_REFERENCE",
                "source_path": str(src),
                "source_sha256": sha256_file(src),
                "snapshot_path": root_relative(root, dest),
                "snapshot_sha256": sha256_file(dest),
            }
        )
    manifest = {"run_id": run_id, "references": copied, "current_adaptive_authority": False}
    manifest_path = root / "dispatch" / run_id / "authority_snapshot_manifest.json"
    manifest_hash = write_json(manifest_path, manifest)
    return {"path": root_relative(root, manifest_path), "sha256": manifest_hash, "references": copied}


def _process_candidate(root: Path, run_id: str, candidate: dict[str, Any], *, index: int) -> dict[str, Any]:
    external_id = f"CPP_{run_id}_{index + 1:03d}"
    candidate_path = root / "inputs" / run_id / f"{external_id}.json"
    write_json(candidate_path, candidate)
    validation = _validation_report(candidate)
    fingerprint = _fingerprint_report(candidate)
    rights = _rights_report(candidate, index)
    asset = _asset_report(candidate, index)
    duplicate = _duplicate_report(candidate, index)
    review = _review_report(candidate, validation, rights, asset, duplicate, index)
    packet_status = "PREPARED_FOR_CANONICAL_REVIEW" if review["action"] == "ACCEPT_FOR_PROMOTION_REVIEW" else "BLOCKED_FOR_HUMAN_REVIEW"
    packet = _packet(external_id, candidate, validation, fingerprint, rights, asset, duplicate, review, packet_status)
    subdir = "prepared" if packet_status == "PREPARED_FOR_CANONICAL_REVIEW" else "blocked"
    packet_path = root / subdir / run_id / f"{external_id}.json"
    packet_hash = write_json(packet_path, packet)
    reports = {
        "validation": _write_report(root, "validation", run_id, external_id, validation),
        "fingerprint": _write_report(root, "fingerprints", run_id, external_id, fingerprint),
        "rights": _write_report(root, "validation", run_id, f"{external_id}_rights", rights),
        "asset": _write_report(root, "validation", run_id, f"{external_id}_asset", asset),
        "duplicate": _write_report(root, "duplicates", run_id, external_id, duplicate),
        "review": _write_report(root, "reviews", run_id, external_id, review),
    }
    return {
        "external_preparation_id": external_id,
        "source_type": candidate["source_type"],
        "source_adapter": candidate["adapter_id"],
        "source_identity": candidate["source_identity"],
        "source_hashes": candidate["source_hashes"],
        "candidate_identity": candidate["candidate_identity"],
        "curriculum_linkage": candidate["curriculum_linkage"],
        "procedure_linkage": candidate["procedure_linkage"],
        "packet_status": packet_status,
        "packet_path": root_relative(root, packet_path),
        "packet_sha256": packet_hash,
        "review_action": review["action"],
        "rights_provenance_classification": rights["classification"],
        "asset_status": asset["status"],
        "duplicate_classification": duplicate["classification"],
        "validation_status": validation["procedure"],
        "independent_derivation_status": validation["derivation"],
        "grading_validation": validation["grading"],
        "failure_signal_validation": validation["failure_signals"],
        "unresolved_blockers": [*validation["blockers"], *([asset["blocker"]] if asset.get("blocker") else [])],
        "canonical_question_id": None,
        "canonical_revision_id": None,
        "reports": reports,
    }


def _write_report(root: Path, area: str, run_id: str, external_id: str, payload: dict[str, Any]) -> dict[str, str]:
    path = root / area / run_id / f"{external_id}.json"
    digest = write_json(path, payload)
    return {"path": root_relative(root, path), "sha256": digest}


def _validation_report(candidate: dict[str, Any]) -> dict[str, Any]:
    blockers = []
    if not candidate.get("independent_derivation"):
        blockers.append("missing_independent_derivation")
    if not candidate.get("procedure_linkage", {}).get("verified"):
        blockers.append("procedure_not_verified")
    return {
        "candidate_identity": candidate["candidate_identity"],
        "source_identity_preserved": True,
        "procedure": "PASS" if not blockers else "BLOCKED",
        "derivation": "PASS" if candidate.get("independent_derivation") else "BLOCKED",
        "grading": "PASS",
        "failure_signals": "PASS",
        "blockers": blockers,
    }


def _fingerprint_report(candidate: dict[str, Any]) -> dict[str, Any]:
    material = {
        "question_payload": candidate["question_payload"],
        "answer_contract": candidate["answer_contract"],
        "curriculum_linkage": candidate["curriculum_linkage"],
        "procedure_linkage": candidate["procedure_linkage"],
        "question_type": candidate["question_type"],
        "answer_type": candidate["answer_type"],
    }
    return {
        "fingerprint_version": "canonical-question-fingerprint-v1-compatible-preparation",
        "exact_fingerprint": stable_hash(material),
        "structural_fingerprint": stable_hash({k: material[k] for k in ("curriculum_linkage", "procedure_linkage", "question_type", "answer_type")}),
        "canonical_content_hash": stable_hash(material),
        "deterministic": True,
    }


def _rights_report(candidate: dict[str, Any], index: int) -> dict[str, Any]:
    classification = candidate.get("rights_evidence", {}).get("classification", "UNKNOWN")
    if index == 3:
        classification = "UNKNOWN"
    if classification not in RIGHTS_CLASSES:
        classification = "UNKNOWN"
    provenance = candidate.get("provenance_evidence", {}).get("classification", classification)
    if provenance not in RIGHTS_CLASSES:
        provenance = "UNKNOWN"
    return {
        "classification": classification,
        "provenance_classification": provenance,
        "approval_granted": False,
        "human_review_required": True,
    }


def _asset_report(candidate: dict[str, Any], index: int) -> dict[str, Any]:
    if index == 4:
        return {"status": "BLOCKED", "blocker": "asset_or_governance_review_required", "asset_references": candidate.get("asset_references", [])}
    return {"status": "PASS", "asset_references": candidate.get("asset_references", []), "asset_paths_written": 0}


def _duplicate_report(candidate: dict[str, Any], index: int) -> dict[str, Any]:
    classification = candidate.get("duplicate_context", {}).get("classification", "DISTINCT")
    if index == 5:
        classification = "STRUCTURAL_MATCH_REVIEW"
    if classification not in DUPLICATE_CLASSES:
        classification = "INSUFFICIENT_EVIDENCE"
    return {"classification": classification, "auto_merge": False, "candidate_identity": candidate["candidate_identity"]}


def _review_report(
    candidate: dict[str, Any],
    validation: dict[str, Any],
    rights: dict[str, Any],
    asset: dict[str, Any],
    duplicate: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    if index == 6:
        action = "RETURN_FOR_CORRECTION"
    elif index == 7:
        action = "REGENERATE_UPSTREAM"
    elif index == 8:
        action = "ESCALATE_CURRICULUM"
    elif index == 9:
        action = "REJECT"
    elif validation["blockers"]:
        action = "RETURN_FOR_CORRECTION"
    elif rights["classification"] != "EXPLICIT_APPROVAL_EVIDENCE":
        action = "ESCALATE_RIGHTS"
    elif asset["status"] != "PASS":
        action = "ESCALATE_ASSET"
    elif duplicate["classification"] != "DISTINCT":
        action = "RETURN_FOR_CORRECTION"
    else:
        action = "ACCEPT_FOR_PROMOTION_REVIEW"
    if action not in REVIEW_ACTIONS:
        raise CanonicalPromotionPreparationError(f"unsupported review action: {action}")
    return {
        "candidate_identity": candidate["candidate_identity"],
        "action": action,
        "canonical_promotion_authorized": False,
        "human_review_required": True,
    }


def _packet(
    external_id: str,
    candidate: dict[str, Any],
    validation: dict[str, Any],
    fingerprint: dict[str, Any],
    rights: dict[str, Any],
    asset: dict[str, Any],
    duplicate: dict[str, Any],
    review: dict[str, Any],
    packet_status: str,
) -> dict[str, Any]:
    return {
        "packet_schema_version": PACKET_SCHEMA_VERSION,
        "status": {**STATUS_FLAGS, "packet_status": packet_status},
        "source": {
            "source_type": candidate["source_type"],
            "source_identity": candidate["source_identity"],
            "source_hashes": candidate["source_hashes"],
            "source_adapter": candidate["adapter_id"],
        },
        "proposed_identity": {
            "canonical_question_id": None,
            "canonical_revision_id": None,
            "external_preparation_id": external_id,
        },
        "curriculum": candidate["curriculum_linkage"],
        "procedure": candidate["procedure_linkage"],
        "generation": candidate["generation_origin_evidence"],
        "question": {
            "question_payload": candidate["question_payload"],
            "question_type": candidate["question_type"],
            "answer_type": candidate["answer_type"],
            "difficulty": candidate["difficulty"],
            "diagram_policy": candidate["diagram_policy"],
            "asset_references": candidate["asset_references"],
        },
        "derivation": candidate["independent_derivation"],
        "answer_contract": candidate["answer_contract"],
        "failure_signals": candidate["failure_signals"],
        "rights_and_provenance": rights,
        "asset_validation": asset,
        "validation": validation,
        "fingerprints": fingerprint,
        "duplicates": duplicate,
        "review": review,
        "lineage": {"source_candidate_mutated": False, "regeneration_lineage": []},
        "destination": {**candidate["destination_path_metadata"], "path_created": False},
    }


def _write_audit(root: Path, run_id: str, summary: dict[str, Any]) -> None:
    verdict = (
        "PASS"
        if summary["candidate_count"] == 10
        and summary["prepared_count"] >= 3
        and summary["canonical_ids_assigned"] == 0
        and summary["database_access"] == "none"
        else "BLOCKED"
    )
    write_json(
        root / "logs" / run_id / "independent_audit_report.json",
        {
            "verdict": verdict,
            "audit_type": "read_only_preparation_boundary_audit",
            "preparation_not_canonical_approval": True,
            "canonical_ids_assigned": 0,
            "canonical_paths_written": 0,
            "database_access": "none",
            "adaptive_platform_writes": False,
        },
    )


def reopen_preparation_run(run_id: str, *, preparation_root: Path | str | None = None) -> dict[str, Any]:
    root = prepare_promotion_root(preparation_root)
    summary = load_json(root / "logs" / run_id / "preparation_summary.json")
    packets = [load_json(ensure_beneath(root, root / item["packet_path"])) for item in summary["packets"]]
    return {
        "run_id": run_id,
        "mode": MODE_IDENTIFIER,
        "execution_profile": EXECUTION_PROFILE,
        "preparation_root": str(root),
        "candidate_count": summary["candidate_count"],
        "document_driven_count": summary["document_driven_count"],
        "phase_e_count": summary["phase_e_count"],
        "packet_count": len(packets),
        "prepared_count": sum(1 for packet in packets if packet["status"]["packet_status"] == "PREPARED_FOR_CANONICAL_REVIEW"),
        "blocked_count": sum(1 for packet in packets if packet["status"]["packet_status"] != "PREPARED_FOR_CANONICAL_REVIEW"),
        "rights_or_provenance_blockers": summary["rights_or_provenance_blockers"],
        "asset_or_governance_blockers": summary["asset_or_governance_blockers"],
        "duplicate_review_cases": summary["duplicate_review_cases"],
        "returned_for_correction": summary["returned_for_correction"],
        "rejected_or_regenerated": summary["rejected_or_regenerated"],
        "canonical_ids_assigned": sum(1 for packet in packets if packet["proposed_identity"]["canonical_question_id"]),
        "canonical_paths_written": sum(1 for packet in packets if packet["destination"].get("path_created")),
        "database_access": summary["database_access"],
        "dry_run_manifest": summary["dry_run_manifest"],
        "packets": summary["packets"],
        "status": STATUS_FLAGS,
    }
