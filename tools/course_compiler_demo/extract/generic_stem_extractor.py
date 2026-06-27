"""Generic STEM fallback extractor for future demo subjects."""

from __future__ import annotations

from typing import Any


def extract_generic_stem_candidates(*, source_id: str, subject: str, course_level: str) -> dict[str, Any]:
    return {
        "topic_candidates": [],
        "micro_skill_candidates": [],
        "source_evidence": [
            {
                "evidence_id": "EV_GENERIC_001",
                "source_id": source_id,
                "evidence_type": "extraction_rationale",
                "line_start": None,
                "line_end": None,
                "section_heading": None,
                "short_excerpt": f"No specialized extractor is implemented yet for {subject} / {course_level}.",
                "confidence": "medium",
            }
        ],
    }
