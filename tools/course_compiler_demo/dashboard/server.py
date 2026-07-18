"""Stdlib HTTP server for the local dashboard."""

from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .controller import DashboardController, DashboardControllerError
from .security import DashboardSecurityError, validate_identifier, validate_loopback


STATIC_ROOT = Path(__file__).resolve().parent


class DashboardRequestHandler(BaseHTTPRequestHandler):
    controller: DashboardController

    def log_message(self, format: str, *args) -> None:
        return

    def _json(self, payload, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _error(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self._json({"error": message}, status)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 5 * 1024 * 1024:
            raise DashboardSecurityError("request too large")
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            parts = [part for part in parsed.path.split("/") if part]
            if parsed.path == "/":
                return self._serve_static("templates/index.html")
            if parsed.path in {"/static/app.js", "/static/styles.css"}:
                return self._serve_static(parsed.path.lstrip("/"))
            if parsed.path == "/api/health":
                return self._json(self.controller.health())
            if parsed.path == "/api/profiles":
                return self._json({"profiles": self.controller.list_profiles()})
            if parsed.path == "/api/generation-families":
                return self._json({"generation_families": self.controller.list_generation_families()})
            if parsed.path == "/api/runs":
                return self._json({"runs": self.controller.list_runs()})
            if len(parts) == 3 and parts[:2] == ["api", "runs"]:
                return self._json(self.controller.get_run(parts[2]))
            if len(parts) == 4 and parts[:3] == ["api", "runs", parts[2]] and parts[3] == "results":
                return self._json(self.controller.results(parts[2]))
            if len(parts) == 5 and parts[0] == "api" and parts[1] == "runs" and parts[3] == "assessments":
                return self._json(self.controller.get_assessment(parts[2], parts[4]))
            if len(parts) == 7 and parts[0] == "api" and parts[1] == "runs" and parts[3] == "assessments" and parts[5] == "exports":
                return self._serve_export(parts[2], parts[4], parts[6])
            if len(parts) == 5 and parts[0] == "api" and parts[1] == "runs" and parts[3] == "artifacts":
                return self._json({"artifact": self.controller.artifact(parts[2], parts[4])})
            return self._error("not found", HTTPStatus.NOT_FOUND)
        except Exception as exc:
            return self._error(str(exc))

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)
            parts = [part for part in parsed.path.split("/") if part]
            payload = self._read_json()
            if parsed.path == "/api/runs":
                return self._json(self.controller.create_run(payload))
            if len(parts) == 4 and parts[0] == "api" and parts[1] == "runs":
                run_id = parts[2]
                action = parts[3]
                if action == "source":
                    content = str(payload.get("content", "")).encode("utf-8")
                    return self._json(self.controller.upload_source(run_id, filename=str(payload.get("filename", "")), content=content, metadata=payload))
                if action == "rights":
                    return self._json(self.controller.confirm_rights(run_id, payload))
                if action == "profile":
                    return self._json(self.controller.select_profile(run_id, str(payload.get("profile_id", ""))))
                if action == "compile":
                    return self._json(self.controller.compile_run(run_id, selected_micro_skill=payload.get("selected_micro_skill")))
                if action == "curriculum-review":
                    return self._json(self.controller.curriculum_review(run_id, payload.get("decisions", [])))
                if action == "assessments":
                    return self._json(self.controller.create_assessment(run_id, payload))
            if len(parts) == 6 and parts[0] == "api" and parts[1] == "runs" and parts[3] == "assessments":
                run_id, assessment_id, action = parts[2], parts[4], parts[5]
                if action == "generate":
                    return self._json(self.controller.generate_assessment(run_id, assessment_id, history_run_ids=payload.get("history_run_ids")))
                if action == "review":
                    return self._json(self.controller.review_assessment(run_id, assessment_id, payload.get("review_records", [])))
                if action == "regenerate":
                    return self._json(self.controller.regenerate(run_id, assessment_id, str(payload.get("slot_id", "")), int(payload.get("child_seed", 1))))
            return self._error("not found", HTTPStatus.NOT_FOUND)
        except (DashboardControllerError, DashboardSecurityError, ValueError, KeyError, json.JSONDecodeError) as exc:
            return self._error(str(exc))

    def _serve_static(self, rel: str) -> None:
        path = STATIC_ROOT / rel
        if not path.exists() or not path.is_file():
            return self._error("not found", HTTPStatus.NOT_FOUND)
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_export(self, run_id: str, assessment_id: str, export_type: str) -> None:
        path = self.controller.export_path(run_id, assessment_id, export_type)
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Disposition", f"attachment; filename={path.name}")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_server(host: str, port: int, controller: DashboardController | None = None) -> ThreadingHTTPServer:
    host, port = validate_loopback(host, port)
    handler = type("BoundDashboardRequestHandler", (DashboardRequestHandler,), {"controller": controller or DashboardController()})
    return ThreadingHTTPServer((host, port), handler)
