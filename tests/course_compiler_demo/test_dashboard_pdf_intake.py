import base64
import inspect
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from tools.course_compiler_demo.dashboard import pdf_intake
from tools.course_compiler_demo.dashboard.controller import DashboardController, DashboardControllerError
from tools.course_compiler_demo.dashboard.pdf_intake import DashboardPdfIntakeError, extract_text_native_pdf
from tools.course_compiler_demo.dashboard.run_storage import DashboardStorage, load_json


def _minimal_text_pdf(pages: list[str]) -> bytes:
    objects: list[bytes] = []

    def add(value: str | bytes) -> None:
        objects.append(value.encode("latin-1") if isinstance(value, str) else value)

    add("1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    kids = " ".join(f"{3 + index * 3} 0 R" for index in range(len(pages)))
    add(f"2 0 obj << /Type /Pages /Kids [{kids}] /Count {len(pages)} >> endobj\n")
    for index, text in enumerate(pages):
        page_id = 3 + index * 3
        font_id = page_id + 1
        content_id = page_id + 2
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
        add(
            f"{page_id} 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >> endobj\n"
        )
        add(f"{font_id} 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")
        add(f"{content_id} 0 obj << /Length {len(stream)} >> stream\n".encode("latin-1") + stream + b"\nendstream endobj\n")

    output = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(output))
        output += obj
    xref = len(output)
    output += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for offset in offsets:
        output += f"{offset:010d} 00000 n \n".encode("latin-1")
    output += f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("latin-1")
    return output


CALCULUS_TEXT = (
    "Calculus I review. Evaluate a limit using limit laws. "
    "Use derivatives, apply the power rule, and apply the chain rule. "
    "Find critical points and analyze increasing and decreasing intervals. "
)


def _large_calculus_pdf() -> bytes:
    page_text = (CALCULUS_TEXT * 120).strip()
    return _minimal_text_pdf([f"Page {index + 1}. {page_text}" for index in range(300)])


def _blank_pdf(page_count: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(page_count):
        writer.add_blank_page(width=612, height=792)
    path = Path("/tmp/axiomiq_blank_test.pdf")
    with path.open("wb") as handle:
        writer.write(handle)
    data = path.read_bytes()
    path.unlink()
    return data


def _zero_page_pdf() -> bytes:
    writer = PdfWriter()
    path = Path("/tmp/axiomiq_zero_test.pdf")
    with path.open("wb") as handle:
        writer.write(handle)
    data = path.read_bytes()
    path.unlink()
    return data


def _encrypted_pdf() -> bytes:
    source = Path("/tmp/axiomiq_source_text.pdf")
    source.write_bytes(_minimal_text_pdf(["Subject Physics encrypted"]))
    reader = PdfReader(str(source))
    writer = PdfWriter()
    writer.append_pages_from_reader(reader)
    writer.encrypt("secret")
    path = Path("/tmp/axiomiq_encrypted_test.pdf")
    with path.open("wb") as handle:
        writer.write(handle)
    data = path.read_bytes()
    source.unlink()
    path.unlink()
    return data


def _controller(tmp_path):
    return DashboardController(DashboardStorage(tmp_path))


def test_single_and_multi_page_pdf_extracts_ordered_text_and_hashes():
    result = extract_text_native_pdf(
        "physics.pdf",
        _minimal_text_pdf(["Subject Physics page one", "Newton page two"]),
        retain_extracted_text=True,
    )

    assert "Subject Physics page one" in result.text
    assert result.text.index("page one") < result.text.index("page two")
    assert result.provenance["page_count"] == 2
    assert result.provenance["processed_page_count"] == 2
    assert result.provenance["pages_containing_text"] == 2
    assert result.provenance["file_size_bytes"] > 0
    assert result.provenance["processing_duration_seconds"] >= 0
    assert result.provenance["applied_resource_limits"]["max_upload_bytes"] == pdf_intake.MAX_UPLOAD_BYTES
    assert result.provenance["blank_page_count"] == 0
    assert result.provenance["original_pdf_sha256"]
    assert result.provenance["extracted_text_sha256"]
    assert result.provenance["pypdf_version"] == "6.14.2"
    assert result.provenance["ocr_used"] is False
    assert result.provenance["external_service_used"] is False
    assert result.provenance["raw_pdf_retained"] is False
    assert result.provenance["extracted_text_retained"] is True


def test_unicode_and_blank_page_inside_valid_pdf():
    result = extract_text_native_pdf(
        "unicode.pdf",
        _minimal_text_pdf(["caf\\351 force component", "", "Newton"]),
        retain_extracted_text=False,
    )

    assert "café force component" in result.text
    assert "Newton" in result.text
    assert result.provenance["blank_page_count"] == 1
    assert result.provenance["pages_containing_text"] == 2
    assert result.provenance["extracted_text_retained"] is False


def test_pdf_rejection_errors_and_decrypt_never_called(monkeypatch):
    called = {"decrypt": False}

    def forbidden_decrypt(*_args, **_kwargs):
        called["decrypt"] = True
        raise AssertionError("decrypt must not be called")

    monkeypatch.setattr(PdfReader, "decrypt", forbidden_decrypt)
    cases = [
        ("encrypted.pdf", _encrypted_pdf(), pdf_intake.PDF_ENCRYPTED_OR_PASSWORD_PROTECTED),
        ("corrupt.pdf", b"%PDF-1.4\nnot a complete pdf", pdf_intake.PDF_CORRUPT_OR_INVALID),
        ("empty.pdf", b"", pdf_intake.PDF_EMPTY_FILE),
        ("fake.pdf", b"not a pdf", pdf_intake.PDF_CORRUPT_OR_INVALID),
        ("zero.pdf", _zero_page_pdf(), pdf_intake.PDF_ZERO_PAGES),
        ("textless.pdf", _blank_pdf(), pdf_intake.PDF_TEXT_EXTRACTION_REQUIRED_OCR_NOT_SUPPORTED),
        ("wrong.txt", _minimal_text_pdf(["Subject Physics"]), pdf_intake.PDF_UNSUPPORTED_FILE_TYPE),
    ]
    for filename, content, code in cases:
        with pytest.raises(DashboardPdfIntakeError, match=code):
            extract_text_native_pdf(filename, content, retain_extracted_text=False)

    assert called["decrypt"] is False


def test_pdf_resource_limits(monkeypatch):
    with pytest.raises(DashboardPdfIntakeError, match=pdf_intake.PDF_RESOURCE_LIMIT_EXCEEDED):
        extract_text_native_pdf("large.pdf", b"%PDF-" + b"x" * pdf_intake.MAX_UPLOAD_BYTES, retain_extracted_text=False)

    monkeypatch.setattr(pdf_intake, "MAX_PDF_PAGES", 1)
    with pytest.raises(DashboardPdfIntakeError, match=pdf_intake.PDF_RESOURCE_LIMIT_EXCEEDED):
        extract_text_native_pdf("pages.pdf", _minimal_text_pdf(["one", "two"]), retain_extracted_text=False)

    monkeypatch.setattr(pdf_intake, "MAX_PDF_EXTRACTED_CHARACTERS", 5)
    with pytest.raises(DashboardPdfIntakeError, match=pdf_intake.PDF_RESOURCE_LIMIT_EXCEEDED):
        extract_text_native_pdf("chars.pdf", _minimal_text_pdf(["Subject Physics"]), retain_extracted_text=False)

    ticks = iter([0.0, 0.0, 0.0, 21.0])
    monkeypatch.setattr(pdf_intake.time, "monotonic", lambda: next(ticks))
    with pytest.raises(DashboardPdfIntakeError, match=pdf_intake.PDF_RESOURCE_LIMIT_EXCEEDED):
        extract_text_native_pdf("slow.pdf", _minimal_text_pdf(["Subject Physics"]), retain_extracted_text=False)


def test_large_text_native_pdf_over_previous_limit_uploads_compiles_and_tracks_retention(tmp_path):
    large_pdf = _large_calculus_pdf()
    assert len(large_pdf) > 5 * 1024 * 1024
    assert len(large_pdf) < pdf_intake.MAX_UPLOAD_BYTES

    ctrl = _controller(tmp_path)
    run = ctrl.create_run({"source_title": "Large Calculus"}, run_id="RUN_LARGE_CALCULUS")
    uploaded = ctrl.upload_source(
        run["run_id"],
        filename="large-calculus.pdf",
        content=large_pdf,
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
        },
    )

    assert uploaded["source_display_filename"] == "large-calculus.pdf"
    assert uploaded["pdf_validation"]["file_size_bytes"] == len(large_pdf)
    assert uploaded["pdf_validation"]["page_count"] == 300
    assert uploaded["pdf_validation"]["processed_page_count"] == 300
    assert uploaded["pdf_validation"]["pages_containing_text"] == 300
    assert uploaded["pdf_validation"]["original_pdf_sha256"]
    assert uploaded["pdf_validation"]["extracted_text_sha256"]
    assert uploaded["pdf_validation"]["raw_pdf_retained"] is False
    assert uploaded["pdf_validation"]["extracted_text_retained"] is True
    assert uploaded["pdf_validation"]["applied_resource_limits"]["max_pdf_pages"] == 1500
    assert not list((tmp_path / "RUN_LARGE_CALCULUS").rglob("*.pdf"))
    assert (tmp_path / "RUN_LARGE_CALCULUS/source/normalized_source.txt").exists()

    compiled = ctrl.compile_run(run["run_id"])
    assert compiled["compiler_status"] == "complete"
    assert compiled["detected_subject"] == "MATHEMATICS"
    assert compiled["detected_course_level"] == "CALCULUS_I"
    assert any(item["run_id"] == run["run_id"] for item in ctrl.list_runs())

    extracted = (tmp_path / "RUN_LARGE_CALCULUS/source/normalized_source.txt").read_text()
    assert extracted.index("Page 1") < extracted.index("Page 300")


def test_large_pdf_without_retention_compiles_from_session_cache_and_removes_text(tmp_path):
    ctrl = _controller(tmp_path)
    run = ctrl.create_run({"source_title": "No retain"}, run_id="RUN_LARGE_NO_RETAIN")
    ctrl.upload_source(
        run["run_id"],
        filename="large-calculus.pdf",
        content=_large_calculus_pdf(),
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": False,
        },
    )

    assert not (tmp_path / "RUN_LARGE_NO_RETAIN/source/normalized_source.txt").exists()
    compiled = ctrl.compile_run(run["run_id"])
    assert compiled["compiler_status"] == "complete"
    assert compiled["raw_or_normalized_source_retained"] is False


def test_pdf_temporary_directory_cleanup_on_success_and_failure(monkeypatch):
    created: list[Path] = []
    original_temporary_directory = pdf_intake.tempfile.TemporaryDirectory

    class TrackingTemporaryDirectory:
        def __init__(self, *args, **kwargs):
            self._inner = original_temporary_directory(*args, **kwargs)

        def __enter__(self):
            path = Path(self._inner.__enter__())
            created.append(path)
            return str(path)

        def __exit__(self, *args):
            return self._inner.__exit__(*args)

    monkeypatch.setattr(pdf_intake.tempfile, "TemporaryDirectory", TrackingTemporaryDirectory)

    extract_text_native_pdf("ok.pdf", _minimal_text_pdf(["Subject Physics"]), retain_extracted_text=False)
    with pytest.raises(DashboardPdfIntakeError, match=pdf_intake.PDF_TEXT_EXTRACTION_REQUIRED_OCR_NOT_SUPPORTED):
        extract_text_native_pdf("blank.pdf", _blank_pdf(), retain_extracted_text=False)

    assert created
    assert all(not path.exists() for path in created)


def test_pdf_upload_rights_gate_retention_and_compile_path(tmp_path):
    ctrl = _controller(tmp_path)
    run = ctrl.create_run({"source_title": "PDF"}, run_id="RUN_PDF")
    uploaded = ctrl.upload_source(
        run["run_id"],
        filename="physics.pdf",
        content=_minimal_text_pdf(["Subject Physics", "INTRO_PHYSICS_MECHANICS", "Newton's Second Law F net equals m a"]),
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
            "profile_id": "PHYSICS_INTRO_MECHANICS_PROFILE_V1",
        },
    )

    assert uploaded["status"] == "source_ready"
    assert uploaded["source_display_filename"] == "physics.pdf"
    assert uploaded["source_format"] == "pdf"
    assert uploaded["source_sha256"]
    assert uploaded["rights_status"] == "approved_local_use"
    assert uploaded["privacy_status"] == "non_private"
    assert uploaded["selected_profile_id"] == "PHYSICS_INTRO_MECHANICS_PROFILE_V1"
    assert uploaded["pdf_validation"]["page_count"] == 3
    receipt = load_json(tmp_path / "RUN_PDF/source/source_receipt.json")
    assert receipt["pdf_provenance"]["raw_pdf_retained"] is False
    assert receipt["pdf_provenance"]["extracted_text_retained"] is True
    assert not list((tmp_path / "RUN_PDF").rglob("*.pdf"))
    compiled = ctrl.compile_run(run["run_id"])
    assert compiled["compiler_status"] == "complete"
    assert ctrl.results(run["run_id"])["topics"]


def test_pdf_no_extracted_text_retention_and_failed_extraction_state(tmp_path):
    ctrl = _controller(tmp_path)
    run = ctrl.create_run({"source_title": "PDF"}, run_id="RUN_NO_RETAIN_PDF")
    ctrl.upload_source(
        run["run_id"],
        filename="physics.pdf",
        content=_minimal_text_pdf(["Subject Physics", "INTRO_PHYSICS_MECHANICS", "Newton's Second Law F net equals m a"]),
        metadata={
            "retain_normalized_source": False,
            "profile_id": "PHYSICS_INTRO_MECHANICS_PROFILE_V1",
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
        },
    )
    assert not (tmp_path / "RUN_NO_RETAIN_PDF/source/normalized_source.txt").exists()
    assert ctrl.compile_run(run["run_id"])["compiler_status"] == "complete"
    assert run["run_id"] not in ctrl._source_text_cache

    failed = ctrl.create_run({"source_title": "Bad PDF"}, run_id="RUN_BAD_PDF")
    with pytest.raises(DashboardPdfIntakeError):
        ctrl.upload_source(failed["run_id"], filename="bad.pdf", content=b"%PDF-bad", metadata={})
    manifest = ctrl.get_run(failed["run_id"])
    assert manifest["compiler_status"] == "not_run"
    assert manifest["status"] == "created"
    assert not (tmp_path / "RUN_BAD_PDF/source/source_receipt.json").exists()


def test_txt_and_md_behavior_unchanged(tmp_path):
    ctrl = _controller(tmp_path)
    for run_id, filename in [("RUN_TXT", "physics.txt"), ("RUN_MD", "physics.md")]:
        run = ctrl.create_run({"source_title": run_id}, run_id=run_id)
        updated = ctrl.upload_source(
            run["run_id"],
            filename=filename,
            content=b"Subject: Physics\nNewton's Second Law states F_net = m a.",
            metadata={"retain_normalized_source": True},
        )
        assert updated["source_format"] == filename.rsplit(".", 1)[1]


def test_pdf_workflow_exports_locking_regeneration_and_reopen(tmp_path):
    ctrl = _controller(tmp_path)
    run = ctrl.create_run({"source_title": "PDF workflow"}, run_id="RUN_PDF_FLOW")
    ctrl.upload_source(
        run["run_id"],
        filename="physics.pdf",
        content=_minimal_text_pdf(["Subject Physics", "INTRO_PHYSICS_MECHANICS", "Newton's Second Law states F net equals m a"]),
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
            "profile_id": "PHYSICS_INTRO_MECHANICS_PROFILE_V1",
        },
    )
    assert ctrl.compile_run(run["run_id"])["compiler_status"] == "complete"
    ctrl.curriculum_review(run["run_id"], [{"candidate_id": "MS_003", "candidate_type": "micro_skill", "decision": "accepted"}])
    blueprint = ctrl.create_assessment(
        run["run_id"],
        {"assessment_id": "ASSESS_PDF", "generation_family_id": "GF_PHYSICS_NEWTON_SECOND_LAW_1D_V1", "question_count": 10},
    )
    data = ctrl.generate_assessment(run["run_id"], blueprint["assessment_id"])
    assert data["validation_report"]["validation_status"] == "pass"
    first, second = data["assessment"]["questions"][0], data["assessment"]["questions"][1]
    ctrl.review_assessment(run["run_id"], blueprint["assessment_id"], [{"question_id": first["question_id"], "decision": "accepted", "locked": True}])
    locked_before = ctrl.get_assessment(run["run_id"], blueprint["assessment_id"])["assessment"]["questions"][0]
    ctrl.regenerate(run["run_id"], blueprint["assessment_id"], second["slot_id"], child_seed=20260721)
    locked_after = ctrl.get_assessment(run["run_id"], blueprint["assessment_id"])["assessment"]["questions"][0]
    assert locked_before == locked_after
    student_json = ctrl.export_path(run["run_id"], blueprint["assessment_id"], "student_json").read_text()
    instructor_json = ctrl.export_path(run["run_id"], blueprint["assessment_id"], "instructor_json").read_text()
    assert "expected_answer" not in student_json
    assert "solution_steps" not in student_json
    assert "expected_answer" in instructor_json

    restarted = DashboardController(DashboardStorage(tmp_path))
    reopened = restarted.get_run(run["run_id"])
    assert reopened["run_id"] == run["run_id"]
    assert reopened["assessment_ids"] == ["ASSESS_PDF"]


def test_server_pdf_payload_is_base64_and_no_forbidden_pdf_behaviors():
    import tools.course_compiler_demo.dashboard.server as server

    assert base64.b64encode(b"pdf bytes").decode("ascii")
    source = inspect.getsource(pdf_intake) + inspect.getsource(server)
    forbidden = ["pytesseract", "tesseract", "easyocr", "ocrmypdf", "requests", "httpx", "adaptive-platform"]
    assert all(token not in source for token in forbidden)
    assert ".decrypt(" not in source


def test_calculus_run_filters_and_rejects_physics_assessment_family(tmp_path):
    ctrl = _controller(tmp_path)
    run = ctrl.create_run({"source_title": "Calculus"}, run_id="RUN_CALCULUS_GUARD")
    ctrl.upload_source(
        run["run_id"],
        filename="calculus.pdf",
        content=_minimal_text_pdf([CALCULUS_TEXT]),
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
        },
    )
    compiled = ctrl.compile_run(run["run_id"])
    assert compiled["compiler_status"] == "complete"
    ctrl.curriculum_review(
        run["run_id"],
        [{"candidate_id": "MSKILL_001", "candidate_type": "micro_skill", "decision": "accepted"}],
    )

    compatible = ctrl.compatible_generation_families(run["run_id"])
    assert compatible["generation_families"] == []
    assert "Assessment generation remains a content gap" in compatible["content_gap"]
    with pytest.raises(DashboardControllerError, match="incompatible_assessment_generation_family"):
        ctrl.create_assessment(
            run["run_id"],
            {
                "assessment_id": "ASSESS_BAD_PHYSICS",
                "generation_family_id": "GF_PHYSICS_NEWTON_SECOND_LAW_1D_V1",
                "question_count": 10,
            },
        )
    guarded = ctrl.get_run(run["run_id"])
    assert guarded["status"] == "assessment_ready"
    assert guarded["compiler_status"] == "complete"
    assert guarded["last_error"] == "incompatible_assessment_generation_family"


def test_physics_run_keeps_compatible_assessment_family(tmp_path):
    ctrl = _controller(tmp_path)
    run = ctrl.create_run({"source_title": "Physics"}, run_id="RUN_PHYSICS_COMPAT")
    ctrl.upload_source(
        run["run_id"],
        filename="physics.pdf",
        content=_minimal_text_pdf(["Subject Physics", "INTRO_PHYSICS_MECHANICS", "Newton's Second Law F net equals m a"]),
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
            "profile_id": "PHYSICS_INTRO_MECHANICS_PROFILE_V1",
        },
    )
    ctrl.compile_run(run["run_id"])
    ctrl.curriculum_review(run["run_id"], [{"candidate_id": "MS_003", "candidate_type": "micro_skill", "decision": "accepted"}])

    families = ctrl.compatible_generation_families(run["run_id"])["generation_families"]
    assert [item["generation_family_id"] for item in families] == ["GF_PHYSICS_NEWTON_SECOND_LAW_1D_V1"]
    blueprint = ctrl.create_assessment(
        run["run_id"],
        {"assessment_id": "ASSESS_PHYSICS_COMPAT", "generation_family_id": "GF_PHYSICS_NEWTON_SECOND_LAW_1D_V1", "question_count": 10},
    )
    assert blueprint["subject_code"] == "PHYSICS"


def test_pdf_upload_manifest_survives_reopen_and_compile_results_persist(tmp_path):
    ctrl = _controller(tmp_path)
    run = ctrl.create_run({"source_title": "Calculus source"}, run_id="RUN_REOPEN")
    uploaded = ctrl.upload_source(
        run["run_id"],
        filename="calculus.pdf",
        content=_minimal_text_pdf(["Subject Physics", "INTRO_PHYSICS_MECHANICS", "Newton's Second Law F net equals m a"]),
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
            "profile_id": "PHYSICS_INTRO_MECHANICS_PROFILE_V1",
        },
    )
    assert uploaded["run_id"] == run["run_id"]
    assert uploaded["status"] == "source_ready"
    assert uploaded["source_display_filename"] == "calculus.pdf"

    reopened = DashboardController(DashboardStorage(tmp_path))
    persisted_upload = reopened.get_run(run["run_id"])
    assert persisted_upload["source_display_filename"] == "calculus.pdf"
    assert persisted_upload["status"] == "source_ready"

    compiled = reopened.compile_run(run["run_id"])
    assert compiled["status"] == "compiled"
    assert compiled["compiler_status"] == "complete"
    assert compiled["artifact_index"]
    assert compiled["last_error"] is None

    reopened_again = DashboardController(DashboardStorage(tmp_path))
    persisted_compile = reopened_again.get_run(run["run_id"])
    assert persisted_compile["source_display_filename"] == "calculus.pdf"
    assert persisted_compile["compiler_status"] == "complete"
    assert persisted_compile["artifact_index"]
