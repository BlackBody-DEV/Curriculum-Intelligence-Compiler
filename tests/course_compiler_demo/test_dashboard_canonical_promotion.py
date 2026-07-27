from pathlib import Path

from tools.course_compiler_demo.canonical_promotion.preparation_mode import MODE_IDENTIFIER
from tools.course_compiler_demo.dashboard.controller import DashboardController
from tools.course_compiler_demo.dashboard.run_storage import DashboardStorage


def test_canonical_promotion_mode_is_dashboard_visible(tmp_path):
    ctrl = DashboardController(
        DashboardStorage(tmp_path / "dashboard"),
        canonical_promotion_root=tmp_path / "promotion",
    )
    mode = ctrl.canonical_promotion_mode()
    assert mode["mode_identifier"] == MODE_IDENTIFIER
    assert mode["execution_profiles"] == ["PREPARATION_ONLY"]
    assert mode["status_labels"]["canonical_promotion_authorized"] is False
    assert mode["status_labels"]["database_write_authorized"] is False
    assert "fingerprints" in mode["dashboard_behavior"]
    assert "duplicate classification" in mode["dashboard_behavior"]


def test_dashboard_runs_and_reopens_canonical_promotion_pilot(tmp_path):
    promotion_root = tmp_path / "promotion"
    dashboard_root = tmp_path / "dashboard"
    ctrl = DashboardController(DashboardStorage(dashboard_root), canonical_promotion_root=promotion_root)
    summary = ctrl.canonical_promotion_run_pilot("RUN_DASHBOARD_PROMO")
    assert summary["candidate_count"] == 10
    assert all(not Path(item["packet_path"]).is_absolute() for item in summary["packets"])

    restarted = DashboardController(DashboardStorage(dashboard_root), canonical_promotion_root=tmp_path / "ignored")
    reopened = restarted.canonical_promotion_reopen("RUN_DASHBOARD_PROMO")
    assert reopened["preparation_root"] == str(promotion_root.resolve())
    assert reopened["packet_count"] == 10
    assert reopened["candidate_count"] == 10
    assert len(reopened["packets"]) == 10
    assert reopened["packets"][0]["source_identity"]
    assert reopened["packets"][0]["curriculum_linkage"]["primary_micro_skill_code"]
    assert reopened["packets"][0]["procedure_linkage"]["verified"] is True
    assert reopened["packets"][0]["grading_validation"] == "PASS"
    assert reopened["packets"][0]["failure_signal_validation"] == "PASS"
    assert reopened["canonical_ids_assigned"] == 0
    assert reopened["canonical_paths_written"] == 0
    assert reopened["database_access"] == "none"


def test_static_dashboard_exposes_canonical_promotion_view():
    app = Path("tools/course_compiler_demo/dashboard/static/app.js").read_text(encoding="utf-8")
    html = Path("tools/course_compiler_demo/dashboard/templates/index.html").read_text(encoding="utf-8")
    assert 'data-view="canonicalPromotion"' in html
    assert "Canonical Promotion Preparation" in app
    assert "/api/canonical-promotion/mode" in app
    assert "/api/canonical-promotion/pilot" in app
    assert "Source adapter" in app
    assert "Independent derivation" in app
    assert "Failure-signal validation" in app
    assert "canonical_promotion_authorized" in app
    assert "database_write_authorized" in app
