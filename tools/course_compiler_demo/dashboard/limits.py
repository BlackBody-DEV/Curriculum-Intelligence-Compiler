"""Shared local dashboard resource limits."""

from __future__ import annotations


MAX_UPLOAD_BYTES = 512 * 1024 * 1024
MAX_PDF_PAGES = 5000
MAX_PDF_EXTRACTED_CHARACTERS = 50_000_000
MAX_PDF_PROCESS_SECONDS = 1800.0
UPLOAD_CHUNK_BYTES = 8 * 1024 * 1024

# JSON / text / legacy base64 path stays smaller so XL PDFs must use streaming multipart.
MAX_JSON_TEXT_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_JSON_UPLOAD_OVERHEAD_BYTES = 1024 * 1024
MAX_JSON_REQUEST_BYTES = int(MAX_JSON_TEXT_UPLOAD_BYTES * 4 / 3) + MAX_JSON_UPLOAD_OVERHEAD_BYTES
MAX_MULTIPART_OVERHEAD_BYTES = 1024 * 1024
MAX_MULTIPART_REQUEST_BYTES = MAX_UPLOAD_BYTES + MAX_MULTIPART_OVERHEAD_BYTES

MIN_TEMP_DISK_BYTES_FLOOR = 2 * 1024 * 1024 * 1024

INTAKE_JOB_STATES = (
    "receiving",
    "uploaded",
    "validating",
    "extracting",
    "ready_to_compile",
    "failed",
    "cancelled",
    "interrupted",
)


def upload_limit_label() -> str:
    return "512 MiB"


def required_temp_disk_bytes(file_size: int) -> int:
    return max(int(file_size) * 3, MIN_TEMP_DISK_BYTES_FLOOR)


def pdf_limit_snapshot() -> dict[str, int | float | str | bool]:
    return {
        "max_upload_bytes": MAX_UPLOAD_BYTES,
        "max_upload_label": upload_limit_label(),
        "max_pdf_pages": MAX_PDF_PAGES,
        "max_pdf_extracted_characters": MAX_PDF_EXTRACTED_CHARACTERS,
        "max_pdf_process_seconds": MAX_PDF_PROCESS_SECONDS,
        "upload_chunk_bytes": UPLOAD_CHUNK_BYTES,
        "pdf_boundary": "TEXT_NATIVE_PDF_ONLY",
        "ocr_supported": False,
        "scanned_image_interpretation": False,
        "external_service": False,
        "database": False,
        "binding": "LOCAL_LOOPBACK_ONLY",
    }
