import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from tools.course_compiler_demo.universal_core import (
    BetaExportPackageV1, CanonicalMappingCandidateV1, ContractError,
    CurriculumNodeV1, CurriculumRelationshipV1, GenerationManifestV1,
    SourceEvidenceV1, UniversalCurriculumPackageV1,
)


def evidence():
    return SourceEvidenceV1("ev-1", "DOCUMENT", "doc-1", "a" * 64).to_dict()


def test_deterministic_json_round_trip_and_evidence_preservation():
    node = CurriculumNodeV1("n-1", "TOPIC", "Vectors", (evidence(),))
    assert node.to_json() == node.to_json()
    assert CurriculumNodeV1.from_json(node.to_json()).to_dict() == node.to_dict()
    assert json.loads(node.to_json())["source_evidence"] == [evidence()]


def test_unknown_missing_identity_and_enum_fail_closed():
    with pytest.raises(ContractError):
        CurriculumNodeV1.from_dict({"node_id": "n", "level": "TOPIC", "title": "T", "surprise": 1})
    with pytest.raises(ContractError):
        CurriculumNodeV1("", "TOPIC", "T")
    with pytest.raises(ContractError):
        CurriculumNodeV1("n", "LESSON", "T")
    with pytest.raises(ContractError):
        CurriculumNodeV1("n", "TOPIC", "T", version="2.0")
    with pytest.raises(ContractError):
        CurriculumNodeV1("n", "TOPIC", "T", review_status="UNKNOWN")


def test_nested_source_evidence_is_a_validated_contract():
    with pytest.raises(ContractError):
        CurriculumNodeV1("n", "TOPIC", "T", ({"truthy": True},))


def test_relationships_require_distinct_known_package_endpoints():
    with pytest.raises(ContractError):
        CurriculumRelationshipV1("r", "n", "n", "CONTAINS")
    nodes = (CurriculumNodeV1("a", "TOPIC", "A").to_dict(), CurriculumNodeV1("b", "SUBTOPIC", "B").to_dict())
    relationship = CurriculumRelationshipV1("r", "a", "b", "CONTAINS").to_dict()
    UniversalCurriculumPackageV1("p", nodes, (relationship,), (evidence(),))
    with pytest.raises(ContractError):
        UniversalCurriculumPackageV1("p", nodes, ({**relationship, "target_node_id": "missing"},), (evidence(),))


def test_proposed_mapping_never_grants_canonical_authority():
    with pytest.raises(ContractError):
        CanonicalMappingCandidateV1("c", "n", "canonical-x", (evidence(),), canonical_authority=True)


@pytest.mark.parametrize("field", ["student_id", "student_attempt", "student_score", "mastery", "progress", "performance_history", "adaptive_assignment"])
def test_performance_fields_are_rejected_recursively(field):
    with pytest.raises(ContractError):
        BetaExportPackageV1("x", "p", ({"question_id": "q", "metadata": {field: "forbidden"}},))


def test_beta_export_is_student_free_and_not_canonical_authority():
    export = BetaExportPackageV1("x", "p", ())
    assert "student" not in export.to_json()
    with pytest.raises(ContractError):
        BetaExportPackageV1("x", "p", (), canonical_authority=True)


def test_manifest_identity_and_positive_count():
    with pytest.raises(ContractError):
        GenerationManifestV1("m", "p", ("f",), 0, "seed")


def test_four_schemas_are_strict_and_versioned():
    root = Path(__file__).parents[2] / "schemas" / "course_compiler_demo"
    expected = {"universal_curriculum_package_v1.schema.json", "generation_manifest_v1.schema.json", "assessment_blueprint_v1.schema.json", "beta_export_package_v1.schema.json"}
    for name in expected:
        schema = json.loads((root / name).read_text())
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False
        assert schema["properties"]["version"]["const"] == "1.0"


def test_schema_accepts_contract_instance_and_rejects_unknown_and_wrong_version():
    root = Path(__file__).parents[2] / "schemas" / "course_compiler_demo"
    schema = json.loads((root / "generation_manifest_v1.schema.json").read_text())
    validator = Draft202012Validator(schema)
    instance = GenerationManifestV1("m", "p", ("family",), 2, "seed").to_dict()
    validator.validate(instance)
    with pytest.raises(ValidationError):
        validator.validate({**instance, "version": "2.0"})
    with pytest.raises(ValidationError):
        validator.validate({**instance, "student_score": 10})
