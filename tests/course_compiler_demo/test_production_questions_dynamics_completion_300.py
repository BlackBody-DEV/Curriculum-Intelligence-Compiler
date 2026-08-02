from tools.course_compiler_demo.production_question_packs.dynamics.completion_300 import audit_completion,build_completion_bank


def test_dynamics_completion_300():
    bank,summary=build_completion_bank(); assert len(bank.candidates)==100==summary.validated; assert all(all(row[key] for key in ("grading_pass","procedure_compatibility_pass","failure_signal_pass","prompt_determinacy_pass","unit_tolerance_pass","answer_contract_pass")) for row in bank.validations); assert len({row["request"]["generation_family_id"] for row in bank.candidates})==10; assert {row["request"]["difficulty"] for row in bank.candidates}=={"introductory","intermediate","advanced"}; assert all(not row["prompt"].lower().startswith(("case ","question ","scenario ")) for row in bank.candidates); assert audit_completion()["status"]=="PASS"
