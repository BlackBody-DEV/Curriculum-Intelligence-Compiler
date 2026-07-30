import json

from tools.course_compiler_demo.answer_engines import build_default_registry
from tools.course_compiler_demo.answer_engines.registry import DISABLED_ENGINE_TYPES, ENABLED_ENGINE_TYPES
from tools.course_compiler_demo.beta_export import dry_run_import_validate
from tools.course_compiler_demo.universal_integration.capability_catalog_wave_044 import (
    EXPECTED_NEW_IDS, allocation_report, build_beta_dry_run, build_wave_artifacts,
    compile_cross_catalog_pilots, compile_diagnostics, discover_course_catalog,
    engine_capability_report, validate_all_catalogs,
)


def test_fourteen_engines_and_33_courses_integrate_without_fallback():
    registry=build_default_registry(); engines=engine_capability_report(); catalog=discover_course_catalog()
    assert engines["enabled_count"]==len(ENABLED_ENGINE_TYPES)==14
    assert all(registry.lookup(name).status=="SUPPORTED" for name in ENABLED_ENGINE_TYPES)
    assert all(registry.lookup(name).status=="UNSUPPORTED" for name in DISABLED_ENGINE_TYPES)
    assert len(catalog["existing"])==6 and len(catalog["new"])==27 and len(catalog["total"])==33
    assert set(catalog["new"])==set(EXPECTED_NEW_IDS) and validate_all_catalogs()["status"]=="PASS"
    assert allocation_report(catalog["total"])["status"]=="PASS"


def test_all_27_pilots_fail_closed_without_emitting_candidates():
    pilots=compile_cross_catalog_pilots()
    assert pilots["status"]=="PARTIAL_BLOCKED" and pilots["planned"]==675
    assert pilots["generated"]==pilots["independently_derived"]==pilots["validated"]==pilots["locked"]==0
    assert pilots["duplicate_report"]=={"exact_duplicates":0,"fingerprint_count":0,"question_count":0,"status":"NOT_APPLICABLE_NO_CANDIDATES"}
    assert len(pilots["courses"])==27
    for result in pilots["courses"]:
        assert result["status"]=="BLOCKED"
        assert result["blockers"]==["TOPIC_SKILL_PROCEDURE_GENERATOR_NOT_IMPLEMENTED"]
        assert result["generated"]==result["independently_derived"]==result["validated"]==result["locked"]==0
        assert result["questions"]==[] and result["synthetic_fixtures"]==0


def test_diagnostics_report_all_27_validated_pilot_shortfalls():
    assessments=compile_diagnostics(compile_cross_catalog_pilots())
    assert assessments["status"]=="PARTIAL_BLOCKED" and assessments["target"]==27
    assert assessments["assessment_count"]==0 and assessments["assessments"]==[] and len(assessments["shortfalls"])==27
    assert all(item["blocker"]=="VALIDATED_PILOT_SHORTFALL" and item["validated"]==0 and item["required"]==15 for item in assessments["shortfalls"])


def test_beta_contains_all_passing_packs_and_zero_invalid_downstream_payloads():
    pilots=compile_cross_catalog_pilots(); assessments=compile_diagnostics(pilots); beta=build_beta_dry_run(pilots,assessments)
    assert len(beta["course_pack_payloads"])==27
    assert beta["pilot_question_payloads"]==[] and beta["assessment_payloads"]==[]
    assert beta["schema_status"]=="PASS" and beta["schema_validation"]==dry_run_import_validate(beta["beta_package"])
    assert beta["schema_validation"]["question_reference_count"]==0 and beta["would_write"] is False
    assert beta["beta_package"]["question_references"]==[] and beta["beta_package"]["assessment_blueprints"]==[]
    assert beta["student_visible"] is False and beta["eligible_for_alpha_import"] is False


def test_artifacts_are_honest_partial_and_record_completed_audits():
    artifacts=build_wave_artifacts(); reopened=json.loads(json.dumps(artifacts,sort_keys=True,separators=(",",":")))
    assert reopened==artifacts and len(artifacts)==10
    assert artifacts["pilot_question_report.json"]["validated"]==0
    assert artifacts["assessment_report.json"]["assessment_count"]==0
    assert artifacts["beta_export_report.json"]["schema_validation"]["question_reference_count"]==0
    assert artifacts["security_audit_report.json"]["status"]=="NOT_APPLICABLE_NO_PILOTS"
    assert artifacts["clean_room_report.json"]["status"]=="PARTIAL_ENVIRONMENT_BLOCKED"
    assert artifacts["clean_room_report.json"]["remote_ci"]["required"] is True
    assert artifacts["independent_audit_report.json"]["status"]=="APPROVE_PARTIAL"
    assert len(artifacts["capability_catalog_manifest.json"]["artifact_sha256"])==9


def test_no_candidate_shaped_payload_is_hidden_in_blocked_outputs():
    artifacts=build_wave_artifacts(); encoded=json.dumps(artifacts,sort_keys=True,separators=(",",":"))
    assert '"candidate_id"' not in encoded and '"normalized_answer"' not in encoded
    assert '"student_visible":true' not in encoded and '"eligible_for_alpha_import":true' not in encoded
