from tools.course_compiler_demo.production_question_packs.modern_physics.checkpoint_200 import audit_checkpoint,build_checkpoint_bank


def test_modern_physics_checkpoint_200():
    bank,summary=build_checkpoint_bank(); assert len(bank.candidates)==100==summary.validated; assert all(all(row[key] for key in ("grading_pass","procedure_compatibility_pass","failure_signal_pass","prompt_determinacy_pass","unit_tolerance_pass","answer_contract_pass")) for row in bank.validations); assert len({row["request"]["generation_family_id"] for row in bank.candidates})==10; assert {row["request"]["difficulty"] for row in bank.candidates}=={"introductory","intermediate","advanced"}; assert all(not row["prompt"].lower().startswith(("case ","question ","scenario ")) for row in bank.candidates); assert audit_checkpoint()["status"]=="PASS"
