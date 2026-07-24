"""Shared local dashboard resource limits."""

from __future__ import annotations


MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_PDF_PAGES = 1500
MAX_PDF_EXTRACTED_CHARACTERS = 8_000_000
MAX_PDF_PROCESS_SECONDS = 180.0
MAX_JSON_UPLOAD_OVERHEAD_BYTES = 1024 * 1024
MAX_JSON_REQUEST_BYTES = int(MAX_UPLOAD_BYTES * 4 / 3) + MAX_JSON_UPLOAD_OVERHEAD_BYTES


def upload_limit_label() -> str:
    return "50 MiB"


def pdf_limit_snapshot() -> dict[str, int | float | str]:
    return {
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "max_upload_label": upload_limit_label(),
        "max_pdf_pages": MAX_PDF_PAGES,
        "max_pdf_extracted_characters": MAX_PDF_EXTRACTED_CHARACTERS,
        "max_pdf_process_seconds": MAX_PDF_PROCESS_SECONDS,
    }
