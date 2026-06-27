"""Performance tracking package builder for the Course Compiler Demo."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load(output_dir: Path, filename: str) -> dict[str, Any]:
    return json.loads((output_dir / filename).read_text(encoding="utf-8"))


def build_performance_tracking_package(output_dir: Path) -> dict[str, Any]:
    source_document = _load(output_dir, "source_document.json")
    source_interpretation = _load(output_dir, "source_interpretation.json")
    tracking_targets = _load(output_dir, "performance_tracking_targets.json").get(
        "performance_tracking_targets", []
    )
    practice_module = _load(output_dir, "practice_module_package.json")
    assessment = _load(output_dir, "practice_assessment_package.json")
    topics = _load(output_dir, "topic_candidates.json").get("topic_candidates", [])
    skills = _load(output_dir, "micro_skill_candidates.json").get("micro_skill_candidates", [])
    content_gaps = _load(output_dir, "content_gaps.json").get("content_gaps", [])

    return {
        "package_id": "PERF_DEMO_001",
        "status": "demo_unverified",
        "tracking_title": "Demo Algebra Performance Tracking Preview",
        "tracking_type": "practice_module",
        "source_context": {
            "source_id": source_document["source_id"],
            "source_title": source_document["source_title"],
            "detected_subject": source_interpretation["detected_subject"],
            "detected_course_level": source_interpretation["detected_course_level"],
            "rights_status": source_document["rights_status"],
            "privacy_status": source_document["privacy_status"],
        },
        "tracked_curriculum": {
            "topics": topics,
            "micro_skills": skills,
            "tracking_targets": tracking_targets,
        },
        "linked_packages": {
            "practice_module_package_ids": [practice_module["package_id"]],
            "practice_assessment_package_ids": [assessment["package_id"]],
        },
        "attempt_record_schema": {
            "attempt_id": "string",
            "item_id": "string",
            "package_id": "string",
            "micro_skill_candidate_id": "string",
            "is_correct": "boolean",
            "attempted_at": "ISO-8601 timestamp",
            "status": "demo_unverified",
        },
        "metric_definitions": {
            "attempt_count": "Total demo attempts recorded.",
            "correct_count": "Total correct demo attempts.",
            "accuracy": "correct_count divided by attempt_count.",
            "accuracy_by_topic": "Accuracy grouped by topic candidate.",
            "accuracy_by_micro_skill": "Accuracy grouped by micro-skill candidate.",
            "current_streak": "Current consecutive correct demo attempts.",
            "best_streak": "Best consecutive correct demo attempts.",
            "readiness_status": "Demo readiness label from accuracy and streak thresholds.",
            "weakness_flags": "Micro-skills below weakness thresholds.",
            "recommended_next_action": "Suggested non-live demo next action.",
        },
        "readiness_model": {
            "model_type": "demo_streak_and_accuracy",
            "not_ready": "accuracy < 0.70",
            "approaching": "accuracy >= 0.70 and accuracy < 0.80",
            "ready_demo": "accuracy >= 0.80 or correct_streak >= 3",
            "disclaimer": "Demo readiness does not update operational Alpha readiness or mastery.",
            "status": "demo_unverified",
        },
        "weakness_detection_model": {
            "rule": "If micro-skill accuracy is below 70%, flag weakness and recommend targeted practice.",
            "threshold": 0.70,
            "status": "demo_unverified",
        },
        "performance_report_model": {
            "sections": [
                "overall_accuracy",
                "accuracy_by_topic",
                "accuracy_by_micro_skill",
                "readiness_status",
                "recommended_next_action",
            ],
            "status": "demo_unverified",
        },
        "recommended_next_action_model": {
            "not_attempted": "Start practice module.",
            "not_ready": "Assign targeted practice.",
            "approaching": "Repeat missed micro-skills, then reassess.",
            "ready_demo": "Proceed to manual review or next demo module.",
            "status": "demo_unverified",
        },
        "demo_attempts": [],
        "computed_demo_results": {
            "overall_accuracy": None,
            "readiness_status": "not_attempted",
            "recommended_next_action": "Start practice module.",
            "status": "demo_unverified",
        },
        "content_gaps": content_gaps,
        "limitations": [
            "No real student data is used.",
            "Computed results are placeholder demo results only.",
            "Does not update operational Alpha readiness or mastery.",
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
