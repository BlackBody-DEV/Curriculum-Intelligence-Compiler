from io import BytesIO
from pathlib import Path
import json
import time

import pytest

from tools.course_compiler_demo.dashboard.controller import DashboardController
from tools.course_compiler_demo.dashboard.run_storage import DashboardStorage
from tools.course_compiler_demo.dashboard.multipart_stream import MultipartStreamError, receive_multipart_file


def _body(content: bytes, filename: str = "large.pdf", boundary: str = "BOUNDARY") -> tuple[bytes, str]:
    prefix = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="rights_status"\r\n\r\n'
        "approved_local_use\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode()
    suffix = f"\r\n--{boundary}--\r\n".encode()
    return prefix + content + suffix, f"multipart/form-data; boundary={boundary}"


def _minimal_pdf() -> bytes:
    from test_dashboard_pdf_intake import _minimal_text_pdf

    return _minimal_text_pdf(["Calculus I limits derivatives power rule chain rule critical points intervals"])


def _wait_ready(ctrl: DashboardController, run_id: str, job_id: str) -> dict:
    for _ in range(200):
        job = ctrl.get_intake_job(run_id, job_id)
        if job["current_stage"] == "ready_to_compile":
            return job
        assert job["current_stage"] not in {"failed", "cancelled", "interrupted"}, job
        time.sleep(0.05)
    raise AssertionError("intake job did not become ready_to_compile")


def test_streaming_multipart_writes_file_and_hashes_incrementally(tmp_path):
    content = b"%PDF-" + b"x" * 9000
    payload, content_type = _body(content)

    result = receive_multipart_file(
        BytesIO(payload),
        content_type=content_type,
        content_length=len(payload),
        destination_dir=tmp_path,
        declared_upload_bytes=len(content),
    )

    assert result.display_filename == "large.pdf"
    assert result.source_path.read_bytes() == content
    assert result.file_size_bytes == len(content)
    assert result.sha256
    assert result.fields["rights_status"] == "approved_local_use"


def test_streaming_rejects_deceptive_declared_size_and_cleans_partial_file(tmp_path):
    payload, content_type = _body(b"%PDF-test")
    with pytest.raises(MultipartStreamError, match="declared upload size mismatch"):
        receive_multipart_file(
            BytesIO(payload),
            content_type=content_type,
            content_length=len(payload),
            destination_dir=tmp_path,
            declared_upload_bytes=999,
        )

    assert not [path for path in tmp_path.iterdir() if path.name.startswith("upload_")]


def test_streaming_rejects_absent_or_short_content_length(tmp_path):
    payload, content_type = _body(b"%PDF-test")
    with pytest.raises(MultipartStreamError, match="ended before declared length"):
        receive_multipart_file(
            BytesIO(payload[:-5]),
            content_type=content_type,
            content_length=len(payload),
            destination_dir=tmp_path,
            declared_upload_bytes=9,
        )


def test_streaming_rejects_bad_boundary_and_unsupported_filename(tmp_path):
    payload, content_type = _body(b"%PDF-test", filename="bad.exe")
    with pytest.raises(Exception):
        receive_multipart_file(
            BytesIO(payload),
            content_type=content_type,
            content_length=len(payload),
            destination_dir=tmp_path,
            declared_upload_bytes=9,
        )

    with pytest.raises(MultipartStreamError, match="multipart boundary missing"):
        receive_multipart_file(
            BytesIO(payload),
            content_type="multipart/form-data",
            content_length=len(payload),
            destination_dir=tmp_path,
        )


def test_source_uses_bounded_reads_not_full_request_read():
    source = Path("tools/course_compiler_demo/dashboard/multipart_stream.py").read_text()
    assert ".read(content_length)" not in source
    assert ".body" not in source
    assert "_copy_body_to_temp" not in source
    assert "UPLOAD_CHUNK_BYTES" in source


def test_intake_job_cancellation_and_interruption_cleanup(tmp_path):
    ctrl = DashboardController(DashboardStorage(tmp_path), startup_cleanup=False)
    run = ctrl.create_run({"source_title": "Cancel"}, run_id="RUN_CANCEL")
    job = ctrl.start_pdf_intake_job(run["run_id"], {})
    tmp_dir = tmp_path / "RUN_CANCEL/intake_jobs" / f"{job['job_id']}_tmp"
    tmp_dir.mkdir(parents=True)
    (tmp_dir / "partial.pdf").write_bytes(b"partial")

    cancelled = ctrl.cancel_intake_job(run["run_id"], job["job_id"])
    assert cancelled["current_stage"] == "cancelled"
    assert not tmp_dir.exists()

    run2 = ctrl.create_run({"source_title": "Interrupted"}, run_id="RUN_INTERRUPTED")
    job2 = ctrl.start_pdf_intake_job(run2["run_id"], {})
    loaded = ctrl.intake_jobs.load_job(run2["run_id"], job2["job_id"])
    loaded["current_stage"] = "extracting"
    ctrl.intake_jobs._save_job(run2["run_id"], loaded)
    tmp_dir2 = tmp_path / "RUN_INTERRUPTED/intake_jobs" / f"{job2['job_id']}_tmp"
    tmp_dir2.mkdir(parents=True)
    (tmp_dir2 / "partial.pdf").write_bytes(b"partial")

    restarted = DashboardController(DashboardStorage(tmp_path), startup_cleanup=True)
    interrupted = restarted.get_intake_job(run2["run_id"], job2["job_id"])
    assert interrupted["current_stage"] == "interrupted"
    assert not tmp_dir2.exists()


def test_intake_job_disk_space_guard(monkeypatch, tmp_path):
    class Usage:
        free = 1

    ctrl = DashboardController(DashboardStorage(tmp_path), startup_cleanup=False)
    run = ctrl.create_run({"source_title": "Disk"}, run_id="RUN_DISK")
    job = ctrl.start_pdf_intake_job(run["run_id"], {})
    monkeypatch.setattr("tools.course_compiler_demo.dashboard.intake_jobs.shutil.disk_usage", lambda _path: Usage())

    payload, content_type = _body(b"%PDF-test")
    with pytest.raises(Exception, match="insufficient temporary disk space"):
        ctrl.receive_pdf_intake_upload(
            run["run_id"],
            job["job_id"],
            BytesIO(payload),
            content_type=content_type,
            content_length=len(payload),
            declared_upload_bytes=9,
        )

    failed = ctrl.get_intake_job(run["run_id"], job["job_id"])
    assert failed["current_stage"] == "failed"


def test_streamed_intake_run_persists_in_history_before_compile_and_after_restart(tmp_path):
    ctrl = DashboardController(DashboardStorage(tmp_path), startup_cleanup=False)
    run = ctrl.create_run({"source_title": "Persisted XL"}, run_id="RUN_STREAM_PERSIST")
    job = ctrl.start_pdf_intake_job(
        run["run_id"],
        {
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
        },
    )
    listed_receiving = ctrl.list_runs()
    assert [item["run_id"] for item in listed_receiving].count(run["run_id"]) == 1
    assert listed_receiving[0]["run_id"] == run["run_id"]
    receiving_manifest = ctrl.get_run(run["run_id"])
    assert receiving_manifest["active_intake_job_id"] == job["job_id"]

    content = _minimal_pdf()
    payload, content_type = _body(content, filename="calculus.pdf")
    ctrl.receive_pdf_intake_upload(
        run["run_id"],
        job["job_id"],
        BytesIO(payload),
        content_type=content_type,
        content_length=len(payload),
        declared_upload_bytes=len(content),
    )
    ready_job = _wait_ready(ctrl, run["run_id"], job["job_id"])
    assert ready_job["run_id"] == run["run_id"]
    assert ready_job["ready_to_compile"] is True

    source_ready = ctrl.get_run(run["run_id"])
    assert source_ready["status"] == "source_ready"
    assert source_ready["source_display_filename"] == "calculus.pdf"
    assert source_ready["source_sha256"] == ready_job["source_sha256"]
    assert source_ready["active_intake_job_id"] == job["job_id"]
    assert not list((tmp_path / run["run_id"]).rglob("*.pdf"))

    runs = ctrl.list_runs()
    assert [item["run_id"] for item in runs].count(run["run_id"]) == 1
    assert runs[0]["source_display_filename"] == "calculus.pdf"
    history_index = json.loads((tmp_path / "run_history_index.json").read_text())
    matches = [item for item in history_index["runs"] if item["run_id"] == run["run_id"]]
    assert len(matches) == 1
    assert matches[0]["status"] == "source_ready"
    assert matches[0]["source_display_filename"] == "calculus.pdf"

    refreshed = DashboardController(DashboardStorage(tmp_path), startup_cleanup=False)
    refreshed_run = refreshed.get_run(run["run_id"])
    assert refreshed_run["source_display_filename"] == "calculus.pdf"
    assert [item["run_id"] for item in refreshed.list_runs()].count(run["run_id"]) == 1

    restarted = DashboardController(DashboardStorage(tmp_path), startup_cleanup=True)
    restarted_run = restarted.get_run(run["run_id"])
    assert restarted_run["status"] == "source_ready"
    assert restarted_run["source_sha256"] == source_ready["source_sha256"]
    assert [item["run_id"] for item in restarted.list_runs()].count(run["run_id"]) == 1
    assert not list((tmp_path / run["run_id"]).rglob("*.pdf"))


def test_failed_streamed_intake_remains_visible(tmp_path):
    ctrl = DashboardController(DashboardStorage(tmp_path), startup_cleanup=False)
    run = ctrl.create_run({"source_title": "Failed visible"}, run_id="RUN_FAILED_VISIBLE")
    job = ctrl.start_pdf_intake_job(run["run_id"], {})
    payload, content_type = _body(b"not-a-pdf", filename="bad.pdf")

    ctrl.receive_pdf_intake_upload(
        run["run_id"],
        job["job_id"],
        BytesIO(payload),
        content_type=content_type,
        content_length=len(payload),
        declared_upload_bytes=len(b"not-a-pdf"),
    )

    failed_job = None
    for _ in range(100):
        failed_job = ctrl.get_intake_job(run["run_id"], job["job_id"])
        if failed_job["current_stage"] == "failed":
            break
        time.sleep(0.05)
    assert failed_job is not None
    assert failed_job["current_stage"] == "failed"
    runs = ctrl.list_runs()
    assert [item["run_id"] for item in runs].count(run["run_id"]) == 1
    assert ctrl.get_run(run["run_id"])["active_intake_job_id"] == job["job_id"]


def test_static_intake_progress_labels_upload_percent_and_capacity_separately():
    app = Path("tools/course_compiler_demo/dashboard/static/app.js").read_text()

    assert "function uploadProgressSummary(job)" in app
    assert "expected_source_bytes || job.file_size_bytes || job.declared_upload_bytes" in app
    assert "uploadComplete ? expected : received" in app
    assert "Maximum capacity used" in app
    assert "Upload state" in app
    assert "indeterminate" in app
    assert "expected_source_bytes: file.size" in app


def test_static_intake_progress_no_longer_uses_capacity_as_upload_percentage():
    app = Path("tools/course_compiler_demo/dashboard/static/app.js").read_text()

    assert "const pct = maxBytes > 0" not in app
    assert "<dt>Upload percentage</dt><dd>${esc(pct)}%</dd>" not in app
    assert "Math.floor((received / maxBytes) * 100)" not in app
