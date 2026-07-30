from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.course_compiler_demo.dashboard.pdf_intake import extract_text_native_pdf
from tools.course_compiler_demo.testing.source_inbox import (
    COMMITTED_SOURCE_INBOX,
    HOST_SOURCE_INBOX_OPT_IN_ENV,
    HOST_SOURCE_INBOX,
    SOURCE_INBOX_ENV,
    optional_host_source_inbox,
    resolve_source_inbox_root,
)


def _marked_root(path: Path) -> Path:
    path.mkdir()
    (path / "fixture_manifest.json").write_text("{}", encoding="utf-8")
    return path.resolve()


@pytest.mark.portable_baseline
def test_resolution_precedence_is_explicit_then_environment_then_committed(tmp_path):
    explicit = _marked_root(tmp_path / "explicit")
    environment = _marked_root(tmp_path / "environment")
    assert resolve_source_inbox_root(explicit, environ={SOURCE_INBOX_ENV: str(environment)}) == explicit
    assert resolve_source_inbox_root(environ={SOURCE_INBOX_ENV: str(environment)}) == environment
    assert resolve_source_inbox_root(environ={}) == COMMITTED_SOURCE_INBOX.resolve()


@pytest.mark.portable_baseline
def test_host_integration_requires_explicit_opt_in_even_when_host_exists(monkeypatch):
    monkeypatch.setattr(Path, "is_dir", lambda path: path == HOST_SOURCE_INBOX)
    assert optional_host_source_inbox(environ={}) is None
    assert optional_host_source_inbox(environ={HOST_SOURCE_INBOX_OPT_IN_ENV: "0"}) is None
    assert optional_host_source_inbox(environ={HOST_SOURCE_INBOX_OPT_IN_ENV: "1"}) == HOST_SOURCE_INBOX


@pytest.mark.portable_baseline
def test_missing_root_fails_with_precise_path_and_explicit_directory_needs_no_marker(tmp_path):
    missing = tmp_path / "missing"
    with pytest.raises(FileNotFoundError, match="is not a directory"):
        resolve_source_inbox_root(missing)
    external = tmp_path / "external"
    external.mkdir()
    assert resolve_source_inbox_root(external) == external.resolve()


@pytest.mark.portable_baseline
def test_manifest_hashes_segments_rights_and_duplicate_probe_are_stable():
    root = resolve_source_inbox_root(environ={})
    manifest = json.loads((root / "fixture_manifest.json").read_text(encoding="utf-8"))
    assert manifest["artifact_class"] == "TEST_FIXTURE"
    assert manifest["noncanonical"] is True
    assert manifest["contains_private_content"] is False
    assert manifest["rights_status"] == "newly_authored_test_fixture"
    assert manifest["privacy_status"] == "non_private"
    assert len(manifest["files"]) == 9
    listed = {record["path"] for record in manifest["files"]}
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    assert actual == listed | {"fixture_manifest.json"}
    for record in manifest["files"]:
        payload = (root / record["path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == record["sha256"]
        assert record["segments"] and record["evidence"]
    duplicates = [record for record in manifest["files"] if record["path"].startswith("Duplicates/")]
    assert len(duplicates) == 2 and len({record["sha256"] for record in duplicates}) == 1


@pytest.mark.portable_baseline
def test_committed_pdf_is_text_native_and_rights_safe():
    root = resolve_source_inbox_root(environ={})
    path = root / "PDF/mechanics_text_native.pdf"
    result = extract_text_native_pdf(path.name, path.read_bytes(), retain_extracted_text=False)
    assert result.text.startswith("TEST_FIXTURE Mechanics PDF")
    assert "net force" in result.text and "F_net = m a" in result.text


@pytest.mark.skipif(
    optional_host_source_inbox() is None,
    reason=f"host Source_Inbox requires {HOST_SOURCE_INBOX_OPT_IN_ENV}=1 and a mounted path",
)
@pytest.mark.host_environment_integration
def test_optional_legacy_host_marker_is_precisely_scoped():
    assert optional_host_source_inbox() == HOST_SOURCE_INBOX
    assert (HOST_SOURCE_INBOX / "Physics/intro_mechanics_real_source_v1/normalized_source.txt").is_file()
    assert (HOST_SOURCE_INBOX / "Statics/User_Authored/me_2301_statics_curriculum_extraction.md").is_file()
