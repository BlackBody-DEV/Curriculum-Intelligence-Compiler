"""Filesystem storage for local dashboard runs."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .security import DashboardSecurityError, ensure_beneath, safe_join, validate_identifier


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DASHBOARD_ROOT = REPO_ROOT / "reports/course_compiler_demo/dashboard_runs"
MANIFEST_VERSION = "dashboard_run_manifest_v1"
RUN_STATES = {
    "created",
    "source_uploaded",
    "rights_confirmed",
    "profile_selected",
    "compiling",
    "compiler_complete",
    "compiler_failed",
    "curriculum_review_pending",
    "assessment_ready",
    "assessment_review_pending",
    "release_ready",
    "complete",
    "corrupt",
}


class DashboardStorageError(ValueError):
    """Raised when a dashboard run cannot be safely read or written."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pretty_json(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


class DashboardStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or DEFAULT_DASHBOARD_ROOT).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def create_run(self, *, source_title: str = "", run_id: str | None = None) -> dict[str, Any]:
        generated = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "_" + secrets.token_hex(3)
        run_id = validate_identifier(generated, "run ID")
        run_dir = safe_join(self.root, run_id)
        if run_dir.exists():
            raise DashboardStorageError("run ID collision")
        for child in ["source", "compiler", "review", "assessments", "release_package"]:
            (run_dir / child).mkdir(parents=True, exist_ok=True)
        manifest = {
            "run_id": run_id,
            "manifest_version": MANIFEST_VERSION,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "status": "created",
            "source_title": source_title,
            "source_display_filename": None,
            "source_sha256": None,
            "source_format": None,
            "rights_status": None,
            "privacy_status": None,
            "raw_or_normalized_source_retained": False,
            "selected_profile_id": None,
            "detected_subject": None,
            "detected_course_level": None,
            "compiler_status": "not_run",
            "curriculum_review_status": "pending",
            "assessment_ids": [],
            "release_status": "not_ready",
            "last_error": None,
            "artifact_index": {},
            "noncanonical": True,
            "student_visible": False,
            "adaptive_platform_write_performed": False,
            "db_read_performed": False,
            "db_write_performed": False,
            "deployment_performed": False,
        }
        self.save_manifest(manifest)
        return manifest

    def run_dir(self, run_id: str) -> Path:
        return safe_join(self.root, run_id)

    def manifest_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "run_manifest.json"

    def load_manifest(self, run_id: str) -> dict[str, Any]:
        path = self.manifest_path(run_id)
        if not path.exists():
            raise DashboardStorageError("run not found")
        try:
            manifest = load_json(path)
        except Exception as exc:
            return {"run_id": run_id, "status": "corrupt", "last_error": str(exc), "artifact_index": {}}
        if manifest.get("manifest_version") != MANIFEST_VERSION or manifest.get("status") not in RUN_STATES:
            manifest["status"] = "corrupt"
        return manifest

    def save_manifest(self, manifest: dict[str, Any]) -> None:
        run_id = validate_identifier(manifest["run_id"], "run ID")
        status = manifest.get("status")
        if status not in RUN_STATES:
            raise DashboardStorageError(f"unsupported run status: {status}")
        manifest["updated_at"] = utc_now()
        path = self.manifest_path(run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(pretty_json(manifest), encoding="utf-8")
        tmp.replace(path)

    def list_runs(self) -> list[dict[str, Any]]:
        runs = []
        for path in sorted(self.root.iterdir() if self.root.exists() else [], reverse=True):
            if path.is_dir():
                runs.append(self.load_manifest(path.name))
        runs.sort(key=lambda item: item.get("updated_at", ""), reverse=True)
        return runs

    def write_json_artifact(self, manifest: dict[str, Any], artifact_key: str, relative_path: str, data: Any) -> Path:
        artifact_key = validate_identifier(artifact_key, "artifact key")
        run_dir = self.run_dir(manifest["run_id"])
        target = ensure_beneath(run_dir, run_dir / relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(pretty_json(data), encoding="utf-8")
        manifest.setdefault("artifact_index", {})[artifact_key] = target.relative_to(run_dir).as_posix()
        self.save_manifest(manifest)
        return target

    def write_text_artifact(self, manifest: dict[str, Any], artifact_key: str, relative_path: str, text: str) -> Path:
        artifact_key = validate_identifier(artifact_key, "artifact key")
        run_dir = self.run_dir(manifest["run_id"])
        target = ensure_beneath(run_dir, run_dir / relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        manifest.setdefault("artifact_index", {})[artifact_key] = target.relative_to(run_dir).as_posix()
        self.save_manifest(manifest)
        return target

    def artifact_path(self, manifest: dict[str, Any], artifact_key: str) -> Path:
        artifact_key = validate_identifier(artifact_key, "artifact key")
        rel = manifest.get("artifact_index", {}).get(artifact_key)
        if not rel:
            raise DashboardStorageError("unknown artifact key")
        if Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise DashboardSecurityError("unsafe artifact path")
        return ensure_beneath(self.run_dir(manifest["run_id"]), self.run_dir(manifest["run_id"]) / rel)
