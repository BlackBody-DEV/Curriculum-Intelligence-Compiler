"""Intake identifiers and intake record helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def timestamp_utc() -> datetime:
    return datetime.now(timezone.utc)


def make_intake_id(*, created_at: datetime, sequence: int) -> str:
    return f"INTAKE_{created_at.strftime('%Y%m%d_%H%M%S')}_{sequence:03d}"


def make_batch_id(*, created_at: datetime) -> str:
    return f"BATCH_{created_at.strftime('%Y%m%d_%H%M%S')}"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_intake_record(
    *,
    intake_id: str,
    original_filename: str,
    original_artifact_path: Path,
    input_path: Path,
    compiler_output_path: Path,
    detected_file_type: str,
    detected_subject: str,
    detected_document_type: str,
    processing_mode: str,
    created_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": "INTAKE_RECORD_v0_1",
        "intake_id": intake_id,
        "status": "processed_non_live",
        "original_filename": original_filename,
        "original_artifact_path": original_artifact_path.as_posix(),
        "input_path": input_path.as_posix(),
        "compiler_output_path": compiler_output_path.as_posix() + "/",
        "detected_file_type": detected_file_type,
        "detected_subject": detected_subject,
        "detected_document_type": detected_document_type,
        "processing_mode": processing_mode,
        "rights_status": "owned_by_axiomiq_or_synthetic_demo",
        "privacy_status": "non_private",
        "db_contact": False,
        "operational_alpha_contact": False,
        "human_review_required": True,
        "created_at": created_at.isoformat(),
        "notes": [
            "Non-live intake engine v0.1 output.",
            "No compiler output becomes active without human review.",
        ],
    }


def build_batch_summary(
    *,
    batch_id: str,
    incoming_path: Path,
    processed: list[dict[str, str]],
    skipped_files: list[dict[str, str]],
    failed_files: list[dict[str, str]],
    created_at: datetime,
) -> dict[str, Any]:
    return {
        "schema_version": "INTAKE_BATCH_SUMMARY_v0_1",
        "status": "processed_non_live",
        "batch_id": batch_id,
        "supported_formats": [".txt", ".md"],
        "incoming_path": incoming_path.as_posix().rstrip("/") + "/",
        "processed_count": len(processed),
        "skipped_count": len(skipped_files),
        "failed_count": len(failed_files),
        "processed_intake_ids": [item["intake_id"] for item in processed],
        "processed_files": processed,
        "skipped_files": skipped_files,
        "failed_files": failed_files,
        "db_contact": False,
        "operational_alpha_contact": False,
        "human_review_required": True,
        "created_at": created_at.isoformat(),
        "notes": [
            "Non-live multi-file intake batch summary.",
            "Unsupported files are not parsed as compiler sources.",
            "No compiler output becomes active without human review.",
        ],
    }
