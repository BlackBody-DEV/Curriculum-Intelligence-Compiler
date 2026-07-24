from pathlib import Path

from tools.course_compiler_demo.dashboard.controller import DashboardController
from tools.course_compiler_demo.dashboard.run_storage import DashboardStorage


PHYSICS_TEXT = b"Subject: Physics\nINTRO_PHYSICS_MECHANICS\nNewton's Second Law states F_net = m a."
CALCULUS_TEXT = (
    "Calculus I review. Evaluate a limit using limit laws. "
    "Use derivatives, apply the power rule, and apply the chain rule. "
    "Find critical points and analyze increasing and decreasing intervals."
)


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


def _compiled_physics_run(tmp_path, *, retain_source=True):
    ctrl = DashboardController(DashboardStorage(tmp_path))
    run = ctrl.create_run({"source_title": "Physics"}, run_id="RUN_FLOW")
    ctrl.upload_source(
        run["run_id"],
        filename="physics.pdf",
        content=_minimal_text_pdf(["Subject Physics", "INTRO_PHYSICS_MECHANICS", "Newton's Second Law F net equals m a"]),
        metadata={
            "rights_status": "owned_by_axiomiq",
            "privacy_status": "non_private",
            "retain_normalized_source": retain_source,
            "profile_id": "PHYSICS_INTRO_MECHANICS_PROFILE_V1",
        },
    )
    compiled = ctrl.compile_run(run["run_id"])
    return ctrl, compiled


def test_compile_summary_exposes_operator_readable_results_and_persistence(tmp_path):
    ctrl, compiled = _compiled_physics_run(tmp_path, retain_source=True)

    assert compiled["compiler_status"] == "complete"
    assert compiled["status"] == "compiled"
    summary = ctrl.compile_summary(compiled["run_id"])
    assert summary["operator_message"] == "Compilation complete"
    assert summary["run_id"] == compiled["run_id"]
    assert summary["source_title"] == "Physics"
    assert summary["selected_profile_id"] == "PHYSICS_INTRO_MECHANICS_PROFILE_V1"
    assert summary["topic_count"] > 0
    assert summary["micro_skill_count"] > 0
    assert any(item["name"] for item in summary["topics"])
    assert any(item["name"] for item in summary["micro_skills"])
    assert summary["retention"]["raw_pdf_retained"] is False
    assert summary["retention"]["extracted_text_retained"] is True
    assert summary["persistence"]["run_saved_to_dashboard_history"] is True
    assert summary["persistence"]["manifest_saved"] is True
    assert summary["persistence"]["source_metadata_saved"] is True
    assert summary["persistence"]["compiler_outputs_saved"] is True
    assert summary["next_steps"] == [
        "Review Curriculum",
        "Save Review Decisions",
        "Configure Assessment",
        "Generate Questions",
    ]


def test_compile_summary_reports_no_extracted_text_retention_when_disabled(tmp_path):
    ctrl, compiled = _compiled_physics_run(tmp_path, retain_source=False)

    assert compiled["compiler_status"] == "complete"
    summary = ctrl.compile_summary(compiled["run_id"])
    assert summary["retention"]["raw_pdf_retained"] is False
    assert summary["retention"]["extracted_text_retained"] is False
    assert summary["retention"]["normalized_source_retained"] is False
    assert not (tmp_path / "RUN_FLOW/source/normalized_source.txt").exists()


def test_empty_curriculum_output_fails_visibly(tmp_path):
    ctrl = DashboardController(DashboardStorage(tmp_path))

    def empty_compile(manifest, _selected_micro_skill):
        ctrl.storage.write_json_artifact(manifest, "topic_candidates", "compiler/topic_candidates.json", {"topic_candidates": []})
        ctrl.storage.write_json_artifact(manifest, "micro_skill_candidates", "compiler/micro_skill_candidates.json", {"micro_skill_candidates": []})
        ctrl.storage.write_json_artifact(manifest, "content_gaps", "compiler/content_gaps.json", {"content_gaps": []})

    ctrl._compile_physics = empty_compile
    run = ctrl.create_run({"source_title": "Empty"}, run_id="RUN_EMPTY")
    ctrl.upload_source(
        run["run_id"],
        filename="physics.txt",
        content=PHYSICS_TEXT,
        metadata={
            "retain_normalized_source": True,
            "profile_id": "PHYSICS_INTRO_MECHANICS_PROFILE_V1",
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
        },
    )
    failed = ctrl.compile_run(run["run_id"])

    assert failed["compiler_status"] == "failed"
    assert failed["status"] == "failed"
    assert "no usable curriculum results" in failed["last_error"]
    summary = ctrl.compile_summary(run["run_id"])
    assert summary["status"] == "compilation_blocked"
    assert summary["operator_message"] == "Compilation did not produce usable curriculum results"


def test_compile_is_rejected_before_source_ready_state(tmp_path):
    ctrl = DashboardController(DashboardStorage(tmp_path))
    run = ctrl.create_run({"source_title": "Created only"}, run_id="RUN_CREATED")

    try:
        ctrl.compile_run(run["run_id"])
    except Exception as exc:
        assert "source upload" in str(exc)
    else:
        raise AssertionError("created run must not compile")

    unchanged = ctrl.get_run(run["run_id"])
    assert unchanged["status"] == "created"
    assert unchanged["compiler_status"] == "not_run"


def test_calculus_pdf_compiles_without_selected_profile(tmp_path):
    ctrl = DashboardController(DashboardStorage(tmp_path))
    run = ctrl.create_run({"source_title": "Calculus"}, run_id="RUN_CALCULUS")
    uploaded = ctrl.upload_source(
        run["run_id"],
        filename="axiomiq-calculus-test.pdf",
        content=_minimal_text_pdf([CALCULUS_TEXT]),
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
        },
    )
    assert uploaded["status"] == "source_ready"
    assert uploaded["selected_profile_id"] == ""

    compiled = ctrl.compile_run(run["run_id"])
    assert compiled["status"] == "compiled"
    assert compiled["compiler_status"] == "complete"
    assert compiled["detected_subject"] == "MATHEMATICS"
    assert compiled["detected_course_level"] == "CALCULUS_I"
    assert compiled["profile_alignment_status"] == "candidate_new"
    assert compiled["review_required"] is True
    assert compiled["student_visible"] is False
    assert compiled["all_outputs_demo_unverified"] is True

    results = ctrl.results(run["run_id"])
    topic_names = {item["topic_name"] for item in results["topics"]}
    skill_names = {item["micro_skill_name"] for item in results["micro_skills"]}
    assert {"Limits", "Derivatives", "Applications of Derivatives"} <= topic_names
    assert {
        "Evaluate a Limit",
        "Apply the Power Rule",
        "Apply the Chain Rule",
        "Find Critical Points",
        "Analyze Increasing and Decreasing Intervals",
    } <= skill_names
    assert not list((tmp_path / "RUN_CALCULUS").rglob("*.pdf"))

    summary = ctrl.compile_summary(run["run_id"])
    assert summary["source_display_filename"] == "axiomiq-calculus-test.pdf"
    assert summary["document_type"] == "instructional_pdf"
    assert summary["detected_subject"] == "MATHEMATICS"
    assert summary["detected_course_level"] == "CALCULUS_I"
    assert summary["profile_alignment_status"] == "candidate_new"
    assert summary["practice_potential"] == "available"
    assert summary["assessment_potential"] == "content_gap"
    assert "No compatible assessment generation family" in summary["assessment_content_gap"]
    assert summary["compatible_generation_families"] == []
    assert summary["persistence"]["run_saved_to_dashboard_history"] is True


def test_conflicting_profile_warns_without_blocking_calculus_extraction(tmp_path):
    ctrl = DashboardController(DashboardStorage(tmp_path))
    run = ctrl.create_run({"source_title": "Calculus conflict"}, run_id="RUN_CONFLICT")
    ctrl.upload_source(
        run["run_id"],
        filename="calculus.pdf",
        content=_minimal_text_pdf([CALCULUS_TEXT]),
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
            "profile_id": "PHYSICS_INTRO_MECHANICS_PROFILE_V1",
        },
    )

    compiled = ctrl.compile_run(run["run_id"])
    assert compiled["compiler_status"] == "complete"
    assert compiled["detected_subject"] == "MATHEMATICS"
    assert compiled["profile_alignment_status"] == "conflict_warning"
    assert "does not match detected subject" in compiled["profile_alignment_warning"]
    assert ctrl.results(run["run_id"])["micro_skills"]


def test_unknown_subject_gets_review_required_candidates(tmp_path):
    ctrl = DashboardController(DashboardStorage(tmp_path))
    run = ctrl.create_run({"source_title": "Unknown"}, run_id="RUN_UNKNOWN")
    ctrl.upload_source(
        run["run_id"],
        filename="unknown.txt",
        content=b"Source notes with sparse vocabulary and one example for review.",
        metadata={
            "rights_status": "approved_local_use",
            "privacy_status": "non_private",
            "retain_normalized_source": True,
        },
    )

    compiled = ctrl.compile_run(run["run_id"])
    assert compiled["compiler_status"] == "complete"
    assert compiled["profile_alignment_status"] == "candidate_new"
    assert ctrl.results(run["run_id"])["topics"]
    assert ctrl.results(run["run_id"])["micro_skills"]
    assert any(gap["gap_id"] == "GAP_UNKNOWN_CLASSIFICATION" for gap in ctrl.results(run["run_id"])["content_gaps"])


def test_static_dashboard_exposes_compile_flow_and_assessment_prerequisites():
    app = Path("tools/course_compiler_demo/dashboard/static/app.js").read_text()
    server = Path("tools/course_compiler_demo/dashboard/server.py").read_text()

    assert "Compilation complete" in app
    assert "Run saved to dashboard history" in app
    assert "Review Curriculum" in app
    assert "Save Review Decisions" in app
    assert "Configure Assessment" in app
    assert "Generate Questions" in app
    assert "Save curriculum-review decisions before configuring an assessment." in app
    assert "Generate Questions is enabled after a valid assessment blueprint is created." in app
    assert "Compilation failed" in app
    assert "Stage: compiler execution" in app
    assert "Source uploaded successfully" in app
    assert "Ready to compile" in app
    assert "Compile is disabled until Upload Source persists source_ready" in app
    assert "Upload failed" in app
    assert "50 MiB upload" in app
    assert "No compatible assessment generation family is available" in app
    assert "Compile request blocked" in app
    assert "Auto-detect / No profile" in app
    assert "No profile is required before compilation." in app
    assert "selected_micro_skill: document.querySelector" not in app
    assert "content_base64" in app
    assert "content_base64" in server
