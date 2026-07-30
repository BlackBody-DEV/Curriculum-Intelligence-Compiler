import json
import hashlib

from tools.course_compiler_demo.answer_engines import build_default_registry
from tools.course_compiler_demo.answer_engines.registry import DISABLED_ENGINE_TYPES, ENABLED_ENGINE_TYPES
from tools.course_compiler_demo.beta_export import dry_run_import_validate
from tools.course_compiler_demo.universal_integration.capability_catalog_wave_044 import (
    EXPECTED_NEW_IDS, allocation_report, build_beta_dry_run, build_wave_artifacts,
    compile_cross_catalog_pilots, compile_diagnostics, discover_course_catalog,
    discover_generation_recipe_runtime, engine_capability_report, validate_all_catalogs,
)


def test_fourteen_engines_and_33_courses_integrate_without_fallback():
    registry=build_default_registry(); engines=engine_capability_report(); catalog=discover_course_catalog()
    assert engines["enabled_count"]==len(ENABLED_ENGINE_TYPES)==14
    assert all(registry.lookup(name).status=="SUPPORTED" for name in ENABLED_ENGINE_TYPES)
    assert all(registry.lookup(name).status=="UNSUPPORTED" for name in DISABLED_ENGINE_TYPES)
    assert len(catalog["existing"])==6 and len(catalog["new"])==27 and len(catalog["total"])==33
    assert set(catalog["new"])==set(EXPECTED_NEW_IDS) and validate_all_catalogs()["status"]=="PASS"
    assert allocation_report(catalog["total"])["status"]=="PASS"


def test_all_27_pilots_compile_exactly_675_validated_questions():
    pilots=compile_cross_catalog_pilots()
    assert pilots["status"]=="PASS" and pilots["planned"]==675
    assert pilots["generated"]==pilots["independently_derived"]==pilots["validated"]==pilots["locked"]==675
    assert pilots["duplicate_report"]=={"exact_duplicates":0,"fingerprint_count":675,"question_count":675,"status":"PASS"}
    assert len(pilots["courses"])==27
    for result in pilots["courses"]:
        assert result["status"]=="PASS" and result["blockers"]==[]
        assert result["generated"]==result["independently_derived"]==result["validated"]==result["locked"]==25
        assert len(result["questions"])==25 and result["synthetic_fixtures"]==0
        coverage=result["coverage_evidence"]
        assert coverage["family_count"]==coverage["micro_skill_count"]==5
        assert coverage["procedure_count"]>=3 and coverage["answer_engine_count"]>=2
        assert len(coverage["difficulty_levels"])==3


def test_recipe_provider_discovery_accepts_all_135_semantically_proved_recipes():
    discovery=discover_generation_recipe_runtime()
    reports={row["provider"].rsplit(".",1)[-1]:row for row in discovery["provider_reports"]}
    assert reports["science_cs"]=={"accepted_recipes":75,"provider":"tools.course_compiler_demo.generation_recipes.domains.science_cs","reasons":[],"status":"PASS"}
    assert reports["math_engineering"]=={"accepted_recipes":60,"provider":"tools.course_compiler_demo.generation_recipes.domains.math_engineering","reasons":[],"status":"PASS"}
    assert len(discovery["accepted"])==135


def test_semantic_manifest_failure_rejects_the_entire_provider(monkeypatch):
    from tools.course_compiler_demo.generation_recipes.domains import science_cs
    original=science_cs.semantic_compatibility_manifest
    rows=list(original()); rows[0]={**rows[0],"matched_terms":[],"status":"FAIL"}
    monkeypatch.setattr(science_cs,"semantic_compatibility_manifest",lambda:tuple(rows))
    discovery=discover_generation_recipe_runtime()
    science=next(row for row in discovery["provider_reports"] if row["provider"].endswith("science_cs"))
    assert science["status"]=="REJECTED" and science["accepted_recipes"]==0
    assert science["reasons"]==["SEMANTIC_COMPATIBILITY_FAILED:W056:MECHANICS:001"]
    assert len(discovery["accepted"])==60


def test_semantic_evidence_cannot_be_reused_for_a_shifted_binding(monkeypatch):
    from tools.course_compiler_demo.generation_recipes.domains import science_cs
    original=science_cs.semantic_compatibility_manifest
    rows=list(original()); rows[0]={**rows[0],"binding":rows[1]["binding"]}
    monkeypatch.setattr(science_cs,"semantic_compatibility_manifest",lambda:tuple(rows))
    discovery=discover_generation_recipe_runtime()
    science=next(row for row in discovery["provider_reports"] if row["provider"].endswith("science_cs"))
    assert science["status"]=="REJECTED" and science["accepted_recipes"]==0
    assert science["reasons"]==["SEMANTIC_BINDING_MISMATCH:W056:MECHANICS:001"]


def test_diagnostics_compile_all_27_through_actual_assessment_compiler():
    assessments=compile_diagnostics(compile_cross_catalog_pilots())
    assert assessments["status"]=="PASS" and assessments["target"]==27
    assert assessments["assessment_count"]==27 and len(assessments["assessments"])==27 and assessments["shortfalls"]==[]
    assert all(item["question_count"]==15 and item["coverage_evidence"]["validator"]=="assessment_compiler.compile_assessment" for item in assessments["assessments"])


def test_beta_contains_full_675_reference_dry_run_payload():
    pilots=compile_cross_catalog_pilots(); assessments=compile_diagnostics(pilots); beta=build_beta_dry_run(pilots,assessments)
    assert len(beta["course_pack_payloads"])==27
    assert len(beta["pilot_question_payloads"])==675 and len(beta["assessment_payloads"])==27
    assert beta["schema_status"]=="PASS" and beta["schema_validation"]==dry_run_import_validate(beta["beta_package"])
    assert beta["schema_validation"]["question_reference_count"]==675 and beta["would_write"] is False
    assert len(beta["beta_package"]["question_references"])==675 and len(beta["beta_package"]["assessment_blueprints"])==27
    assert beta["student_visible"] is False and beta["eligible_for_alpha_import"] is False


def test_artifacts_record_full_runtime_diagnostics_and_beta_proof():
    artifacts=build_wave_artifacts(); reopened=json.loads(json.dumps(artifacts,sort_keys=True,separators=(",",":")))
    assert reopened==artifacts and len(artifacts)==10
    assert artifacts["pilot_question_report.json"]["validated"]==675
    assert artifacts["assessment_report.json"]["assessment_count"]==27
    assert artifacts["beta_export_report.json"]["schema_validation"]["question_reference_count"]==675
    assert artifacts["security_audit_report.json"]["status"]=="PASS"
    assert artifacts["clean_room_report.json"]["status"]=="CONTENT_PASS_RELEASE_BLOCKED"
    assert artifacts["clean_room_report.json"]["remote_ci"]["required"] is True
    assert artifacts["independent_audit_report.json"]["status"]=="APPROVE_CONTENT_RELEASE_BLOCKED"
    assert len(artifacts["capability_catalog_manifest.json"]["artifact_sha256"])==9


def test_fingerprints_are_content_only_and_outputs_remain_noncanonical():
    pilots=compile_cross_catalog_pilots(); question=pilots["courses"][0]["questions"][0]
    material={"answer_engine":question["answer_engine"],"normalized_answer":question["normalized_answer"],"parameters":question["parameters"],"prompt":question["prompt"]}
    expected=hashlib.sha256(json.dumps(material,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()).hexdigest()
    assert question["semantic_fingerprint"]==expected
    assert all(q["synthetic_fixture"] is False for course in pilots["courses"] for q in course["questions"])
    encoded=json.dumps(pilots,sort_keys=True,separators=(",",":"))
    assert '"student_visible":true' not in encoded and '"eligible_for_alpha_import":true' not in encoded
