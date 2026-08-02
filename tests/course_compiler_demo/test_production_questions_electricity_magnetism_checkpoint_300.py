from tools.course_compiler_demo.production_question_packs.electricity_magnetism.checkpoint_300 import (
    audit_checkpoint,
    build_checkpoint_bank,
    build_checkpoint_inventory,
)


def test_em_checkpoint_300_adds_exactly_100_validated_questions():
    bank, summary = build_checkpoint_bank()
    assert len(bank.candidates) == 100 == summary.generated == summary.validated == summary.locked
    gates = (
        "grading_pass", "procedure_compatibility_pass", "failure_signal_pass",
        "prompt_determinacy_pass", "unit_tolerance_pass", "answer_contract_pass",
    )
    assert all(all(row[gate] for gate in gates) for row in bank.validations)
    assert all(row["classification"] != "EXACT_DUPLICATE" for row in bank.duplicates)


def test_em_checkpoint_300_inventory_has_required_production_evidence():
    inventory = build_checkpoint_inventory()
    assert len(inventory) == 100
    required = {
        "question_id", "course_id", "unit_id", "topic_id", "micro_skill_id",
        "procedure_id", "generation_family_id", "difficulty", "answer_contract",
        "grading_rule", "failure_signals", "provenance", "fingerprint",
        "production_status", "independent_derivation", "validation",
    }
    assert all(required <= set(row) for row in inventory)
    assert all(row["production_status"] == "LOCKED_PRODUCTION_VALIDATED" for row in inventory)


def test_em_checkpoint_300_cumulative_duplicate_and_count_audit():
    audit = audit_checkpoint()
    assert audit == {
        "course_id": "ELECTRICITY_AND_MAGNETISM",
        "before": 200,
        "added": 100,
        "after": 300,
        "identity_overlap": 0,
        "exact_prompt_duplicates": 0,
        "fingerprint_duplicates": 0,
        "exact_duplicates": 0,
        "validated": 100,
        "locked": 100,
        "inventory_records": 100,
        "status": "PASS",
    }
