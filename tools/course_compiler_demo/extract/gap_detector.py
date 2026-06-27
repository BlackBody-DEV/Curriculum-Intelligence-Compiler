"""Content gap detection for demo extraction outputs."""

from __future__ import annotations

from typing import Any


def detect_content_gaps(
    *,
    topic_candidates: list[dict[str, Any]],
    micro_skill_candidates: list[dict[str, Any]],
    source_type: str,
) -> list[dict[str, Any]]:
    gaps = [
        {
            "gap_id": "GAP_001",
            "gap_type": "missing_reviewed_procedure",
            "description": "Detected skills do not yet have reviewed procedure content in the demo lane.",
            "recommended_action": "Create reviewed procedure candidates in a later package stage.",
            "confidence": "high",
            "status": "demo_unverified",
        },
        {
            "gap_id": "GAP_002",
            "gap_type": "missing_reviewed_question_bank",
            "description": "Questions are source-derived only; no reviewed question bank is attached.",
            "recommended_action": "Generate and review a demo question bank before live use.",
            "confidence": "high",
            "status": "demo_unverified",
        },
        {
            "gap_id": "GAP_003",
            "gap_type": "demo_only_content",
            "description": "All extracted content is local demo content and remains unverified.",
            "recommended_action": "Keep status demo_unverified until reviewed.",
            "confidence": "high",
            "status": "demo_unverified",
        },
    ]
    if source_type not in {"practice_test", "quiz_review", "midterm_review", "final_review"}:
        gaps.append(
            {
                "gap_id": "GAP_004",
                "gap_type": "thin_assessment_coverage",
                "description": "The source is not an assessment document, so assessment coverage is inferred.",
                "recommended_action": "Add assessment-specific source material in a later stage.",
                "confidence": "medium",
                "status": "demo_unverified",
            }
        )
    if len(micro_skill_candidates) < 5 or len(topic_candidates) < 3:
        gaps.append(
            {
                "gap_id": "GAP_005",
                "gap_type": "thin_practice_coverage",
                "description": "The demo source covers a small number of candidate topics and skills.",
                "recommended_action": "Use additional sources before broad practice generation.",
                "confidence": "medium",
                "status": "demo_unverified",
            }
        )
    return gaps
