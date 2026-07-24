"""Local text-native PDF extraction for the dashboard intake boundary."""

from __future__ import annotations

import hashlib
import tempfile
import time
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


class DashboardPdfIntakeError(ValueError):
    """Raised for operator-safe PDF intake failures."""


@dataclass(frozen=True)
class PdfIntakeResult:
    text: str
    provenance: dict[str, Any]


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
    processed_pages = 0
    pages_with_text = 0
    blank_pages = 0
    extracted_raw_characters = 0
    try:
        with tempfile.TemporaryDirectory(prefix="axiomiq_pdf_intake_") as tmp:
            pdf_path = Path(tmp) / "upload.pdf"
            with pdf_path.open("wb") as handle:
                for offset in range(0, len(content), 1024 * 1024):
                    _enforce_elapsed(started)
                    handle.write(content[offset : offset + 1024 * 1024])
            try:
                reader = PdfReader(str(pdf_path))
            except Exception:
                _fail(PDF_CORRUPT_OR_INVALID)
            _enforce_elapsed(started)
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

            chunks: list[str] = []
            for page in reader.pages:
                _enforce_elapsed(started)
                processed_pages += 1
                try:
                    page_text = page.extract_text() or ""
                except (PdfReadError, Exception):
                    _fail(PDF_PAGE_EXTRACTION_FAILED)
                if page_text.strip():
                    pages_with_text += 1
                    chunks.append(page_text)
                    extracted_raw_characters += len(page_text)
                else:
                    blank_pages += 1
                if extracted_raw_characters > MAX_PDF_EXTRACTED_CHARACTERS:
                    _fail(PDF_RESOURCE_LIMIT_EXCEEDED)
    except DashboardPdfIntakeError:
        raise

    normalized = normalize_extracted_text("\n".join(chunks))
    if not normalized:
        _fail(PDF_TEXT_EXTRACTION_REQUIRED_OCR_NOT_SUPPORTED)
    if len(normalized) > MAX_PDF_EXTRACTED_CHARACTERS:
        _fail(PDF_RESOURCE_LIMIT_EXCEEDED)

    extracted_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    duration = time.monotonic() - started
    return PdfIntakeResult(
        text=normalized,
        provenance={
            "pdf_boundary": "TEXT_NATIVE_PDF_ONLY",
            "original_pdf_sha256": pdf_sha,
            "extracted_text_sha256": extracted_hash,
            "file_size_bytes": len(content),
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
