import pytest

from tools.course_compiler_demo.beta_export import BetaExportError, build_beta_export, dry_run_import_validate, stable_export_hash
from tools.course_compiler_demo.universal_core import ContractError
from test_assessment_compiler import blueprint, reference


def test_export_contains_required_reference_data_and_is_stable():
    package = build_beta_export("export-1", "curriculum-1", [reference(i) for i in range(300)], blueprints=(blueprint(),))
    assert len(package.question_references) == 300
    question = package.question_references[0]
    required = {"curriculum_mapping", "proposed_canonical_mapping_status", "question_id", "question_revision",
                "procedure_id", "difficulty", "answer_contract_id", "grading_contract", "failure_signals",
                "assessment_identity", "assessment_role", "source_evidence", "provenance", "asset_references", "version_data"}
    assert required <= question.keys()
    assert stable_export_hash(package) == stable_export_hash(package.to_dict())
    result = dry_run_import_validate(package.to_dict())
    assert result["valid"] and not result["would_write"] and result["question_reference_count"] == 300


@pytest.mark.parametrize("field", ["student_id", "student_attempt", "student_score", "mastery", "progress", "performance_history", "adaptive_assignment"])
def test_performance_fields_excluded_recursively(field):
    payload = reference(1).to_dict()
    payload["provenance"] = {field: "forbidden"}
    with pytest.raises(ContractError):
        build_beta_export("e", "p", [payload])


def test_export_duplicate_and_invalid_payload_fail_closed():
    q = reference(1).to_dict()
    with pytest.raises(BetaExportError, match="duplicate"):
        dry_run_import_validate(build_beta_export("e", "p", [q]).to_dict() | {"question_references": [q, q]})
    with pytest.raises(BetaExportError):
        dry_run_import_validate({"export_id": "e"})


@pytest.mark.parametrize("field", ["assessment_identity", "assessment_role"])
def test_export_requires_qualified_assessment_references(field):
    q = reference(1).to_dict()
    q[field] = ""
    with pytest.raises(BetaExportError, match=field):
        build_beta_export("e", "p", [q])
