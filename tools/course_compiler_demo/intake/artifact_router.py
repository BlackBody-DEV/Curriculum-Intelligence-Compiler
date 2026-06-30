"""Folder and artifact routing helpers for the non-live intake engine."""

from __future__ import annotations

import shutil
from pathlib import Path


REQUIRED_OUTPUT_FILES = [
    "source_document.json",
    "source_interpretation.json",
    "source_feature_flags.json",
    "curriculum_extraction_package.json",
    "topic_candidates.json",
    "micro_skill_candidates.json",
    "practice_targets.json",
    "assessment_targets.json",
    "performance_tracking_targets.json",
    "content_gaps.json",
    "practice_module_package.json",
    "practice_assessment_package.json",
    "performance_tracking_package.json",
    "content_gap_report.md",
    "demo_report.md",
    "validation_report.json",
]


def ensure_folder_model(
    *,
    incoming_dir: Path,
    original_artifacts_dir: Path,
    output_root: Path,
) -> dict[str, Path]:
    folders = {
        "incoming": incoming_dir,
        "original_artifacts": original_artifacts_dir,
        "output_root": output_root,
        "intake_runs": output_root / "intake_runs",
        "math": output_root / "math",
        "packages": output_root / "math" / "packages",
        "procedures": output_root / "math" / "procedures",
        "questions": output_root / "math" / "questions",
        "generation_families": output_root / "math" / "generation_families",
        "validation": output_root / "math" / "validation",
    }
    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)
    return folders


def supported_input_files(incoming_dir: Path, supported_suffixes: set[str]) -> list[Path]:
    if not incoming_dir.exists():
        return []
    return sorted(
        path
        for path in incoming_dir.iterdir()
        if path.is_file() and not path.name.startswith(".") and path.suffix.lower() in supported_suffixes
    )


def unsupported_input_files(incoming_dir: Path, supported_suffixes: set[str]) -> list[Path]:
    if not incoming_dir.exists():
        return []
    return sorted(
        path
        for path in incoming_dir.iterdir()
        if path.is_file() and not path.name.startswith(".") and path.suffix.lower() not in supported_suffixes
    )


def archive_original(source_path: Path, original_artifacts_dir: Path, intake_id: str) -> Path:
    archive_name = f"{intake_id}_{source_path.name}"
    target = original_artifacts_dir / archive_name
    if target.exists():
        target = original_artifacts_dir / f"{source_path.stem}_{intake_id}{source_path.suffix}"
    counter = 2
    while target.exists():
        target = original_artifacts_dir / f"{source_path.stem}_{intake_id}_{counter}{source_path.suffix}"
        counter += 1
    shutil.move(source_path.as_posix(), target.as_posix())
    return target


def verify_required_outputs(run_dir: Path) -> list[str]:
    return [filename for filename in REQUIRED_OUTPUT_FILES if not (run_dir / filename).is_file()]
