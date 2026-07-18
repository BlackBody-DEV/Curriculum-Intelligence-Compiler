import json
import subprocess
import sys
from pathlib import Path

from tests.course_compiler_demo.test_assessment_generation_contract import blueprint_for, load
from tools.course_compiler_demo.assessment_generation.exporters import instructor_assessment, student_assessment, write_exports
from tools.course_compiler_demo.assessment_generation.generator import generate_assessment
from tools.course_compiler_demo.assessment_generation.models import write_json


ROOT = Path(__file__).resolve().parents[2]
FAMILY = ROOT / "tools/course_compiler_demo/assessment_generation/families/apply_newtons_second_law_1d_v1.json"
CLI = ROOT / "tools/course_compiler_demo/run_assessment_generation.py"


def test_student_export_excludes_answers_and_instructor_export_includes_key(tmp_path):
    family = load(FAMILY)
    blueprint = blueprint_for(family, count=3)
    assessment, _, _ = generate_assessment(family=family, blueprint=blueprint)
    student = student_assessment(assessment)
    instructor = instructor_assessment(assessment)
    assert student["student_visible"] is False
    assert student["non_live_boundary"]["canonical_approved"] is False
    assert all("expected_answer" not in q and "solution_steps" not in q for q in student["questions"])
    assert all("expected_answer" in q and "solution_steps" in q for q in instructor["questions"])
    paths = write_exports(assessment, tmp_path)
    assert "expected_answer" not in Path(paths["student_json"]).read_text()
    assert "Solution:" not in Path(paths["student_markdown"]).read_text()
    assert "expected_answer" in Path(paths["instructor_json"]).read_text()
    assert "Solution:" in Path(paths["instructor_markdown"]).read_text()


def test_cli_generates_valid_assessment_run(tmp_path):
    family = load(FAMILY)
    blueprint = blueprint_for(family, count=2)
    blueprint_path = tmp_path / "blueprint.json"
    write_json(blueprint_path, blueprint)
    output_dir = tmp_path / "out"
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--family",
            str(FAMILY),
            "--blueprint",
            str(blueprint_path),
            "--output",
            str(output_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "ASSESSMENT_GENERATION_VALID" in result.stdout
    generated = json.loads((output_dir / "generated_assessment.json").read_text())
    assert generated["validation_status"] == "pass"
    assert (output_dir / "exports/student_assessment.json").exists()
