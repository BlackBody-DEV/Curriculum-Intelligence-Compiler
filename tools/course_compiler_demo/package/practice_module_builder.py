"""Practice module package builder for the Course Compiler Demo."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load(output_dir: Path, filename: str) -> dict[str, Any]:
    return json.loads((output_dir / filename).read_text(encoding="utf-8"))


def _skill_by_name(skills: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    normalized = name.lower()
    for skill in skills:
        if skill.get("micro_skill_name", "").lower() == normalized:
            return skill
    return None


def _topic_lookup(topics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {topic["candidate_id"]: topic for topic in topics}


def _practice_item(
    *,
    item_id: str,
    prompt: str,
    answer: str,
    solution_summary: str,
    skill: dict[str, Any],
    difficulty: int,
) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "item_type": "generated_demo_question",
        "prompt": prompt,
        "answer": answer,
        "solution_summary": solution_summary,
        "target_micro_skill_candidate_id": skill["candidate_id"],
        "difficulty": difficulty,
        "estimated_time_seconds": 90,
        "rights_status": "generated_demo",
        "status": "demo_unverified",
    }


def _build_practice_sequence(skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    templates = [
        (
            "Isolate the Variable",
            "Solve for x: x + 9 = 14.",
            "x = 5",
            "Subtract 9 from both sides to isolate x.",
            1,
        ),
        (
            "Combine Like Terms",
            "Simplify: 4x + 3x - 2.",
            "7x - 2",
            "Combine the like x-terms: 4x + 3x = 7x.",
            1,
        ),
        (
            "Compute Slope",
            "Find the slope of the line through (2, 3) and (6, 11).",
            "2",
            "Use rise over run: (11 - 3) / (6 - 2) = 8 / 4 = 2.",
            2,
        ),
        (
            "Identify Y-Intercept",
            "Identify the y-intercept of y = -3x + 8.",
            "8",
            "In slope-intercept form y = mx + b, the y-intercept is b.",
            1,
        ),
        (
            "Solve a Two-Step Equation",
            "Solve for x: 5x - 4 = 21.",
            "x = 5",
            "Add 4 to both sides, then divide by 5.",
            2,
        ),
        (
            "Graph a Line from an Equation",
            "For y = 2x - 1, name one point on the line.",
            "(0, -1)",
            "Set x = 0 to find the y-intercept point.",
            2,
        ),
    ]
    for name, prompt, answer, summary, difficulty in templates:
        skill = _skill_by_name(skills, name)
        if skill is None:
            continue
        items.append(
            _practice_item(
                item_id=f"PM_ITEM_{len(items) + 1:03d}",
                prompt=prompt,
                answer=answer,
                solution_summary=summary,
                skill=skill,
                difficulty=difficulty,
            )
        )
    return items


def build_practice_module_package(output_dir: Path) -> dict[str, Any]:
    source_document = _load(output_dir, "source_document.json")
    source_interpretation = _load(output_dir, "source_interpretation.json")
    practice_targets = _load(output_dir, "practice_targets.json").get("practice_target_candidates", [])
    topics = _load(output_dir, "topic_candidates.json").get("topic_candidates", [])
    skills = _load(output_dir, "micro_skill_candidates.json").get("micro_skill_candidates", [])
    content_gaps = _load(output_dir, "content_gaps.json").get("content_gaps", [])
    topic_by_id = _topic_lookup(topics)

    target = practice_targets[0] if practice_targets else {}
    target_topic_ids = target.get("target_topic_candidate_ids", [topic["candidate_id"] for topic in topics])
    target_skill_ids = target.get(
        "target_micro_skill_candidate_ids", [skill["candidate_id"] for skill in skills]
    )
    target_topics = [topic_by_id[topic_id] for topic_id in target_topic_ids if topic_id in topic_by_id]
    target_skills = [skill for skill in skills if skill["candidate_id"] in target_skill_ids]

    package = {
        "package_id": "PM_DEMO_001",
        "status": "demo_unverified",
        "module_title": "Demo Algebra Skills Practice",
        "module_type": "skill_practice",
        "source_context": {
            "source_id": source_document["source_id"],
            "source_title": source_document["source_title"],
            "source_type": source_document["source_type"],
            "detected_subject": source_interpretation["detected_subject"],
            "detected_course_level": source_interpretation["detected_course_level"],
            "rights_status": source_document["rights_status"],
            "privacy_status": source_document["privacy_status"],
        },
        "target_curriculum": {
            "topics": target_topics,
            "micro_skills": target_skills,
        },
        "prerequisites": [
            "Basic arithmetic fluency",
            "Familiarity with variables and coordinate points",
        ],
        "practice_sequence": _build_practice_sequence(target_skills),
        "difficulty_plan": {
            "difficulty_scale": "1_to_5",
            "sequence_strategy": "warmup_to_target",
            "difficulty_sequence": [1, 1, 2, 2, 3],
        },
        "readiness_condition": "3 correct in a row in demo mode",
        "feedback_policy": {
            "policy_type": "basic",
            "show_solution_summary": True,
            "operational_alpha_updates": False,
        },
        "performance_metrics": [
            "attempt_count",
            "correct_count",
            "accuracy",
            "current_streak",
            "accuracy_by_micro_skill",
        ],
        "evidence_refs": sorted(
            {
                evidence_ref
                for skill in target_skills
                for evidence_ref in skill.get("evidence_refs", [])
            }
        ),
        "content_gaps": content_gaps,
        "limitations": [
            "Generated demo practice only; not reviewed for live instruction.",
            "Does not update operational Alpha readiness or mastery.",
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return package
