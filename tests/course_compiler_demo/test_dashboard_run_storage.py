from pathlib import Path

import pytest

from tools.course_compiler_demo.dashboard.run_storage import DashboardStorage, DashboardStorageError
from tools.course_compiler_demo.dashboard.security import DashboardSecurityError


def test_run_creation_manifest_persistence_and_history(tmp_path):
    storage = DashboardStorage(tmp_path)
    manifest = storage.create_run(source_title="Physics source", run_id="TEST_RUN")
    assert manifest["status"] == "created"
    loaded = storage.load_manifest("TEST_RUN")
    assert loaded["source_title"] == "Physics source"
    assert storage.list_runs()[0]["run_id"] == "TEST_RUN"


def test_artifact_registry_and_path_isolation(tmp_path):
    storage = DashboardStorage(tmp_path)
    manifest = storage.create_run(run_id="RUN1")
    storage.write_json_artifact(manifest, "result", "compiler/result.json", {"ok": True})
    loaded = storage.load_manifest("RUN1")
    assert storage.artifact_path(loaded, "result").read_text()
    with pytest.raises(DashboardStorageError):
        storage.artifact_path(loaded, "missing")
    with pytest.raises(DashboardSecurityError):
        storage.write_json_artifact(loaded, "bad", "../escape.json", {})


def test_corrupt_run_is_reported_not_deleted(tmp_path):
    storage = DashboardStorage(tmp_path)
    run_dir = tmp_path / "BROKEN"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text("{not-json", encoding="utf-8")
    manifest = storage.load_manifest("BROKEN")
    assert manifest["status"] == "corrupt"
    assert run_dir.exists()
