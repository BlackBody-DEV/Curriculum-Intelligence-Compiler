import json

import pytest

from tools.course_compiler_demo.subject_packs.engineering_mathematics import (
    COURSE_IDS, ENGINE_ALLOCATIONS, build_engineering_mathematics_catalog,
    validate_engineering_mathematics_catalog,
)
from tools.course_compiler_demo.universal_integration.system import build_universal_package, plan_course_jobs


EXPECTED={"NUMERICAL_METHODS","ENGINEERING_ANALYSIS","APPLIED_MATHEMATICS"}


def test_three_courses_pass_all_common_pack_gates():
    pack=build_engineering_mathematics_catalog(); validate_engineering_mathematics_catalog(pack)
    assert set(COURSE_IDS)==set(pack["courses"])==EXPECTED
    for course_id,course in pack["courses"].items():
        assert course["course_identity"]["course_id"]==course_id and course["domain"]=="ENGINEERING_MATHEMATICS" and course["subject"]
        assert len(course["units"])>=8 and len(course["topics"])>=25 and len(course["micro_skills"])>=50
        assert len(course["procedures"])>=15 and len(course["generation_families"])>=15
        assert len(course["assessment_blueprints"])==2 and course["target_production_count"]==300
        assert course["noncanonical"] and course["human_review_required"] and course["canonical_authority"] is False
        assert course["difficulty_model"] and course["failure_signal_allocations"] and course["asset_policy"]


def test_every_course_allocates_all_five_required_engine_classes():
    pack=build_engineering_mathematics_catalog()
    assert set(ENGINE_ALLOCATIONS)=={"numeric_scalar","symbolic_expression","matrix","graph_diagram","scientific_structured_response"}
    for course in pack["courses"].values():
        assert tuple(course["answer_engine_allocations"])==ENGINE_ALLOCATIONS
        allocated={family["answer_engine"] for family in course["generation_families"]}
        assert allocated==set(ENGINE_ALLOCATIONS)
        assert all(sum(f["difficulty_allocation"].values())==pytest.approx(1) for f in course["generation_families"])


def test_generation_families_define_every_common_contract_field():
    required={"micro_skill_id","procedure_id","parameter_domains","difficulty_allocation","answer_contract","answer_engine","failure_signals","assessment_role","duplicate_constraints"}
    for course in build_engineering_mathematics_catalog()["courses"].values():
        skills={x["micro_skill_id"] for x in course["micro_skills"]}; procedures={x["procedure_id"] for x in course["procedures"]}
        for family in course["generation_families"]:
            assert required.issubset(family)
            assert family["micro_skill_id"] in skills and family["procedure_id"] in procedures
            assert family["parameter_domains"]["variant"]["maximum"]>family["parameter_domains"]["variant"]["minimum"]
            assert family["answer_contract"] and family["failure_signals"]
            assert family["assessment_role"]=="PRACTICE_AND_SUMMATIVE"
            assert family["duplicate_constraints"]=={"parameter_fingerprint":"REQUIRED","maximum_exact_duplicates":0}


def test_hierarchy_prerequisites_procedures_and_blueprints_resolve():
    for course in build_engineering_mathematics_catalog()["courses"].values():
        units={x["unit_id"] for x in course["units"]}; topics={x["topic_id"] for x in course["topics"]}; skills={x["micro_skill_id"] for x in course["micro_skills"]}; relationships={x["relationship_id"] for x in course["relationships"]}
        assert all(t["unit_id"] in units for t in course["topics"])
        assert all(s["topic_id"] in topics for s in course["micro_skills"])
        assert {x for p in course["procedures"] for x in p["micro_skill_ids"]}==skills
        assert all(r["source_node_id"] in skills and r["target_node_id"] in skills for r in course["relationships"])
        assert all(set(b["unit_scope"]).issubset(units) and set(b["prerequisite_coverage"]).issubset(relationships) for b in course["assessment_blueprints"])


def test_universal_package_and_300_job_plans_preserve_explicit_blockers():
    pack=build_engineering_mathematics_catalog()
    for course_id,course in pack["courses"].items():
        universal=build_universal_package(course); jobs=plan_course_jobs(course)
        assert universal.package_id==f"universal:{course_id}" and len(jobs)==300 and len({j.job_id for j in jobs})==300
        assert sum(j.executable for j in jobs)==60
        assert {j.answer_engine for j in jobs if not j.executable}=={"symbolic_expression","matrix","graph_diagram","scientific_structured_response"}
        assert all(j.blocker for j in jobs if not j.executable)


def test_catalog_is_deterministic_and_never_claims_canonical_authority():
    first=build_engineering_mathematics_catalog(); second=build_engineering_mathematics_catalog()
    assert first==second and first["deterministic_sha256"]==second["deterministic_sha256"]
    assert json.dumps(first,sort_keys=True,separators=(",",":"))==json.dumps(second,sort_keys=True,separators=(",",":"))
    assert first["noncanonical"] and first["human_review_required"] and first["canonical_authority"] is False


@pytest.mark.parametrize("mutation", [
    "missing_course","canonical","course_canonical","count","unit","topic","skill","procedure",
    "relationship","duplicate_family","engine","answer_contract","difficulty","failure","assessment_role",
    "duplicates","allocation","asset","blueprint_unit","blueprint_distribution",
])
def test_malformed_catalogs_fail_closed(mutation):
    pack=build_engineering_mathematics_catalog(); course=pack["courses"]["NUMERICAL_METHODS"]; family=course["generation_families"][0]
    if mutation=="missing_course": del pack["courses"]["APPLIED_MATHEMATICS"]
    elif mutation=="canonical": pack["canonical_authority"]=True
    elif mutation=="course_canonical": course["canonical_authority"]=True
    elif mutation=="count": course["target_production_count"]=299
    elif mutation=="unit": course["topics"][0]["unit_id"]="MISSING"
    elif mutation=="topic": course["micro_skills"][0]["topic_id"]="MISSING"
    elif mutation=="skill": family["micro_skill_id"]="MISSING"
    elif mutation=="procedure": family["procedure_id"]="MISSING"
    elif mutation=="relationship": course["relationships"][0]["target_node_id"]="MISSING"
    elif mutation=="duplicate_family": course["generation_families"][1]["family_id"]=family["family_id"]
    elif mutation=="engine": family["answer_engine"]="NO_ENGINE"
    elif mutation=="answer_contract": family["answer_contract"]={}
    elif mutation=="difficulty": family["difficulty_allocation"]={"FOUNDATIONAL":2}
    elif mutation=="failure": family["failure_signals"]=["UNKNOWN"]
    elif mutation=="assessment_role": family["assessment_role"]="UNKNOWN"
    elif mutation=="duplicates": family["duplicate_constraints"]["maximum_exact_duplicates"]=1
    elif mutation=="allocation": course["answer_engine_allocations"]=["numeric_scalar"]
    elif mutation=="asset": course["asset_policy"]={}
    elif mutation=="blueprint_unit": course["assessment_blueprints"][0]["unit_scope"]=["MISSING"]
    else: course["assessment_blueprints"][0]["difficulty_distribution"]={"FOUNDATIONAL":2}
    with pytest.raises((ValueError,TypeError)):
        validate_engineering_mathematics_catalog(pack)
