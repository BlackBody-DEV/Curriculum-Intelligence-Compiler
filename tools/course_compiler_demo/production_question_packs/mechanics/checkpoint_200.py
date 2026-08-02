"""Physics 124 Mechanics checkpoint: a second locked bank of 100 questions."""
from __future__ import annotations

from dataclasses import replace
import hashlib

from tools.course_compiler_demo.production_questions import (
    ProductionFamily,
    ProductionQuestionCandidateV1,
    duplicate_record,
    produce_course_bank,
)
from tools.course_compiler_demo.subject_packs.physics_engineering import (
    build_physics_engineering_course_catalog,
    validate_physics_engineering_course_catalog,
)

from .bank import _family, artifact_reviewer, build_bank, mechanics_validator


def _checkpoint_family(index: int, course: dict) -> ProductionFamily:
    base = _family(index, course)

    def checkpoint_parameters(candidate_index: int, builder=base.parameter_builder) -> dict:
        parameters = builder(candidate_index)
        parameters["a"] += 200.0
        parameters["b"] += 200.0
        parameters["speed"] += 20.0
        parameters["time"] += 10.0
        parameters["mass"] += 20.0
        parameters["radius"] += 10.0
        return parameters

    return replace(base, parameter_builder=checkpoint_parameters)


def build_checkpoint_bank():
    existing_bank, _, _ = build_bank()
    pack = build_physics_engineering_course_catalog()
    validate_physics_engineering_course_catalog(pack)
    course = pack["courses"]["MECHANICS"]
    families = tuple(_checkpoint_family(index, course) for index in range(10))
    evidence = ({
        "evidence_id": "MECHANICS:COURSE_CATALOG",
        "source_identity": pack["pack_id"],
        "source_hash": pack["deterministic_sha256"],
        "access": "READ_ONLY_REFERENCE",
    },)
    seen: dict[str, str] = {}
    for payload in existing_bank.candidates:
        duplicate_record(ProductionQuestionCandidateV1(**payload), seen)

    def cross_bank_duplicate_analyzer(candidate, _local_seen):
        return duplicate_record(candidate, seen)

    inspected = {}

    def validator(candidate, derivation, generator_answer):
        result = mechanics_validator(candidate, derivation, generator_answer)
        inspected[candidate.candidate_id] = (candidate, derivation, result)
        return result

    def reviewer(subject, level):
        return artifact_reviewer(families, inspected, subject, level)

    bank, summary = produce_course_bank(
        "MECHANICS",
        pack["pack_id"],
        pack["deterministic_sha256"],
        evidence,
        families,
        reviewer=reviewer,
        duplicate_analyzer=cross_bank_duplicate_analyzer,
        validator=validator,
    )
    bank = replace(bank, bank_id="bank:MECHANICS:physics-124-checkpoint:v1")
    summary = replace(summary, summary_id="summary:MECHANICS:physics-124-checkpoint:v1")
    return bank, summary


def build_checkpoint_inventory(bank=None) -> tuple[dict, ...]:
    bank = bank or build_checkpoint_bank()[0]
    derivations = {row["candidate_id"]: row for row in bank.derivations}
    validations = {row["candidate_id"]: row for row in bank.validations}
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
            "grading_rule": {
                "engine_type": candidate["answer_contract"]["engine_type"],
                "tolerance": candidate["answer_contract"]["tolerance"],
            },
            "provenance": {
                "deterministic_seed": request["deterministic_seed"],
                "source_evidence": candidate["authority"]["source_evidence"],
            },
            "fingerprint": duplicate["fingerprint"],
            "structural_fingerprint": duplicate["structural_fingerprint"],
            "duplicate_status": duplicate["classification"],
            "production_status": "LOCKED_PRODUCTION_VALIDATED",
            "independent_derivation": derivations[candidate_id],
            "validation": validations[candidate_id],
        })
    return tuple(rows)


def audit_checkpoint() -> dict:
    existing, _, _ = build_bank()
    added, summary = build_checkpoint_bank()
    inventory = build_checkpoint_inventory(added)
    all_candidates = tuple(existing.candidates) + tuple(added.candidates)
    existing_ids = {row["candidate_id"] for row in existing.candidates}
    added_ids = {row["candidate_id"] for row in added.candidates}
    prompts = [hashlib.sha256(row["prompt"].strip().lower().encode()).hexdigest() for row in all_candidates]
    fingerprints = [row["fingerprint"] for row in existing.duplicates] + [row["fingerprint"] for row in added.duplicates]
    passed = (
        len(existing_ids) == len(added_ids) == 100
        and len(existing_ids | added_ids) == 200
        and not existing_ids & added_ids
        and len(prompts) == len(set(prompts)) == 200
        and len(fingerprints) == len(set(fingerprints)) == 200
        and summary.validated == summary.locked == 100
        and len(inventory) == 100
        and all(row["production_status"] == "LOCKED_PRODUCTION_VALIDATED" for row in inventory)
    )
    return {
        "course_id": "MECHANICS",
        "before": len(existing_ids),
        "added": len(added_ids),
        "after": len(existing_ids | added_ids),
        "identity_overlap": len(existing_ids & added_ids),
        "exact_prompt_duplicates": len(prompts) - len(set(prompts)),
        "fingerprint_duplicates": len(fingerprints) - len(set(fingerprints)),
        "exact_duplicates": sum(row["classification"] == "EXACT_DUPLICATE" for row in added.duplicates),
        "validated": summary.validated,
        "inventory_records": len(inventory),
        "status": "PASS" if passed else "FAIL",
    }
