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


def _base_validation(
    *,
    fully_classified: bool,
    procedure_exists: bool,
    diagram_required: bool,
    known_gaps: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "fully_classified": fully_classified,
        "procedure_exists": procedure_exists,
        "solvable_by_procedure": False,
        "answer_verified": False,
        "diagram_status": "not_reviewed" if diagram_required else "not_required",
        "human_review_required": True,
        "known_gaps": known_gaps or [],
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


def _question_source_ref(item: dict[str, Any], intake_record: dict[str, Any]) -> dict[str, Any]:
    source_name = intake_record.get("original_filename") or "synthetic_demo_source"
    return {
        "source_type": "compiler_generated_from_demo",
        "source_name": source_name,
        "source_item_id": item.get("item_id"),
        "rights_status": item.get("rights_status", "generated_demo"),
    }


def _image_ref(item: dict[str, Any], micro_skill: str) -> dict[str, Any]:
    existing_ref = item.get("image_ref")
    if isinstance(existing_ref, dict) and "value" in existing_ref:
        return {
            "type": existing_ref.get("type", "provided"),
            "value": existing_ref.get("value"),
            "alt_text": existing_ref.get(
                "alt_text",
                "Diagram or visual reference placeholder for human review.",
            ),
        }
    if bool(item.get("diagram_required", False)):
        return {
            "type": "generated_later",
            "value": None,
            "alt_text": f"Generated-later visual placeholder for the micro-skill: {micro_skill.lower()}.",
        }
    return {
        "type": "not_required",
        "value": None,
        "alt_text": "No diagram required for this scaffold-level generated demo question.",
    }


def _question_payload(
    item: dict[str, Any],
    intake_record: dict[str, Any],
    micro_skill: str,
) -> dict[str, Any]:
    return {
        "prompt": item.get("prompt"),
        "given": item.get("given", []),
        "ask": item.get("ask") or item.get("prompt"),
        "diagram_required": bool(item.get("diagram_required", False)),
        "image_ref": _image_ref(item, micro_skill),
        "source_item_id": item.get("item_id"),
        "source_type": "compiler_generated_from_demo",
        "source_name": intake_record.get("original_filename") or "synthetic_demo_source",
        "rights_status": item.get("rights_status", "generated_demo"),
    }


def _answer_block(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "verified_answer": item.get("answer"),
        "unit": item.get("unit"),
        "tolerance": item.get("tolerance"),
        "answer_parts": item.get("answer_parts", []),
        "grading_notes": [
            "Answer is carried from demo source generation and requires human verification before use."
        ],
    }


def _procedure_step_refs(procedure: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not procedure:
        return []
    return [
        {
            "procedure_step_id": step.get("step_id"),
            "step_index": step.get("step_index"),
        }
        for step in procedure.get("procedure_steps", [])
    ]


def _solution_block(
    *,
    item: dict[str, Any],
    procedure_id: str,
    procedure: dict[str, Any] | None,
) -> dict[str, Any]:
    procedure_steps = _procedure_step_refs(procedure)
    summary = item.get("solution_summary") or "Human reviewer must author or approve the solution."
    solution_steps = []
    if procedure_steps:
        for ref in procedure_steps:
            solution_steps.append(
                {
                    "step_index": ref["step_index"],
                    "procedure_step_id": ref["procedure_step_id"],
                    "explanation": summary,
                    "human_review_required": True,
                }
            )
    else:
        solution_steps.append(
            {
                "step_index": 1,
                "procedure_step_id": None,
                "explanation": summary,
                "human_review_required": True,
            }
        )
    return {
        "procedure_id": procedure_id,
        "solution_steps": solution_steps,
        "final_answer": item.get("answer"),
    }


def _canonical_failure_signals(procedure: dict[str, Any] | None) -> list[str]:
    if not procedure:
        return ["unclassified"]
    signals = [
        mapping.get("signal")
        for mapping in procedure.get("failure_signal_mappings", [])
        if mapping.get("signal") in CANONICAL_FAILURE_SIGNALS
    ]
    return signals or ["unclassified"]


def _feedback_step_refs(
    *,
    procedure: dict[str, Any] | None,
    failure_signals: list[str],
) -> list[dict[str, Any]]:
    step_refs = _procedure_step_refs(procedure)
    fallback_ref = step_refs[0] if step_refs else {"procedure_step_id": None, "step_index": None}
    return [
        {
            "failure_signal": signal,
            "procedure_step_id": fallback_ref["procedure_step_id"],
            "step_index": fallback_ref["step_index"],
            "feedback": "Human reviewer must approve feedback before this scaffold can be used.",
        }
        for signal in failure_signals
    ]


def _generation_family_block(
    *,
    intake_id: str,
    index: int,
    question_id: str,
    classification: dict[str, Any],
) -> dict[str, Any]:
    return {
        "family_id": f"GENFAM_{intake_id}_{index:03d}",
        "canonical_seed_id": question_id,
        "parameterization": {
            "variable_fields": [
                "prompt",
                "given",
                "ask",
                "verified_answer",
            ],
            "constraints": [
                "Generated variants must remain non-live until human review.",
                "Generated variants must preserve the same micro-skill and procedure link.",
            ],
            "invariants": {
                "micro_skill": classification["micro_skill"],
                "procedure_id": classification["procedure_id"],
                "answer_type": classification["answer_type"],
                "question_type": classification["question_type"],
            },
        },
        "difficulty_range": {
            "min": classification["difficulty_level"],
            "max": classification["difficulty_level"],
        },
    }


def _question_scaffold(
    *,
    intake_id: str,
    index: int,
    item: dict[str, Any],
    skill_by_id: dict[str, dict[str, Any]],
    topics_by_id: dict[str, dict[str, Any]],
    procedure_by_skill_id: dict[str, dict[str, Any]],
    subject_code: str,
    intake_record: dict[str, Any],
) -> dict[str, Any]:
    skill_ids = item.get("target_micro_skill_candidate_ids") or [item.get("target_micro_skill_candidate_id")]
    skill_id = next((candidate for candidate in skill_ids if candidate), None)
    skill = skill_by_id.get(skill_id or "", {})
    topic = _topic_for_skill(skill, topics_by_id)
    topic_code = _topic_code(topic)
    subtopic_code = _subtopic_code(topic_code)
    micro_skill = _slug(skill.get("micro_skill_name"), "MICRO_SKILL_REVIEW_REQUIRED")
    procedure = procedure_by_skill_id.get(skill_id or "")
    procedure_id = procedure.get("procedure_id", "PROCEDURE_REVIEW_REQUIRED") if procedure else "PROCEDURE_REVIEW_REQUIRED"
    question_id = f"Q_{intake_id}_{index:03d}"
    classification = {
        "subject_code": subject_code,
        "topic_code": topic_code,
        "subtopic_code": subtopic_code,
        "micro_skill": micro_skill,
        "procedure_id": procedure_id,
        "difficulty_level": item.get("difficulty", "review_required"),
        "question_type": item.get("question_type", "short_response"),
        "answer_type": item.get("answer_type", "text"),
        "attempt_type_default": "module_practice",
        "is_active": False,
    }
    failure_signals = _canonical_failure_signals(procedure)
    assert set(failure_signals).issubset(CANONICAL_FAILURE_SIGNALS)
    diagram_required = bool(item.get("diagram_required", False))
    known_gaps = [
        "answer_not_machine_verified",
        "solution_not_human_reviewed",
        "question_not_canonical_or_active",
    ]
    if not procedure:
        known_gaps.append("procedure_match_review_required")
    return {
        "schema_version": "ACEF_QUESTION_v0_1",
        "artifact_type": "canonical_seed_question",
        "status": "human_review_required",
        "question_id": question_id,
        "source_ref": _question_source_ref(item, intake_record),
        "classification": classification,
        "question_payload": _question_payload(item, intake_record, micro_skill),
        "answer": _answer_block(item),
        "solution": _solution_block(item=item, procedure_id=procedure_id, procedure=procedure),
        "procedure_step_refs": _procedure_step_refs(procedure),
        "feedback_step_refs": _feedback_step_refs(procedure=procedure, failure_signals=failure_signals),
        "failure_signals": failure_signals,
        "diagnostic_signal_annotations": [
            "Generated demo question requires human review before any use.",
            "Rich diagnostic labels remain annotations; live failure signals use only canonical values.",
        ],
        "generation_family": _generation_family_block(
            intake_id=intake_id,
            index=index,
            question_id=question_id,
            classification=classification,
        ),
        "non_live_status": {
            "student_visible": False,
            "live_deployable": False,
            "exposure_status": "not_exposed",
            "activation_performed": False,
        },
        "validation": _base_validation(
            fully_classified=bool(skill and topic and procedure),
            procedure_exists=bool(procedure),
            diagram_required=diagram_required,
            known_gaps=known_gaps,
        ),
    }


def _generation_family_scaffold(
    *,
    intake_id: str,
    index: int,
    question: dict[str, Any],
) -> dict[str, Any]:
    family = question["generation_family"]
    family_id = family["family_id"] if isinstance(family, dict) else family
    classification = question["classification"]
    parameterization = family.get("parameterization", {}) if isinstance(family, dict) else {}
    difficulty = classification.get("difficulty_level", 2)
    if isinstance(difficulty, (int, float)):
        difficulty_range = [max(1, int(difficulty) - 1), min(4, int(difficulty) + 1)]
    else:
        difficulty_range = [1, 3]
    source_ref = question.get("source_ref")
    source_refs = [source_ref] if isinstance(source_ref, dict) else []
    procedure_id = classification.get("procedure_id", "PROCEDURE_REVIEW_REQUIRED")
    seed_question_id = question["question_id"]
    question_type = classification.get("question_type", "short_response")
    answer_type = classification.get("answer_type", "text")
    variable_fields = parameterization.get(
        "variable_fields",
        [
            "question_payload.prompt",
            "question_payload.given",
            "question_payload.ask",
            "answer.verified_answer",
        ],
    )
    constraints = [
        "Generated variants must preserve the same micro-skill.",
        "Generated variants must preserve the same procedure_id.",
        "Generated variants must preserve the same answer_type.",
        "Generated variants must remain appropriate for the detected course level.",
        "Generated variants must be solvable by the linked procedure after human review.",
    ]
    invariants = [
        "same subject_code",
        "same topic_code",
        "same subtopic_code",
        "same micro_skill",
        "same procedure_id",
        "same question_type",
        "same answer_type",
        "same feedback signal policy",
    ]
    procedure_exists = procedure_id != "PROCEDURE_REVIEW_REQUIRED"
    return {
        "schema_version": "ACEF_GENERATION_FAMILY_v0_1",
        "artifact_type": "generation_family",
        "status": "human_review_required",
        "family_id": family_id,
        "family_name": f"{classification.get('micro_skill', 'review_required').lower()} generation family",
        "subject_code": classification.get("subject_code", "SUBJECT_REVIEW_REQUIRED"),
        "topic_code": classification.get("topic_code", "TOPIC_REVIEW_REQUIRED"),
        "subtopic_code": classification.get("subtopic_code", "SUBTOPIC_REVIEW_REQUIRED"),
        "micro_skill": classification.get("micro_skill", "MICRO_SKILL_REVIEW_REQUIRED"),
        "micro_skill_name": classification.get("micro_skill", "MICRO_SKILL_REVIEW_REQUIRED").replace("_", " ").title(),
        "procedure_id": procedure_id,
        "canonical_seed_ids": [seed_question_id],
        "source_question_ids": [seed_question_id],
        "parameterization": {
            "variable_fields": variable_fields,
            "constraints": constraints,
            "invariants": invariants,
        },
        "difficulty_range": difficulty_range,
        "invariants": invariants,
        "constraints": constraints,
        "linked_artifacts": {
            "procedure_id": procedure_id,
            "seed_question_ids": [seed_question_id],
            "source_question_ids": [seed_question_id],
            "question_type": question_type,
            "answer_type": answer_type,
        },
        "source_refs": source_refs,
        "allowed_failure_signals": sorted(CANONICAL_FAILURE_SIGNALS),
        "generation_policy": "review_before_commit",
        "non_live_status": {
            "student_visible": False,
            "live_deployable": False,
            "exposure_status": "not_exposed",
            "activation_performed": False,
        },
        "validation": {
            "human_review_required": True,
            "seed_questions_exist": True,
            "procedure_exists": procedure_exists,
            "parameterization_complete": bool(variable_fields and constraints and invariants),
            "variants_generated": False,
            "variants_verified": False,
            "ready_for_generation": False,
            "known_gaps": [
                "generation_variants_not_generated",
                "generation_variants_not_verified",
                "human_review_required_before_generation",
            ]
            + ([] if procedure_exists else ["procedure_link_requires_review"]),
        },
        "created_by": "course_compiler_demo.acef_mapper",
        "notes": [
            f"Generation family scaffold {index} for {intake_id}; not active content.",
            "Subject → Topic → Subtopic → Micro-skill → Procedure → Question linkage is scaffold-level.",
            "Human review is required before variant generation or canonical use.",
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
        skill["candidate_id"]: procedure
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
            intake_record=intake_record,
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
    first_topic_code = _topic_code(first_topic)
    package = {
        "schema_version": "ACEF_PACKAGE_v0_1",
        "package_id": f"PKG_{intake_id}",
        "status": "human_review_required",
        "subject_code": subject_code,
        "topic_code": first_topic_code,
        "subtopic_code": _subtopic_code(first_topic_code),
        "micro_skill": _slug(first_skill.get("micro_skill_name"), "MICRO_SKILL_REVIEW_REQUIRED"),
        "artifacts": {
            "procedures": [procedure["procedure_id"] for procedure in procedures],
            "procedure_scaffold_paths": [
                f"compiler_output/math/procedures/{intake_id}_{procedure['topic_code']}_{procedure['micro_skill'].lower()}.json"
                for procedure in procedures
            ],
            "questions": [question["question_id"] for question in questions],
            "question_scaffold_paths": [
                f"compiler_output/math/questions/{intake_id}_{question['classification']['topic_code']}_{question['classification']['micro_skill'].lower()}_Q{index:03d}.json"
                for index, question in enumerate(questions, start=1)
            ],
            "generation_families": [
                family["family_id"] for family in generation_families
            ],
            "generation_family_scaffold_paths": [
                f"compiler_output/math/generation_families/{intake_id}_{family['topic_code']}_{family['micro_skill'].lower()}_GEN{index:03d}.json"
                for index, family in enumerate(generation_families, start=1)
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
            "schema_version": "ACEF_QUESTION_SCAFFOLD_COLLECTION_v0_1",
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
    legacy_question_collection = staging_dirs["questions"] / f"{intake_id}_acef_question_scaffolds.json"
    if legacy_question_collection.exists():
        legacy_question_collection.unlink()
    for index, question in enumerate(questions, start=1):
        classification = question["classification"]
        staging_path = (
            staging_dirs["questions"]
            / f"{intake_id}_{classification['topic_code']}_{classification['micro_skill'].lower()}_Q{index:03d}.json"
        )
        write_json(staging_path, question)
    legacy_generation_collection = staging_dirs["generation_families"] / f"{intake_id}_acef_generation_family_scaffolds.json"
    if legacy_generation_collection.exists():
        legacy_generation_collection.unlink()
    for index, family in enumerate(generation_families, start=1):
        staging_path = (
            staging_dirs["generation_families"]
            / f"{intake_id}_{family['topic_code']}_{family['micro_skill'].lower()}_GEN{index:03d}.json"
        )
        write_json(staging_path, family)
    return output_paths
