"""Physics 126 Mechanics completion: a third locked bank of 100 questions."""
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
from .checkpoint_200 import build_checkpoint_bank


def _completion_family(index: int, course: dict) -> ProductionFamily:
    base = _family(index, course)

    def completion_parameters(candidate_index: int, builder=base.parameter_builder) -> dict:
        parameters = builder(candidate_index)
        parameters["a"] += 400.0
        parameters["b"] += 400.0
        parameters["speed"] += 40.0
        parameters["time"] += 20.0
        parameters["mass"] += 40.0
        parameters["radius"] += 20.0
        return parameters

    return replace(base, parameter_builder=completion_parameters)


def build_completion_bank():
    existing_bank, _, _ = build_bank()
    checkpoint_bank, _ = build_checkpoint_bank()
    pack = build_physics_engineering_course_catalog()
    validate_physics_engineering_course_catalog(pack)
    course = pack["courses"]["MECHANICS"]
    families = tuple(_completion_family(index, course) for index in range(10))
    evidence = ({
        "evidence_id": "MECHANICS:COURSE_CATALOG",
        "source_identity": pack["pack_id"],
        "source_hash": pack["deterministic_sha256"],
        "access": "READ_ONLY_REFERENCE",
    },)
    seen: dict[str, str] = {}
    for prior_bank in (existing_bank, checkpoint_bank):
        for payload in prior_bank.candidates:
            duplicate_record(ProductionQuestionCandidateV1(**payload), seen)

    def cumulative_duplicate_analyzer(candidate, _local_seen):
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
        duplicate_analyzer=cumulative_duplicate_analyzer,
        validator=validator,
    )
    bank = replace(bank, bank_id="bank:MECHANICS:physics-126-completion:v1")
    summary = replace(summary, summary_id="summary:MECHANICS:physics-126-completion:v1")
    return bank, summary


def build_completion_inventory(bank=None) -> tuple[dict, ...]:
    bank = bank or build_completion_bank()[0]
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


def audit_completion() -> dict:
    existing, _, _ = build_bank()
    checkpoint, _ = build_checkpoint_bank()
    added, summary = build_completion_bank()
    inventory = build_completion_inventory(added)
    banks = (existing, checkpoint, added)
    candidates = [row for bank in banks for row in bank.candidates]
    ids = [row["candidate_id"] for row in candidates]
    prompts = [hashlib.sha256(row["prompt"].strip().lower().encode()).hexdigest() for row in candidates]
    fingerprints = [row["fingerprint"] for bank in banks for row in bank.duplicates]
    records = [ProductionQuestionCandidateV1(**row).to_json() for row in candidates]
    passed = (
        all(len(bank.candidates) == 100 for bank in banks)
        and len(set(ids)) == len(set(prompts)) == len(set(fingerprints)) == len(set(records)) == 300
        and summary.validated == summary.locked == 100
        and len(inventory) == 100
        and all(row["production_status"] == "LOCKED_PRODUCTION_VALIDATED" for row in inventory)
    )
    return {
        "course_id": "MECHANICS",
        "before": 200,
        "added": len(added.candidates),
        "after": len(set(ids)),
        "duplicate_identities": len(ids) - len(set(ids)),
        "exact_prompt_duplicates": len(prompts) - len(set(prompts)),
        "fingerprint_duplicates": len(fingerprints) - len(set(fingerprints)),
        "exact_record_duplicates": len(records) - len(set(records)),
        "exact_duplicates": sum(row["classification"] == "EXACT_DUPLICATE" for row in added.duplicates),
        "validated": summary.validated,
        "inventory_records": len(inventory),
        "status": "PASS" if passed else "FAIL",
    }
