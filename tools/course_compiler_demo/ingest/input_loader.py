"""Input loading for non-live Course Compiler Demo sources."""

from __future__ import annotations

from pathlib import Path
from typing import Any


SUPPORTED_INPUT_FORMATS = {".txt": "txt", ".md": "md"}


def load_text_input(source_path: str | Path) -> dict[str, Any]:
    """Read a supported text input file without modifying it."""
    path = Path(source_path)
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")

    input_format = SUPPORTED_INPUT_FORMATS.get(path.suffix.lower())
    if input_format is None:
        supported = ", ".join(sorted(SUPPORTED_INPUT_FORMATS))
        raise ValueError(f"Unsupported input format '{path.suffix}'. Supported: {supported}")

    raw_text = path.read_text(encoding="utf-8")
    return {
        "raw_text": raw_text,
        "input_format": input_format,
        "source_path": path.as_posix(),
        "line_count": len(raw_text.splitlines()),
        "char_count": len(raw_text),
    }
