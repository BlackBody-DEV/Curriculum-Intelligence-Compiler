import json
from pathlib import Path
import pytest
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_reference_pack, validate_physics_engineering_reference_pack

def test_courses_contract_counts_and_assessments():
    pack=build_physics_engineering_reference_pack(); validate_physics_engineering_reference_pack(pack)
    assert set(pack["courses"])=={"STATICS","ELECTRICITY_AND_MAGNETISM"}
    for course in pack["courses"].values():
        assert len(course["units"])>=8 and len(course["topics"])>=25 and len(course["micro_skills"])>=50
        assert len(course["procedures"])>=15 and len(course["generation_families"])>=15 and len(course["assessment_blueprints"])==2

def test_statics_authority_references_resolve_without_mutation():
    before={x["relative_path"]:x["sha256"] for x in build_physics_engineering_reference_pack()["statics_authority_references"]}
    pack=build_physics_engineering_reference_pack(); validate_physics_engineering_reference_pack(pack)
    assert before=={x["relative_path"]:x["sha256"] for x in pack["statics_authority_references"]}
    assert {x["authority_identity"] for x in pack["statics_authority_references"]}=={"CENTROIDS","VECTOR_OPERATIONS","FORCE_SYSTEMS","MOMENTS_AND_COUPLES"}

def test_unit_vector_procedure_and_family_policies():
    for course in build_physics_engineering_reference_pack()["courses"].values():
        procedures={x["procedure_id"] for x in course["procedures"]}
        assert course["unit_policy"]["dimensional_analysis_required"] and course["vector_convention"]["angle_reference"]=="POSITIVE_X_CCW"
        assert all(x["procedure_id"] in procedures and x["allocation_rules"]["target_variants"]>1 for x in course["generation_families"])

def test_deterministic_and_noncanonical():
    a=build_physics_engineering_reference_pack(); b=build_physics_engineering_reference_pack()
    assert json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True) and a["deterministic_sha256"]==b["deterministic_sha256"]
    assert a["noncanonical"] and a["human_review_required"] and not a["canonical_authority"]

def test_canonical_claim_rejected():
    pack=build_physics_engineering_reference_pack(); pack["canonical_authority"]=True
    with pytest.raises(ValueError): validate_physics_engineering_reference_pack(pack)

@pytest.mark.parametrize("kind",["skill","engine","blueprint","duplicate"])
def test_invalid_resolution_engine_blueprint_and_identity_rejected(kind):
    pack=build_physics_engineering_reference_pack(); c=pack["courses"]["STATICS"]
    if kind=="skill": c["procedures"][0]["micro_skill_ids"]=["MISSING"]
    elif kind=="engine": c["generation_families"][0]["answer_engine"]="NO_ENGINE"
    elif kind=="blueprint": c["assessment_blueprints"][0]["question_count"]=0
    else: c["generation_families"][1]["family_id"]=c["generation_families"][0]["family_id"]
    with pytest.raises((ValueError,TypeError)): validate_physics_engineering_reference_pack(pack)

@pytest.mark.parametrize("kind",["authority","topic","unit","dimensional","angle"])
def test_authority_blueprint_unit_and_vector_semantics_fail_closed(kind):
    pack=build_physics_engineering_reference_pack(); c=pack["courses"]["STATICS"]
    if kind=="authority": pack["statics_authority_references"]=[]
    elif kind=="topic": c["assessment_blueprints"][0]["topic_weights"]={"MISSING":.2}
    elif kind=="unit": c["assessment_blueprints"][0]["unit_scope"]=["MISSING"]
    elif kind=="dimensional": c["unit_policy"]["dimensional_analysis_required"]=False
    else: c["vector_convention"]["angle_reference"]="BAD"
    with pytest.raises(ValueError): validate_physics_engineering_reference_pack(pack)

def test_prerequisite_scope_and_question_types_resolve():
    pack=build_physics_engineering_reference_pack()
    for c in pack["courses"].values():
        rels={x["relationship_id"] for x in c["relationships"]}
        assert all(set(b["prerequisite_coverage"]).issubset(rels) and set(b["question_type_distribution"])=={"numeric"} for b in c["assessment_blueprints"])
    pack["courses"]["STATICS"]["assessment_blueprints"][0]["prerequisite_coverage"]=["MISSING"]
    with pytest.raises(ValueError): validate_physics_engineering_reference_pack(pack)

@pytest.mark.parametrize("kind",["endpoint","type"])
def test_prerequisite_relationships_fail_closed(kind):
    pack=build_physics_engineering_reference_pack(); rel=pack["courses"]["STATICS"]["relationships"][0]
    if kind=="endpoint": rel["target_node_id"]="MISSING"
    else: rel["relationship_type"]="CONTAINS"
    with pytest.raises(ValueError): validate_physics_engineering_reference_pack(pack)
