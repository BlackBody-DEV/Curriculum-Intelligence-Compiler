"""Practice assessment package builder for the Course Compiler Demo."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load(output_dir: Path, filename: str) -> dict[str, Any]:
    return json.loads((output_dir / filename).read_text(encoding="utf-8"))


def _items(skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prompts = {
        "Isolate the Variable": ("Solve for x: x - 6 = 13.", "x = 19", "Add 6 to both sides."),
        "Combine Like Terms": ("Simplify: 8a - 3a + 4.", "5a + 4", "Combine 8a and -3a."),
        "Compute Slope": (
            "Find the slope through (1, 4) and (5, 12).",
            "2",
            "Compute (12 - 4) / (5 - 1) = 8 / 4.",
        ),
        "Identify Y-Intercept": (
            "What is the y-intercept of y = 4x - 7?",
            "-7",
            "The y-intercept is b in y = mx + b.",
        ),
        "Solve a Two-Step Equation": (
            "Solve for x: 3x + 2 = 17.",
            "x = 5",
            "Subtract 2, then divide by 3.",
        ),
        "Graph a Line from an Equation": (
            "Which point is on y = x + 2?",
            "(0, 2)",
            "Substitute x = 0 to get y = 2.",
        ),
    }
    result: list[dict[str, Any]] = []
    for skill in skills:
        prompt = prompts.get(skill["micro_skill_name"])
        if prompt is None:
            continue
        result.append(
            {
                "item_id": f"PA_ITEM_{len(result) + 1:03d}",
                "item_type": "generated_demo_question",
                "prompt": prompt[0],
                "answer": prompt[1],
                "solution_summary": prompt[2],
                "target_topic_candidate_id": skill["parent_topic_candidate_id"],
                "target_micro_skill_candidate_ids": [skill["candidate_id"]],
                "difficulty": 2,
                "question_type": "short_response",
                "answer_type": "text",
                "points": 1,
                "estimated_time_seconds": 120,
                "rights_status": "generated_demo",
                "status": "demo_unverified",
            }
        )
    return result


def build_practice_assessment_package(output_dir: Path) -> dict[str, Any]:
    source_document = _load(output_dir, "source_document.json")
    source_interpretation = _load(output_dir, "source_interpretation.json")
    assessment_targets = _load(output_dir, "assessment_targets.json").get(
        "assessment_target_candidates", []
    )
    topics = _load(output_dir, "topic_candidates.json").get("topic_candidates", [])
    skills = _load(output_dir, "micro_skill_candidates.json").get("micro_skill_candidates", [])
    content_gaps = _load(output_dir, "content_gaps.json").get("content_gaps", [])
    target = assessment_targets[0] if assessment_targets else {}
    topic_ids = set(target.get("covered_topic_candidate_ids", [topic["candidate_id"] for topic in topics]))
    skill_ids = set(target.get("covered_micro_skill_candidate_ids", [skill["candidate_id"] for skill in skills]))
    covered_topics = [topic for topic in topics if topic["candidate_id"] in topic_ids]
    covered_skills = [skill for skill in skills if skill["candidate_id"] in skill_ids]

    return {
        "package_id": "PA_DEMO_001",
        "status": "demo_unverified",
        "assessment_title": "Demo Algebra Skills Checkpoint",
        "assessment_type": "checkpoint_assessment",
        "source_context": {
            "source_id": source_document["source_id"],
            "source_title": source_document["source_title"],
            "detected_subject": source_interpretation["detected_subject"],
            "detected_course_level": source_interpretation["detected_course_level"],
            "rights_status": source_document["rights_status"],
            "privacy_status": source_document["privacy_status"],
        },
        "target_goal": target.get(
            "target_goal", "Check readiness on extracted algebra skills before practice packaging."
        ),
        "covered_curriculum": {
            "topics": covered_topics,
            "micro_skills": covered_skills,
        },
        "assessment_blueprint": {
            "recommended_question_count": max(5, len(covered_skills)),
            "difficulty_distribution": target.get(
                "difficulty_distribution",
                {"introductory": 0.6, "intermediate": 0.4, "advanced": 0.0},
            ),
            "coverage_strategy": "one_or_more_items_per_detected_micro_skill",
        },
        "assessment_items": _items(covered_skills),
        "scoring_policy": {
            "scoring_type": "percent_correct",
            "passing_threshold": 0.80,
            "readiness_threshold": 0.80,
            "points_per_item": 1,
        },
        "weakness_detection_rules": [
            "If micro-skill accuracy is below 70%, recommend targeted practice."
        ],
        "performance_report_template": {
            "include_overall_accuracy": True,
            "include_accuracy_by_micro_skill": True,
            "include_next_actions": True,
            "status": "demo_unverified",
        },
        "recommended_next_actions": [
            "assign_practice_module",
            "repeat_assessment",
            "manual_review",
        ],
        "evidence_refs": sorted(
            {
                evidence_ref
                for skill in covered_skills
                for evidence_ref in skill.get("evidence_refs", [])
            }
        ),
        "content_gaps": content_gaps,
        "limitations": [
            "Generated demo assessment only; not reviewed for live grading.",
            "Does not update operational Alpha readiness or mastery.",
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
