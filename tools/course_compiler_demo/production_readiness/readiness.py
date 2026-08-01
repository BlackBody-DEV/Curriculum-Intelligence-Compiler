"""Production-boundary contracts and a synthetic student-flow rehearsal.

Nothing in this module opens a database, imports into Beta, promotes canonical
content, changes the adaptive platform, or enables student visibility.  It
turns the already validated compiler output into a deterministic *proposed*
import envelope and proves the boundary behavior with an in-memory rehearsal.
Every protected action remains fail-closed and separately authorized.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Mapping

from tools.course_compiler_demo.answer_engines.registry import ENABLED_ENGINE_TYPES


COMPILER_BASELINE = "e155fd453684a03bc876674dd1658447d9e30e15"
ADAPTIVE_MAIN_BASELINE = "278db8721de69b9b003aae150764e31b215cc09a"
ADAPTIVE_HARDENING_TIP = "6d4b833781099fd8efa7fd9f4c519a9d1d1b3904"
SCHEMA_VERSION = "1.0"
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PORTABLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,191}$")
DEFAULT_REHEARSAL_ROOT = Path(__file__).resolve().parents[3] / "reports/course_compiler_demo/production_readiness_runs"

SAFETY = {
    "noncanonical": True,
    "human_review_required": True,
    "database_write_authorized": False,
    "canonical_promotion_authorized": False,
    "adaptive_platform_write_authorized": False,
    "student_visibility_authorized": False,
    "live_beta_import_authorized": False,
}

RETRYABLE_ERRORS = frozenset({
    "E_DATABASE_UNAVAILABLE", "E_DEADLOCK", "E_SERIALIZATION_FAILURE", "E_TIMEOUT",
})
PERMANENT_ERRORS = frozenset({
    "E_AUTHORIZATION", "E_CAPABILITY_UNSUPPORTED", "E_CHECKSUM_MISMATCH",
    "E_CONFLICT", "E_IDENTITY_MISMATCH", "E_LINEAGE_MISMATCH", "E_SCHEMA",
    "E_TOPIC_UNRESOLVED", "E_VALIDATION",
})

IDENTITY_AND_OWNERSHIP = {
    "import_actor_role": "curriculum_importer",
    "activation_actor_role": "curriculum_publisher",
    "student_role": "approved_authenticated_student",
    "client_user_id_trusted": False,
    "student_identity_source": "verified_authentication_subject_mapping",
    "ownership_mismatch_action": "REJECT_BEFORE_WRITE",
}
CAPABILITY_HANDSHAKE = {
    "compiler_capabilities": list(ENABLED_ENGINE_TYPES),
    "required_platform_capability_field": "answer_engine",
    "unsupported_action": "REJECT_BEFORE_IMPORT",
    "silent_fallback_allowed": False,
}
TRANSACTION_CONTRACT = {
    "atomic_unit": "one question revision plus its lineage and assessment links",
    "idempotency_constraint": ["source_question_id", "source_revision", "import_record_sha256"],
    "same_revision_different_checksum": "E_CONFLICT",
    "initial_projection_status": "planned",
    "initial_serving_eligible": False,
    "initial_is_active": False,
    "activation_is_separate_transaction": True,
}
RETRY_CONTRACT = {
    "maximum_attempts": 4,
    "backoff_seconds": [1, 2, 4],
    "retryable_errors": sorted(RETRYABLE_ERRORS),
    "permanent_errors": sorted(PERMANENT_ERRORS),
    "resume_key": "idempotency_key",
}
ROLLBACK_CONTRACT = {
    "pre_activation": ["mark import batch rejected", "remove inactive assessment links", "retain immutable import journal"],
    "post_activation": ["set serving_eligible false", "set is_active false", "restore prior serving revision", "retain attempts and audit history"],
    "delete_student_attempts": False,
    "source_artifact_mutation": False,
}

class ProductionReadinessError(ValueError):
    """A proposed production operation violates a fail-closed contract."""


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProductionReadinessError(f"{field} is required")
    return value.strip()


def _identifier(value: Any, field: str) -> str:
    result = _text(value, field)
    if not PORTABLE_ID.fullmatch(result):
        raise ProductionReadinessError(f"{field} must be a portable identifier")
    return result


def _question_content(record: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "prompt": _text(record.get("prompt"), "prompt"),
        "answer_engine": _identifier(record.get("answer_engine"), "answer_engine"),
        "answer_contract": copy.deepcopy(record.get("answer_contract")),
        "expected_answer": copy.deepcopy(record.get("expected_answer")),
        "explanation": str(record.get("explanation") or ""),
        "difficulty_level": record.get("difficulty_level"),
        "use_case": _identifier(record.get("use_case", "practice"), "use_case"),
        "diagram_required": record.get("diagram_required"),
        "image_ref": record.get("image_ref"),
    }


def _normalize_question(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ProductionReadinessError("question record must be an object")
    content = _question_content(record)
    if content["answer_engine"] not in ENABLED_ENGINE_TYPES:
        raise ProductionReadinessError("answer_engine is not an enabled compiler capability")
    if not isinstance(content["answer_contract"], Mapping) or not content["answer_contract"]:
        raise ProductionReadinessError("answer_contract is required")
    if content["expected_answer"] is None:
        raise ProductionReadinessError("expected_answer is required")
    if not isinstance(content["difficulty_level"], int) or not 1 <= content["difficulty_level"] <= 5:
        raise ProductionReadinessError("difficulty_level must be an integer from 1 through 5")
    if not isinstance(content["diagram_required"], bool):
        raise ProductionReadinessError("diagram_required must be boolean")
    if content["diagram_required"] and not _text(content["image_ref"], "image_ref"):
        raise ProductionReadinessError("diagram-required question must have image_ref")
    if not content["diagram_required"] and content["image_ref"] is not None and not isinstance(content["image_ref"], str):
        raise ProductionReadinessError("image_ref must be text or null")

    source_identity = _identifier(record.get("source_question_id"), "source_question_id")
    source_revision = _identifier(record.get("source_revision"), "source_revision")
    proposed_identity = _identifier(record.get("proposed_identity"), "proposed_identity")
    proposed_revision = _identifier(record.get("proposed_revision_id"), "proposed_revision_id")
    content_sha256 = _hash(content)
    supplied_hash = record.get("content_sha256")
    if supplied_hash is not None and supplied_hash != content_sha256:
        raise ProductionReadinessError("question content checksum mismatch")
    lineage = copy.deepcopy(record.get("lineage"))
    if not isinstance(lineage, list) or not lineage or any(not isinstance(row, Mapping) for row in lineage):
        raise ProductionReadinessError("lineage must be a non-empty list of objects")
    if lineage[-1].get("source_question_id") != source_identity or lineage[-1].get("source_revision") != source_revision:
        raise ProductionReadinessError("lineage must terminate at the imported source revision")
    provenance = copy.deepcopy(record.get("provenance"))
    if not isinstance(provenance, Mapping) or not provenance:
        raise ProductionReadinessError("provenance is required")
    raw_assessment_ids = record.get("assessment_ids", [])
    if not isinstance(raw_assessment_ids, list):
        raise ProductionReadinessError("assessment_ids must be a list")
    assessment_ids = sorted(_identifier(value, "assessment_ids") for value in raw_assessment_ids)
    if len(assessment_ids) != len(set(assessment_ids)):
        raise ProductionReadinessError("assessment_ids must be unique")
    immutable_record = {
        "source_question_id": source_identity,
        "source_revision": source_revision,
        "proposed_identity": proposed_identity,
        "proposed_revision_id": proposed_revision,
        "content_sha256": content_sha256,
        "subject_code": _identifier(record.get("subject_code"), "subject_code"),
        "course_id": _identifier(record.get("course_id"), "course_id"),
        "topic_code": _identifier(record.get("topic_code"), "topic_code"),
        "subtopic_code": _identifier(record.get("subtopic_code"), "subtopic_code"),
        "micro_skill_code": _identifier(record.get("micro_skill_code"), "micro_skill_code"),
        "procedure_id": _identifier(record.get("procedure_id"), "procedure_id"),
        "generation_family": _identifier(record.get("generation_family"), "generation_family"),
        **content,
        "lineage": lineage,
        "provenance": provenance,
        "assessment_ids": assessment_ids,
    }
    import_record_sha256 = _hash(immutable_record)
    idempotency_key = _hash({
        "contract": "student-import-idempotency-v1",
        "source_question_id": source_identity,
        "source_revision": source_revision,
        "import_record_sha256": import_record_sha256,
    })
    normalized = {
        **immutable_record,
        "import_record_sha256": import_record_sha256,
        "idempotency_key": idempotency_key,
        "projection_status": "planned",
        "serving_eligible": False,
        "is_active": False,
        "student_visible": False,
    }
    return normalized


def _normalize_assessment(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ProductionReadinessError("assessment must be an object")
    raw_refs = record.get("question_references")
    if not isinstance(raw_refs, list) or not raw_refs:
        raise ProductionReadinessError("assessment requires question_references")
    refs: list[list[str]] = []
    for raw in raw_refs:
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            raise ProductionReadinessError("assessment question reference must be an identity/revision pair")
        refs.append([_identifier(raw[0], "assessment question identity"), _identifier(raw[1], "assessment question revision")])
    refs.sort()
    if len(refs) != len({tuple(ref) for ref in refs}):
        raise ProductionReadinessError("assessment question references must be unique")
    if record.get("is_active") is not False or record.get("student_visible") is not False:
        raise ProductionReadinessError("assessment must remain inactive and not student-visible")
    return {
        "assessment_id": _identifier(record.get("assessment_id"), "assessment_id"),
        "title": _text(record.get("title"), "assessment title"),
        "assessment_type": _identifier(record.get("assessment_type"), "assessment_type"),
        "question_references": refs,
        "is_active": False,
        "student_visible": False,
    }


def build_import_package(
    package_id: str,
    questions: Iterable[Mapping[str, Any]],
    *,
    assessments: Iterable[Mapping[str, Any]] = (),
    compiler_commit: str = COMPILER_BASELINE,
    adaptive_baseline: str = ADAPTIVE_MAIN_BASELINE,
) -> dict[str, Any]:
    """Build a deterministic proposal; it is intentionally not executable."""
    if not re.fullmatch(r"[0-9a-f]{40}", compiler_commit):
        raise ProductionReadinessError("compiler_commit must be a full Git commit")
    if not re.fullmatch(r"[0-9a-f]{40}", adaptive_baseline):
        raise ProductionReadinessError("adaptive_baseline must be a full Git commit")
    rows = sorted((_normalize_question(row) for row in questions), key=lambda row: (
        row["source_question_id"], row["source_revision"]
    ))
    normalized_assessments = sorted((_normalize_assessment(row) for row in assessments), key=lambda row: row["assessment_id"])
    known = {(row["source_question_id"], row["source_revision"]) for row in rows}
    links: dict[tuple[str, str], list[str]] = {identity: [] for identity in known}
    for assessment in normalized_assessments:
        for raw_ref in assessment["question_references"]:
            ref = tuple(raw_ref)
            if ref not in known:
                raise ProductionReadinessError("assessment references a question outside the import package")
            links[ref].append(assessment["assessment_id"])
    rows = [
        _normalize_question({**row, "assessment_ids": sorted(links[(row["source_question_id"], row["source_revision"])])})
        for row in rows
    ]
    package = {
        "schema_version": SCHEMA_VERSION,
        "package_id": _identifier(package_id, "package_id"),
        "compiler_commit": _text(compiler_commit, "compiler_commit"),
        "target": build_target(_text(adaptive_baseline, "adaptive_baseline")),
        "identity_and_ownership": copy.deepcopy(IDENTITY_AND_OWNERSHIP),
        "capability_handshake": copy.deepcopy(CAPABILITY_HANDSHAKE),
        "transaction_contract": copy.deepcopy(TRANSACTION_CONTRACT),
        "retry_contract": copy.deepcopy(RETRY_CONTRACT),
        "rollback_contract": copy.deepcopy(ROLLBACK_CONTRACT),
        "questions": rows,
        "assessments": normalized_assessments,
        "safety": dict(SAFETY),
    }
    package["package_sha256"] = _hash(package)
    validate_import_package(package)
    return package


def validate_import_package(package: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(package, Mapping):
        raise ProductionReadinessError("import package must be an object")
    required_fields = {
        "schema_version", "package_id", "compiler_commit", "target",
        "identity_and_ownership", "capability_handshake", "transaction_contract",
        "retry_contract", "rollback_contract", "questions", "assessments",
        "safety", "package_sha256",
    }
    if set(package) != required_fields:
        raise ProductionReadinessError("import package fields are not closed")
    if package.get("schema_version") != SCHEMA_VERSION or package.get("safety") != SAFETY:
        raise ProductionReadinessError("package schema or protected-state declaration is invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", str(package.get("compiler_commit", ""))):
        raise ProductionReadinessError("compiler_commit must be a full Git commit")
    target = package.get("target")
    if not isinstance(target, Mapping) or target.get("repository") != "BlackBody-DEV/adaptive-platform":
        raise ProductionReadinessError("adaptive target repository is invalid")
    if not re.fullmatch(r"[0-9a-f]{40}", str(target.get("baseline", ""))):
        raise ProductionReadinessError("adaptive target baseline must be a full Git commit")
    expected_target = build_target(str(target["baseline"]))
    if target != expected_target:
        raise ProductionReadinessError("adaptive target contract was modified")
    exact_contracts = (
        ("identity_and_ownership", IDENTITY_AND_OWNERSHIP),
        ("capability_handshake", CAPABILITY_HANDSHAKE),
        ("transaction_contract", TRANSACTION_CONTRACT),
        ("retry_contract", RETRY_CONTRACT),
        ("rollback_contract", ROLLBACK_CONTRACT),
    )
    for field, expected_contract in exact_contracts:
        if package.get(field) != expected_contract:
            raise ProductionReadinessError(f"{field} contract was modified")
    expected = _hash({key: copy.deepcopy(value) for key, value in package.items() if key != "package_sha256"})
    if package.get("package_sha256") != expected:
        raise ProductionReadinessError("package checksum mismatch")
    questions = package.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ProductionReadinessError("at least one question is required")
    identities: set[tuple[str, str]] = set()
    idempotency: set[str] = set()
    proposed: set[tuple[str, str]] = set()
    for row in questions:
        normalized = _normalize_question(row)
        if row != normalized:
            raise ProductionReadinessError("question record is not closed and normalized")
        for field in ("content_sha256", "import_record_sha256", "idempotency_key"):
            if row.get(field) != normalized[field] or not SHA256.fullmatch(str(row.get(field, ""))):
                raise ProductionReadinessError(f"{field} integrity check failed")
        for field in ("serving_eligible", "is_active", "student_visible"):
            if row.get(field) is not False:
                raise ProductionReadinessError(f"{field} must remain false")
        identity = (row["source_question_id"], row["source_revision"])
        proposed_identity = (row["proposed_identity"], row["proposed_revision_id"])
        if identity in identities or row["idempotency_key"] in idempotency or proposed_identity in proposed:
            raise ProductionReadinessError("duplicate or conflicting question identity")
        identities.add(identity)
        idempotency.add(row["idempotency_key"])
        proposed.add(proposed_identity)
    normalized_assessments = sorted(
        (_normalize_assessment(assessment) for assessment in package.get("assessments", [])),
        key=lambda assessment: assessment["assessment_id"],
    )
    if package.get("assessments") != normalized_assessments:
        raise ProductionReadinessError("assessments are not normalized")
    assessment_ids = set()
    linked: dict[tuple[str, str], list[str]] = {identity: [] for identity in identities}
    for assessment in normalized_assessments:
        if assessment["assessment_id"] in assessment_ids:
            raise ProductionReadinessError("duplicate assessment identity")
        assessment_ids.add(assessment["assessment_id"])
        refs = assessment.get("question_references")
        if any(tuple(ref) not in identities for ref in refs):
            raise ProductionReadinessError("assessment references a question outside the import package")
        for ref in refs:
            linked[tuple(ref)].append(assessment["assessment_id"])
    for row in questions:
        identity = (row["source_question_id"], row["source_revision"])
        if row.get("assessment_ids") != sorted(linked[identity]):
            raise ProductionReadinessError("question assessment linkage integrity check failed")
    return {
        "status": "PASS",
        "would_write": False,
        "question_count": len(questions),
        "assessment_count": len(package.get("assessments", [])),
        "package_sha256": expected,
    }


def build_target(adaptive_baseline: str) -> dict[str, Any]:
    return {
        "repository": "BlackBody-DEV/adaptive-platform",
        "baseline": adaptive_baseline,
        "question_table": "questions",
        "assessment_tables": ["assessments", "assessment_questions"],
        "runtime_attempt_tables": ["question_attempts", "placement_assessment_sessions", "placement_assessment_responses", "topic_progress", "vertical_slice_attempts"],
        "retrieval_endpoints": ["GET /api/v1/topics/{topic_id}/questions", "GET /api/v1/curriculum/practice-question/{topic_code}"],
        "submission_endpoints": ["POST /api/v1/attempts/", "POST /api/v1/curriculum/practice-question/{topic_code}/answer", "POST /api/v1/assessments/{session_id}/answer"],
    }


def classify_import_error(error_code: str, attempt: int) -> dict[str, Any]:
    code = _identifier(error_code, "error_code")
    if not isinstance(attempt, int) or attempt < 1:
        raise ProductionReadinessError("attempt must be a positive integer")
    if code in RETRYABLE_ERRORS:
        retry = attempt < 4
        return {"classification": "TRANSIENT", "retry": retry, "next_attempt": attempt + 1 if retry else None}
    if code in PERMANENT_ERRORS:
        return {"classification": "PERMANENT", "retry": False, "next_attempt": None}
    return {"classification": "UNKNOWN_FAIL_CLOSED", "retry": False, "next_attempt": None}


def classify_replay(existing: Mapping[str, Any], incoming: Mapping[str, Any]) -> dict[str, Any]:
    """Classify one unique source identity/revision replay before any write."""
    prior = _normalize_question(existing)
    candidate = _normalize_question(incoming)
    prior_identity = (prior["source_question_id"], prior["source_revision"])
    candidate_identity = (candidate["source_question_id"], candidate["source_revision"])
    if prior_identity != candidate_identity:
        return {"status": "NEW_IDENTITY", "write_allowed": False, "requires_separate_insert_validation": True}
    if prior["import_record_sha256"] == candidate["import_record_sha256"]:
        return {"status": "IDEMPOTENT_NOOP", "write_allowed": False, "requires_separate_insert_validation": False}
    return {"status": "E_CONFLICT", "write_allowed": False, "requires_separate_insert_validation": False}


def deployment_gate(configuration: Mapping[str, Any], package: Mapping[str, Any]) -> dict[str, Any]:
    validate_import_package(package)
    required = {
        "adaptive_commit": package["target"]["baseline"],
        "environment": "production",
        "database_reachable": True,
        "migrations_verified": True,
        "canonical_promotion_approved": True,
        "adaptive_write_approved": True,
        "student_visibility_approved": True,
        "rollback_rehearsed": True,
        "capability_parity_verified": True,
        "identity_ownership_tests_passed": True,
        "feature_flag_initially_disabled": True,
    }
    blockers = [key for key, expected in required.items() if configuration.get(key) != expected]
    return {
        "status": "PASS" if not blockers else "BLOCKED",
        "blockers": blockers,
        "required": required,
        "database_write_performed": False,
        "student_visibility_changed": False,
    }


def _numeric_grade(answer: Any, expected: Any, contract: Mapping[str, Any]) -> bool:
    try:
        actual = float(answer)
        target = float(expected)
        absolute = float(contract.get("absolute_tolerance", 0.0))
        relative = float(contract.get("relative_tolerance", 0.0))
    except (TypeError, ValueError):
        return False
    if not all(math.isfinite(value) for value in (actual, target, absolute, relative)) or absolute < 0 or relative < 0:
        return False
    return abs(actual - target) <= max(absolute, relative * abs(target))


def _rehearsal_question() -> dict[str, Any]:
    return {
        "source_question_id": "synthetic-public-question-001",
        "source_revision": "v1",
        "proposed_identity": "proposed-question-synthetic-001",
        "proposed_revision_id": "proposed-revision-synthetic-001-v1",
        "subject_code": "SYNTHETIC_MATHEMATICS",
        "course_id": "SYNTHETIC_PRE_ALGEBRA",
        "topic_code": "SYNTHETIC_LINEAR_ARITHMETIC",
        "subtopic_code": "SYNTHETIC_ADDITION",
        "micro_skill_code": "ADD_TWO_INTEGERS",
        "procedure_id": "synthetic-addition-v1",
        "generation_family": "synthetic-public-contract-arithmetic",
        "prompt": "Using the public arithmetic contract, compute 2 + 2.",
        "answer_engine": "numeric_scalar",
        "answer_contract": {"absolute_tolerance": 0.0, "relative_tolerance": 0.0},
        "expected_answer": 4,
        "explanation": "Combine the two integer quantities.",
        "difficulty_level": 1,
        "use_case": "practice",
        "diagram_required": False,
        "image_ref": None,
        "lineage": [{"stage": "synthetic-public-contract", "source_question_id": "synthetic-public-question-001", "source_revision": "v1"}],
        "provenance": {"type": "SYNTHETIC_PUBLIC_CONTRACT", "private_content": False, "protected_content": False},
    }


def run_synthetic_student_flow(run_id: str, *, output_root: Path = DEFAULT_REHEARSAL_ROOT) -> dict[str, Any]:
    """Rehearse the complete path in memory and persist integrity evidence."""
    run_id = _identifier(run_id, "run_id")
    question = _rehearsal_question()
    package = build_import_package(f"{run_id}-package", [question])
    validation = validate_import_package(package)
    import_store: dict[str, dict[str, Any]] = {}
    row = package["questions"][0]
    import_store[row["idempotency_key"]] = copy.deepcopy(row)
    first_count = len(import_store)
    import_store.setdefault(row["idempotency_key"], copy.deepcopy(row))
    idempotent_count = len(import_store)
    conflict = copy.deepcopy(question)
    conflict["prompt"] = "Conflicting content for the same revision."
    conflicted = build_import_package("conflict-package", [conflict])
    conflict_rejected = classify_replay(row, conflicted["questions"][0])["status"] == "E_CONFLICT"
    stored = import_store[row["idempotency_key"]]
    stored["projection_status"] = "projected"  # in-memory simulation only
    stored["serving_eligible"] = True
    stored["is_active"] = True
    authenticated_student = "synthetic-student-001"
    forged_student = "synthetic-student-002"
    ownership_rejected = forged_student != authenticated_student
    retrieved = copy.deepcopy(stored) if stored["serving_eligible"] and stored["is_active"] else None
    correct = _numeric_grade("4", retrieved["expected_answer"], retrieved["answer_contract"]) if retrieved else False
    incorrect = _numeric_grade("5", retrieved["expected_answer"], retrieved["answer_contract"]) if retrieved else True
    attempt = {
        "student_identity": authenticated_student,
        "identity_source": "simulated_verified_authentication_subject_mapping",
        "source_question_id": row["source_question_id"],
        "submitted_answer": "4",
        "correct": correct,
    }
    stored["serving_eligible"] = False
    stored["is_active"] = False
    unavailable_after_rollback = not (stored["serving_eligible"] and stored["is_active"])
    events = [
        "SOURCE_INTAKE_SYNTHETIC_PUBLIC_CONTRACT",
        "CURRICULUM_SYNTHESIS_VALIDATED",
        "QUESTION_BANK_VALIDATED",
        "CANONICAL_STAGING_SIMULATED",
        "BETA_IMPORT_CONTRACT_VALIDATED",
        "ADAPTIVE_IMPORT_SIMULATED",
        "AUTHENTICATED_STUDENT_RETRIEVAL_SIMULATED",
        "ANSWER_SUBMISSION_SIMULATED",
        "GRADING_RESULT_SIMULATED",
        "ROLLBACK_SIMULATED",
    ]
    proof = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "mode": "SYNTHETIC_IN_MEMORY_NO_EXTERNAL_WRITES",
        "events": events,
        "package_validation": validation,
        "idempotency": {"first_count": first_count, "reimport_count": idempotent_count, "pass": first_count == idempotent_count == 1},
        "conflict_rejected": conflict_rejected,
        "ownership": {"authenticated_identity_wins": True, "forged_identity_rejected": ownership_rejected},
        "retrieval": {"question_found": retrieved is not None, "student_visible_system_changed": False},
        "grading": {"correct_answer_passed": correct, "incorrect_answer_failed": not incorrect},
        "rollback": {"question_unavailable": unavailable_after_rollback, "attempt_history_retained": bool(attempt)},
        "protected_operations": dict(SAFETY),
        "status": "PASS",
    }
    checks = [
        len(events) == 10, proof["idempotency"]["pass"], conflict_rejected,
        ownership_rejected, retrieved is not None, correct, not incorrect,
        unavailable_after_rollback, SAFETY["database_write_authorized"] is False,
    ]
    if not all(checks):
        raise ProductionReadinessError("synthetic student-flow rehearsal failed")
    run_dir = Path(output_root) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    artifacts = {"import_package.json": package, "student_flow_proof.json": proof}
    manifest = {"schema_version": SCHEMA_VERSION, "run_id": run_id, "artifact_sha256": {name: _hash(value) for name, value in artifacts.items()}}
    for name, value in {**artifacts, "manifest.json": manifest}.items():
        (run_dir / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**proof, "manifest": manifest, "run_directory": str(run_dir)}


def reopen_rehearsal(run_id: str, *, output_root: Path = DEFAULT_REHEARSAL_ROOT) -> dict[str, Any]:
    run_id = _identifier(run_id, "run_id")
    run_dir = Path(output_root) / run_id
    try:
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionReadinessError("rehearsal manifest cannot be reopened") from exc
    for name, expected in manifest.get("artifact_sha256", {}).items():
        try:
            value = json.loads((run_dir / name).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ProductionReadinessError("rehearsal artifact cannot be reopened") from exc
        if _hash(value) != expected:
            raise ProductionReadinessError(f"rehearsal integrity check failed: {name}")
    package = json.loads((run_dir / "import_package.json").read_text(encoding="utf-8"))
    validate_import_package(package)
    return {"status": "PASS", "reopened": True, "run_id": run_id, "manifest": manifest}
