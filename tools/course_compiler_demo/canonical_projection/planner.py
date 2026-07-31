"""Non-live canonical projection planning.

The planner emits external review artifacts only.  Proposed identities are not
canonical identities, operations are not executable instructions, and no
database, canonical store, Beta service, or student-facing system is accessed.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from tools.course_compiler_demo.beta_export import BetaExportError, dry_run_import_validate
from tools.course_compiler_demo.canonical_promotion.common import canonical_json_bytes, sha256_file, write_json


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROJECTION_ROOT = REPO_ROOT / "reports/course_compiler_demo/canonical_projection_runs"
MODE_IDENTIFIER = "CANONICAL_EXECUTION_BETA_PROJECTION_PLANNING"
EXECUTION_PROFILE = "NON_LIVE_DATABASE_NEUTRAL"
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SAFETY = {
    "noncanonical": True,
    "human_review_required": True,
    "student_visible": False,
    "database_write": False,
    "promotion_authorized": False,
    "canonical_write": False,
    "beta_import_live": False,
    "adaptive_platform_modified": False,
}


class ProjectionPlanningError(ValueError):
    """Projection inputs cannot be represented safely and deterministically."""


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectionPlanningError(f"{field} is required")
    return value.strip()


def _validate_run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id):
        raise ProjectionPlanningError("run_id must be a portable identifier")
    return run_id


def _normalize_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProjectionPlanningError("projection candidate must be an object")
    candidate = copy.deepcopy(dict(value))
    normalized = {
        "source_system": _required_text(candidate.get("source_system"), "source_system"),
        "source_identity": _required_text(candidate.get("source_identity"), "source_identity"),
        "source_revision": _required_text(candidate.get("source_revision"), "source_revision"),
        "content_sha256": _required_text(candidate.get("content_sha256"), "content_sha256").lower(),
        "preparation_id": _required_text(candidate.get("preparation_id"), "preparation_id"),
        "prior_proposed_revision_id": candidate.get("prior_proposed_revision_id"),
        "source_lineage": copy.deepcopy(candidate.get("source_lineage", [])),
        "review_action": candidate.get("review_action"),
        "eligible": candidate.get("eligible"),
    }
    if not SHA256_PATTERN.fullmatch(normalized["content_sha256"]):
        raise ProjectionPlanningError("content_sha256 must be lowercase SHA-256")
    if normalized["review_action"] != "ACCEPT_FOR_PROMOTION_REVIEW" or normalized["eligible"] is not True:
        raise ProjectionPlanningError("candidate is not eligible for projection planning")
    if normalized["prior_proposed_revision_id"] is not None:
        normalized["prior_proposed_revision_id"] = _required_text(
            normalized["prior_proposed_revision_id"], "prior_proposed_revision_id"
        )
    if not isinstance(normalized["source_lineage"], list) or any(
        not isinstance(item, Mapping) for item in normalized["source_lineage"]
    ):
        raise ProjectionPlanningError("source_lineage must be a list of objects")
    return normalized


def _proposed_identity(candidate: Mapping[str, Any]) -> str:
    digest = _stable_hash({
        "contract": "proposed-canonical-identity-v1",
        "source_system": candidate["source_system"],
        "source_identity": candidate["source_identity"],
    })[:24]
    return f"proposed-question-{digest}"


def _proposed_revision(candidate: Mapping[str, Any], identity: str, parent: str | None) -> str:
    digest = _stable_hash({
        "contract": "proposed-canonical-revision-v1",
        "proposed_identity": identity,
        "source_revision": candidate["source_revision"],
        "content_sha256": candidate["content_sha256"],
        "parent_proposed_revision_id": parent,
    })[:24]
    return f"proposed-revision-{digest}"


def _prior_index(previous_records: Iterable[Mapping[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in previous_records:
        record = copy.deepcopy(dict(raw))
        key = (_required_text(record.get("source_system"), "prior source_system"),
               _required_text(record.get("source_identity"), "prior source_identity"))
        if key in result:
            raise ProjectionPlanningError("prior projection state contains duplicate source identity")
        for field in ("source_revision", "content_sha256", "proposed_identity", "proposed_revision_id"):
            _required_text(record.get(field), f"prior {field}")
        if not SHA256_PATTERN.fullmatch(record["content_sha256"]):
            raise ProjectionPlanningError("prior content_sha256 must be lowercase SHA-256")
        expected_identity = _proposed_identity(record)
        if record["proposed_identity"] != expected_identity:
            raise ProjectionPlanningError("prior proposed identity fails deterministic integrity check")
        expected_revision = _proposed_revision(record, expected_identity, record.get("parent_proposed_revision_id"))
        if record["proposed_revision_id"] != expected_revision:
            raise ProjectionPlanningError("prior proposed revision fails deterministic integrity check")
        lineage = record.get("lineage")
        if not isinstance(lineage, list) or not lineage or any(not isinstance(item, Mapping) for item in lineage):
            raise ProjectionPlanningError("prior projection lineage is missing or malformed")
        if any(lineage[-1].get(field) != record.get(field) for field in (
            "source_system", "source_identity", "source_revision", "content_sha256", "preparation_id"
        )):
            raise ProjectionPlanningError("prior projection lineage does not terminate at the prior record")
        result[key] = record
    return result


def _plan_records(
    candidates: Iterable[Mapping[str, Any]], previous_records: Iterable[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    normalized = [_normalize_candidate(item) for item in candidates]
    normalized.sort(key=lambda item: (item["source_system"], item["source_identity"], item["source_revision"]))
    source_keys = [(item["source_system"], item["source_identity"]) for item in normalized]
    if len(source_keys) != len(set(source_keys)):
        raise ProjectionPlanningError("duplicate projection candidate")
    prior_by_source = _prior_index(previous_records)
    records: list[dict[str, Any]] = []
    proposed_ids: dict[str, tuple[str, str]] = {}
    for candidate in normalized:
        source_key = (candidate["source_system"], candidate["source_identity"])
        identity = _proposed_identity(candidate)
        if identity in proposed_ids and proposed_ids[identity] != source_key:
            raise ProjectionPlanningError("proposed identity collision")
        proposed_ids[identity] = source_key
        prior = prior_by_source.get(source_key)
        parent: str | None = None
        if prior is None:
            if candidate["prior_proposed_revision_id"] is not None:
                raise ProjectionPlanningError("new source cannot declare a prior proposed revision")
            operation = "STAGE_CREATE"
        else:
            if prior["proposed_identity"] != identity:
                raise ProjectionPlanningError("prior proposed identity fails deterministic integrity check")
            if candidate["source_revision"] == prior["source_revision"]:
                if candidate["content_sha256"] != prior["content_sha256"]:
                    raise ProjectionPlanningError("source revision conflict: content changed without a new revision")
                if candidate["prior_proposed_revision_id"] not in (None, prior["proposed_revision_id"]):
                    raise ProjectionPlanningError("idempotent reprojection declares the wrong prior revision")
                operation = "REPROJECT_NOOP"
                parent = prior.get("parent_proposed_revision_id")
            else:
                if candidate["prior_proposed_revision_id"] != prior["proposed_revision_id"]:
                    raise ProjectionPlanningError("revision lineage conflict: prior proposed revision is missing or stale")
                operation = "STAGE_REVISION"
                parent = prior["proposed_revision_id"]
        revision = prior["proposed_revision_id"] if operation == "REPROJECT_NOOP" else _proposed_revision(candidate, identity, parent)
        lineage = copy.deepcopy(prior["lineage"] if prior is not None else [])
        for item in candidate["source_lineage"]:
            if item not in lineage:
                lineage.append(copy.deepcopy(item))
        lineage.append({
            "source_system": candidate["source_system"],
            "source_identity": candidate["source_identity"],
            "source_revision": candidate["source_revision"],
            "content_sha256": candidate["content_sha256"],
            "preparation_id": candidate["preparation_id"],
        })
        records.append({
            "operation": operation,
            "source_system": candidate["source_system"],
            "source_identity": candidate["source_identity"],
            "source_revision": candidate["source_revision"],
            "content_sha256": candidate["content_sha256"],
            "preparation_id": candidate["preparation_id"],
            "proposed_identity": identity,
            "proposed_revision_id": revision,
            "parent_proposed_revision_id": parent,
            "lineage": lineage,
            "status": "AWAITING_HUMAN_REVIEW",
            "safety": dict(SAFETY),
        })
    return records


def _stage_beta_import(payload: Mapping[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        validation = dry_run_import_validate(payload)
    except BetaExportError as exc:
        raise ProjectionPlanningError(f"Beta import contract rejected: {exc}") from exc
    by_question_revision = {
        (record["source_identity"], record["source_revision"]): record for record in records
    }
    question_keys = [
        (question["question_id"], question["question_revision"])
        for question in payload.get("question_references", [])
    ]
    missing = sorted(set(question_keys) - set(by_question_revision))
    if missing:
        raise ProjectionPlanningError(
            f"Beta reference has no exact projection candidate revision: {missing[0][0]}@{missing[0][1]}"
        )
    mappings = [{
        "question_id": question_id,
        "question_revision": question_revision,
        "proposed_identity": by_question_revision[(question_id, question_revision)]["proposed_identity"],
        "proposed_revision_id": by_question_revision[(question_id, question_revision)]["proposed_revision_id"],
        "mapping_status": "PROPOSED",
        "human_review_required": True,
    } for question_id, question_revision in question_keys]
    return {
        "status": "VALIDATED_NOT_IMPORTED",
        "contract_validation": validation,
        "export_id": payload.get("export_id"),
        "export_sha256": validation["export_sha256"],
        "question_reference_count": len(question_keys),
        "proposed_mappings": mappings,
        "safety": dict(SAFETY),
    }


def _stage_assessments(
    assessments: Iterable[Mapping[str, Any]], beta_stage: Mapping[str, Any]
) -> dict[str, Any]:
    beta_keys = {
        (item["question_id"], item["question_revision"]) for item in beta_stage["proposed_mappings"]
    }
    staged: list[dict[str, Any]] = []
    identities: set[str] = set()
    for raw in assessments:
        item = copy.deepcopy(dict(raw))
        assessment_id = _required_text(item.get("assessment_id"), "assessment_id")
        if assessment_id in identities:
            raise ProjectionPlanningError("duplicate assessment staging identity")
        identities.add(assessment_id)
        references = item.get("question_references")
        if not isinstance(references, list) or not references:
            raise ProjectionPlanningError("assessment staging requires question_references")
        if any(not isinstance(ref, Mapping) for ref in references):
            raise ProjectionPlanningError("assessment staging references must include question identity and revision")
        question_keys = [
            (_required_text(ref.get("question_id"), "assessment question_id"),
             _required_text(ref.get("question_revision"), "assessment question_revision"))
            for ref in references
        ]
        if len(question_keys) != len(set(question_keys)):
            raise ProjectionPlanningError("assessment staging contains duplicate question references")
        if not set(question_keys).issubset(beta_keys):
            raise ProjectionPlanningError("assessment staging references a question outside the validated Beta package")
        staged.append({
            "assessment_id": assessment_id,
            "question_references": [
                {"question_id": question_id, "question_revision": question_revision}
                for question_id, question_revision in question_keys
            ],
            "source_assessment_sha256": _stable_hash(item),
            "status": "AWAITING_HUMAN_REVIEW",
            "promotion_authorized": False,
            "student_visible": False,
        })
    staged.sort(key=lambda item: item["assessment_id"])
    return {"assessment_count": len(staged), "assessments": staged, "safety": dict(SAFETY)}


def _rollback_plan(records: list[dict[str, Any]]) -> dict[str, Any]:
    steps = []
    for record in reversed(records):
        if record["operation"] == "REPROJECT_NOOP":
            continue
        steps.append({
            "action": "REMOVE_EXTERNAL_STAGED_REVISION",
            "proposed_identity": record["proposed_identity"],
            "proposed_revision_id": record["proposed_revision_id"],
            "restores_proposed_revision_id": record["parent_proposed_revision_id"],
        })
    return {
        "complete": len(steps) == sum(record["operation"] != "REPROJECT_NOOP" for record in records),
        "execution_authorized": False,
        "database_instructions": [],
        "canonical_store_instructions": [],
        "steps": steps,
        "safety": dict(SAFETY),
    }


def projection_mode() -> dict[str, Any]:
    return {
        "mode_identifier": MODE_IDENTIFIER,
        "execution_profile": EXECUTION_PROFILE,
        "status_labels": dict(SAFETY),
        "operator_controls": [
            "validate projection inputs",
            "stage external packages",
            "validate Beta import contract",
            "stage assessment promotion review",
            "inspect conflicts and no-op reprojections",
            "inspect rollback plan",
            "reopen persisted run",
        ],
        "forbidden_controls": ["promote", "write database", "import Beta", "publish to students"],
    }


def run_projection(
    run_id: str,
    candidates: Iterable[Mapping[str, Any]],
    beta_export: Mapping[str, Any],
    assessments: Iterable[Mapping[str, Any]],
    *,
    projection_root: Path | str | None = None,
    previous_records: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    run_id = _validate_run_id(run_id)
    root = Path(projection_root or DEFAULT_PROJECTION_ROOT).expanduser().resolve()
    run_dir = root / run_id
    if run_dir.exists():
        raise ProjectionPlanningError("projection run already exists; reopen it instead")
    records = _plan_records(candidates, previous_records)
    beta_stage = _stage_beta_import(beta_export, records)
    assessment_stage = _stage_assessments(assessments, beta_stage)
    rollback = _rollback_plan(records)
    packages = [{
        "package_id": f"external-stage-{record['proposed_revision_id']}",
        "record": record,
        "canonical_identity_assigned": False,
        "human_review_required": True,
    } for record in records if record["operation"] != "REPROJECT_NOOP"]
    plan = {
        "schema_version": "canonical-projection-plan-v1",
        "run_id": run_id,
        "mode_identifier": MODE_IDENTIFIER,
        "execution_profile": EXECUTION_PROFILE,
        "records": records,
        "external_staging_packages": packages,
        "safety": dict(SAFETY),
    }
    operator = {
        "run_id": run_id,
        "status": "AWAITING_HUMAN_REVIEW",
        "counts": {
            "records": len(records),
            "creates": sum(item["operation"] == "STAGE_CREATE" for item in records),
            "revisions": sum(item["operation"] == "STAGE_REVISION" for item in records),
            "idempotent_noops": sum(item["operation"] == "REPROJECT_NOOP" for item in records),
            "assessments": assessment_stage["assessment_count"],
            "beta_references": beta_stage["question_reference_count"],
        },
        "available_actions": ["REVIEW", "RETURN_FOR_CORRECTION", "REJECT", "REOPEN"],
        "unavailable_actions": ["PROMOTE", "IMPORT", "PUBLISH", "WRITE_DATABASE"],
        "safety": dict(SAFETY),
    }
    artifacts = {
        "projection_plan.json": plan,
        "beta_import_stage.json": beta_stage,
        "assessment_promotion_stage.json": assessment_stage,
        "rollback_plan.json": rollback,
        "operator_state.json": operator,
    }
    run_dir.mkdir(parents=True, exist_ok=False)
    hashes = {name: write_json(run_dir / name, payload) for name, payload in artifacts.items()}
    manifest = {
        "schema_version": "canonical-projection-run-manifest-v1",
        "run_id": run_id,
        "artifact_sha256": hashes,
        "plan_sha256": _stable_hash(plan),
        "record_count": len(records),
        "safety": dict(SAFETY),
    }
    write_json(run_dir / "run_manifest.json", manifest)
    return {**operator, "projection_root": str(root), "manifest": manifest, "records": records}


def reopen_projection_run(run_id: str, *, projection_root: Path | str | None = None) -> dict[str, Any]:
    run_id = _validate_run_id(run_id)
    root = Path(projection_root or DEFAULT_PROJECTION_ROOT).expanduser().resolve()
    run_dir = root / run_id
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.is_file():
        raise ProjectionPlanningError("projection run not found")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("run_id") != run_id or manifest.get("safety") != SAFETY:
        raise ProjectionPlanningError("projection manifest integrity check failed")
    for name, expected in manifest.get("artifact_sha256", {}).items():
        path = run_dir / name
        if not path.is_file() or sha256_file(path) != expected:
            raise ProjectionPlanningError(f"projection artifact integrity check failed: {name}")
    plan = json.loads((run_dir / "projection_plan.json").read_text(encoding="utf-8"))
    if _stable_hash(plan) != manifest.get("plan_sha256"):
        raise ProjectionPlanningError("projection plan semantic hash check failed")
    operator = json.loads((run_dir / "operator_state.json").read_text(encoding="utf-8"))
    return {**operator, "projection_root": str(root), "manifest": manifest, "records": plan["records"], "reopened": True}
