import copy
from pathlib import Path

from tests.course_compiler_demo.test_assessment_generation_contract import blueprint_for, load
from tools.course_compiler_demo.assessment_generation.answer_calculators import calculate_answer
from tools.course_compiler_demo.assessment_generation.generator import generate_assessment, regenerate_question
from tools.course_compiler_demo.assessment_generation.validators import validate_question


ROOT = Path(__file__).resolve().parents[2]
FAMILY = ROOT / "tools/course_compiler_demo/assessment_generation/families/apply_newtons_second_law_1d_v1.json"


def test_physics_generates_ten_valid_mixed_questions_deterministically():
    family = load(FAMILY)
    blueprint = blueprint_for(family, count=10)
    first, report, _ = generate_assessment(family=family, blueprint=blueprint)
    second, second_report, _ = generate_assessment(family=family, blueprint=blueprint)
    assert first == second
    assert report["generated_count"] == 10
    assert second_report["parameter_space_exhausted"] is False
    assert {q["parameter_set"]["target_variable"] for q in first["questions"]} >= {"acceleration", "net_force"}
    assert all(q["validation_status"] == "pass" for q in first["questions"])
    for q in first["questions"]:
        assert calculate_answer(family["answer_calculator_id"], q["parameter_set"]) == q["expected_answer"]


def test_physics_different_seed_varies_and_tampered_answer_rejects():
    family = load(FAMILY)
    blueprint = blueprint_for(family, count=5)
    first, _, _ = generate_assessment(family=family, blueprint=blueprint)
    varied_blueprint = {**blueprint, "assessment_id": "ASSESS_PHYSICS_VARIED", "random_seed": 24681}
    second, _, _ = generate_assessment(family=family, blueprint=varied_blueprint)
    assert [q["parameter_set"] for q in first["questions"]] != [q["parameter_set"] for q in second["questions"]]
    q = copy.deepcopy(first["questions"][0])
    q["expected_answer"]["value"] = q["expected_answer"]["value"] + 1
    assert "answer recomputation mismatch" in validate_question(q, family, blueprint)


def test_single_question_regeneration_and_locked_preservation():
    family = load(FAMILY)
    blueprint = blueprint_for(family, count=3)
    assessment, _, _ = generate_assessment(family=family, blueprint=blueprint)
    replacement = regenerate_question(
        assessment=assessment,
        family=family,
        blueprint=blueprint,
        slot_id="SLOT_002",
        child_seed=999,
    )
    assert replacement["slot_id"] == "SLOT_002"
    assert replacement["question_id"].endswith("_R001")
    assessment["questions"][1]["locked"] = True
    try:
        regenerate_question(assessment=assessment, family=family, blueprint=blueprint, slot_id="SLOT_002", child_seed=1000)
    except ValueError as exc:
        assert "locked" in str(exc)
    else:
        raise AssertionError("locked question regeneration should fail")
