"""Pure export boundary; this module performs no writes or imports."""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping

from tools.course_compiler_demo.universal_core import (
    AssessmentBlueprintV1, BetaExportPackageV1, ContractError,
    FORBIDDEN_PERFORMANCE_FIELDS, ValidatedQuestionReferenceV1,
)


class BetaExportError(ValueError):
    pass


def build_beta_export(export_id: str, curriculum_package_id: str,
                      questions: Iterable[ValidatedQuestionReferenceV1 | Mapping[str, Any]], *,
                      blueprints: Iterable[AssessmentBlueprintV1 | Mapping[str, Any]] = (),
                      proposed_canonical_mappings: Iterable[Mapping[str, Any]] = (),
                      source_evidence: Iterable[Mapping[str, Any]] = ()) -> BetaExportPackageV1:
    q = tuple(x.to_dict() if isinstance(x, ValidatedQuestionReferenceV1) else ValidatedQuestionReferenceV1.from_dict(x).to_dict() for x in questions)
    bp = tuple(x.to_dict() if isinstance(x, AssessmentBlueprintV1) else AssessmentBlueprintV1.from_dict(x).to_dict() for x in blueprints)
    package = BetaExportPackageV1(export_id, curriculum_package_id, q, bp,
                                  tuple(dict(x) for x in proposed_canonical_mappings),
                                  tuple(dict(x) for x in source_evidence))
    dry_run_import_validate(package.to_dict())
    return package


def stable_export_hash(package: BetaExportPackageV1 | Mapping[str, Any]) -> str:
    obj = package if isinstance(package, BetaExportPackageV1) else BetaExportPackageV1.from_dict(package)
    return hashlib.sha256(obj.to_json().encode("utf-8")).hexdigest()


def dry_run_import_validate(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate shape and identities without writing to Beta or any database."""
    try:
        package = BetaExportPackageV1.from_dict(payload)
    except (ContractError, TypeError, ValueError) as exc:
        raise BetaExportError(str(exc)) from exc
    ids = [(q["question_id"], q["question_revision"]) for q in package.question_references]
    if len(ids) != len(set(ids)):
        raise BetaExportError("duplicate question identity and revision")
    for question in package.question_references:
        for field in ("assessment_identity", "assessment_role", "procedure_id", "answer_contract_id",
                      "validation_result_id", "difficulty"):
            if not isinstance(question.get(field), str) or not question[field].strip():
                raise BetaExportError(f"qualified export reference requires {field}")
        if not question.get("curriculum_mapping") or not question.get("grading_contract") or not question.get("provenance"):
            raise BetaExportError("qualified export reference requires curriculum mapping, grading contract, and provenance")
    encoded = package.to_json()
    if any(f'"{name}"' in encoded for name in FORBIDDEN_PERFORMANCE_FIELDS):
        raise BetaExportError("student-performance data is forbidden")
    return {"valid": True, "would_write": False, "question_reference_count": len(ids),
            "export_sha256": hashlib.sha256(encoded.encode()).hexdigest()}
