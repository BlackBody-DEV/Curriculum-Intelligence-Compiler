"""Duplicate detection helpers for demo extraction results."""

from __future__ import annotations

from typing import Any


def mark_duplicate_names(candidates: list[dict[str, Any]], name_key: str) -> None:
    seen: set[str] = set()
    for candidate in candidates:
        normalized = " ".join(candidate.get(name_key, "").lower().split())
        if normalized in seen:
            candidate["alignment_status"] = "possible_duplicate"
        seen.add(normalized)
