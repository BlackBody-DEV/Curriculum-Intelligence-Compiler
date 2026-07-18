"""Security helpers for the local-only dashboard."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".txt", ".md"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,96}$")


class DashboardSecurityError(ValueError):
    """Raised when a dashboard request violates the local safety boundary."""


def validate_loopback(host: str, port: int) -> tuple[str, int]:
    if host != "127.0.0.1":
        raise DashboardSecurityError("dashboard may bind only to 127.0.0.1")
    if not isinstance(port, int) or port < 1 or port > 65535:
        raise DashboardSecurityError("invalid dashboard port")
    return host, port


def validate_identifier(value: str, label: str = "identifier") -> str:
    decoded = unquote(str(value))
    if decoded in {"", ".", ".."}:
        raise DashboardSecurityError(f"invalid {label}")
    if any(token in decoded for token in ["/", "\\", ".."]):
        raise DashboardSecurityError(f"{label} may not contain path traversal")
    if not ID_PATTERN.fullmatch(decoded):
        raise DashboardSecurityError(f"{label} contains unsupported characters")
    return decoded


def sanitize_display_filename(filename: str) -> str:
    base = Path(str(filename).replace("\x00", "")).name
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", base).strip(" .")
    if not cleaned:
        raise DashboardSecurityError("empty filename")
    if "/" in cleaned or "\\" in cleaned or cleaned in {".", ".."}:
        raise DashboardSecurityError("unsafe filename")
    suffix = Path(cleaned).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise DashboardSecurityError(f"unsupported upload extension: {suffix}")
    return cleaned[:120]


def validate_upload(filename: str, content: bytes) -> tuple[str, str]:
    display = sanitize_display_filename(filename)
    if not content:
        raise DashboardSecurityError("empty upload")
    if len(content) > MAX_UPLOAD_BYTES:
        raise DashboardSecurityError("upload exceeds 5 MiB limit")
    if b"\x00" in content:
        raise DashboardSecurityError("upload contains NUL byte")
    suffix = Path(display).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise DashboardSecurityError(f"unsupported upload extension: {suffix}")
    return display, suffix.lstrip(".")


def ensure_beneath(root: Path, path: Path) -> Path:
    resolved_root = root.resolve()
    resolved = path.resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise DashboardSecurityError("path escapes dashboard root") from exc
    if resolved.is_symlink():
        raise DashboardSecurityError("symlink escape rejected")
    return resolved


def safe_join(root: Path, *parts: str) -> Path:
    current = root
    for part in parts:
        current = current / validate_identifier(part, "path segment")
    return ensure_beneath(root, current)
