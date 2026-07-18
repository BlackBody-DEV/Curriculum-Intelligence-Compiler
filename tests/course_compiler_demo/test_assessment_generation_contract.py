import copy
import json
from pathlib import Path

import pytest

from tools.course_compiler_demo.assessment_generation.blueprint import validate_blueprint
from tools.course_compiler_demo.assessment_generation.family_loader import validate_family
from tools.course_compiler_demo.assessment_generation.generator import generate_assessment
from tools.course_compiler_demo.assessment_generation.models import AssessmentGenerationError


ROOT = Path(__file__).resolve().parents[2]
PHYSICS_FAMILY = ROOT / "tools/course_compiler_demo/assessment_generation/families/apply_newtons_second_law_1d_v1.json"
STATICS_FAMILY = ROOT / "tools/course_compiler_demo/assessment_generation/families/vector_components_2d_v1.json"
SCHEMAS = ROOT / "tools/course_compiler_demo/schemas"


def load(path: Path):
    return json.loads(path.read_text())


def physics_family():
    return load(PHYSICS_FAMILY)


def statics_family():
    return load(STATICS_FAMILY)


def blueprint_for(family: dict, *, count=3, status="generation_ready") -> dict:
    return {
        "assessment_id": f"ASSESS_{family['target_micro_skill_code'].upper()}_TEST",
        "contract_version": "assessment_generation_contract_v1",
        "title": "Test assessment",
        "assessment_type": "practice_set",
        "subject_code": family["subject_code"],
        "course_profile": "compiler_test_profile",
        "selected_topic_codes": [family["topic_code"]],
        "selected_micro_skill_codes": [family["target_micro_skill_code"]],
        "question_count": count,
        "difficulty_distribution": {"foundational": 1, "standard": max(0, count - 2), "advanced": 1 if count > 1 else 0},
        "question_type_distribution": {family["question_types"][0]: count},
        "generation_family_allocation": {
            family["generation_family_id"]: {
                "question_count": count,
                "approved_procedure_codes": [family["approved_procedure_code"]],
            }
        },
        "prerequisite_policy": {"allowed_prerequisite_skills": family["approved_prerequisite_skills"]},
        "scaffolding_policy": {"include_scaffolding": False},
        "solution_policy": {"include_solutions_in_instructor_export": True},
        "answer_key_policy": {"student_export_includes_answers": False},
        "uniqueness_policy": {"reject_exact_duplicates": True, "reject_structural_duplicates": True},
        "scope_policy": {"forbidden_downstream_micro_skills": []},
        "rights_boundary": {
            "eligible_for_alpha_import": False,
            "canonical_approved": False,
            "student_visible": False,
            "human_review_required": True,
        },
        "random_seed": 24680,
        "status": status,
    }


def test_all_new_schemas_are_valid_json():
    expected = {
        "assessment_generation_family_v1.schema.json",
        "assessment_blueprint_v1.schema.json",
        "generated_question_v1.schema.json",
        "generated_assessment_v1.schema.json",
        "assessment_validation_report_v1.schema.json",
        "assessment_review_decisions_v1.schema.json",
    }
    assert expected <= {path.name for path in SCHEMAS.glob("*.schema.json")}
    for name in sorted(expected):
        path = SCHEMAS / name
        assert json.loads(path.read_text())["$schema"]


@pytest.mark.parametrize("field,value,error", [
    ("contract_version", "unknown", "unknown family contract version"),
    ("prompt_builder_id", "not_registered", "unknown prompt builder ID"),
    ("answer_calculator_id", "not_registered", "unknown answer calculator ID"),
    ("enabled", False, "disabled"),
])
def test_family_contract_rejects_unsafe_or_unknown_controls(field, value, error):
    family = physics_family()
    family[field] = value
    with pytest.raises(AssessmentGenerationError, match=error):
        validate_family(family)


def test_loader_accepts_generic_third_family_with_registered_controls():
    family = physics_family()
    family["generation_family_id"] = "GF_SYNTHETIC_THIRD_FAMILY"
    family["topic_code"] = "synthetic_topic"
    family["target_micro_skill_code"] = "synthetic_skill"
    family["supported_micro_skills"] = ["synthetic_skill"]
    validate_family(family)


def test_invalid_blueprint_and_scope_fail_closed():
    family = physics_family()
    blueprint = blueprint_for(family, status="draft")
    with pytest.raises(AssessmentGenerationError, match="generation_ready"):
        validate_blueprint(blueprint)

    blueprint = blueprint_for(family)
    blueprint["difficulty_distribution"] = {"graduate": 1, "standard": 2}
    with pytest.raises(AssessmentGenerationError, match="unsupported difficulty"):
        validate_blueprint(blueprint)
    with pytest.raises(AssessmentGenerationError, match="unsupported difficulty"):
        generate_assessment(family=family, blueprint=blueprint)

    blueprint = blueprint_for(family)
    blueprint["difficulty_distribution"] = {"foundational": 1}
    with pytest.raises(AssessmentGenerationError, match="difficulty distribution"):
        validate_blueprint(blueprint)
    with pytest.raises(AssessmentGenerationError, match="difficulty distribution"):
        generate_assessment(family=family, blueprint=blueprint)

    blueprint = blueprint_for(family)
    blueprint["question_type_distribution"] = {"numeric_with_unit": 1}
    with pytest.raises(AssessmentGenerationError, match="question type distribution"):
        validate_blueprint(blueprint)

    blueprint = blueprint_for(family)
    blueprint["selected_topic_codes"] = ["wrong_topic"]
    with pytest.raises(AssessmentGenerationError, match="topic"):
        generate_assessment(family=family, blueprint=blueprint)

    blueprint = blueprint_for(family)
    blueprint["selected_micro_skill_codes"] = ["wrong_skill"]
    with pytest.raises(AssessmentGenerationError, match="micro-skill"):
        generate_assessment(family=family, blueprint=blueprint)

    blueprint = blueprint_for(family)
    blueprint["prerequisite_policy"] = {"allowed_prerequisite_skills": []}
    with pytest.raises(AssessmentGenerationError, match="prerequisite"):
        generate_assessment(family=family, blueprint=blueprint)

    blueprint = blueprint_for(family)
    blueprint["scope_policy"] = {"forbidden_downstream_micro_skills": ["apply_newtons_second_law_1d"]}
    with pytest.raises(AssessmentGenerationError, match="downstream"):
        generate_assessment(family=family, blueprint=blueprint)


def test_scope_exclusion_and_answer_validation_failures_are_reported():
    family = statics_family()
    blueprint = blueprint_for(family)
    assessment, _, _ = generate_assessment(family=family, blueprint=blueprint)
    q = copy.deepcopy(assessment["questions"][0])
    q["prompt"] += " Find the resultant magnitude too."
    from tools.course_compiler_demo.assessment_generation.validators import validate_question

    assert any("scope exclusion" in err for err in validate_question(q, family, blueprint))
    q = copy.deepcopy(assessment["questions"][0])
    q["expected_answer"]["unit"] = "lb"
    assert "unsupported unit" in validate_question(q, family, blueprint)
    q = copy.deepcopy(assessment["questions"][0])
    q["tolerance"] = {"absolute": -1}
    assert "invalid tolerance" in validate_question(q, family, blueprint)
