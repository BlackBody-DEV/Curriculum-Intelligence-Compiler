import copy
import json

import pytest

from tools.course_compiler_demo.subject_packs.physics_engineering import (
    NEW_COURSE_IDS, build_physics_engineering_course_catalog,
    build_physics_engineering_reference_pack, validate_physics_engineering_course_catalog,
)
from tools.course_compiler_demo.universal_integration.system import build_universal_package, plan_course_jobs


EXPECTED_NEW = {
    "MECHANICS", "WAVES_AND_OPTICS", "MODERN_PHYSICS", "DYNAMICS",
    "MECHANICS_OF_MATERIALS", "STRENGTH_OF_MATERIALS", "FLUID_MECHANICS",
    "HYDRAULICS", "FLUID_DYNAMICS",
}


def test_nine_course_packs_pass_every_common_gate():
    pack=build_physics_engineering_course_catalog(); validate_physics_engineering_course_catalog(pack)
    assert set(NEW_COURSE_IDS)==EXPECTED_NEW
    assert set(pack["courses"])==EXPECTED_NEW|{"STATICS","ELECTRICITY_AND_MAGNETISM"}
    for course_id in NEW_COURSE_IDS:
        course=pack["courses"][course_id]
        assert course["course_identity"]["course_id"]==course_id and course["domain"] and course["subject"]
        assert len(course["units"])>=8 and len(course["topics"])>=25 and len(course["micro_skills"])>=50
        assert len(course["procedures"])>=15 and len(course["generation_families"])>=15
        assert len(course["assessment_blueprints"])==2 and course["target_production_count"]==300
        assert course["noncanonical"] and course["human_review_required"]


def test_statics_and_electromagnetism_are_preserved_exactly():
    legacy=build_physics_engineering_reference_pack(); expanded=build_physics_engineering_course_catalog()
    assert expanded["courses"]["STATICS"]==legacy["courses"]["STATICS"]
    assert expanded["courses"]["ELECTRICITY_AND_MAGNETISM"]==legacy["courses"]["ELECTRICITY_AND_MAGNETISM"]
    assert expanded["statics_authority_references"]==legacy["statics_authority_references"]


def test_units_dimensions_vectors_and_signs_are_explicit_at_every_level():
    for course_id in NEW_COURSE_IDS:
        course=build_physics_engineering_course_catalog()["courses"][course_id]
        assert course["unit_policy"]=={"system":"SI","base_dimensions":["M","L","T","I","Theta"],"dimensional_analysis_required":True}
        assert course["vector_convention"]["basis"]=="RIGHT_HANDED_CARTESIAN"
        assert course["vector_convention"]["angle_reference"]=="POSITIVE_X_CCW"
        assert course["sign_convention"]["moments"]=="RIGHT_HAND_RULE"
        assert all(p["dimensional_check"]=="REQUIRED" and p["sign_convention"] for p in course["procedures"])
        assert all(f["answer_contract"]["units"]=="REQUIRED" and f["answer_contract"]["dimensions"]=="REQUIRED" for f in course["generation_families"])


def test_generation_families_have_complete_generation_contracts():
    required={"micro_skill_id","procedure_id","parameter_domains","difficulty_allocation","answer_contract","answer_engine","failure_signals","assessment_role","duplicate_constraints"}
    for course_id in NEW_COURSE_IDS:
        course=build_physics_engineering_course_catalog()["courses"][course_id]
        skills={x["micro_skill_id"] for x in course["micro_skills"]}; procedures={x["procedure_id"] for x in course["procedures"]}
        for family in course["generation_families"]:
            assert required.issubset(family)
            assert family["micro_skill_id"] in skills and family["procedure_id"] in procedures
            assert sum(family["difficulty_allocation"].values())==pytest.approx(1)
            assert family["duplicate_constraints"]["maximum_exact_duplicates"]==0
            assert family["assessment_role"]=="PRACTICE_AND_SUMMATIVE"


def test_universal_curriculum_and_300_job_contracts_for_all_nine_courses():
    pack=build_physics_engineering_course_catalog()
    for course_id in NEW_COURSE_IDS:
        course=pack["courses"][course_id]
        universal=build_universal_package(course)
        jobs=plan_course_jobs(course)
        assert universal.package_id==f"universal:{course_id}"
        assert len(jobs)==300 and len({job.job_id for job in jobs})==300
        assert all(job.course_id==course_id and job.answer_engine in {"numeric_scalar","numeric_vector"} for job in jobs)


def test_catalog_is_deterministic_noncanonical_and_human_reviewed():
    first=build_physics_engineering_course_catalog(); second=build_physics_engineering_course_catalog()
    assert first==second
    assert json.dumps(first,sort_keys=True,separators=(",",":"))==json.dumps(second,sort_keys=True,separators=(",",":"))
    assert first["noncanonical"] and first["human_review_required"] and first["canonical_authority"] is False


@pytest.mark.parametrize("mutation", [
    "missing_course", "canonical", "legacy_change", "count", "hierarchy", "family_skill",
    "family_engine", "family_difficulty", "units", "dimensions", "vector", "sign",
    "duplicate_family", "duplicate_policy", "blueprint_scope", "failure_signal",
])
def test_malformed_catalogs_fail_closed(mutation):
    pack=build_physics_engineering_course_catalog(); course=pack["courses"]["FLUID_MECHANICS"]
    if mutation=="missing_course": del pack["courses"]["HYDRAULICS"]
    elif mutation=="canonical": pack["canonical_authority"]=True
    elif mutation=="legacy_change": pack["courses"]["STATICS"]["units"][0]["title"]="changed"
    elif mutation=="count": course["target_production_count"]=299
    elif mutation=="hierarchy": course["topics"][0]["unit_id"]="MISSING"
    elif mutation=="family_skill": course["generation_families"][0]["micro_skill_id"]="MISSING"
    elif mutation=="family_engine": course["generation_families"][0]["answer_engine"]="NO_ENGINE"
    elif mutation=="family_difficulty": course["generation_families"][0]["difficulty_allocation"]={"FOUNDATIONAL":2}
    elif mutation=="units": course["unit_policy"]["system"]="UNDECLARED"
    elif mutation=="dimensions": course["unit_policy"]["base_dimensions"]=[]
    elif mutation=="vector": course["vector_convention"]["components_order"]=["y","x"]
    elif mutation=="sign": course["sign_convention"]={}
    elif mutation=="duplicate_family": course["generation_families"][1]["family_id"]=course["generation_families"][0]["family_id"]
    elif mutation=="duplicate_policy": course["generation_families"][0]["duplicate_constraints"]["maximum_exact_duplicates"]=1
    elif mutation=="blueprint_scope": course["assessment_blueprints"][0]["unit_scope"]=["MISSING"]
    else: course["generation_families"][0]["failure_signals"]=["UNKNOWN"]
    with pytest.raises((ValueError,TypeError)):
        validate_physics_engineering_course_catalog(pack)
