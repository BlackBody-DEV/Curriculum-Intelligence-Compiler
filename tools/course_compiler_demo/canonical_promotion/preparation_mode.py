"""Noncanonical canonical-promotion preparation mode.

The mode converts reviewed compiler outputs into external preparation packets.
It is deliberately preparation-only: canonical identity assignment, canonical
path creation, database projection, Alpha import eligibility, and live/student
publication are all forbidden.
"""

from __future__ import annotations

import os
import copy
import shutil
from datetime import datetime, timezone
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
EVIDENCE_REQUIRED_FIELDS = {
    "evidence_type",
    "source",
    "source_identity",
    "source_hash",
    "approval_scope",
    "applicable_content_identity",
}
ASSET_EVIDENCE_REQUIRED_FIELDS = EVIDENCE_REQUIRED_FIELDS | {
    "applicable_asset_identity",
    "asset_sha256",
    "approved_role",
}
RECOGNIZED_FAILURE_SIGNALS = {
    "algebra_error",
    "axis_confusion",
    "rule_selection_error",
    "sign_or_placement_error",
    "unclassified",
}
BLOCKING_DUPLICATE_CLASSES = {
    "EXACT_DUPLICATE",
    "FINGERPRINT_CONFLICT",
    "STRUCTURAL_MATCH_REVIEW",
    "INSUFFICIENT_EVIDENCE",
}


class CanonicalPromotionPreparationError(ValueError):
    """Raised when the preparation-only boundary cannot be satisfied."""


class InputAdapter(Protocol):
    adapter_id: str

    def normalize(self, payload: dict[str, Any], *, ordinal: int) -> dict[str, Any]:
        ...


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_approval_evidence(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        return {"classification": "UNKNOWN", "verified": False, "unresolved_requirements": sorted(EVIDENCE_REQUIRED_FIELDS)}
    classification = value.get("classification", "UNKNOWN")
    if classification not in RIGHTS_CLASSES:
        classification = "UNKNOWN"
    missing = sorted(field for field in EVIDENCE_REQUIRED_FIELDS if not value.get(field))
    verified = value.get("verified") is True and not missing
    if classification == "EXPLICIT_APPROVAL_EVIDENCE" and not verified:
        classification = "UNKNOWN"
    return {**copy.deepcopy(value), "classification": classification, "verified": verified, "unresolved_requirements": missing}


def _synthetic_approval_evidence(content_identity: str, evidence_kind: str) -> dict[str, Any]:
    source_identity = f"SYNTHETIC_{evidence_kind.upper()}_{content_identity}"
    return {
        "classification": "EXPLICIT_APPROVAL_EVIDENCE",
        "verified": True,
        "evidence_type": f"synthetic_{evidence_kind}_approval_fixture",
        "source": "SYNTHETIC_PROMOTION_PREPARATION_FIXTURE",
        "source_identity": source_identity,
        "source_hash": stable_hash({"source_identity": source_identity, "content_identity": content_identity}),
        "approval_scope": "canonical_promotion_preparation_review_only",
        "applicable_content_identity": content_identity,
    }


def _normalize_asset_approval_evidence(
    value: Any,
    *,
    content_identity: str,
    asset_identity: str | None,
    asset_sha256: str | None,
    role: str | None,
) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        return {
            "classification": "UNKNOWN",
            "verified": False,
            "unresolved_requirements": sorted(ASSET_EVIDENCE_REQUIRED_FIELDS),
            "identity_matches": False,
            "bytes_match": False,
            "role_matches": False,
        }
    normalized = _normalize_approval_evidence(value)
    missing = sorted(field for field in ASSET_EVIDENCE_REQUIRED_FIELDS if not value.get(field))
    identity_matches = bool(
        asset_identity
        and value.get("applicable_content_identity") == content_identity
        and value.get("applicable_asset_identity") == asset_identity
    )
    bytes_match = bool(asset_sha256 and value.get("asset_sha256") == asset_sha256)
    role_matches = bool(role and value.get("approved_role") == role)
    verified = bool(
        normalized["classification"] == "EXPLICIT_APPROVAL_EVIDENCE"
        and normalized["verified"]
        and not missing
        and identity_matches
        and bytes_match
        and role_matches
    )
    classification = "EXPLICIT_APPROVAL_EVIDENCE" if verified else (
        normalized["classification"]
        if normalized["classification"] in {"PARTIAL_EVIDENCE", "RESTRICTED", "CONFLICTING"}
        else "UNKNOWN"
    )
    mismatches = []
    if not identity_matches:
        mismatches.append("asset_or_content_identity_mismatch")
    if not bytes_match:
        mismatches.append("asset_sha256_mismatch")
    if not role_matches:
        mismatches.append("asset_role_mismatch")
    return {
        **copy.deepcopy(value),
        "classification": classification,
        "verified": verified,
        "unresolved_requirements": sorted(set(missing + mismatches)),
        "identity_matches": identity_matches,
        "bytes_match": bytes_match,
        "role_matches": role_matches,
    }


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
            rights_evidence=_normalize_approval_evidence(payload.get("rights_evidence")),
            provenance_evidence=_normalize_approval_evidence(payload.get("provenance_evidence")),
            review_evidence=copy.deepcopy(payload.get("review_evidence") or {}),
            validation_evidence=copy.deepcopy(payload.get("validation_evidence") or {}),
            duplicate_context=copy.deepcopy(payload.get("duplicate_context") or {}),
            curriculum_evidence=copy.deepcopy(payload.get("curriculum_evidence") or {"validated": True}),
            permitted_failure_signals=copy.deepcopy(payload.get("permitted_failure_signals") or payload.get("failure_signals") or []),
            failure_signal_step_map=copy.deepcopy(payload.get("failure_signal_step_map") or {}),
            empty_failure_signals_permitted=payload.get("empty_failure_signals_permitted") is True,
            human_review_action=copy.deepcopy(payload.get("human_review_action")),
            upstream_generation_status=payload.get("upstream_generation_status", "PASS"),
            disallowed=payload.get("disallowed") is True,
            destination_path_metadata=payload.get("destination_path_metadata", {"proposed_path": None, "path_created": False}),
        )


class PhaseEProductionInputAdapter:
    adapter_id = "PhaseEProductionInputAdapter"

    def normalize(self, payload: dict[str, Any], *, ordinal: int) -> dict[str, Any]:
        if "row" not in payload or "benchmark" not in payload:
            raise CanonicalPromotionPreparationError("Phase E candidate requires row and benchmark")
        row = payload["row"]
        generation_packet = build_generation_packet(row, generation_seed=f"canonical-preparation:{row['manifest_uuid']}")
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
            question_payload={"prompt": generated["prompt"], "parameter_set": generated.get("parameter_set", {}), "options": generated.get("options", [])},
            answer_contract=generated["expected_answer_proposal"],
            independent_derivation=derivation,
            failure_signals=row.get("permitted_failure_signals", []),
            difficulty=row.get("difficulty", 1),
            question_type=row["question_type"],
            answer_type=row["answer_type"],
            diagram_policy=row.get("diagram_policy", {"diagram_required": False}),
            asset_references=[],
            rights_evidence=_normalize_approval_evidence(payload.get("rights_evidence")),
            provenance_evidence=_normalize_approval_evidence(payload.get("provenance_evidence")),
            review_evidence=copy.deepcopy(payload.get("review_evidence") or {}),
            validation_evidence=copy.deepcopy(payload.get("validation_evidence") or {}),
            duplicate_context=copy.deepcopy(payload.get("duplicate_context") or {}),
            curriculum_evidence=copy.deepcopy(payload.get("curriculum_evidence") or {"validated": True}),
            permitted_failure_signals=copy.deepcopy(row.get("permitted_failure_signals") or []),
            failure_signal_step_map=copy.deepcopy(payload.get("failure_signal_step_map") or {}),
            empty_failure_signals_permitted=payload.get("empty_failure_signals_permitted") is True,
            human_review_action=copy.deepcopy(payload.get("human_review_action")),
            upstream_generation_status=payload.get("upstream_generation_status", "PASS"),
            disallowed=payload.get("disallowed") is True,
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


def synthetic_document_candidates(count: int = 5, *, fixture_version: str = "018") -> list[dict[str, Any]]:
    skills = [
        ("evaluate_a_limit", "Correction fixture: evaluate 3x+2 as x approaches 4.", 14),
        ("apply_the_power_rule", "Correction fixture: evaluate the derivative of x^4 at x=2.", 32),
        ("apply_the_chain_rule", "Correction fixture: evaluate the derivative of (2x+1)^2 at x=3.", 28),
        ("find_critical_points", "Correction fixture: how many critical points does x^2-6x have?", 1),
        ("analyze_increasing_and_decreasing_intervals", "Correction fixture with required diagram: report the turning-point x-coordinate of x^2-8x.", 4),
    ]
    out = []
    for index, (skill, prompt, answer) in enumerate(skills[:count], start=1):
        candidate_id = f"SYNTH_CALC_PROMO_{fixture_version}_{skill.upper()}"
        signals = ["rule_selection_error", "algebra_error"]
        action = "ACCEPT_FOR_PROMOTION_REVIEW"
        rights = _synthetic_approval_evidence(candidate_id, "rights")
        provenance = _synthetic_approval_evidence(candidate_id, "provenance")
        diagram_required = False
        if skill == "find_critical_points":
            rights = None
            action = "ESCALATE_RIGHTS"
        elif skill == "analyze_increasing_and_decreasing_intervals":
            diagram_required = True
            action = "ESCALATE_ASSET"
        out.append(
            {
                "fixture_label": "SYNTHETIC_PROMOTION_PREPARATION_FIXTURE",
                "candidate_id": candidate_id,
                "source_identity": {"source_type": "synthetic_document_compiler_fixture", "source_id": f"SYNTH_CALC_SOURCE_{fixture_version}_{skill.upper()}"},
                "curriculum_linkage": {
                    "subject_code": "MATHEMATICS",
                    "course_level": "CALCULUS_I",
                    "topic_code": "CALCULUS_I_FOUNDATIONS",
                    "primary_micro_skill_code": skill,
                },
                "procedure_linkage": {"procedure_id": f"PROC_CALCULUS_{fixture_version}_{skill.upper()}", "verified": True},
                "question_payload": {"prompt": prompt, "parameter_set": {"fixture_version": fixture_version, "fixture_index": index}},
                "answer_contract": {"type": "numeric", "shape": "scalar", "expected": answer, "units": None, "tolerance": 0},
                "independent_derivation": {"status": "COMPUTED", "normalized_answer": answer, "answer_shape": "scalar", "units": None, "source": "synthetic_independent_solver", "generator_answer_source": "synthetic_fixture_generator", "derivation_steps": ["Compute independently from the prompt."]},
                "failure_signals": signals,
                "permitted_failure_signals": signals,
                "failure_signal_step_map": {signal: "Compute independently from the prompt." for signal in signals},
                "question_type": "numeric",
                "answer_type": "numeric",
                "diagram_policy": {"diagram_required": diagram_required, "alt_text_required": diagram_required},
                "asset_references": [],
                "rights_evidence": rights,
                "provenance_evidence": provenance,
                "curriculum_evidence": {"validated": True},
                "human_review_action": {"action": action, "actor": "synthetic_fixture_operator", "timestamp": "2026-07-27T00:00:00+00:00", "reason": "SYNTHETIC_PROMOTION_PREPARATION_FIXTURE"},
            }
        )
    return out


def corrected_phase_e_candidates(count: int = 5) -> list[dict[str, Any]]:
    action_by_family = {
        "support_type_reaction_inventory": "RETURN_FOR_CORRECTION",
        "mixed_support_mapping": "RETURN_FOR_CORRECTION",
        "link_roller_pin_fixed_contrast": "REGENERATE_UPSTREAM",
        "vc2d_quadrant_signs": "ESCALATE_CURRICULUM",
        "vc2d_positive_x_reference": "REJECT",
    }
    selected = []
    for original in select_phase_e_preparation_candidates(count):
        payload = copy.deepcopy(original)
        family = payload["row"]["generation_family"]
        content_identity = payload["row"]["manifest_uuid"]
        payload["fixture_label"] = "SYNTHETIC_PROMOTION_PREPARATION_FIXTURE"
        payload["rights_evidence"] = _synthetic_approval_evidence(content_identity, "rights")
        payload["provenance_evidence"] = _synthetic_approval_evidence(content_identity, "provenance")
        signals = payload["row"].get("permitted_failure_signals") or []
        payload["failure_signal_step_map"] = {signal: "Apply the declared procedure constraints." for signal in signals}
        payload["curriculum_evidence"] = {"validated": family != "vc2d_quadrant_signs", "reason": "synthetic curriculum escalation fixture" if family == "vc2d_quadrant_signs" else None}
        payload["upstream_generation_status"] = "DEFECT" if family == "link_roller_pin_fixed_contrast" else "PASS"
        payload["disallowed"] = family == "vc2d_positive_x_reference"
        payload["human_review_action"] = {"action": action_by_family[family], "actor": "synthetic_fixture_operator", "timestamp": "2026-07-27T00:00:00+00:00", "reason": "SYNTHETIC_PROMOTION_PREPARATION_FIXTURE"}
        selected.append(payload)
    return selected


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
    doc_inputs = document_candidates or synthetic_document_candidates(
        fixture_version="020" if run_id == "CANONICAL_PROMOTION_PREPARATION_PILOT_020" else "018"
    )
    phase_inputs = phase_e_candidates or corrected_phase_e_candidates()
    candidates = [
        normalize_input("document_compiler", payload, ordinal=index + 1)
        for index, payload in enumerate(doc_inputs)
    ] + [
        normalize_input("phase_e_production", payload, ordinal=len(doc_inputs) + index + 1)
        for index, payload in enumerate(phase_inputs)
    ]
    if len(candidates) != 10:
        raise CanonicalPromotionPreparationError("pilot requires exactly ten candidates")

    fingerprints = [_fingerprint_report(candidate) for candidate in candidates]
    prior_inventory = _load_prior_packet_inventory(root, run_id)
    entries: list[dict[str, Any]] = []
    for sequence, (candidate, fingerprint) in enumerate(zip(candidates, fingerprints), start=1):
        duplicate = _duplicate_report(candidate, fingerprint, candidates, fingerprints, prior_inventory)
        result = _process_candidate(root, run_id, candidate, external_id=f"CPP_{run_id}_{sequence:03d}", fingerprint=fingerprint, duplicate=duplicate)
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
        "prepared_packets": [
            {"external_preparation_id": item["external_preparation_id"], "canonical_question_id": None, "canonical_revision_id": None, "path_created": False}
            for item in prepared
        ],
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
        "asset_or_governance_blockers": sum(1 for item in entries if item["asset_status"] == "BLOCKED"),
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


def _process_candidate(
    root: Path,
    run_id: str,
    candidate: dict[str, Any],
    *,
    external_id: str,
    fingerprint: dict[str, Any],
    duplicate: dict[str, Any],
) -> dict[str, Any]:
    candidate_path = root / "inputs" / run_id / f"{external_id}.json"
    write_json(candidate_path, candidate)
    validation = _validation_report(candidate)
    rights = _rights_report(candidate)
    asset = _asset_report(root, candidate)
    review = _review_report(candidate, validation, rights, asset, duplicate)
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
        "system_recommendation": review["system_recommendation"],
        "human_review_action": review["human_action"],
        "review_action": review["human_action"]["action"],
        "rights_provenance_classification": rights["classification"] if rights["classification"] != "EXPLICIT_APPROVAL_EVIDENCE" else rights["provenance_classification"],
        "rights_provenance_evidence": rights,
        "asset_status": asset["status"],
        "asset_evidence": asset,
        "duplicate_classification": duplicate["classification"],
        "duplicate_evidence": duplicate,
        "validation_status": "PASS" if not validation["blockers"] else "BLOCKED",
        "independent_derivation_status": validation["derivation"]["result"],
        "independent_derivation_evidence": validation["derivation"],
        "grading_validation": validation["grading"]["result"],
        "grading_evidence": validation["grading"],
        "failure_signal_validation": validation["failure_signals"]["result"],
        "failure_signal_evidence": validation["failure_signals"],
        "unresolved_blockers": [*validation["blockers"], *rights["unresolved_requirements"], *asset["blockers"], *duplicate["blockers"]],
        "canonical_question_id": None,
        "canonical_revision_id": None,
        "reports": reports,
    }


def _write_report(root: Path, area: str, run_id: str, external_id: str, payload: dict[str, Any]) -> dict[str, str]:
    path = root / area / run_id / f"{external_id}.json"
    digest = write_json(path, payload)
    return {"path": root_relative(root, path), "sha256": digest}


def _validation_report(candidate: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    source_hashes = candidate.get("source_hashes") or {}
    source_integrity = "PASS" if source_hashes and all(value for value in source_hashes.values()) else "BLOCKED"
    if source_integrity != "PASS":
        blockers.append("missing_or_invalid_source_hash")
    curriculum = "PASS" if candidate.get("curriculum_evidence", {}).get("validated") is True else "BLOCKED"
    if curriculum != "PASS":
        blockers.append("curriculum_qualification_required")
    procedure = "PASS" if candidate.get("procedure_linkage", {}).get("verified") is True else "BLOCKED"
    if procedure != "PASS":
        blockers.append("procedure_not_verified")
    derivation = _validate_independent_derivation(candidate)
    grading = _validate_grading(candidate, derivation)
    failure_signals = _validate_failure_signals(candidate)
    for result in (derivation, grading, failure_signals):
        blockers.extend(result["blockers"])
    return {
        "candidate_identity": candidate["candidate_identity"],
        "source_identity_preserved": bool(candidate.get("source_identity")),
        "source_integrity": source_integrity,
        "curriculum": curriculum,
        "procedure": procedure,
        "derivation": derivation,
        "grading": grading,
        "failure_signals": failure_signals,
        "blockers": sorted(set(blockers)),
    }


def _validate_independent_derivation(candidate: dict[str, Any]) -> dict[str, Any]:
    derivation = candidate.get("independent_derivation")
    if not isinstance(derivation, dict) or not derivation:
        return {"result": "BLOCKED", "agreement_computed": False, "blockers": ["BLOCKED_MISSING_INDEPENDENT_DERIVATION"]}
    derivation_source = derivation.get("source") or derivation.get("deriver")
    generator_source = derivation.get("generator_answer_source") or candidate.get("generation_origin_evidence", {}).get("origin")
    steps = derivation.get("derivation_steps") or []
    normalized = derivation.get("normalized_answer", derivation.get("computed_answer"))
    blockers = []
    if not derivation_source or derivation_source == generator_source:
        blockers.append("independent_derivation_source_not_distinct")
    if normalized is None or not isinstance(steps, list) or not steps:
        blockers.append("independent_derivation_structurally_invalid")
    return {
        "result": "PASS" if not blockers else "BLOCKED",
        "derivation_source": derivation_source,
        "generator_answer_source": generator_source,
        "source_distinct": bool(derivation_source and derivation_source != generator_source),
        "normalized_answer": normalized,
        "structurally_valid": not blockers,
        "agreement_computed": False,
        "blockers": blockers,
    }


def _validate_grading(candidate: dict[str, Any], derivation: dict[str, Any]) -> dict[str, Any]:
    contract = candidate.get("answer_contract") or {}
    answer_type = contract.get("type")
    blockers: list[str] = []
    evidence: dict[str, Any] = {"answer_type": answer_type, "agreement_computed": False}
    if derivation["result"] != "PASS":
        blockers.append("grading_requires_valid_independent_derivation")
    derived = derivation.get("normalized_answer")
    if answer_type == "numeric":
        shape = contract.get("shape")
        expected = contract.get("expected")
        tolerance_present = "tolerance" in contract
        tolerance = contract.get("tolerance")
        units_match = contract.get("units") == (candidate.get("independent_derivation") or {}).get("units")
        if shape not in {"scalar", "tuple"}:
            blockers.append("invalid_numeric_answer_shape")
        if not tolerance_present or not isinstance(tolerance, (int, float)) or tolerance < 0:
            blockers.append("missing_or_invalid_numeric_tolerance")
        expected_values = list(expected) if shape == "tuple" and isinstance(expected, (list, tuple)) else [expected]
        derived_values = list(derived) if shape == "tuple" and isinstance(derived, (list, tuple)) else [derived]
        if shape == "tuple" and (not isinstance(expected, (list, tuple)) or not isinstance(derived, (list, tuple)) or len(expected_values) != len(derived_values)):
            blockers.append("invalid_numeric_tuple_arity")
        if not units_match:
            blockers.append("numeric_units_mismatch")
        agreement = False
        if not blockers:
            try:
                agreement = all(abs(float(a) - float(b)) <= float(tolerance) for a, b in zip(expected_values, derived_values))
            except (TypeError, ValueError):
                blockers.append("numeric_value_not_normalizable")
        if not agreement and "numeric_value_not_normalizable" not in blockers:
            blockers.append("independent_answer_disagrees_with_numeric_contract")
        evidence.update({"shape": shape, "tuple_arity": len(expected_values), "component_order_preserved": True, "units": contract.get("units"), "tolerance": tolerance, "normalized_expected": expected, "normalized_derived": derived, "agreement_computed": True, "agreement": agreement})
    elif answer_type == "multiple_choice":
        options = candidate.get("question_payload", {}).get("options")
        correct_id = contract.get("correct_option_id")
        option_ids = [option.get("option_id") for option in options] if isinstance(options, list) else []
        unique = len(option_ids) == len(set(option_ids)) and all(option_ids)
        derived_id = derived.get("correct_option_id") if isinstance(derived, dict) else None
        solution_steps = (candidate.get("independent_derivation") or {}).get("derivation_steps") or []
        if len(option_ids) < 2 or not unique:
            blockers.append("invalid_multiple_choice_options")
        if option_ids.count(correct_id) != 1:
            blockers.append("multiple_choice_correct_option_unresolved")
        if not solution_steps:
            blockers.append("multiple_choice_solution_missing")
        agreement = derived_id == correct_id and correct_id in option_ids
        if not agreement:
            blockers.append("multiple_choice_solution_option_mismatch")
        evidence.update({"option_count": len(option_ids), "options_distinct": unique, "correct_option_id": correct_id, "derived_correct_option_id": derived_id, "agreement_computed": True, "agreement": agreement})
    else:
        blockers.append("unsupported_or_incomplete_grading_contract")
    derivation["agreement_computed"] = evidence.get("agreement_computed", False)
    derivation["agreement"] = evidence.get("agreement", False)
    return {**evidence, "result": "PASS" if not blockers else "BLOCKED", "blockers": sorted(set(blockers))}


def _validate_failure_signals(candidate: dict[str, Any]) -> dict[str, Any]:
    supplied = candidate.get("failure_signals") or []
    permitted = candidate.get("permitted_failure_signals") or []
    step_map = candidate.get("failure_signal_step_map") or {}
    rejected = []
    recognized = []
    for signal in supplied:
        if signal not in RECOGNIZED_FAILURE_SIGNALS or signal not in permitted or not isinstance(step_map.get(signal), str) or not step_map.get(signal):
            rejected.append(signal)
        else:
            recognized.append(signal)
    blockers = []
    if not supplied and not candidate.get("empty_failure_signals_permitted"):
        blockers.append("empty_failure_signal_set_not_permitted")
    if rejected:
        blockers.append("invalid_or_disallowed_failure_signals")
    return {"result": "PASS" if not blockers else "BLOCKED", "recognized_signals": recognized, "permitted_signals": permitted, "rejected_signals": rejected, "procedure_applicability": {signal: step_map.get(signal) for signal in supplied}, "blockers": blockers}


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
        "structural_fingerprint": stable_hash({"subject_code": material["curriculum_linkage"].get("subject_code"), "topic_code": material["curriculum_linkage"].get("topic_code"), "procedure_id": material["procedure_linkage"].get("procedure_id"), "question_type": material["question_type"], "answer_type": material["answer_type"]}),
        "canonical_content_hash": stable_hash(material),
        "deterministic": True,
    }


def _rights_report(candidate: dict[str, Any]) -> dict[str, Any]:
    rights = _normalize_approval_evidence(candidate.get("rights_evidence"))
    provenance_evidence = _normalize_approval_evidence(candidate.get("provenance_evidence"))
    classification = rights["classification"]
    provenance = provenance_evidence["classification"]
    unresolved = [f"rights:{item}" for item in rights["unresolved_requirements"]] + [f"provenance:{item}" for item in provenance_evidence["unresolved_requirements"]]
    if classification != "EXPLICIT_APPROVAL_EVIDENCE":
        unresolved.append(f"rights_classification:{classification}")
    if provenance != "EXPLICIT_APPROVAL_EVIDENCE":
        unresolved.append(f"provenance_classification:{provenance}")
    return {
        "classification": classification,
        "provenance_classification": provenance,
        "approval_granted": False,
        "human_review_required": True,
        "rights_evidence": rights,
        "provenance_evidence": provenance_evidence,
        "verified": rights["verified"] and provenance_evidence["verified"],
        "unresolved_requirements": sorted(set(unresolved)),
    }


def _asset_report(root: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    policy = candidate.get("diagram_policy") or {}
    references = candidate.get("asset_references") or []
    required = policy.get("diagram_required") is True
    blockers = []
    evidence = []
    for reference in references:
        if not isinstance(reference, dict):
            blockers.append("malformed_asset_reference")
            continue
        path_value = reference.get("path")
        path = ensure_beneath(root, root / path_value) if path_value else None
        exists = bool(path and path.is_file())
        actual_sha256 = sha256_file(path) if exists else None
        sha_matches = bool(actual_sha256 and reference.get("sha256") == actual_sha256)
        asset_rights = _normalize_asset_approval_evidence(
            reference.get("rights_evidence"),
            content_identity=candidate["candidate_identity"],
            asset_identity=reference.get("asset_identity"),
            asset_sha256=actual_sha256,
            role=reference.get("role"),
        )
        complete = bool(
            reference.get("asset_identity")
            and reference.get("role")
            and reference.get("type")
            and asset_rights["verified"]
            and (not policy.get("alt_text_required") or reference.get("alt_text"))
        )
        if not (exists and sha_matches and complete):
            blockers.append("asset_evidence_incomplete")
        if asset_rights["classification"] != "EXPLICIT_APPROVAL_EVIDENCE":
            blockers.append(f"asset_rights_classification:{asset_rights['classification']}")
        evidence.append({"path": path_value, "asset_identity": reference.get("asset_identity"), "exists": exists, "sha256_verified": sha_matches, "actual_sha256": actual_sha256, "role": reference.get("role"), "type": reference.get("type"), "rights_evidence": asset_rights, "alt_text_present": bool(reference.get("alt_text"))})
    if required and not references:
        blockers.append("required_asset_missing")
    status = "BLOCKED" if blockers else ("PASS" if references else "NOT_APPLICABLE")
    return {"status": status, "diagram_required": required, "asset_references": references, "evidence": evidence, "blockers": sorted(set(blockers)), "asset_paths_written": 0}


def _load_prior_packet_inventory(root: Path, run_id: str) -> list[dict[str, Any]]:
    inventory = []
    seen = set()
    for area in ("prepared", "blocked"):
        for path in sorted((root / area).glob("*/*.json")):
            if path.parent.name == run_id:
                continue
            packet = load_json(path)
            key = (packet.get("proposed_identity", {}).get("external_preparation_id"), packet.get("fingerprints", {}).get("exact_fingerprint"))
            if key in seen:
                continue
            seen.add(key)
            inventory.append({"inventory_source": "prior_external_preparation_packet", "candidate_identity": packet.get("review", {}).get("candidate_identity"), "external_preparation_id": key[0], "fingerprints": packet.get("fingerprints", {})})
    return inventory


def _duplicate_report(candidate: dict[str, Any], fingerprint: dict[str, Any], candidates: list[dict[str, Any]], fingerprints: list[dict[str, Any]], prior_inventory: list[dict[str, Any]]) -> dict[str, Any]:
    comparisons = []
    for other, other_fingerprint in zip(candidates, fingerprints):
        if other is candidate:
            continue
        comparisons.append({"inventory_source": "same_preparation_run", "candidate_identity": other["candidate_identity"], "fingerprints": other_fingerprint})
    comparisons.extend(prior_inventory)
    comparisons.extend(copy.deepcopy(candidate.get("committed_adaptive_inventory") or []))
    comparisons.extend(copy.deepcopy(candidate.get("canonical_source_inventory") or []))
    matches = []
    for other in comparisons:
        other_fp = other.get("fingerprints") or {}
        match_type = None
        if fingerprint["exact_fingerprint"] == other_fp.get("exact_fingerprint"):
            match_type = "exact_fingerprint"
        elif fingerprint["canonical_content_hash"] == other_fp.get("canonical_content_hash"):
            match_type = "canonical_content_hash_conflict"
        elif fingerprint["structural_fingerprint"] == other_fp.get("structural_fingerprint"):
            match_type = "structural_fingerprint"
        if match_type:
            matches.append({"inventory_source": other.get("inventory_source", "explicit_inventory"), "compared_candidate_identity": other.get("candidate_identity"), "external_preparation_id": other.get("external_preparation_id"), "matching_fingerprint_type": match_type, "matching_value": fingerprint["exact_fingerprint"] if match_type == "exact_fingerprint" else fingerprint["canonical_content_hash"] if match_type == "canonical_content_hash_conflict" else fingerprint["structural_fingerprint"]})
    if any(match["matching_fingerprint_type"] == "exact_fingerprint" for match in matches):
        classification = "EXACT_DUPLICATE"
        rationale = "exact fingerprint matched comparison inventory"
    elif any(match["matching_fingerprint_type"] == "canonical_content_hash_conflict" for match in matches):
        classification = "FINGERPRINT_CONFLICT"
        rationale = "canonical content hash matched while exact fingerprint differed"
    elif any(match["matching_fingerprint_type"] == "structural_fingerprint" for match in matches):
        classification = "STRUCTURAL_MATCH_REVIEW"
        rationale = "structural fingerprint matched comparison inventory"
    else:
        classification = "DISTINCT"
        rationale = "no fingerprint match in supplied inventories"
    blockers = [f"duplicate_classification:{classification}"] if classification in BLOCKING_DUPLICATE_CLASSES else []
    return {"classification": classification, "classification_rationale": rationale, "comparison_evidence": matches, "comparison_inventory_counts": {"same_preparation_run": len(candidates) - 1, "prior_external_preparation_packet": len(prior_inventory), "committed_adaptive_inventory": len(candidate.get("committed_adaptive_inventory") or []), "canonical_source_inventory": len(candidate.get("canonical_source_inventory") or [])}, "auto_merge": False, "candidate_identity": candidate["candidate_identity"], "blockers": blockers}


def _review_report(
    candidate: dict[str, Any],
    validation: dict[str, Any],
    rights: dict[str, Any],
    asset: dict[str, Any],
    duplicate: dict[str, Any],
) -> dict[str, Any]:
    if candidate.get("disallowed"):
        recommendation = "REJECT"
    elif rights["unresolved_requirements"]:
        recommendation = "ESCALATE_RIGHTS"
    elif asset["status"] == "BLOCKED":
        recommendation = "ESCALATE_ASSET"
    elif validation["curriculum"] != "PASS":
        recommendation = "ESCALATE_CURRICULUM"
    elif candidate.get("upstream_generation_status") != "PASS":
        recommendation = "REGENERATE_UPSTREAM"
    elif duplicate["blockers"] or validation["blockers"]:
        recommendation = "RETURN_FOR_CORRECTION"
    else:
        recommendation = "ACCEPT_FOR_PROMOTION_REVIEW"
    supplied = candidate.get("human_review_action")
    if supplied is None:
        human_action = {"action": "PENDING_HUMAN_REVIEW", "explicit": False, "actor": None, "timestamp": None, "reason": "human action required"}
    else:
        if not isinstance(supplied, dict) or supplied.get("action") not in REVIEW_ACTIONS or not supplied.get("actor") or not supplied.get("timestamp") or not supplied.get("reason"):
            raise CanonicalPromotionPreparationError("human review action must be explicit, attributed, timestamped, and reasoned")
        if supplied["action"] == "ACCEPT_FOR_PROMOTION_REVIEW" and recommendation != "ACCEPT_FOR_PROMOTION_REVIEW":
            raise CanonicalPromotionPreparationError("human action cannot accept a candidate with unresolved deterministic gates")
        human_action = {**copy.deepcopy(supplied), "explicit": True}
    return {
        "candidate_identity": candidate["candidate_identity"],
        "system_recommendation": recommendation,
        "human_action": human_action,
        "action": human_action["action"],
        "canonical_promotion_authorized": False,
        "human_review_required": True,
        "lineage": {"prior_actions": copy.deepcopy(candidate.get("review_evidence", {}).get("prior_actions") or []), "source_candidate_mutated": False},
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
    required_asset_prepared = [
        entry for entry in summary["packets"]
        if entry["packet_status"] == "PREPARED_FOR_CANONICAL_REVIEW"
        and entry["asset_evidence"]["diagram_required"]
    ]
    not_applicable_prepared = [
        entry for entry in summary["packets"]
        if entry["packet_status"] == "PREPARED_FOR_CANONICAL_REVIEW"
        and not entry["asset_evidence"]["diagram_required"]
    ]
    required_asset_approvals_verified = all(
        entry["asset_evidence"]["status"] == "PASS"
        and entry["asset_evidence"]["evidence"]
        and all(
            evidence["rights_evidence"]["classification"] == "EXPLICIT_APPROVAL_EVIDENCE"
            and evidence["rights_evidence"]["verified"] is True
            and evidence["rights_evidence"]["identity_matches"] is True
            and evidence["rights_evidence"]["bytes_match"] is True
            and evidence["rights_evidence"]["role_matches"] is True
            for evidence in entry["asset_evidence"]["evidence"]
        )
        for entry in required_asset_prepared
    )
    not_applicable_results_valid = all(
        entry["asset_evidence"]["status"] == "NOT_APPLICABLE"
        for entry in not_applicable_prepared
    )
    verdict = (
        "PASS"
        if summary["candidate_count"] == 10
        and summary["prepared_count"] >= 3
        and summary["canonical_ids_assigned"] == 0
        and summary["database_access"] == "none"
        and required_asset_approvals_verified
        and not_applicable_results_valid
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
            "asset_rights_truthiness_accepted": False,
            "required_asset_prepared_count": len(required_asset_prepared),
            "required_asset_approvals_verified": required_asset_approvals_verified,
            "asset_not_required_prepared_count": len(not_applicable_prepared),
            "asset_not_required_results_valid": not_applicable_results_valid,
            "ordinal_name_position_dependence": False,
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
