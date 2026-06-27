"""Markdown report generation for the Course Compiler Demo."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load(output_dir: Path, filename: str) -> dict[str, Any]:
    return json.loads((output_dir / filename).read_text(encoding="utf-8"))


def _bullet(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values) if values else "- None"


def generate_markdown_reports(output_dir: Path, validation_summary: dict[str, Any]) -> None:
    source = _load(output_dir, "source_document.json")
    interpretation = _load(output_dir, "source_interpretation.json")
    topics = _load(output_dir, "topic_candidates.json").get("topic_candidates", [])
    skills = _load(output_dir, "micro_skill_candidates.json").get("micro_skill_candidates", [])
    gaps = _load(output_dir, "content_gaps.json").get("content_gaps", [])
    practice = _load(output_dir, "practice_module_package.json")
    assessment = _load(output_dir, "practice_assessment_package.json")
    tracking = _load(output_dir, "performance_tracking_package.json")
    extraction = _load(output_dir, "curriculum_extraction_package.json")

    demo_report = _demo_report(
        source=source,
        interpretation=interpretation,
        topics=topics,
        skills=skills,
        gaps=gaps,
        practice=practice,
        assessment=assessment,
        tracking=tracking,
        extraction=extraction,
        validation_summary=validation_summary,
    )
    gap_report = _gap_report(
        source=source,
        gaps=gaps,
        practice=practice,
        assessment=assessment,
        tracking=tracking,
    )
    (output_dir / "demo_report.md").write_text(demo_report, encoding="utf-8")
    (output_dir / "content_gap_report.md").write_text(gap_report, encoding="utf-8")


def _demo_report(
    *,
    source: dict[str, Any],
    interpretation: dict[str, Any],
    topics: list[dict[str, Any]],
    skills: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    practice: dict[str, Any],
    assessment: dict[str, Any],
    tracking: dict[str, Any],
    extraction: dict[str, Any],
    validation_summary: dict[str, Any],
) -> str:
    topic_lines = [
        f"{topic['topic_name']} ({topic.get('alignment_status', 'unknown')})"
        for topic in topics
    ]
    skill_lines = [
        f"{skill['micro_skill_name']} -> {skill['parent_topic_candidate_id']}"
        for skill in skills
    ]
    gap_lines = [
        f"{gap['gap_type']}: {gap['description']}"
        for gap in gaps
    ]
    limitations = extraction.get("limitations", []) + practice.get("limitations", [])
    return f"""# AxiomIQ Course Compiler Demo Report

## Status

This output is demo_unverified.
This is not canonical curriculum.
This is not production-ready content.

## Input Summary

- Source ID: {source['source_id']}
- Source title: {source['source_title']}
- Source file: {source['file_path']}
- Source scale: {source['source_scale']}

## Document Interpretation

- Processing recommendation: {interpretation['processing_recommendation']}
- Primary use: {', '.join(interpretation.get('detected_primary_use', []))}

## Detected Subject

{interpretation['detected_subject']} with {interpretation['subject_confidence']} confidence.

## Detected Source Type

{interpretation['detected_source_type']} with {interpretation['source_type_confidence']} confidence.

## Topic Map

{_bullet(topic_lines)}

## Micro-Skill Map

{_bullet(skill_lines)}

## Practice Module Summary

- Package ID: {practice['package_id']}
- Module title: {practice['module_title']}
- Practice items: {len(practice.get('practice_sequence', []))}
- Readiness condition: {practice['readiness_condition']}

## Practice Assessment Summary

- Package ID: {assessment['package_id']}
- Assessment title: {assessment['assessment_title']}
- Assessment items: {len(assessment.get('assessment_items', []))}
- Scoring policy: {assessment.get('scoring_policy', {}).get('scoring_type')}

## Performance Tracking Preview

- Package ID: {tracking['package_id']}
- Tracking type: {tracking['tracking_type']}
- Readiness model: {tracking.get('readiness_model', {}).get('model_type')}
- Demo readiness does not update operational Alpha readiness or mastery.

## Content Gaps

{_bullet(gap_lines)}

## Rights Summary

- Rights status: {source['rights_status']}
- Privacy status: {source['privacy_status']}
- No database contact occurred.

## Limitations

{_bullet(limitations)}

## Validation Summary

- Overall result: {validation_summary.get('overall_result')}
- Missing files: {validation_summary.get('missing_files', [])}
- Required field errors: {validation_summary.get('required_field_errors', [])}

## Recommended Next Step

COURSE-COMPILER-DEMO-RUN-001

## Non-Live Boundary

This is a non-live local demo artifact. This output is demo_unverified. This is not canonical curriculum. This is not production-ready content. This does not update operational Alpha readiness or mastery. No database contact occurred.
"""


def _gap_report(
    *,
    source: dict[str, Any],
    gaps: list[dict[str, Any]],
    practice: dict[str, Any],
    assessment: dict[str, Any],
    tracking: dict[str, Any],
) -> str:
    gap_lines = [
        f"- {gap['gap_type']}: {gap['description']}"
        for gap in gaps
    ]
    action_lines = [
        f"- {gap.get('recommended_action', 'Manual review required.')}"
        for gap in gaps
    ]
    return f"""# Course Compiler Content Gap Report

## Status

demo_unverified

## Source

- Source ID: {source['source_id']}
- Source title: {source['source_title']}

## Gaps Identified

{chr(10).join(gap_lines) if gap_lines else '- No content gaps detected in demo scope.'}

## Impact

Gaps may limit instructional reliability, assessment coverage, and readiness interpretation for this demo package.

## Recommended Actions

{chr(10).join(action_lines) if action_lines else '- Continue manual review.'}

## Review Requirements

- Review practice package {practice['package_id']} before live use.
- Review assessment package {assessment['package_id']} before live use.
- Review performance package {tracking['package_id']} before live use.

## Non-Live Boundary

This Content Gap report is demo_unverified, non-live, and does not update operational Alpha readiness or mastery.
"""
