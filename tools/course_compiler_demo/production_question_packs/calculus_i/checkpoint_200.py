"""Math 110 Calculus I checkpoint: a second locked bank of 100 questions."""
from __future__ import annotations

from dataclasses import replace
import hashlib

from tools.course_compiler_demo.production_questions import (
    ProductionFamily,
    ProductionQuestionCandidateV1,
    ProductionValidationRecordV1,
    default_validator,
    duplicate_record,
    produce_course_bank,
)
from tools.course_compiler_demo.subject_packs.mathematics import build_mathematics_reference_pack

from .bank import _choice_evidence, _family, build_bank
from .reviewer import build_evidence_reviewer


CHECKPOINT_PARAMETER_DELTA = 1000


def _checkpoint_family(index: int, course: dict) -> ProductionFamily:
    base = _family(index, course)

    def checkpoint_parameters(candidate_index: int, builder=base.parameter_builder) -> dict:
        parameters = builder(candidate_index)
        for name in ("x", "y", "span"):
            parameters[name] += CHECKPOINT_PARAMETER_DELTA
        parameters["checkpoint_series"] = 2
        return parameters

    return replace(base, parameter_builder=checkpoint_parameters)


def build_checkpoint_bank():
    existing_bank, _ = build_bank()
    pack = build_mathematics_reference_pack()
    course = pack["courses"]["CALCULUS_I"]
    families = tuple(_checkpoint_family(index, course) for index in range(15))
    evidence = ({
        "evidence_id": "CALCULUS_I_REFERENCE_PACK",
        "source_identity": pack["pack_id"],
        "source_hash": pack["deterministic_sha256"],
    },)

    seen: dict[str, str] = {}
    for payload in existing_bank.candidates:
        duplicate_record(ProductionQuestionCandidateV1(**payload), seen)

    def cross_bank_duplicate_analyzer(candidate, _local_seen):
        return duplicate_record(candidate, seen)

    review_evidence = {}

    def validator(candidate, derivation, generator_answer):
        base = default_validator(candidate, derivation, generator_answer)
        choice = _choice_evidence(candidate, derivation.normalized_answer)
        passed = base.answer_contract_pass and choice["passed"]
        result = ProductionValidationRecordV1(
            base.validation_id,
            base.candidate_id,
            base.grading_pass,
            base.procedure_compatibility_pass,
            base.failure_signal_pass,
            base.prompt_determinacy_pass,
            base.unit_tolerance_pass,
            passed,
            base.reasons + (() if choice["passed"] else ("MULTIPLE_CHOICE_CONTRACT_INVALID",)),
        )
        review_evidence[candidate.candidate_id] = {
            "family_id": candidate.request["generation_family_id"],
            "choice_count": choice["choice_count"],
            "answer_matches": choice["answer_matches"],
            "numeric_matches": choice.get("numeric_matches", 0),
            "candidate_digest": hashlib.sha256(candidate.to_json().encode()).hexdigest(),
            "validation_digest": hashlib.sha256(result.to_json().encode()).hexdigest(),
            "passed": result.passed,
        }
        return result

    bank, summary = produce_course_bank(
        "CALCULUS_I",
        pack["pack_id"],
        pack["deterministic_sha256"],
        evidence,
        families,
        reviewer=build_evidence_reviewer(review_evidence),
        duplicate_analyzer=cross_bank_duplicate_analyzer,
        validator=validator,
    )
    bank = replace(bank, bank_id="bank:CALCULUS_I:math-110-checkpoint:v1")
    summary = replace(summary, summary_id="summary:CALCULUS_I:math-110-checkpoint:v1")
    return bank, summary


def build_checkpoint_inventory(bank=None) -> tuple[dict, ...]:
    bank = bank or build_checkpoint_bank()[0]
    validations = {row["candidate_id"]: row for row in bank.validations}
    derivations = {row["candidate_id"]: row for row in bank.derivations}
    duplicates = {row["candidate_id"]: row for row in bank.duplicates}
    rows = []
    for candidate in bank.candidates:
        candidate_id = candidate["candidate_id"]
        request = candidate["request"]
        duplicate = duplicates[candidate_id]
        rows.append({
            **candidate,
            "question_id": candidate_id,
            "course_id": request["course_id"],
            "generation_family_id": request["generation_family_id"],
            "difficulty": request["difficulty"],
            "grading_rule": {"engine_type": candidate["answer_contract"]["engine_type"], "tolerance": candidate["answer_contract"]["tolerance"]},
            "provenance": {"deterministic_seed": request["deterministic_seed"], "source_evidence": candidate["authority"]["source_evidence"]},
            "fingerprint": duplicate["fingerprint"],
            "structural_fingerprint": duplicate["structural_fingerprint"],
            "duplicate_status": duplicate["classification"],
            "production_status": "LOCKED_PRODUCTION_VALIDATED",
            "independent_derivation": derivations[candidate_id],
            "validation": validations[candidate_id],
        })
    return tuple(rows)


def audit_checkpoint() -> dict:
    existing, _ = build_bank()
    added, summary = build_checkpoint_bank()
    inventory = build_checkpoint_inventory(added)
    existing_ids = {q["candidate_id"] for q in existing.candidates}
    added_ids = {q["candidate_id"] for q in added.candidates}
    return {
        "course_id": "CALCULUS_I",
        "before": len(existing_ids),
        "added": len(added_ids),
        "after": len(existing_ids | added_ids),
        "identity_overlap": len(existing_ids & added_ids),
        "exact_duplicates": sum(x["classification"] == "EXACT_DUPLICATE" for x in added.duplicates),
        "validated": summary.validated,
        "locked": summary.locked,
        "inventory_records": len(inventory),
        "status": "PASS" if len(existing_ids | added_ids) == 200 and not existing_ids & added_ids and len(inventory) == 100 and all(row["fingerprint"] and row["production_status"] == "LOCKED_PRODUCTION_VALIDATED" for row in inventory) else "FAIL",
    }
