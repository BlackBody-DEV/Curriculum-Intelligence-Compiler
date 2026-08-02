from tools.course_compiler_demo.production_question_packs.waves_optics.completion_300 import (
    audit_completion,
    build_completion_bank,
    build_completion_inventory,
)


def test_waves_optics_completion_adds_100_validated_diverse_questions():
    bank, summary = build_completion_bank()
    assert len(bank.candidates) == 100 == summary.generated == summary.validated == summary.locked
    gates = ("grading_pass", "procedure_compatibility_pass", "failure_signal_pass", "prompt_determinacy_pass", "unit_tolerance_pass", "answer_contract_pass")
    assert all(all(row[gate] for gate in gates) for row in bank.validations)
    families = {row["request"]["generation_family_id"] for row in bank.candidates}
    assert len(families) == 10
    assert max(sum(row["request"]["generation_family_id"] == family for row in bank.candidates) for family in families) <= 25
    assert {row["request"]["difficulty"] for row in bank.candidates} == {"introductory", "intermediate", "advanced"}


def test_waves_optics_completion_inventory_domains_and_cumulative_audit():
    inventory = build_completion_inventory()
    assert len(inventory) == 100
    assert all(row["fingerprint"] and row["production_status"] == "LOCKED_PRODUCTION_VALIDATED" for row in inventory)
    assert all(not row["prompt"].lower().startswith(("case ", "question ", "scenario ")) for row in inventory)
    diffraction = [row for row in inventory if row["generation_family_id"].endswith("_06")]
    assert all(0 < row["request"]["parameters"]["b"] * row["request"]["parameters"]["wavelength"] / (row["request"]["parameters"]["a"] * 1e-3) <= 1 for row in diffraction)
    assert audit_completion() == {
        "course_id": "WAVES_AND_OPTICS", "before": 200, "added": 100, "after": 300,
        "duplicate_identities": 0, "exact_prompt_duplicates": 0, "fingerprint_duplicates": 0,
        "exact_record_duplicates": 0, "exact_duplicates": 0, "validated": 100,
        "inventory_records": 100, "status": "PASS",
    }
