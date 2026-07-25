"""Persisted local PDF intake-job lifecycle for the dashboard."""

from __future__ import annotations

import threading
import time
import shutil
from pathlib import Path
from typing import Any

from .limits import MAX_UPLOAD_BYTES, required_temp_disk_bytes
from .multipart_stream import MultipartStreamError, receive_multipart_file, remove_tree
from .pdf_intake import DashboardPdfIntakeError, extract_text_native_pdf_from_path
from .run_storage import DashboardStorage, load_json, pretty_json, utc_now
from .security import validate_identifier


class IntakeJobError(ValueError):
    """Raised when an intake job cannot proceed."""


class IntakeJobManager:
    def __init__(self, storage: DashboardStorage, controller: Any) -> None:
        self.storage = storage
        self.controller = controller

    def _jobs_dir(self, run_id: str) -> Path:
        return self.storage.run_dir(validate_identifier(run_id, "run ID")) / "intake_jobs"

    def _job_path(self, run_id: str, job_id: str) -> Path:
        job_id = validate_identifier(job_id, "job ID")
        return self._jobs_dir(run_id) / f"{job_id}.json"

    def _job_tmp_dir(self, run_id: str, job_id: str) -> Path:
        return self._jobs_dir(run_id) / f"{job_id}_tmp"

    def _save_job(self, run_id: str, job: dict[str, Any]) -> dict[str, Any]:
        job["updated_at"] = utc_now()
        path = self._job_path(run_id, str(job["job_id"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(pretty_json(job), encoding="utf-8")
        tmp.replace(path)
        return job

    def load_job(self, run_id: str, job_id: str) -> dict[str, Any]:
        path = self._job_path(run_id, job_id)
        if not path.exists():
            raise IntakeJobError("intake job not found")
        return load_json(path)

    def create_receiving_job(self, run_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
        run_id = validate_identifier(run_id, "run ID")
        manifest = self.storage.load_manifest(run_id)
        job_id = f"JOB_{int(time.time() * 1000000)}"
        job = {
            "job_id": job_id,
            "run_id": run_id,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "current_stage": "receiving",
            "ready_to_compile": False,
            "upload_complete": False,
            "received_bytes": 0,
            "maximum_bytes": MAX_UPLOAD_BYTES,
            "display_filename": metadata.get("filename") or "",
            "source_title": metadata.get("source_title") or manifest.get("source_title") or "",
            "rights_status": metadata.get("rights_status", "rights_review_required"),
            "privacy_status": metadata.get("privacy_status", "privacy_review_required"),
            "profile_id": metadata.get("profile_id") or metadata.get("selected_profile_id") or "",
            "document_type": metadata.get("document_type"),
            "author_or_institution": metadata.get("author_or_institution", ""),
            "optional_source_reference": metadata.get("optional_source_reference", ""),
            "retain_normalized_source": bool(metadata.get("retain_normalized_source")),
            "last_error": None,
            "cancel_requested": False,
        }
        manifest["active_intake_job_id"] = job_id
        self.storage.save_manifest(manifest)
        return self._save_job(run_id, job)

    def get_job_progress(self, run_id: str, job_id: str) -> dict[str, Any]:
        return self.load_job(run_id, job_id)

    def cancel_job(self, run_id: str, job_id: str) -> dict[str, Any]:
        job = self.load_job(run_id, job_id)
        if job.get("current_stage") not in {"ready_to_compile", "failed", "cancelled", "interrupted"}:
            job["cancel_requested"] = True
            job["current_stage"] = "cancelled"
            job["last_error"] = "cancelled"
            remove_tree(self._job_tmp_dir(run_id, job_id))
        return self._save_job(run_id, job)

    def mark_interrupted_jobs(self) -> None:
        root = self.storage.root
        if not root.exists():
            return
        for path in root.glob("*/intake_jobs/*.json"):
            run_id = path.parents[1].name
            job = load_json(path)
            if job.get("current_stage") in {"receiving", "uploaded", "validating", "extracting"}:
                job["current_stage"] = "interrupted"
                job["last_error"] = "intake interrupted before completion"
                remove_tree(self._job_tmp_dir(run_id, str(job.get("job_id"))))
                self._save_job(run_id, job)

    def _progress_callback(self, run_id: str, job_id: str):
        def update(progress: dict[str, Any]) -> None:
            job = self.load_job(run_id, job_id)
            if job.get("cancel_requested") or job.get("current_stage") == "cancelled":
                return
            job.update(progress)
            self._save_job(run_id, job)

        return update

    def _cancel_callback(self, run_id: str, job_id: str):
        def cancelled() -> bool:
            try:
                job = self.load_job(run_id, job_id)
            except IntakeJobError:
                return True
            return bool(job.get("cancel_requested")) or job.get("current_stage") == "cancelled"

        return cancelled

    def receive_multipart_upload(
        self,
        run_id: str,
        job_id: str,
        stream,
        *,
        content_type: str,
        content_length: int | None,
        declared_upload_bytes: int | None,
    ) -> dict[str, Any]:
        run_id = validate_identifier(run_id, "run ID")
        job_id = validate_identifier(job_id, "job ID")
        job = self.load_job(run_id, job_id)
        if job.get("current_stage") != "receiving":
            raise IntakeJobError("intake job is not receiving")
        tmp_dir = self._job_tmp_dir(run_id, job_id)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        try:
            expected_size = declared_upload_bytes if declared_upload_bytes is not None else content_length
            if expected_size is not None:
                required = required_temp_disk_bytes(expected_size)
                if shutil.disk_usage(tmp_dir).free < required:
                    raise IntakeJobError("insufficient temporary disk space for PDF intake")
            result = receive_multipart_file(
                stream,
                content_type=content_type,
                content_length=content_length,
                destination_dir=tmp_dir,
                declared_upload_bytes=declared_upload_bytes,
            )
            job.update(
                {
                    "current_stage": "uploaded",
                    "upload_complete": True,
                    "display_filename": result.display_filename,
                    "received_bytes": result.file_size_bytes,
                    "source_sha256": result.sha256,
                    "file_size_bytes": result.file_size_bytes,
                    "temp_pdf_path": str(result.source_path),
                    "last_error": None,
                }
            )
            for key in [
                "rights_status",
                "privacy_status",
                "profile_id",
                "source_title",
                "document_type",
                "author_or_institution",
                "optional_source_reference",
            ]:
                if result.fields.get(key):
                    job[key] = result.fields[key]
            if "retain_normalized_source" in result.fields:
                job["retain_normalized_source"] = result.fields["retain_normalized_source"].lower() == "true"
            self._save_job(run_id, job)
            thread = threading.Thread(target=self._extract_job, args=(run_id, job_id), daemon=True)
            thread.start()
            return self.get_job_progress(run_id, job_id)
        except (MultipartStreamError, DashboardPdfIntakeError, Exception) as exc:
            job["current_stage"] = "failed"
            job["last_error"] = str(exc)
            self._save_job(run_id, job)
            remove_tree(tmp_dir)
            raise IntakeJobError(str(exc)) from exc

    def _extract_job(self, run_id: str, job_id: str) -> None:
        job = self.load_job(run_id, job_id)
        tmp_dir = self._job_tmp_dir(run_id, job_id)
        pdf_path = Path(str(job.get("temp_pdf_path")))
        text_path = self.storage.run_dir(run_id) / "source/normalized_source.txt" if job.get("retain_normalized_source") else None
        try:
            if self._cancel_callback(run_id, job_id)():
                raise IntakeJobError("cancelled")
            job["current_stage"] = "validating"
            self._save_job(run_id, job)
            result = extract_text_native_pdf_from_path(
                str(job.get("display_filename") or "upload.pdf"),
                pdf_path,
                retain_extracted_text=bool(job.get("retain_normalized_source")),
                known_sha256=str(job.get("source_sha256") or ""),
                known_size_bytes=int(job.get("file_size_bytes") or 0),
                normalized_text_path=text_path,
                progress_callback=self._progress_callback(run_id, job_id),
                cancel_callback=self._cancel_callback(run_id, job_id),
            )
            self.controller.finalize_pdf_intake_job(run_id, job_id, result, text_path=text_path)
            job = self.load_job(run_id, job_id)
            job.update(
                {
                    "current_stage": "ready_to_compile",
                    "ready_to_compile": True,
                    "page_count": result.provenance["page_count"],
                    "processed_page_count": result.provenance["processed_page_count"],
                    "pages_containing_text": result.provenance["pages_containing_text"],
                    "extracted_character_count": result.provenance["extracted_character_count"],
                    "elapsed_seconds": result.provenance["processing_duration_seconds"],
                    "last_error": None,
                }
            )
            self._save_job(run_id, job)
        except Exception as exc:
            job = self.load_job(run_id, job_id)
            job["current_stage"] = "cancelled" if str(exc) == "PDF_CANCELLED" or str(exc) == "cancelled" else "failed"
            job["ready_to_compile"] = False
            job["last_error"] = str(exc)
            self._save_job(run_id, job)
        finally:
            if pdf_path.exists():
                pdf_path.unlink(missing_ok=True)
            remove_tree(tmp_dir)
