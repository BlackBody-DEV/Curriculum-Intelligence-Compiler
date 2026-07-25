from pathlib import Path
import http.client
import importlib.util
import socket
import threading
import time

import pytest

from tools.course_compiler_demo.dashboard.controller import DashboardController
from tools.course_compiler_demo.dashboard.run_storage import DashboardStorage
from tools.course_compiler_demo.dashboard.server import build_server


_PDF_HELPERS_PATH = Path(__file__).with_name("test_dashboard_pdf_intake.py")
_PDF_HELPERS_SPEC = importlib.util.spec_from_file_location("dashboard_pdf_intake_helpers", _PDF_HELPERS_PATH)
assert _PDF_HELPERS_SPEC and _PDF_HELPERS_SPEC.loader
_PDF_HELPERS = importlib.util.module_from_spec(_PDF_HELPERS_SPEC)
_PDF_HELPERS_SPEC.loader.exec_module(_PDF_HELPERS)
_large_calculus_pdf = _PDF_HELPERS._large_calculus_pdf


def _unused_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", 0))
        except PermissionError:
            pytest.skip("local loopback socket binding is unavailable in this sandbox")
        return int(sock.getsockname()[1])


class _MultipartFileStream:
    def __init__(self, path: Path, *, boundary: str, fields: dict[str, str]) -> None:
        self.path = path
        self.boundary = boundary
        prefix_parts = []
        for key, value in fields.items():
            prefix_parts.append(
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
                f"{value}\r\n"
            )
        prefix_parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        )
        self.prefix = "".join(prefix_parts).encode("utf-8")
        self.suffix = f"\r\n--{boundary}--\r\n".encode("utf-8")
        self._file = path.open("rb")
        self._prefix_offset = 0
        self._suffix_offset = 0
        self._file_done = False

    @property
    def content_length(self) -> int:
        return len(self.prefix) + self.path.stat().st_size + len(self.suffix)

    @property
    def content_type(self) -> str:
        return f"multipart/form-data; boundary={self.boundary}"

    def read(self, size: int = -1) -> bytes:
        if size == 0:
            return b""
        parts: list[bytes] = []
        remaining = size if size and size > 0 else 8 * 1024 * 1024
        if self._prefix_offset < len(self.prefix):
            chunk = self.prefix[self._prefix_offset : self._prefix_offset + remaining]
            self._prefix_offset += len(chunk)
            parts.append(chunk)
            remaining -= len(chunk)
        if remaining and not self._file_done:
            chunk = self._file.read(remaining)
            if chunk:
                parts.append(chunk)
                remaining -= len(chunk)
            else:
                self._file_done = True
        if remaining and self._file_done and self._suffix_offset < len(self.suffix):
            chunk = self.suffix[self._suffix_offset : self._suffix_offset + remaining]
            self._suffix_offset += len(chunk)
            parts.append(chunk)
        return b"".join(parts)

    def readline(self, size: int = -1) -> bytes:
        chunks = []
        while size < 0 or sum(len(item) for item in chunks) < size:
            chunk = self.read(1)
            if not chunk:
                break
            chunks.append(chunk)
            if chunk == b"\n":
                break
        return b"".join(chunks)

    def close(self) -> None:
        self._file.close()


def test_real_xl_pdf_path_uploads_extracts_compiles_and_cleans(tmp_path):
    fixture = Path("/Users/fanarichardson/Documents/AxiomIQ Test Files/axiomiq-xl-calculus-human-acceptance.pdf")
    if not fixture.exists():
        pytest.skip("375+ MB human-acceptance PDF fixture is not present")
    if fixture.stat().st_size < 375_000_000:
        pytest.skip("human-acceptance PDF fixture is present but below the 375+ MB XL gate")
    if fixture.stat().st_size > 512 * 1024 * 1024:
        pytest.fail("human-acceptance PDF fixture exceeds the 512 MiB XL gate")

    ctrl = DashboardController(DashboardStorage(tmp_path))
    run = ctrl.create_run({"source_title": "XL Calculus"}, run_id="RUN_XL_REAL")
    metadata = {
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
    }
    job = ctrl.start_pdf_intake_job(run["run_id"], metadata)
    stream = _MultipartFileStream(
        fixture,
        boundary="XLBOUNDARY",
        fields={**metadata, "retain_normalized_source": "true"},
    )
    server = build_server("127.0.0.1", _unused_loopback_port(), controller=ctrl)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        conn = http.client.HTTPConnection(host, port, timeout=120)
        conn.request(
            "POST",
            f"/api/runs/{run['run_id']}/intake-jobs/{job['job_id']}/upload",
            body=stream,
            headers={
                "Content-Type": stream.content_type,
                "Content-Length": str(stream.content_length),
                "X-Declared-Upload-Bytes": str(fixture.stat().st_size),
            },
        )
        response = conn.getresponse()
        body = response.read()
        conn.close()
        assert response.status == 200, body.decode("utf-8", errors="replace")
    finally:
        stream.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    for _ in range(300):
        job = ctrl.get_intake_job(run["run_id"], job["job_id"])
        if job["current_stage"] == "ready_to_compile":
            break
        assert job["current_stage"] not in {"failed", "cancelled", "interrupted"}
        time.sleep(0.1)
    uploaded = ctrl.get_run(run["run_id"])

    assert uploaded["status"] == "source_ready"
    assert uploaded["source_file_size_bytes"] == fixture.stat().st_size
    assert uploaded["pdf_validation"]["page_count"] >= 300
    assert uploaded["pdf_validation"]["raw_pdf_retained"] is False
    assert uploaded["pdf_validation"]["extracted_text_retained"] is True
    compiled = ctrl.compile_run(run["run_id"])
    assert compiled["compiler_status"] == "complete"
    assert compiled["artifact_index"]
    assert not list((tmp_path / "RUN_XL_REAL").rglob("*.pdf"))


def test_xl_regression_uses_controller_path_without_real_fixture(tmp_path):
    data = _large_calculus_pdf()
    assert len(data) > 5 * 1024 * 1024
    ctrl = DashboardController(DashboardStorage(tmp_path))
    run = ctrl.create_run({"source_title": "Generated XL Regression"}, run_id="RUN_XL_GENERATED")
    uploaded = ctrl.upload_source(
        run["run_id"],
        filename="generated-large-calculus.pdf",
        content=data,
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
        },
    )
    assert uploaded["pdf_validation"]["page_count"] == 300
    assert uploaded["pdf_validation"]["pages_containing_text"] == 300
    assert ctrl.compile_run(run["run_id"])["compiler_status"] == "complete"
