from pathlib import Path

from tests.course_compiler_demo.test_assessment_generation_contract import blueprint_for, load
from tools.course_compiler_demo.assessment_generation import generator
from tools.course_compiler_demo.assessment_generation.generator import generate_assessment
from tools.course_compiler_demo.assessment_generation.validators import review_record


ROOT = Path(__file__).resolve().parents[2]
FAMILY = ROOT / "tools/course_compiler_demo/assessment_generation/families/vector_components_2d_v1.json"


def test_historical_fingerprint_rejection_is_recorded():
    family = load(FAMILY)
    blueprint = blueprint_for(family, count=1)
    assessment, _, _ = generate_assessment(family=family, blueprint=blueprint)
    q = assessment["questions"][0]
    _, report, _ = generate_assessment(
        family=family,
        blueprint=blueprint,
        historical_fingerprints={q["exact_fingerprint"], q["structural_fingerprint"]},
    )
    assert report["rejected_exact_duplicates"] + report["rejected_structural_duplicates"] > 0
    assert report["generated_count"] == 1


def test_parameter_space_exhaustion_is_honest(monkeypatch):
    family = load(FAMILY)
    family["scenario_templates"] = [{"scenario_template_id": "only", "object": "A bracket"}]
    blueprint = blueprint_for(family, count=2)

    def constant_params(_difficulty, _rng):
        return {"magnitude": 50, "angle_degrees": 30, "x_sign": 1, "y_sign": 1, "quadrant_label": "Quadrant I"}

    monkeypatch.setitem(generator.PARAM_BUILDERS, family["family_type"], constant_params)
    monkeypatch.setattr(generator, "MAX_ATTEMPTS_PER_SLOT", 3)
    _, report, _ = generate_assessment(family=family, blueprint=blueprint)
    assert report["generated_count"] == 1
    assert report["parameter_space_exhausted"] is True
    assert report["rejected_exact_duplicates"] + report["rejected_structural_duplicates"] > 0


def test_math_edit_invalidates_validation():
    record = review_record(
        question_id="Q1",
        decision="needs_revision",
        math_content_edited=True,
        reviewer_note="Changed the component value.",
    )
    assert record["validation_invalidated"] is True
