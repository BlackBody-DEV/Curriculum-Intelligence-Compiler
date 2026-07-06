"""CLI for the non-live Course Compiler Demo pipeline stages."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

from ingest.document_classifier import (
    ALLOWED_SUBJECTS,
    classify_document,
    detect_math_course_level,
    detect_subject,
)
from ingest.feature_detector import detect_features
from ingest.input_loader import load_text_input
from ingest.source_registry import register_source_document
from extract.curriculum_extractor import run_curriculum_extraction
from report.markdown_reporter import generate_markdown_reports
from validate.package_validator import validate_demo_package
from validate.schema_validator import validate_outputs


ALLOWED_MODES = {
    "student_practice",
    "exam_preparation",
    "course_planning",
    "curriculum_build",
    "corpus_build",
    "institutional_training",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AxiomIQ Course Compiler Demo input and extraction-stage CLI."
    )
    parser.add_argument("--input", help="Path to a .txt or .md demo source file.")
    parser.add_argument("--subject", choices=sorted(ALLOWED_SUBJECTS), help="Subject orientation.")
    parser.add_argument("--mode", choices=sorted(ALLOWED_MODES), help="Compiler use mode.")
    parser.add_argument("--output", help="Directory for local demo JSON outputs.")
    parser.add_argument(
        "--version",
        action="version",
        version="course-compiler-demo 0.0.0-demo",
    )
    return parser


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def _primary_use(source_type: str, mode: str) -> list[str]:
    uses: list[str] = []
    if mode == "student_practice" or source_type in {"homework", "problem_set", "study_guide"}:
        uses.append("practice_generation")
    if source_type in {"homework", "problem_set", "practice_test", "quiz_review"}:
        uses.append("performance_tracking")
    if mode == "exam_preparation" or source_type in {
        "practice_test",
        "quiz_review",
        "midterm_review",
        "final_review",
    }:
        uses.append("assessment_preparation")
    return uses or ["source_interpretation"]


def _run_packaging_stage(output_dir: Path) -> None:
    practice_builder = importlib.import_module("package.practice_module_builder")
    assessment_builder = importlib.import_module("package.assessment_builder")
    tracking_builder = importlib.import_module("package.performance_tracking_builder")

    practice_package = practice_builder.build_practice_module_package(output_dir)
    validate_demo_package(
        practice_package,
        [
            "package_id",
            "status",
            "module_title",
            "module_type",
            "source_context",
            "target_curriculum",
            "practice_sequence",
        ],
    )
    _write_json(output_dir / "practice_module_package.json", practice_package)

    assessment_package = assessment_builder.build_practice_assessment_package(output_dir)
    validate_demo_package(
        assessment_package,
        [
            "package_id",
            "status",
            "assessment_title",
            "assessment_type",
            "covered_curriculum",
            "assessment_blueprint",
            "assessment_items",
            "scoring_policy",
        ],
    )
    _write_json(output_dir / "practice_assessment_package.json", assessment_package)

    tracking_package = tracking_builder.build_performance_tracking_package(output_dir)
    validate_demo_package(
        tracking_package,
        [
            "package_id",
            "status",
            "tracking_title",
            "tracking_type",
            "linked_packages",
            "attempt_record_schema",
            "metric_definitions",
            "readiness_model",
        ],
    )
    _write_json(output_dir / "performance_tracking_package.json", tracking_package)


def _run_reporting_validation_stage(output_dir: Path) -> None:
    preliminary_validation = validate_outputs(output_dir)
    _write_json(output_dir / "validation_report.json", preliminary_validation)
    generate_markdown_reports(output_dir, preliminary_validation)
    final_validation = validate_outputs(output_dir)
    _write_json(output_dir / "validation_report.json", final_validation)
    generate_markdown_reports(output_dir, final_validation)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not any([args.input, args.subject, args.mode, args.output]):
        parser.print_help()
        return 0
    missing = [
        name
        for name in ("input", "subject", "mode", "output")
        if getattr(args, name) is None
    ]
    if missing:
        parser.error("the following arguments are required for demo execution: " + ", ".join(f"--{name}" for name in missing))

    loaded_input = load_text_input(args.input)
    classification = classify_document(loaded_input["raw_text"])
    subject = detect_subject(loaded_input["raw_text"], args.subject)
    if subject["detected_subject"] == "MATHEMATICS":
        course_level = detect_math_course_level(loaded_input["raw_text"])
    else:
        course_level = {
            "detected_course_level": "UNKNOWN_MATH_LEVEL",
            "course_level_confidence": "low",
        }
    feature_flags = detect_features(
        loaded_input["raw_text"], classification["detected_source_type"]
    )

    source_document = register_source_document(
        loaded_input=loaded_input,
        source_type=classification["detected_source_type"],
        subject_guess=subject["detected_subject"],
        course_level_guess=course_level["detected_course_level"],
    )
    source_interpretation = {
        "status": "demo_unverified",
        "source_id": source_document["source_id"],
        "detected_source_type": classification["detected_source_type"],
        "source_type_confidence": classification["source_type_confidence"],
        "classification_evidence": classification["classification_evidence"],
        "detected_subject": subject["detected_subject"],
        "subject_confidence": subject["subject_confidence"],
        "detected_course_level": course_level["detected_course_level"],
        "course_level_confidence": course_level["course_level_confidence"],
        "input_format": source_document["input_format"],
        "detected_primary_use": _primary_use(classification["detected_source_type"], args.mode),
        "feature_flags": feature_flags,
        "rights_status": source_document["rights_status"],
        "privacy_status": source_document["privacy_status"],
        "processing_recommendation": "extraction_ready",
        "blocking_issues": [],
        "notes": [],
    }
    source_feature_flags = {
        "status": "demo_unverified",
        "source_id": source_document["source_id"],
        "feature_flags": feature_flags,
    }

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "source_document.json", source_document)
    _write_json(output_dir / "source_interpretation.json", source_interpretation)
    _write_json(output_dir / "source_feature_flags.json", source_feature_flags)
    run_curriculum_extraction(
        raw_text=loaded_input["raw_text"],
        output_dir=output_dir,
        mode=args.mode,
    )
    _run_packaging_stage(output_dir)
    _run_reporting_validation_stage(output_dir)

    print(f"Wrote full non-live demo outputs to {output_dir.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
