"""Extraction orchestration for the non-live Course Compiler Demo."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from align.canonical_matcher import match_candidates_to_demo_registry
from align.duplicate_detector import mark_duplicate_names
from align.subject_orientation import is_math_subject
from extract.gap_detector import detect_content_gaps
from extract.generic_stem_extractor import extract_generic_stem_candidates
from extract.math_extractor import extract_math_candidates


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _practice_targets(
    topic_candidates: list[dict[str, Any]],
    micro_skill_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not micro_skill_candidates:
        return []
    return [
        {
            "candidate_id": "PRACTICE_TARGET_001",
            "target_type": "student_practice_sequence",
            "target_name": "Algebra Line Skills Practice",
            "target_topic_candidate_ids": [topic["candidate_id"] for topic in topic_candidates],
            "target_micro_skill_candidate_ids": [
                skill["candidate_id"] for skill in micro_skill_candidates
            ],
            "recommended_practice_count": max(6, len(micro_skill_candidates) * 2),
            "recommended_difficulty_sequence": ["introductory", "guided", "independent"],
            "readiness_condition": "Student completes source-aligned practice with reviewed explanations.",
            "rationale": "Detected source questions and math micro-skills support a demo practice sequence.",
            "confidence": "high",
            "status": "demo_unverified",
        }
    ]


def _assessment_targets(
    topic_candidates: list[dict[str, Any]],
    micro_skill_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not micro_skill_candidates:
        return []
    return [
        {
            "candidate_id": "ASSESS_TARGET_001",
            "assessment_type": "demo_readiness_check",
            "target_goal": "Check readiness on extracted algebra skills before practice packaging.",
            "covered_topic_candidate_ids": [topic["candidate_id"] for topic in topic_candidates],
            "covered_micro_skill_candidate_ids": [
                skill["candidate_id"] for skill in micro_skill_candidates
            ],
            "recommended_question_count": max(4, len(micro_skill_candidates)),
            "difficulty_distribution": {
                "introductory": 0.6,
                "intermediate": 0.4,
                "advanced": 0.0,
            },
            "scoring_policy": "demo_unverified_simple_accuracy",
            "weakness_detection_rules": [
                "Flag any micro-skill with fewer than 2 correct responses in reviewed assessment."
            ],
            "confidence": "medium",
            "status": "demo_unverified",
        }
    ]


def _performance_tracking_targets(
    topic_candidates: list[dict[str, Any]],
    micro_skill_candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for index, skill in enumerate(micro_skill_candidates, start=1):
        targets.append(
            {
                "candidate_id": f"TRACK_TARGET_{index:03d}",
                "tracked_entity_type": "micro_skill_candidate",
                "tracked_entity_id": skill["candidate_id"],
                "metrics": ["attempt_count", "accuracy_rate", "latest_confidence"],
                "weakness_thresholds": {
                    "accuracy_rate_below": 0.7,
                    "minimum_attempts": 3,
                },
                "confidence": "medium",
                "status": "demo_unverified",
            }
        )
    if not targets and topic_candidates:
        targets.append(
            {
                "candidate_id": "TRACK_TARGET_001",
                "tracked_entity_type": "topic_candidate",
                "tracked_entity_id": topic_candidates[0]["candidate_id"],
                "metrics": ["coverage_seen", "practice_readiness"],
                "weakness_thresholds": {"practice_readiness": "manual_review_required"},
                "confidence": "low",
                "status": "demo_unverified",
            }
        )
    return targets


def _confidence_summary(
    topic_candidates: list[dict[str, Any]],
    micro_skill_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "topic_candidate_count": len(topic_candidates),
        "micro_skill_candidate_count": len(micro_skill_candidates),
        "overall_confidence": "high" if topic_candidates and len(micro_skill_candidates) >= 3 else "medium",
        "rationale": "Rule-based demo extraction from explicit topic and problem text.",
        "status": "demo_unverified",
    }


def run_curriculum_extraction(
    *,
    raw_text: str,
    output_dir: Path,
    mode: str,
) -> dict[str, Any]:
    source_document = json.loads((output_dir / "source_document.json").read_text(encoding="utf-8"))
    source_interpretation = json.loads(
        (output_dir / "source_interpretation.json").read_text(encoding="utf-8")
    )

    subject = source_interpretation["detected_subject"]
    course_level = source_interpretation["detected_course_level"]
    if is_math_subject(subject):
        extracted = extract_math_candidates(
            raw_text,
            source_id=source_document["source_id"],
            subject=subject,
            course_level=course_level,
        )
    else:
        extracted = extract_generic_stem_candidates(
            source_id=source_document["source_id"],
            subject=subject,
            course_level=course_level,
        )

    topic_candidates = extracted["topic_candidates"]
    micro_skill_candidates = extracted["micro_skill_candidates"]
    mark_duplicate_names(topic_candidates, "topic_name")
    mark_duplicate_names(micro_skill_candidates, "micro_skill_name")
    match_candidates_to_demo_registry(topic_candidates, micro_skill_candidates)

    practice_targets = _practice_targets(topic_candidates, micro_skill_candidates)
    assessment_targets = _assessment_targets(topic_candidates, micro_skill_candidates)
    tracking_targets = _performance_tracking_targets(topic_candidates, micro_skill_candidates)
    content_gaps = detect_content_gaps(
        topic_candidates=topic_candidates,
        micro_skill_candidates=micro_skill_candidates,
        source_type=source_document["source_type"],
    )

    rights_summary = {
        "rights_status": source_document["rights_status"],
        "privacy_status": source_document["privacy_status"],
        "allowed_for_demo_processing": True,
        "status": "demo_unverified",
    }
    limitations = [
        "Rule-based candidate extraction only.",
        "No reviewed practice, assessment, or performance package generated in this stage.",
        "Demo-only canonical matching; production canonical content was not consulted.",
    ]

    package = {
        "package_id": "EXTRACT_DEMO_001",
        "status": "demo_unverified",
        "source_id": source_document["source_id"],
        "source_title": source_document["source_title"],
        "source_type": source_document["source_type"],
        "source_scale": source_document["source_scale"],
        "detected_subject": subject,
        "detected_course_level": course_level,
        "extraction_mode": mode,
        "extraction_status": "completed",
        "subject_candidates": [
            {
                "subject": subject,
                "confidence": source_interpretation["subject_confidence"],
                "status": "demo_unverified",
            }
        ],
        "topic_candidates": topic_candidates,
        "subtopic_candidates": [],
        "micro_skill_candidates": micro_skill_candidates,
        "formula_candidates": [],
        "procedure_candidates": [],
        "worked_example_candidates": [],
        "question_candidates": [],
        "timeline_candidates": [],
        "dependency_candidates": [],
        "practice_target_candidates": practice_targets,
        "assessment_target_candidates": assessment_targets,
        "performance_tracking_targets": tracking_targets,
        "content_gaps": content_gaps,
        "source_evidence": extracted["source_evidence"],
        "confidence_summary": _confidence_summary(topic_candidates, micro_skill_candidates),
        "rights_summary": rights_summary,
        "limitations": limitations,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    outputs = {
        "curriculum_extraction_package.json": package,
        "topic_candidates.json": {
            "status": "demo_unverified",
            "source_id": source_document["source_id"],
            "topic_candidates": topic_candidates,
        },
        "micro_skill_candidates.json": {
            "status": "demo_unverified",
            "source_id": source_document["source_id"],
            "micro_skill_candidates": micro_skill_candidates,
        },
        "practice_targets.json": {
            "status": "demo_unverified",
            "source_id": source_document["source_id"],
            "practice_target_candidates": practice_targets,
        },
        "assessment_targets.json": {
            "status": "demo_unverified",
            "source_id": source_document["source_id"],
            "assessment_target_candidates": assessment_targets,
        },
        "performance_tracking_targets.json": {
            "status": "demo_unverified",
            "source_id": source_document["source_id"],
            "performance_tracking_targets": tracking_targets,
        },
        "content_gaps.json": {
            "status": "demo_unverified",
            "source_id": source_document["source_id"],
            "content_gaps": content_gaps,
        },
    }
    for filename, payload in outputs.items():
        _write_json(output_dir / filename, payload)
    return outputs
