from pathlib import Path

from tests.course_compiler_demo.test_assessment_generation_contract import blueprint_for, load
from tools.course_compiler_demo.assessment_generation.answer_calculators import calculate_answer
from tools.course_compiler_demo.assessment_generation.generator import generate_assessment


ROOT = Path(__file__).resolve().parents[2]
FAMILY = ROOT / "tools/course_compiler_demo/assessment_generation/families/vector_components_2d_v1.json"


def test_statics_generates_ten_valid_unique_questions_with_directional_variation():
    family = load(FAMILY)
    blueprint = blueprint_for(family, count=10)
    assessment, report, _ = generate_assessment(family=family, blueprint=blueprint)
    assert report["requested_count"] == 10
    assert report["generated_count"] == 10
    assert report["rejected_exact_duplicates"] >= 0
    assert report["rejected_structural_duplicates"] >= 0
    assert report["parameter_space_exhausted"] is False
    patterns = {(q["parameter_set"]["x_sign"], q["parameter_set"]["y_sign"]) for q in assessment["questions"]}
    assert len(patterns) >= 3
    assert len({q["exact_fingerprint"] for q in assessment["questions"]}) == 10
    assert len({q["structural_fingerprint"] for q in assessment["questions"]}) == 10
    for q in assessment["questions"]:
        assert q["question_type"] == "numeric_pair"
        assert calculate_answer(family["answer_calculator_id"], q["parameter_set"]) == q["expected_answer"]
