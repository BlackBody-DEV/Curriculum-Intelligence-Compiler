from pathlib import Path

import pytest

from tools.course_compiler_demo.dashboard.security import (
    MAX_UPLOAD_BYTES,
    DashboardSecurityError,
    ensure_beneath,
    sanitize_display_filename,
    validate_identifier,
    validate_loopback,
    validate_upload,
)


def test_localhost_only_server_binding_and_port_validation():
    assert validate_loopback("127.0.0.1", 8765) == ("127.0.0.1", 8765)
    with pytest.raises(DashboardSecurityError):
        validate_loopback("0.0.0.0", 8765)
    with pytest.raises(DashboardSecurityError):
        validate_loopback("192.168.1.10", 8765)
    with pytest.raises(DashboardSecurityError):
        validate_loopback("127.0.0.1", 0)


def test_upload_extension_size_empty_nul_and_filename_sanitization():
    assert validate_upload("source.md", b"Subject: PHYSICS")[1] == "md"
    assert sanitize_display_filename("../my source.txt") == "my source.txt"
    with pytest.raises(DashboardSecurityError):
        validate_upload("source.docx", b"x")
    with pytest.raises(DashboardSecurityError):
        validate_upload("source.txt", b"")
    with pytest.raises(DashboardSecurityError):
        validate_upload("source.txt", b"bad\x00content")
    with pytest.raises(DashboardSecurityError):
        validate_upload("source.txt", b"x" * (MAX_UPLOAD_BYTES + 1))


def test_identifier_and_path_traversal_rejection(tmp_path):
    assert validate_identifier("RUN_123-ok") == "RUN_123-ok"
    for value in ["", ".", "..", "a/b", "a%2Fb", "a\\b", "x" * 120]:
        with pytest.raises(DashboardSecurityError):
            validate_identifier(value)
    root = tmp_path / "root"
    root.mkdir()
    good = root / "child"
    good.mkdir()
    assert ensure_beneath(root, good) == good.resolve()
    with pytest.raises(DashboardSecurityError):
        ensure_beneath(root, tmp_path / "outside")


def test_symlink_escape_rejected(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    link = root / "link"
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(DashboardSecurityError):
        ensure_beneath(root, link)
