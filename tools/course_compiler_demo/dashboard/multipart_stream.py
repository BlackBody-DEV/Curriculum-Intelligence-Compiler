"""Streaming multipart intake helpers for local dashboard uploads."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from .limits import MAX_UPLOAD_BYTES, UPLOAD_CHUNK_BYTES
from .security import DashboardSecurityError, sanitize_display_filename


class MultipartStreamError(ValueError):
    """Raised when a multipart upload cannot be received safely."""


@dataclass(frozen=True)
class MultipartFileResult:
    display_filename: str
    source_path: Path
    sha256: str
    file_size_bytes: int
    fields: dict[str, str]
    received_bytes: int


def _boundary_from_content_type(content_type: str) -> bytes:
    for item in content_type.split(";"):
        item = item.strip()
        if item.startswith("boundary="):
            boundary = item.split("=", 1)[1].strip().strip('"')
            if not boundary:
                break
            return boundary.encode("utf-8")
    raise MultipartStreamError("multipart boundary missing")


def _parse_disposition(value: str) -> dict[str, str]:
    parts = [part.strip() for part in value.split(";")]
    parsed: dict[str, str] = {}
    for part in parts[1:]:
        if "=" in part:
            key, raw = part.split("=", 1)
            parsed[key.strip().lower()] = raw.strip().strip('"')
    return parsed


def _readline(reader: BinaryIO, *, remaining: list[int | None]) -> bytes:
    line = reader.readline()
    if not line:
        return b""
    if remaining[0] is not None:
        remaining[0] -= len(line)
        if remaining[0] < 0:
            raise MultipartStreamError("multipart body exceeded declared length")
    return line


class _MultipartReader:
    def __init__(self, stream: BinaryIO, *, content_length: int | None) -> None:
        self.stream = stream
        self.remaining = content_length
        self.received = 0
        self.buffer = bytearray()

    def _read_more(self, minimum: int = 1) -> bool:
        read_any = False
        while len(self.buffer) < minimum and (self.remaining is None or self.remaining > 0):
            size = UPLOAD_CHUNK_BYTES if self.remaining is None else min(UPLOAD_CHUNK_BYTES, self.remaining)
            chunk = self.stream.read(size)
            if not chunk:
                break
            read_any = True
            self.buffer.extend(chunk)
            self.received += len(chunk)
            if self.remaining is not None:
                self.remaining -= len(chunk)
                if self.remaining < 0:
                    raise MultipartStreamError("multipart body exceeded declared length")
        return read_any

    def readline(self) -> bytes:
        while True:
            newline = self.buffer.find(b"\n")
            if newline >= 0:
                line = bytes(self.buffer[: newline + 1])
                del self.buffer[: newline + 1]
                return line
            if self.remaining == 0 or not self._read_more(len(self.buffer) + 1):
                if not self.buffer:
                    return b""
                line = bytes(self.buffer)
                self.buffer.clear()
                return line

    def read_part_to_boundary(self, *, boundary: bytes, writer: BinaryIO | None, digest) -> tuple[int, bytes, bool]:
        delimiter = b"\r\n--" + boundary
        fallback_delimiter = b"--" + boundary
        keep = len(delimiter) + 8
        file_size = 0

        while True:
            index = self.buffer.find(delimiter)
            if index < 0 and file_size == 0:
                fallback = self.buffer.find(fallback_delimiter)
                if fallback == 0:
                    index = 0
                    delimiter = fallback_delimiter
            if index >= 0:
                payload = bytes(self.buffer[:index])
                if writer is not None and payload:
                    writer.write(payload)
                    digest.update(payload)
                    file_size += len(payload)
                    if file_size > MAX_UPLOAD_BYTES:
                        raise MultipartStreamError("upload exceeds size limit")
                del self.buffer[: index + len(delimiter)]
                while b"\n" not in self.buffer:
                    if not self._read_more(len(self.buffer) + 1):
                        break
                boundary_line = self.readline()
                done = boundary_line.strip().startswith(b"--")
                return file_size, payload, done

            if len(self.buffer) > keep:
                emit = bytes(self.buffer[:-keep])
                if writer is not None and emit:
                    writer.write(emit)
                    digest.update(emit)
                    file_size += len(emit)
                    if file_size > MAX_UPLOAD_BYTES:
                        raise MultipartStreamError("upload exceeds size limit")
                del self.buffer[:-keep]

            if self.remaining == 0:
                raise MultipartStreamError("multipart boundary not found")
            if not self._read_more(len(self.buffer) + 1):
                raise MultipartStreamError("multipart body ended before declared length")

    def finish(self) -> None:
        if self.remaining not in {None, 0}:
            raise MultipartStreamError("multipart body ended before declared length")


def receive_multipart_file(
    stream: BinaryIO,
    *,
    content_type: str,
    content_length: int | None,
    destination_dir: Path,
    declared_upload_bytes: int | None = None,
) -> MultipartFileResult:
    """Receive one file part from multipart/form-data without keeping it in RAM."""

    if "multipart/form-data" not in content_type.lower():
        raise MultipartStreamError("multipart/form-data required")
    boundary = _boundary_from_content_type(content_type)
    destination_dir.mkdir(parents=True, exist_ok=True)
    file_path = Path(tempfile.mkstemp(prefix="upload_", suffix=".pdf", dir=destination_dir)[1])
    try:
        fields: dict[str, str] = {}
        display_filename: str | None = None
        file_size = 0
        digest = hashlib.sha256()
        marker = b"--" + boundary
        reader = _MultipartReader(stream, content_length=content_length)

        with file_path.open("wb") as writer:
            line = reader.readline()
            if line.strip() != marker:
                raise MultipartStreamError("multipart boundary not found")
            while True:
                headers: dict[str, str] = {}
                while True:
                    line = reader.readline()
                    if line in {b"", b"\r\n", b"\n"}:
                        break
                    text = line.decode("utf-8", errors="replace").strip()
                    if ":" in text:
                        key, value = text.split(":", 1)
                        headers[key.lower()] = value.strip()
                disposition = _parse_disposition(headers.get("content-disposition", ""))
                name = disposition.get("name", "")
                filename = disposition.get("filename")
                if filename:
                    part_size, _payload, done = reader.read_part_to_boundary(
                        boundary=boundary,
                        writer=writer,
                        digest=digest,
                    )
                    file_size += part_size
                else:
                    _part_size, payload, done = reader.read_part_to_boundary(
                        boundary=boundary,
                        writer=None,
                        digest=None,
                    )
                    if name:
                        fields[name] = payload.decode("utf-8", errors="replace")
                if filename:
                    display_filename = sanitize_display_filename(filename)
                    if file_size > MAX_UPLOAD_BYTES:
                        raise MultipartStreamError("upload exceeds size limit")
                if done:
                    break
        reader.finish()
        if not display_filename:
            raise MultipartStreamError("file field missing")
        if file_size <= 0:
            raise MultipartStreamError("empty upload")
        if declared_upload_bytes is not None and declared_upload_bytes != file_size:
            raise MultipartStreamError("declared upload size mismatch")
        return MultipartFileResult(
            display_filename=display_filename,
            source_path=file_path,
            sha256=digest.hexdigest(),
            file_size_bytes=file_size,
            fields=fields,
            received_bytes=reader.received,
        )
    except Exception:
        file_path.unlink(missing_ok=True)
        raise


def remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
