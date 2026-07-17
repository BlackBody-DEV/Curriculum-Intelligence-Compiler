"""Deterministic non-live release package emitter for compiler candidates."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PACKAGE_VERSION = "compiler_release_package_v1"
EMITTER_VERSION = "release_package_emitter_v1"
PACKAGE_STATUS = "compiler_non_live_review_pending"
PROTECTED_ALPHA_ROOT = Path("/Users/fanarichardson/adaptive-platform").resolve()


class ReleasePackageEmitterError(ValueError):
    """Raised when a package cannot be safely emitted."""


@dataclass(frozen=True)
class ReleasePackageResult:
    package_path: Path
    manifest_path: Path
    report_path: Path
    validation_path: Path
    validation_status: str
    semantic_digest: str


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ReleasePackageEmitterError(f"Invalid JSON input: {exc}") from exc
    if not isinstance(data, dict):
        raise ReleasePackageEmitterError("Input must be a JSON object.")
    return data


def write_json(path: Path, payload: Any) -> None:
    path.write_bytes(canonical_json_bytes(payload))


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _sanitize_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_]+", "_", value.strip()).strip("_").lower()
    if not slug:
        raise ReleasePackageEmitterError("Package slug cannot be empty.")
    return slug


def _upper_report_name(slug: str) -> str:
    return f"{slug.upper()}_RELEASE_PACKAGE_V1.md"


def _safe_output_dir(output_dir: Path) -> Path:
    resolved = output_dir.expanduser().resolve()
    try:
        resolved.relative_to(PROTECTED_ALPHA_ROOT)
    except ValueError:
        return resolved
    raise ReleasePackageEmitterError("Output directory inside adaptive-platform is forbidden.")
    return resolved


def _semantic_package(package: dict[str, Any]) -> dict[str, Any]:
    clone = copy.deepcopy(package)
    clone.pop("created_at", None)
    clone.pop("semantic_digest", None)
    validation = clone.get("validation_summary")
    if isinstance(validation, dict):
        validation.pop("validated_at", None)
    return clone


def semantic_digest(package: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(_semantic_package(package)))


def _require_text(data: dict[str, Any], key: str, errors: list[str]) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"missing {key}")
        return ""
    return value.strip()


def _list(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    return value if isinstance(value, list) else []


def _first_present(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def normalize_source_payload(source_payload: dict[str, Any], package_id: str, package_version: str) -> dict[str, Any]:
    """Normalize known compiler candidate shapes into one release package object."""
    if not isinstance(source_payload, dict):
        raise ReleasePackageEmitterError("source_payload must be a dict.")
    if not package_id or not package_id.strip():
        raise ReleasePackageEmitterError("missing package ID")

    if "procedure_candidates" in source_payload or "practice_module_package" in source_payload:
        normalized = copy.deepcopy(source_payload)
        normalized["package_id"] = package_id
        normalized.setdefault("package_version", package_version)
        normalized.setdefault("package_status", PACKAGE_STATUS)
        normalized.setdefault("emitter_version", EMITTER_VERSION)
        normalized.setdefault("created_at", _now())
        normalized.setdefault("integration_boundary", _default_boundary())
        normalized.setdefault("validation_summary", {})
        return normalized

    procedure_seed = source_payload.get("procedure_seed")
    question_seed = source_payload.get("question_seed")
    family_seed = source_payload.get("generation_family_seed")
    if not isinstance(procedure_seed, dict) or not isinstance(question_seed, dict):
        raise ReleasePackageEmitterError("unknown or malformed top-level input")

    micro_skill = str(source_payload.get("selected_micro_skill_code", "")).strip()
    subject = str(_first_present(source_payload, "subject", "subject_code") or "").strip().upper()
    topic = str(_first_present(source_payload, "topic_code", "topic_guess") or "").strip()
    subtopic = _first_present(source_payload, "subtopic_code", "subtopic_guess")
    question_id = str(question_seed.get("question_seed_id", "")).strip()
    procedure_id = str(procedure_seed.get("procedure_seed_id", "")).strip()
    family_id = str((family_seed or {}).get("generation_family_seed_id", "")).strip()

    procedure = {
        "candidate_id": procedure_id,
        "procedure_id": procedure_id,
        "subject_code": subject,
        "topic_code": topic,
        "subtopic_code": subtopic,
        "micro_skill_code": micro_skill,
        "description": procedure_seed.get("description"),
        "steps": procedure_seed.get("steps", []),
        "status": "human_review_required",
        "human_review_required": True,
    }
    practice_item = question_seed.get("practice_item", {})
    question = {
        "candidate_id": question_id,
        "question_id": question_id,
        "subject_code": subject,
        "topic_code": topic,
        "subtopic_code": subtopic,
        "micro_skill_code": micro_skill,
        "procedure_id": procedure_id,
        "question_type": question_seed.get("question_type"),
        "prompt": practice_item.get("prompt"),
        "answer": practice_item.get("correct_answer_pair"),
        "tolerance": practice_item.get("tolerance"),
        "student_visible": False,
        "status": "human_review_required",
        "human_review_required": True,
    }
    generation_family = {
        "family_id": family_id,
        "subject_code": subject,
        "topic_code": topic,
        "subtopic_code": subtopic,
        "micro_skill_code": micro_skill,
        "procedure_id": procedure_id,
        "question_ids": [question_id],
        "family_type": (family_seed or {}).get("family_type"),
        "variable_fields": (family_seed or {}).get("variable_fields", []),
        "variation_rules": (family_seed or {}).get("variation_rules", {}),
        "status": "human_review_required",
        "human_review_required": True,
    }
    practice_module = {
        "package_id": f"PM_{_sanitize_slug(micro_skill).upper()}_001",
        "selected_micro_skill_code": micro_skill,
        "question_ids": [question_id],
        "procedure_ids": [procedure_id],
        "status": "human_review_required",
        "student_visible": False,
    }
    assessment = {
        "package_id": f"PA_{_sanitize_slug(micro_skill).upper()}_001",
        "selected_micro_skill_code": micro_skill,
        "question_ids": [question_id],
        "assessment_type": "single_micro_skill_internal_check",
        "status": "human_review_required",
        "student_visible": False,
    }
    performance = {
        "package_id": f"PERF_{_sanitize_slug(micro_skill).upper()}_001",
        "selected_micro_skill_code": micro_skill,
        "tracked_question_ids": [question_id],
        "tracked_micro_skill_codes": [micro_skill],
        "status": "human_review_required",
        "student_visible": False,
    }

    rights = source_payload.get("rights_status")
    if isinstance(rights, dict):
        rights_summary = rights
    else:
        rights_summary = {"rights_status": rights or "rights_review_required"}
    source_provenance = {
        "source_payload_package_id": source_payload.get("package_id"),
        "evidence_refs": source_payload.get("evidence_refs", []),
        "privacy_status": source_payload.get("privacy_status", {}),
    }
    return {
        "package_id": package_id,
        "package_version": package_version,
        "package_status": PACKAGE_STATUS,
        "created_at": _now(),
        "emitter_version": EMITTER_VERSION,
        "subject_code": subject,
        "topic_code": topic,
        "subtopic_code": subtopic,
        "selected_micro_skill_code": micro_skill,
        "source_artifacts": source_payload.get("evidence_refs", []),
        "source_provenance": source_provenance,
        "rights_summary": rights_summary,
        "review_state": {
            "status": source_payload.get("status"),
            "review_status": source_payload.get("review_status"),
            "human_review_required": True,
        },
        "procedure_candidates": [procedure],
        "question_candidates": [question],
        "generation_family_candidates": [generation_family] if family_id else [],
        "practice_module_package": practice_module,
        "practice_assessment_package": assessment,
        "performance_tracking_package": performance,
        "content_gaps": [],
        "known_limitations": source_payload.get("known_limitations", []),
        "validation_summary": {},
        "integration_boundary": _default_boundary(),
    }


def _default_boundary() -> dict[str, Any]:
    return {
        "internal_preview_only": True,
        "live_eligible": False,
        "eligible_for_alpha_import": False,
        "canonical_approved": False,
        "canonical_promotion_performed": False,
        "db_read_performed": False,
        "db_write_performed": False,
        "adaptive_platform_write_performed": False,
        "student_visible_publish_performed": False,
        "deployment_performed": False,
        "human_review_required": True,
    }


def validate_release_package(package: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    gaps: list[str] = list(package.get("content_gaps") or [])
    boundary_checks: list[dict[str, Any]] = []
    ref_checks: list[dict[str, Any]] = []
    status_checks: list[dict[str, Any]] = []

    required_top_level = {
        "source_artifacts",
        "source_provenance",
        "rights_summary",
        "review_state",
        "generation_family_candidates",
        "content_gaps",
        "known_limitations",
        "validation_summary",
        "integration_boundary",
    }
    missing_top_level = sorted(required_top_level - set(package))
    for key in missing_top_level:
        errors.append(f"missing {key}")

    subject = _require_text(package, "subject_code", errors)
    micro_skill = _require_text(package, "selected_micro_skill_code", errors)
    _require_text(package, "package_id", errors)
    _require_text(package, "package_version", errors)

    procedures = _list(package, "procedure_candidates")
    questions = _list(package, "question_candidates")
    families = _list(package, "generation_family_candidates")
    if not procedures:
        errors.append("missing procedure candidates")
    if not questions:
        errors.append("missing question candidates")
    for key in ["practice_module_package", "practice_assessment_package", "performance_tracking_package"]:
        if not isinstance(package.get(key), dict):
            errors.append(f"missing {key.replace('_', '-')}")
    if not isinstance(package.get("source_provenance"), dict) or not package.get("source_provenance"):
        errors.append("missing provenance")
    rights = package.get("rights_summary")
    if not isinstance(rights, dict) or not rights:
        errors.append("missing rights status")

    procedure_ids = _unique_ids(procedures, ["candidate_id", "procedure_id"], "procedure", errors)
    question_ids = _unique_ids(questions, ["candidate_id", "question_id"], "question", errors)
    family_ids = _unique_ids(families, ["family_id", "candidate_id"], "generation family", errors)
    if family_ids is None:
        family_ids = set()

    for proc in procedures:
        _check_same(proc, "subject_code", subject, "procedure", errors)
        _check_same(proc, "micro_skill_code", micro_skill, "procedure", errors)
    for q in questions:
        _check_same(q, "subject_code", subject, "question", errors)
        _check_same(q, "micro_skill_code", micro_skill, "question", errors)
        pid = q.get("procedure_id") or q.get("procedure_candidate_id")
        ok = isinstance(pid, str) and pid in procedure_ids
        ref_checks.append({"check": "question_procedure_reference", "id": q.get("candidate_id") or q.get("question_id"), "pass": ok})
        if not ok:
            errors.append("question linked to a missing procedure")
    for fam in families:
        _check_same(fam, "subject_code", subject, "generation family", errors)
        _check_same(fam, "micro_skill_code", micro_skill, "generation family", errors)
        pid = fam.get("procedure_id") or fam.get("procedure_candidate_id")
        if pid and pid not in procedure_ids:
            errors.append("generation family linked to missing procedure")
        for qid in fam.get("question_ids", []):
            ok = qid in question_ids
            ref_checks.append({"check": "generation_family_question_reference", "id": fam.get("family_id"), "question_id": qid, "pass": ok})
            if not ok:
                errors.append("generation family linked to missing question")

    for component_name in ["practice_module_package", "practice_assessment_package", "performance_tracking_package"]:
        component = package.get(component_name)
        if isinstance(component, dict):
            _check_same(component, "selected_micro_skill_code", micro_skill, component_name, errors)
            if component_name == "practice_module_package":
                _check_component_refs(
                    component,
                    "question_ids",
                    question_ids,
                    component_name,
                    errors,
                    ref_checks,
                    required=True,
                )
                _check_component_refs(
                    component,
                    "procedure_ids",
                    procedure_ids,
                    component_name,
                    errors,
                    ref_checks,
                    required=True,
                )
            elif component_name == "practice_assessment_package":
                _check_component_refs(
                    component,
                    "question_ids",
                    question_ids,
                    component_name,
                    errors,
                    ref_checks,
                    required=True,
                )
            elif component_name == "performance_tracking_package":
                _check_component_refs(
                    component,
                    "tracked_question_ids",
                    question_ids,
                    component_name,
                    errors,
                    ref_checks,
                    required=True,
                )

    boundary = package.get("integration_boundary", {})
    expected = _default_boundary()
    for key, expected_value in expected.items():
        actual = boundary.get(key)
        ok = actual is expected_value
        boundary_checks.append({"field": key, "expected": expected_value, "actual": actual, "pass": ok})
        if not ok:
            errors.append(f"unsafe boundary field {key}")

    status_ok = package.get("package_status") == PACKAGE_STATUS
    status_checks.append({"field": "package_status", "expected": PACKAGE_STATUS, "actual": package.get("package_status"), "pass": status_ok})
    if not status_ok:
        errors.append("package status is not compiler_non_live_review_pending")

    if _contains_unsafe_live_claim(package):
        errors.append("canonical/live status present without an explicit approved review gate")
    for unsafe_key in ["canonical_approved", "live_eligible", "eligible_for_alpha_import", "student_visible", "live_deployable"]:
        if package.get(unsafe_key) is True:
            errors.append("canonical/live status present without an explicit approved review gate")
    if not families:
        warnings.append("generation family enrichment missing or optional")

    return {
        "validation_status": "pass" if not errors else "fail",
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "content_gaps": gaps,
        "boundary_checks": boundary_checks,
        "referential_integrity_checks": ref_checks,
        "status_checks": status_checks,
    }


def _unique_ids(items: list[Any], keys: list[str], label: str, errors: list[str]) -> set[str]:
    values: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            errors.append(f"malformed {label} candidate")
            continue
        value = next((item.get(key) for key in keys if isinstance(item.get(key), str) and item.get(key).strip()), None)
        if not value:
            errors.append(f"missing {label} ID")
        else:
            values.append(value)
    if len(values) != len(set(values)):
        errors.append("duplicate IDs")
    return set(values)


def _check_same(item: dict[str, Any], key: str, expected: str, label: str, errors: list[str]) -> None:
    actual = item.get(key)
    if actual and str(actual).strip().upper() != expected.upper():
        errors.append(f"package components targeting inconsistent subjects or micro-skills: {label}.{key}")


def _check_component_refs(
    component: dict[str, Any],
    field: str,
    known_ids: set[str],
    label: str,
    errors: list[str],
    ref_checks: list[dict[str, Any]],
    *,
    required: bool,
) -> None:
    refs = component.get(field)
    if not isinstance(refs, list) or not refs:
        if required:
            errors.append(f"{label} missing {field}")
        ref_checks.append({"check": f"{label}.{field}", "pass": False, "refs": refs})
        return
    for ref in refs:
        ok = isinstance(ref, str) and ref in known_ids
        ref_checks.append({"check": f"{label}.{field}", "ref": ref, "pass": ok})
        if not ok:
            errors.append(f"{label} linked to missing {field[:-1]}")


def _contains_unsafe_live_claim(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in {
                "canonical_approved",
                "live_eligible",
                "eligible_for_alpha_import",
                "student_visible",
                "live_deployable",
                "canonical_ready",
                "production_ready",
                "live_ready",
            } and item is True:
                return True
            if _contains_unsafe_live_claim(item):
                return True
    elif isinstance(value, list):
        return any(_contains_unsafe_live_claim(item) for item in value)
    return False


def _attach_validation(package: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    enriched = copy.deepcopy(package)
    enriched["validation_summary"] = {
        "validation_status": validation["validation_status"],
        "error_count": len(validation["errors"]),
        "warning_count": len(validation["warnings"]),
        "validated_at": _now(),
    }
    enriched["semantic_digest"] = semantic_digest(enriched)
    return enriched


def _manifest(
    *,
    package_id: str,
    package_version: str,
    input_sha256: str,
    package_path: Path,
    manifest_path: Path,
    report_path: Path,
    validation_path: Path,
    validation_status: str,
    package: dict[str, Any],
    source_refs: list[str],
) -> dict[str, Any]:
    generated = [package_path, report_path, validation_path]
    generated_entries = {path.name: sha256_file(path) for path in generated}
    return {
        "manifest_version": "compiler_release_manifest_v1",
        "package_id": package_id,
        "package_version": package_version,
        "input_sha256": input_sha256,
        "package_sha256": sha256_file(package_path),
        "semantic_package_sha256": semantic_digest(package),
        "generated_file_paths": [path.name for path in [package_path, manifest_path, report_path, validation_path]],
        "generated_file_sha256": generated_entries,
        "manifest_checksum_policy": "manifest self-checksum is recorded after omitting manifest_sha256_excluding_self",
        "source_artifact_refs": source_refs,
        "validation_status": validation_status,
    }


def _markdown_report(package: dict[str, Any], validation: dict[str, Any]) -> str:
    procedures = package.get("procedure_candidates", [])
    questions = package.get("question_candidates", [])
    families = package.get("generation_family_candidates", [])
    lines = [
        f"# {package['selected_micro_skill_code']} Release Package v1",
        "",
        "This package is compiler-side, non-live, and review-pending.",
        "It has not been imported into adaptive-platform.",
        "It has not been promoted to canonical content.",
        "It is not student-visible.",
        "",
        "## Package Identity",
        f"- package_id: `{package['package_id']}`",
        f"- package_version: `{package['package_version']}`",
        f"- package_status: `{package['package_status']}`",
        f"- emitter_version: `{package['emitter_version']}`",
        "",
        "## Source Summary",
        f"- subject_code: `{package.get('subject_code')}`",
        f"- topic_code: `{package.get('topic_code')}`",
        f"- subtopic_code: `{package.get('subtopic_code')}`",
        f"- selected_micro_skill_code: `{package.get('selected_micro_skill_code')}`",
        "",
        "## Procedures Included",
        *[f"- `{p.get('candidate_id') or p.get('procedure_id')}`: {p.get('description', '')}" for p in procedures],
        "",
        "## Questions Included",
        *[f"- `{q.get('candidate_id') or q.get('question_id')}`: {q.get('prompt', '')}" for q in questions],
        "",
        "## Generation Families Included",
        *[f"- `{g.get('family_id')}`: {g.get('family_type', '')}" for g in families],
        "",
        "## Practice Module Summary",
        f"- package_id: `{package.get('practice_module_package', {}).get('package_id')}`",
        "",
        "## Assessment Summary",
        f"- package_id: `{package.get('practice_assessment_package', {}).get('package_id')}`",
        "",
        "## Performance-Tracking Summary",
        f"- package_id: `{package.get('performance_tracking_package', {}).get('package_id')}`",
        "",
        "## Content Gaps",
        *(f"- {gap}" for gap in (validation.get("content_gaps") or ["none"])),
        "",
        "## Validation Result",
        f"- validation result: {validation['validation_status']}",
        f"- errors: {len(validation['errors'])}",
        f"- warnings: {len(validation['warnings'])}",
        "",
        "## Rights and Provenance Summary",
        f"- rights_summary: `{package.get('rights_summary')}`",
        f"- source_provenance: `{package.get('source_provenance')}`",
        "",
        "## Non-Live Boundary",
        "- adaptive-platform write: false",
        "- DB read/write: false",
        "- canonical promotion: false",
        "- student-visible publishing: false",
        "- deployment: false",
        "",
        "## Known Limitations",
        *(f"- {item}" for item in (package.get("known_limitations") or ["Requires human review before any integration."])),
        "",
        "## Recommended Review Step",
        "Human review and controlled protected-integration audit are required before any Alpha import.",
        "",
    ]
    return "\n".join(lines)


def emit_release_package(
    *,
    source_payload: dict[str, Any],
    output_dir: Path,
    package_id: str,
    package_version: str = PACKAGE_VERSION,
) -> ReleasePackageResult:
    output = _safe_output_dir(output_dir)
    normalized = normalize_source_payload(source_payload, package_id, package_version)
    validation = validate_release_package(normalized)
    if validation["validation_status"] != "pass":
        raise ReleasePackageEmitterError("; ".join(validation["errors"]))

    slug = _sanitize_slug(str(normalized["selected_micro_skill_code"]))
    package_path = output / f"{slug}_release_package_v1.json"
    manifest_path = output / f"{slug}_release_manifest_v1.json"
    report_path = output / _upper_report_name(slug)
    validation_path = output / f"{slug}_release_validation_v1.json"
    allowed = {package_path.resolve(), manifest_path.resolve(), report_path.resolve(), validation_path.resolve()}
    output.mkdir(parents=True, exist_ok=True)

    package = _attach_validation(normalized, validation)
    validation_doc = {
        "validation_report_id": f"{slug}_release_validation_v1",
        "package_id": package_id,
        "package_version": package_version,
        **validation,
    }
    for path in allowed:
        try:
            path.relative_to(output.resolve())
        except ValueError as exc:
            raise ReleasePackageEmitterError(f"Refusing to write outside output directory: {path}") from exc

    write_json(package_path, package)
    write_json(validation_path, validation_doc)
    report_path.write_text(_markdown_report(package, validation), encoding="utf-8")
    manifest = _manifest(
        package_id=package_id,
        package_version=package_version,
        input_sha256=sha256_bytes(canonical_json_bytes(source_payload)),
        package_path=package_path,
        manifest_path=manifest_path,
        report_path=report_path,
        validation_path=validation_path,
        validation_status=validation["validation_status"],
        package=package,
        source_refs=[str(ref.get("path", ref)) if isinstance(ref, dict) else str(ref) for ref in normalized.get("source_artifacts", [])],
    )
    write_json(manifest_path, manifest)
    manifest["manifest_sha256_excluding_self"] = sha256_file(manifest_path)
    write_json(manifest_path, manifest)
    return ReleasePackageResult(
        package_path=package_path,
        manifest_path=manifest_path,
        report_path=report_path,
        validation_path=validation_path,
        validation_status=validation["validation_status"],
        semantic_digest=package["semantic_digest"],
    )
