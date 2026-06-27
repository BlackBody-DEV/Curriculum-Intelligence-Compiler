"""Lightweight evidence records for demo extraction traces."""

from __future__ import annotations

from typing import Any


def _section_heading(lines: list[str], line_index: int) -> str | None:
    for index in range(line_index, -1, -1):
        stripped = lines[index].strip()
        if stripped.endswith(":") or (stripped and not stripped.startswith(("-", "*"))):
            return stripped.rstrip(":")
    return None


def short_excerpt(text: str, limit: int = 120) -> str:
    compact = " ".join(text.strip().split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def build_evidence_record(
    *,
    evidence_id: str,
    source_id: str,
    evidence_type: str,
    line_number: int,
    line_text: str,
    all_lines: list[str],
    confidence: str = "medium",
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "evidence_type": evidence_type,
        "line_start": line_number,
        "line_end": line_number,
        "section_heading": _section_heading(all_lines, max(line_number - 1, 0)),
        "short_excerpt": short_excerpt(line_text),
        "confidence": confidence,
    }


def find_evidence_for_terms(
    raw_text: str,
    source_id: str,
    terms: list[str],
    evidence_type: str,
    prefix: str,
) -> list[dict[str, Any]]:
    lines = raw_text.splitlines()
    records: list[dict[str, Any]] = []
    lowered_terms = [term.lower() for term in terms]
    for index, line in enumerate(lines, start=1):
        lowered_line = line.lower()
        if any(term in lowered_line for term in lowered_terms):
            records.append(
                build_evidence_record(
                    evidence_id=f"{prefix}_{len(records) + 1:03d}",
                    source_id=source_id,
                    evidence_type=evidence_type,
                    line_number=index,
                    line_text=line,
                    all_lines=lines,
                    confidence="high",
                )
            )
    return records
