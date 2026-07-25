"""Local text-native PDF extraction for the dashboard intake boundary."""

from __future__ import annotations

import hashlib
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pypdf
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .limits import (
    MAX_PDF_EXTRACTED_CHARACTERS,
    MAX_PDF_PAGES,
    MAX_PDF_PROCESS_SECONDS,
    MAX_UPLOAD_BYTES,
    UPLOAD_CHUNK_BYTES,
    pdf_limit_snapshot,
)

PDF_ENCRYPTED_OR_PASSWORD_PROTECTED = "PDF_ENCRYPTED_OR_PASSWORD_PROTECTED"
PDF_CORRUPT_OR_INVALID = "PDF_CORRUPT_OR_INVALID"
PDF_EMPTY_FILE = "PDF_EMPTY_FILE"
PDF_ZERO_PAGES = "PDF_ZERO_PAGES"
PDF_PAGE_EXTRACTION_FAILED = "PDF_PAGE_EXTRACTION_FAILED"
PDF_TEXT_EXTRACTION_REQUIRED_OCR_NOT_SUPPORTED = "PDF_TEXT_EXTRACTION_REQUIRED_OCR_NOT_SUPPORTED"
PDF_RESOURCE_LIMIT_EXCEEDED = "PDF_RESOURCE_LIMIT_EXCEEDED"
PDF_UNSUPPORTED_FILE_TYPE = "PDF_UNSUPPORTED_FILE_TYPE"
PDF_CANCELLED = "PDF_CANCELLED"


class DashboardPdfIntakeError(ValueError):
    """Raised for operator-safe PDF intake failures."""


@dataclass(frozen=True)
class PdfIntakeResult:
    text: str
    provenance: dict[str, Any]


ProgressCallback = Callable[[dict[str, Any]], None]
CancelCallback = Callable[[], bool]


def _fail(code: str) -> None:
    raise DashboardPdfIntakeError(code)


def _enforce_elapsed(started: float) -> None:
    if time.monotonic() - started > MAX_PDF_PROCESS_SECONDS:
        _fail(PDF_RESOURCE_LIMIT_EXCEEDED)


def normalize_extracted_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    cleaned = []
    for char in normalized:
        if char == "\n" or char == "\t" or ord(char) >= 32:
            cleaned.append(char)
        elif char.isspace():
            cleaned.append(" ")
    lines = [" ".join(line.split()) for line in "".join(cleaned).split("\n")]
    return "\n".join(line for line in lines if line).strip()


def _sha256_file(path: Path, *, started: float) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            _enforce_elapsed(started)
            chunk = handle.read(UPLOAD_CHUNK_BYTES)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def extract_text_native_pdf_from_path(
    display_filename: str,
    pdf_path: Path,
    *,
    retain_extracted_text: bool,
    known_sha256: str | None = None,
    known_size_bytes: int | None = None,
    normalized_text_path: Path | None = None,
    progress_callback: ProgressCallback | None = None,
    cancel_callback: CancelCallback | None = None,
) -> PdfIntakeResult:
    if Path(display_filename).suffix.lower() != ".pdf":
        _fail(PDF_UNSUPPORTED_FILE_TYPE)
    if not pdf_path.is_file():
        _fail(PDF_EMPTY_FILE)

    started = time.monotonic()
    if cancel_callback and cancel_callback():
        _fail(PDF_CANCELLED)

    file_size = known_size_bytes if known_size_bytes is not None else pdf_path.stat().st_size
    if file_size <= 0:
        _fail(PDF_EMPTY_FILE)
    if file_size > MAX_UPLOAD_BYTES:
        _fail(PDF_RESOURCE_LIMIT_EXCEEDED)

    with pdf_path.open("rb") as handle:
        signature = handle.read(5)
    if signature != b"%PDF-":
        _fail(PDF_CORRUPT_OR_INVALID)

    if progress_callback:
        progress_callback({"current_stage": "validating", "elapsed_seconds": time.monotonic() - started})

    pdf_sha = known_sha256 or _sha256_file(pdf_path, started=started)[0]
    processed_pages = 0
    pages_with_text = 0
    blank_pages = 0
    extracted_raw_characters = 0
    page_count = 0
    text_digest = hashlib.sha256()
    write_handle = None
    first_chunk = True

    try:
        if normalized_text_path is not None:
            normalized_text_path.parent.mkdir(parents=True, exist_ok=True)
            write_handle = normalized_text_path.open("w", encoding="utf-8")

        try:
            reader = PdfReader(str(pdf_path))
        except Exception:
            _fail(PDF_CORRUPT_OR_INVALID)
        _enforce_elapsed(started)
        if cancel_callback and cancel_callback():
            _fail(PDF_CANCELLED)
        if reader.is_encrypted:
            _fail(PDF_ENCRYPTED_OR_PASSWORD_PROTECTED)
        try:
            page_count = len(reader.pages)
        except Exception:
            _fail(PDF_CORRUPT_OR_INVALID)
        if page_count == 0:
            _fail(PDF_ZERO_PAGES)
        if page_count > MAX_PDF_PAGES:
            _fail(PDF_RESOURCE_LIMIT_EXCEEDED)

        if progress_callback:
            progress_callback(
                {
                    "current_stage": "extracting",
                    "page_count": page_count,
                    "processed_page_count": 0,
                    "pages_containing_text": 0,
                    "extracted_character_count": 0,
                    "elapsed_seconds": time.monotonic() - started,
                }
            )

        normalized_parts: list[str] = []
        for page in reader.pages:
            _enforce_elapsed(started)
            if cancel_callback and cancel_callback():
                _fail(PDF_CANCELLED)
            processed_pages += 1
            try:
                page_text = page.extract_text() or ""
            except (PdfReadError, Exception):
                _fail(PDF_PAGE_EXTRACTION_FAILED)
            if page_text.strip():
                pages_with_text += 1
                page_normalized = normalize_extracted_text(page_text)
                if page_normalized:
                    if normalized_parts:
                        # Join pages with newline without holding a second full copy forever.
                        piece = "\n" + page_normalized
                    else:
                        piece = page_normalized
                    normalized_parts.append(page_normalized)
                    encoded = piece.encode("utf-8")
                    text_digest.update(encoded)
                    if write_handle is not None:
                        if first_chunk:
                            write_handle.write(page_normalized)
                            first_chunk = False
                        else:
                            write_handle.write("\n")
                            write_handle.write(page_normalized)
                    extracted_raw_characters += len(page_text)
            else:
                blank_pages += 1
            if extracted_raw_characters > MAX_PDF_EXTRACTED_CHARACTERS:
                _fail(PDF_RESOURCE_LIMIT_EXCEEDED)
            if progress_callback:
                progress_callback(
                    {
                        "current_stage": "extracting",
                        "page_count": page_count,
                        "processed_page_count": processed_pages,
                        "pages_containing_text": pages_with_text,
                        "extracted_character_count": extracted_raw_characters,
                        "elapsed_seconds": time.monotonic() - started,
                    }
                )
    finally:
        if write_handle is not None:
            write_handle.close()

    if not normalized_parts:
        if normalized_text_path is not None and normalized_text_path.exists():
            normalized_text_path.unlink(missing_ok=True)
        _fail(PDF_TEXT_EXTRACTION_REQUIRED_OCR_NOT_SUPPORTED)

    # Single join for return value / classification; hash already computed incrementally.
    normalized = "\n".join(normalized_parts)
    if len(normalized) > MAX_PDF_EXTRACTED_CHARACTERS:
        _fail(PDF_RESOURCE_LIMIT_EXCEEDED)

    extracted_hash = text_digest.hexdigest()
    duration = time.monotonic() - started
    return PdfIntakeResult(
        text=normalized,
        provenance={
            "pdf_boundary": "TEXT_NATIVE_PDF_ONLY",
            "original_pdf_sha256": pdf_sha,
            "extracted_text_sha256": extracted_hash,
            "file_size_bytes": file_size,
            "page_count": page_count,
            "processed_page_count": processed_pages,
            "pages_containing_text": pages_with_text,
            "blank_page_count": blank_pages,
            "extracted_character_count": len(normalized),
            "raw_extracted_character_count": extracted_raw_characters,
            "pypdf_version": pypdf.__version__,
            "processing_duration_seconds": duration,
            "applied_resource_limits": pdf_limit_snapshot(),
            "ocr_used": False,
            "external_service_used": False,
            "raw_pdf_retained": False,
            "extracted_text_retained": bool(retain_extracted_text),
        },
    )


def extract_text_native_pdf(display_filename: str, content: bytes, *, retain_extracted_text: bool) -> PdfIntakeResult:
    if Path(display_filename).suffix.lower() != ".pdf":
        _fail(PDF_UNSUPPORTED_FILE_TYPE)
    if not content:
        _fail(PDF_EMPTY_FILE)
    if len(content) > MAX_UPLOAD_BYTES:
        _fail(PDF_RESOURCE_LIMIT_EXCEEDED)
    if not content.startswith(b"%PDF-"):
        _fail(PDF_CORRUPT_OR_INVALID)

    started = time.monotonic()
    pdf_sha = hashlib.sha256(content).hexdigest()
    with tempfile.TemporaryDirectory(prefix="axiomiq_pdf_intake_") as tmp:
        pdf_path = Path(tmp) / "upload.pdf"
        with pdf_path.open("wb") as handle:
            for offset in range(0, len(content), UPLOAD_CHUNK_BYTES):
                _enforce_elapsed(started)
                handle.write(content[offset : offset + UPLOAD_CHUNK_BYTES])
        return extract_text_native_pdf_from_path(
            display_filename,
            pdf_path,
            retain_extracted_text=retain_extracted_text,
            known_sha256=pdf_sha,
            known_size_bytes=len(content),
        )
