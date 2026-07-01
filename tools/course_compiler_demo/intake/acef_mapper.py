"""ACEF scaffold generation for non-live intake runs."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from intake_registry import write_json


CANONICAL_FAILURE_SIGNALS = {"axis_confusion", "sign_or_placement_error", "simple_average_used", "unclassified"}
TOPIC_CODE_OVERRIDES = {
    "LINEAR_EQUATIONS": "MATH_ALGEBRA_LINEAR_EQUATIONS",
    "GRAPHING_LINES": "MATH_ALGEBRA_GRAPHING_LINES",
}


def _load(run_dir: Path, filename: str) -> dict[str, Any]:
    return json.loads((run_dir / filename).read_text(encoding="utf-8"))


def _slug(value: str | None, fallback: str) -> str:
    raw = value or fallback
    slug = re.sub(r"[^A-Z0-9]+", "_", raw.upper()).strip("_")
    return slug or fallback


def _topic_code(topic: dict[str, Any]) -> str:
    slug = _slug(topic.get("topic_name"), "TOPIC_REVIEW_REQUIRED")
    return TOPIC_CODE_OVERRIDES.get(slug, f"MATH_ALGEBRA_{slug}")


def _subtopic_code(topic_code: str) -> str:
    if topic_code.startswith("MATH_ALGEBRA_"):
        return f"{topic_code}_BASIC"
    return "SUBTOPIC_REVIEW_REQUIRED"


def _source_refs(skill: dict[str, Any], intake_record: dict[str, Any]) -> list[dict[str, Any]]:
    source_name = intake_record.get("original_filename") or "synthetic_demo_source"
    return [
        {
            "source_type": "synthetic_demo",
            "source_name": source_name,
            "evidence_refs": skill.get("evidence_refs", []),
            "confidence": skill.get("confidence", "medium"),
        }
    ]


def _procedure_guidance(micro_skill_name: str) -> dict[str, Any]:
    skill_key = _slug(micro_skill_name, "REVIEW_REQUIRED")
    if "SLOPE" in skill_key:
        return {
            "formula": "slope = (change in y) / (change in x)",
            "given_required": [
                "two ordered pairs or a table with at least two points",
                "clear x-values and y-values",
            ],
            "procedure": [
                "Identify two points or two rows from the representation.",
                "Find the change in y between the two points.",
                "Find the change in x between the same two points.",
                "Divide change in y by change in x and simplify if appropriate.",
                "Check that the direction of movement was not reversed.",
            ],
            "common_errors": [
                {
                    "label": "Axis confusion",
                    "description": "Student reverses x- and y-change when computing slope.",
                    "signal": "axis_confusion",
                },
                {
                    "label": "Simple average used",
                    "description": "Student averages values instead of comparing rates of change.",
                    "signal": "simple_average_used",
                },
            ],
            "failure_signal_mappings": [
                {
                    "signal": "axis_confusion",
                    "review_note": "Use only when x/y movement is reversed.",
                },
                {
                    "signal": "simple_average_used",
                    "review_note": "Use only when rate is replaced by an average.",
                },
            ],
        }
    if "VARIABLE" in skill_key or "EQUATION" in skill_key:
        return {
            "formula": "inverse operations preserve equality",
            "given_required": [
                "a linear equation with one variable",
                "visible constants and coefficients",
            ],
            "procedure": [
                "Locate the variable term and the constants in the equation.",
                "Use inverse operations to move constants away from the variable term.",
                "If needed, divide or multiply to isolate the variable.",
                "Apply each operation to both sides of the equation.",
                "Substitute the result back into the original equation to check it.",
            ],
            "common_errors": [
                {
                    "label": "Sign or placement error",
                    "description": "Student changes only one side or applies the inverse operation with the wrong sign.",
                    "signal": "sign_or_placement_error",
                },
                {
                    "label": "Unclassified procedural gap",
                    "description": "Student response requires human review because the error does not fit a canonical signal.",
                    "signal": "unclassified",
                },
            ],
            "failure_signal_mappings": [
                {
                    "signal": "sign_or_placement_error",
                    "review_note": "Use only for sign, side, or inverse-operation placement mistakes.",
                },
                {
                    "signal": "unclassified",
                    "review_note": "Use when the scaffold cannot confidently map the error.",
                },
            ],
        }
    return {
        "formula": "review_required",
        "given_required": ["human reviewer must confirm required givens"],
        "procedure": [
            "Read the problem and identify the target micro-skill.",
            "Select the relevant given information.",
            "Apply the reviewer-approved procedure for the micro-skill.",
            "Check that the answer type matches the prompt.",
        ],
        "common_errors": [
            {
                "label": "Unclassified procedural gap",
                "description": "Human reviewer must classify likely errors for this scaffold.",
                "signal": "unclassified",
            }
        ],
        "failure_signal_mappings": [
            {
                "signal": "unclassified",
                "review_note": "Placeholder signal until a reviewer classifies the error pattern.",
            }
        ],
    }


def _procedure_steps(*, procedure_id: str, procedure: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "step_index": index,
            "step_id": f"{procedure_id}_STEP_{index:02d}",
            "title": f"Step {index}",
            "instruction": instruction,
            "student_visible": False,
        }
        for index, instruction in enumerate(procedure, start=1)
    ]


def _topic_for_skill(
    skill: dict[str, Any],
    topics_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return topics_by_id.get(skill.get("parent_topic_candidate_id", ""), {})


def _base_validation() -> dict[str, Any]:
    return {
        "human_review_required": True,
        "worked_example_checked": False,
        "student_visible": False,
        "live_deployable": False,
        "canonical_approval": False,
    }


def _procedure_validation() -> dict[str, Any]:
    return {
        "solvable_by_procedure": False,
        "worked_example_checked": False,
        "human_review_required": True,
        "known_gaps": [],
        "student_visible": False,
        "live_deployable": False,
        "canonical_approval": False,
    }


def _procedure_scaffold(
    *,
    intake_id: str,
    index: int,
    subject_code: str,
    skill: dict[str, Any],
    topic: dict[str, Any],
    intake_record: dict[str, Any],
) -> dict[str, Any]:
    topic_code = _topic_code(topic)
    subtopic_code = _subtopic_code(topic_code)
    micro_skill = _slug(skill.get("micro_skill_name"), f"MICRO_SKILL_{index:03d}")
    micro_skill_name = skill.get("micro_skill_name", "Review required")
    procedure_id = f"PROC_{intake_id}_{index:03d}"
    guidance = _procedure_guidance(micro_skill_name)
    procedure = guidance["procedure"]
    failure_signal_mappings = guidance["failure_signal_mappings"]
    for mapping in failure_signal_mappings:
        assert mapping["signal"] in CANONICAL_FAILURE_SIGNALS
    return {
        "schema_version": "ACEF_PROCEDURE_v0_1",
        "artifact_type": "procedure",
        "status": "human_review_required",
        "procedure_id": procedure_id,
        "subject_code": subject_code,
        "topic_code": topic_code,
        "subtopic_code": subtopic_code,
        "micro_skill": micro_skill,
        "micro_skill_name": micro_skill_name,
        "source_refs": _source_refs(skill, intake_record),
        "concept": skill.get(
            "micro_skill_description",
            "Human reviewer must confirm concept statement.",
        ),
        "formula": guidance["formula"],
        "given_required": guidance["given_required"],
        "procedure": procedure,
        "procedure_steps": _procedure_steps(procedure_id=procedure_id, procedure=procedure),
        "worked_example": {
            "status": "human_review_required",
            "prompt": "Human reviewer must approve or author a worked example.",
            "steps": [],
            "answer": None,
        },
        "common_errors": guidance["common_errors"],
        "failure_signal_mappings": failure_signal_mappings,
        "diagnostic_signal_annotations": [
            "Rich diagnostic labels are review annotations only and are not live routing labels.",
            "Failure signal mappings use only canonical live values.",
        ],
        "generation_invariants": [
            "The problem must target the same micro-skill.",
            "The solution must be reachable by the listed procedure steps.",
            "Generated variants must preserve the same answer type.",
            "Generated variants must remain appropriate for the detected course level.",
        ],
        "author_notes": [
            "Procedure scaffold generated from synthetic demo material.",
            "Human review is required before any canonical or active use.",
        ],
        "review_notes": [
            "Confirm concept, formula, givens, steps, worked example, and failure mappings.",
        ],
        "validation": _procedure_validation(),
    }


def _question_payload(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "prompt": item.get("prompt"),
        "source_item_id": item.get("item_id"),
        "rights_status": item.get("rights_status", "generated_demo"),
    }


def _question_scaffold(
    *,
    intake_id: str,
    index: int,
    item: dict[str, Any],
    skill_by_id: dict[str, dict[str, Any]],
    topics_by_id: dict[str, dict[str, Any]],
    procedure_by_skill_id: dict[str, str],
    subject_code: str,
) -> dict[str, Any]:
    skill_ids = item.get("target_micro_skill_candidate_ids") or [item.get("target_micro_skill_candidate_id")]
    skill_id = next((candidate for candidate in skill_ids if candidate), None)
    skill = skill_by_id.get(skill_id or "", {})
    topic = _topic_for_skill(skill, topics_by_id)
    topic_code = _slug(topic.get("topic_name"), "TOPIC_REVIEW_REQUIRED")
    micro_skill = _slug(skill.get("micro_skill_name"), "MICRO_SKILL_REVIEW_REQUIRED")
    procedure_id = procedure_by_skill_id.get(skill_id or "", "PROCEDURE_REVIEW_REQUIRED")
    generation_family = f"GENFAM_{intake_id}_{index:03d}"
    failure_signals = ["unclassified"]
    assert set(failure_signals).issubset(CANONICAL_FAILURE_SIGNALS)
    return {
        "schema_version": "ACEF_QUESTION_v0_1",
        "artifact_type": "canonical_seed_question",
        "status": "human_review_required",
        "question_id": f"Q_{intake_id}_{index:03d}",
        "source_ref": item.get("item_id"),
        "classification": {
            "subject_code": subject_code,
            "topic_code": topic_code,
            "subtopic_code": "SUBTOPIC_REVIEW_REQUIRED",
            "micro_skill": micro_skill,
            "procedure_id": procedure_id,
            "difficulty_level": item.get("difficulty", "review_required"),
            "question_type": item.get("question_type", "short_response"),
            "answer_type": item.get("answer_type", "text"),
            "attempt_type_default": "single_attempt",
            "is_active": False,
        },
        "question_payload": _question_payload(item),
        "answer": item.get("answer"),
        "solution": item.get("solution_summary"),
        "procedure_step_refs": [],
        "feedback_step_refs": [],
        "failure_signals": failure_signals,
        "diagnostic_signal_annotations": [
            "Generated demo question requires human review before any use."
        ],
        "generation_family": generation_family,
        "non_live_status": {
            "student_visible": False,
            "live_deployable": False,
            "exposure_status": "not_exposed",
            "activation_performed": False,
        },
        "validation": _base_validation(),
    }


def _generation_family_scaffold(
    *,
    intake_id: str,
    index: int,
    question: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "ACEF_GENERATION_FAMILY_v0_1",
        "artifact_type": "generation_family",
        "status": "human_review_required",
        "generation_family_id": question["generation_family"],
        "seed_question_id": question["question_id"],
        "allowed_failure_signals": sorted(CANONICAL_FAILURE_SIGNALS),
        "generation_policy": "review_before_commit",
        "student_visible": False,
        "live_deployable": False,
        "human_review_required": True,
        "review_notes": [
            f"Generation family scaffold {index} for {intake_id}; not active content."
        ],
    }


def _validation_scaffold(
    *,
    intake_id: str,
    validation_report: dict[str, Any],
    procedure_count: int,
    question_count: int,
) -> dict[str, Any]:
    return {
        "schema_version": "ACEF_VALIDATION_v0_1",
        "artifact_type": "validation_report",
        "status": "human_review_required",
        "intake_id": intake_id,
        "compiler_validation_result": validation_report.get("overall_result"),
        "procedure_scaffold_count": procedure_count,
        "question_scaffold_count": question_count,
        "known_gaps": [
            "textbook_extraction_not_implemented",
            "pdf_docx_not_supported",
            "procedure_review_required",
            "question_review_required",
        ],
        "promotion_recommendation": "review_before_commit",
        "db_contact": False,
        "operational_alpha_contact": False,
        "human_review_required": True,
        "student_visible": False,
        "live_deployable": False,
    }


def write_acef_scaffolds(*, run_dir: Path, staging_dirs: dict[str, Path], intake_id: str) -> dict[str, Path]:
    source_interpretation = _load(run_dir, "source_interpretation.json")
    intake_record = _load(run_dir, "intake_record.json") if (run_dir / "intake_record.json").exists() else {}
    topics = _load(run_dir, "topic_candidates.json").get("topic_candidates", [])
    skills = _load(run_dir, "micro_skill_candidates.json").get("micro_skill_candidates", [])
    practice_items = _load(run_dir, "practice_module_package.json").get("practice_sequence", [])
    assessment_items = _load(run_dir, "practice_assessment_package.json").get("assessment_items", [])
    validation_report = _load(run_dir, "validation_report.json")
    content_gaps = _load(run_dir, "content_gaps.json").get("content_gaps", [])

    subject_code = source_interpretation.get("detected_subject", "SUBJECT_REVIEW_REQUIRED")
    topics_by_id = {topic["candidate_id"]: topic for topic in topics}
    skill_by_id = {skill["candidate_id"]: skill for skill in skills}

    procedures = [
        _procedure_scaffold(
            intake_id=intake_id,
            index=index,
            subject_code=subject_code,
            skill=skill,
            topic=_topic_for_skill(skill, topics_by_id),
            intake_record=intake_record,
        )
        for index, skill in enumerate(skills, start=1)
    ]
    procedure_by_skill_id = {
        skill["candidate_id"]: procedure["procedure_id"]
        for skill, procedure in zip(skills, procedures)
    }

    raw_question_items = assessment_items or practice_items
    questions = [
        _question_scaffold(
            intake_id=intake_id,
            index=index,
            item=item,
            skill_by_id=skill_by_id,
            topics_by_id=topics_by_id,
            procedure_by_skill_id=procedure_by_skill_id,
            subject_code=subject_code,
        )
        for index, item in enumerate(raw_question_items, start=1)
    ]
    generation_families = [
        _generation_family_scaffold(intake_id=intake_id, index=index, question=question)
        for index, question in enumerate(questions, start=1)
    ]
    validation = _validation_scaffold(
        intake_id=intake_id,
        validation_report=validation_report,
        procedure_count=len(procedures),
        question_count=len(questions),
    )

    first_topic = topics[0] if topics else {}
    first_skill = skills[0] if skills else {}
    package = {
        "schema_version": "ACEF_PACKAGE_v0_1",
        "package_id": f"PKG_{intake_id}",
        "status": "human_review_required",
        "subject_code": subject_code,
        "topic_code": _slug(first_topic.get("topic_name"), "TOPIC_REVIEW_REQUIRED"),
        "subtopic_code": "SUBTOPIC_REVIEW_REQUIRED",
        "micro_skill": _slug(first_skill.get("micro_skill_name"), "MICRO_SKILL_REVIEW_REQUIRED"),
        "artifacts": {
            "procedures": [procedure["procedure_id"] for procedure in procedures],
            "procedure_scaffold_paths": [
                f"compiler_output/math/procedures/{intake_id}_{procedure['topic_code']}_{procedure['micro_skill'].lower()}.json"
                for procedure in procedures
            ],
            "questions": [question["question_id"] for question in questions],
            "generation_families": [
                family["generation_family_id"] for family in generation_families
            ],
            "validation_reports": [f"ACEF_VALIDATION_{intake_id}"],
        },
        "compiler_summary": {
            "source_materials_used": ["intake_record.json", "source_document.json"],
            "human_review_required": True,
            "known_gaps": [
                gap.get("gap_type", "review_required") for gap in content_gaps
            ]
            + [
                "textbook_extraction_not_implemented",
                "pdf_docx_not_supported",
                "procedure_review_required",
                "question_review_required",
            ],
            "promotion_recommendation": "review_before_commit",
        },
    }

    outputs: dict[str, Any] = {
        "acef_package_scaffold.json": package,
        "acef_procedure_scaffolds.json": {
            "schema_version": "ACEF_PROCEDURE_SCAFFOLD_COLLECTION_v0_1",
            "status": "human_review_required",
            "human_review_required": True,
            "procedures": procedures,
        },
        "acef_question_scaffolds.json": {
            "schema_version": "ACEF_QUESTION_SCAFFOLDS_v0_1",
            "status": "human_review_required",
            "human_review_required": True,
            "questions": questions,
        },
        "acef_generation_family_scaffolds.json": {
            "schema_version": "ACEF_GENERATION_FAMILY_SCAFFOLDS_v0_1",
            "status": "human_review_required",
            "human_review_required": True,
            "generation_families": generation_families,
        },
        "acef_validation_scaffold.json": validation,
    }
    output_paths: dict[str, Path] = {}
    for filename, payload in outputs.items():
        path = run_dir / filename
        write_json(path, payload)
        output_paths[filename] = path

    shutil.copy2(
        output_paths["acef_package_scaffold.json"],
        staging_dirs["packages"] / f"{intake_id}_acef_package_scaffold.json",
    )
    legacy_collection = staging_dirs["procedures"] / f"{intake_id}_acef_procedure_scaffolds.json"
    if legacy_collection.exists():
        legacy_collection.unlink()
    for procedure in procedures:
        staging_path = (
            staging_dirs["procedures"]
            / f"{intake_id}_{procedure['topic_code']}_{procedure['micro_skill'].lower()}.json"
        )
        write_json(staging_path, procedure)
    return output_paths
