"""Source registration for non-live demo inputs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def derive_source_title(raw_text: str, source_path: str) -> str:
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return Path(source_path).stem.replace("_", " ").title()


def register_source_document(
    *,
    loaded_input: dict[str, Any],
    source_type: str,
    subject_guess: str,
    course_level_guess: str,
) -> dict[str, Any]:
    return {
        "source_id": "SRC_DEMO_001",
        "source_title": derive_source_title(
            loaded_input["raw_text"], loaded_input["source_path"]
        ),
        "source_type": source_type,
        "source_scale": "single_document",
        "subject_guess": subject_guess,
        "course_guess": None,
        "course_level_guess": course_level_guess,
        "institution_or_origin": None,
        "file_path": loaded_input["source_path"],
        "input_format": loaded_input["input_format"],
        "rights_status": "owned_by_axiomiq",
        "privacy_status": "non_private",
        "processing_status": "registered",
        "status": "demo_unverified",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notes": [],
    }
