import json

import pytest

from tools.course_compiler_demo.subject_packs.computer_science import (
    COURSE_IDS, ENGINE_ALLOCATIONS, build_computer_science_course_catalog,
    build_programming_fundamentals_pack, validate_computer_science_course_catalog,
)
from tools.course_compiler_demo.universal_integration.system import build_universal_package, plan_course_jobs


EXPECTED={"DATA_STRUCTURES","ALGORITHMS","COMPUTATIONAL_THINKING"}


def test_three_new_courses_pass_every_common_gate():
    pack=build_computer_science_course_catalog(); validate_computer_science_course_catalog(pack)
    assert set(COURSE_IDS)==EXPECTED and set(pack["courses"])==EXPECTED|{"PROGRAMMING_FUNDAMENTALS"}
    for course_id in COURSE_IDS:
        course=pack["courses"][course_id]
        assert course["course_identity"]["course_id"]==course_id and course["domain"]=="COMPUTER_SCIENCE" and course["subject"]
        assert len(course["units"])>=8 and len(course["topics"])>=25 and len(course["micro_skills"])>=50
        assert len(course["procedures"])>=15 and len(course["generation_families"])>=15
        assert len(course["assessment_blueprints"])==2 and course["target_production_count"]==300
        assert course["noncanonical"] and course["human_review_required"] and course["canonical_authority"] is False
        assert course["difficulty_model"] and course["failure_signal_allocations"] and course["asset_policy"]


def test_programming_fundamentals_payload_is_preserved_exactly():
    legacy=build_programming_fundamentals_pack(); expanded=build_computer_science_course_catalog()
    assert expanded["courses"]["PROGRAMMING_FUNDAMENTALS"]==legacy["course"]
    assert expanded["programming_fundamentals_reference"]["deterministic_sha256"]==legacy["deterministic_sha256"]


def test_bounded_code_choice_numeric_trace_and_rubric_allocations():
    assert set(ENGINE_ALLOCATIONS)=={"code_execution","multiple_choice","numeric_vector","rubric_scored_explanation"}
    for course_id in COURSE_IDS:
        course=build_computer_science_course_catalog()["courses"][course_id]
        assert {f["answer_engine"] for f in course["generation_families"]}==set(ENGINE_ALLOCATIONS)
        for family in course["generation_families"]:
            assert family["answer_contract"] and family["failure_signals"]
            if family["answer_engine"]=="code_execution":
                assert family["bounded_execution"]=={"language":"python","entrypoint":"solve","timeout_ms":1000,"memory_mb":64,"network":False,"filesystem":False,"imports":[]}
            if family["answer_engine"]=="numeric_vector": assert family["answer_contract"]["shape"]=="ordered_numeric_trace"
            if family["answer_engine"]=="rubric_scored_explanation": assert family["answer_contract"]["freeform_prose"] is False


def test_generation_families_and_hierarchies_resolve():
    required={"micro_skill_id","procedure_id","parameter_domains","difficulty_allocation","answer_contract","answer_engine","failure_signals","assessment_role","duplicate_constraints"}
    for course_id in COURSE_IDS:
        course=build_computer_science_course_catalog()["courses"][course_id]
        units={x["unit_id"] for x in course["units"]}; topics={x["topic_id"] for x in course["topics"]}; skills={x["micro_skill_id"] for x in course["micro_skills"]}; procedures={x["procedure_id"] for x in course["procedures"]}
        assert all(t["unit_id"] in units for t in course["topics"]) and all(s["topic_id"] in topics for s in course["micro_skills"])
        assert {x for p in course["procedures"] for x in p["micro_skill_ids"]}==skills
        for family in course["generation_families"]:
            assert required.issubset(family) and family["micro_skill_id"] in skills and family["procedure_id"] in procedures
            assert sum(family["difficulty_allocation"].values())==pytest.approx(1)
            assert family["duplicate_constraints"]["maximum_exact_duplicates"]==0


def test_universal_packages_and_300_job_plans_are_explicit():
    pack=build_computer_science_course_catalog()
    for course_id in COURSE_IDS:
        course=pack["courses"][course_id]; universal=build_universal_package(course); jobs=plan_course_jobs(course)
        assert universal.package_id==f"universal:{course_id}" and len(jobs)==300 and len({j.job_id for j in jobs})==300
        assert sum(j.executable for j in jobs)==300
        assert {j.answer_engine for j in jobs}=={"code_execution_python","multiple_choice","numeric_vector","rubric_scored_explanation"}
        assert all(j.blocker is None for j in jobs)


def test_catalog_is_deterministic_noncanonical_and_review_required():
    first=build_computer_science_course_catalog(); second=build_computer_science_course_catalog()
    assert first==second and first["deterministic_sha256"]==second["deterministic_sha256"]
    assert json.dumps(first,sort_keys=True,separators=(",",":"))==json.dumps(second,sort_keys=True,separators=(",",":"))
    assert first["noncanonical"] and first["human_review_required"] and first["canonical_authority"] is False


@pytest.mark.parametrize("mutation",[
    "missing","canonical","legacy","count","unit","topic","skill","procedure","relationship",
    "duplicate","engine","contract","difficulty","failure","role","duplicates","allocation","asset",
    "code_network","code_timeout","blueprint_unit","blueprint_distribution",
])
def test_malformed_catalogs_fail_closed(mutation):
    pack=build_computer_science_course_catalog(); course=pack["courses"]["DATA_STRUCTURES"]; family=course["generation_families"][0]
    if mutation=="missing": del pack["courses"]["ALGORITHMS"]
    elif mutation=="canonical": pack["canonical_authority"]=True
    elif mutation=="legacy": pack["courses"]["PROGRAMMING_FUNDAMENTALS"]["units"][0]["title"]="changed"
    elif mutation=="count": course["target_production_count"]=0
    elif mutation=="unit": course["topics"][0]["unit_id"]="MISSING"
    elif mutation=="topic": course["micro_skills"][0]["topic_id"]="MISSING"
    elif mutation=="skill": family["micro_skill_id"]="MISSING"
    elif mutation=="procedure": family["procedure_id"]="MISSING"
    elif mutation=="relationship": course["relationships"][0]["target_node_id"]="MISSING"
    elif mutation=="duplicate": course["generation_families"][1]["family_id"]=family["family_id"]
    elif mutation=="engine": family["answer_engine"]="NO_ENGINE"
    elif mutation=="contract": family["answer_contract"]={}
    elif mutation=="difficulty": family["difficulty_allocation"]={"FOUNDATIONAL":2}
    elif mutation=="failure": family["failure_signals"]=["UNKNOWN"]
    elif mutation=="role": family["assessment_role"]="UNKNOWN"
    elif mutation=="duplicates": family["duplicate_constraints"]["maximum_exact_duplicates"]=1
    elif mutation=="allocation": course["answer_engine_allocations"]=["multiple_choice"]
    elif mutation=="asset": course["asset_policy"]={}
    elif mutation=="code_network": family["bounded_execution"]["network"]=True
    elif mutation=="code_timeout": family["bounded_execution"]["timeout_ms"]=0
    elif mutation=="blueprint_unit": course["assessment_blueprints"][0]["unit_scope"]=["MISSING"]
    else: course["assessment_blueprints"][0]["difficulty_distribution"]={"FOUNDATIONAL":2}
    with pytest.raises((ValueError,TypeError)):
        validate_computer_science_course_catalog(pack)
