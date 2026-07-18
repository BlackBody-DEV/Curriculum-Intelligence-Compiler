"""Filesystem-backed assessment generation output."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .exporters import write_exports
from .models import load_json, write_json
from .validators import validation_report


def write_assessment_run(
    *,
    output_dir: Path,
    blueprint: dict[str, Any],
    family: dict[str, Any],
    assessment: dict[str, Any],
    duplicate_report: dict[str, Any],
    review_decisions: dict[str, Any],
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    validation = validation_report(assessment=assessment, duplicate_report=duplicate_report, errors=[])
    generation_manifest = {
        "assessment_id": blueprint["assessment_id"],
        "generation_family_id": family["generation_family_id"],
        "random_seed": blueprint["random_seed"],
        "generated_count": len(assessment["questions"]),
        "validation_status": validation["validation_status"],
        "non_live_boundary": assessment["non_live_boundary"],
    }
    paths = {
        "assessment_blueprint": output_dir / "assessment_blueprint.json",
        "generation_manifest": output_dir / "generation_manifest.json",
        "generated_assessment": output_dir / "generated_assessment.json",
        "duplicate_report": output_dir / "duplicate_report.json",
        "validation_report": output_dir / "validation_report.json",
        "review_decisions": output_dir / "review_decisions.json",
    }
    write_json(paths["assessment_blueprint"], blueprint)
    write_json(paths["generation_manifest"], generation_manifest)
    write_json(paths["generated_assessment"], assessment)
    write_json(paths["duplicate_report"], duplicate_report)
    write_json(paths["validation_report"], validation)
    write_json(paths["review_decisions"], review_decisions)
    export_paths = write_exports(assessment, output_dir)
    paths.update({key: Path(value) for key, value in export_paths.items()})
    return paths


def load_historical_fingerprints(history_root: Path | None) -> set[str]:
    if history_root is None:
        return set()
    if not history_root.exists():
        return set()
    fingerprints: set[str] = set()
    for path in history_root.rglob("*.json"):
        data = load_json(path)
        if isinstance(data, dict):
            for key in ("exact_fingerprint", "structural_fingerprint"):
                value = data.get(key)
                if isinstance(value, str):
                    fingerprints.add(value)
            for question in data.get("questions", []):
                for key in ("exact_fingerprint", "structural_fingerprint"):
                    value = question.get(key)
                    if isinstance(value, str):
                        fingerprints.add(value)
    return fingerprints
