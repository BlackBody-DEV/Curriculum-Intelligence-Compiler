"""Local student/instructor export writers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import write_json


def student_assessment(assessment: dict[str, Any]) -> dict[str, Any]:
    clean = {k: v for k, v in assessment.items() if k != "questions"}
    clean["student_visible"] = False
    clean["non_live_boundary"] = dict(assessment["non_live_boundary"])
    clean["non_live_boundary"]["student_visible"] = False
    clean["questions"] = []
    for q in assessment["questions"]:
        clean["questions"].append(
            {
                key: q[key]
                for key in [
                    "question_id",
                    "slot_id",
                    "subject_code",
                    "topic_code",
                    "micro_skill_code",
                    "difficulty",
                    "question_type",
                    "prompt",
                    "accepted_units",
                    "grading_type",
                    "review_status",
                    "validation_status",
                ]
            }
        )
    return clean


def instructor_assessment(assessment: dict[str, Any]) -> dict[str, Any]:
    return dict(assessment)


def _markdown(assessment: dict[str, Any], *, include_answers: bool) -> str:
    lines = [f"# {assessment['title']}", "", f"Assessment ID: `{assessment['assessment_id']}`", ""]
    for i, q in enumerate(assessment["questions"], start=1):
        lines.append(f"## Question {i}")
        lines.append(q["prompt"])
        if include_answers:
            lines.append("")
            lines.append(f"Answer: `{q['expected_answer']}`")
            lines.extend(["", "Solution:"])
            lines.extend([f"- {step}" for step in q["solution_steps"]])
        lines.append("")
    lines.append("Noncanonical local export; student_visible remains false.")
    return "\n".join(lines) + "\n"


def write_exports(assessment: dict[str, Any], output_dir: Path) -> dict[str, str]:
    exports = output_dir / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    student_json = student_assessment(assessment)
    instructor_json = instructor_assessment(assessment)
    paths = {
        "student_json": exports / "student_assessment.json",
        "instructor_json": exports / "instructor_assessment.json",
        "student_markdown": exports / "student_assessment.md",
        "instructor_markdown": exports / "instructor_assessment.md",
    }
    write_json(paths["student_json"], student_json)
    write_json(paths["instructor_json"], instructor_json)
    paths["student_markdown"].write_text(_markdown(student_json, include_answers=False), encoding="utf-8")
    paths["instructor_markdown"].write_text(_markdown(instructor_json, include_answers=True), encoding="utf-8")
    return {key: path.as_posix() for key, path in paths.items()}
