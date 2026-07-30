import json
import pytest
from tools.course_compiler_demo.subject_packs.mathematics import build_mathematics_reference_pack, validate_mathematics_reference_pack

def test_mathematics_pack_contract_counts_and_courses():
    pack = build_mathematics_reference_pack(); validate_mathematics_reference_pack(pack)
    assert set(pack["courses"]) == {"ALGEBRA_I", "CALCULUS_I"}
    for course in pack["courses"].values():
        assert len(course["units"]) >= 8 and len(course["topics"]) >= 25 and len(course["micro_skills"]) >= 50
        assert len(course["procedures"]) >= 15 and len(course["generation_families"]) >= 15 and len(course["assessment_blueprints"]) == 2
        assert course["target_validated_question_count"] == 300

def test_identifiers_relationships_procedures_and_engines_resolve():
    for course in build_mathematics_reference_pack()["courses"].values():
        procedures = {x["procedure_id"] for x in course["procedures"]}; skills = {x["micro_skill_id"] for x in course["micro_skills"]}
        assert all(x["procedure_id"] in procedures and x["answer_engine"] in course["answer_engine_allocations"] for x in course["generation_families"])
        assert all(x["source_node_id"] in skills and x["target_node_id"] in skills for x in course["relationships"])

def test_generation_families_support_multiple_variants():
    for course in build_mathematics_reference_pack()["courses"].values():
        assert all(x["parameter_domains"]["variant"]["maximum"] > x["parameter_domains"]["variant"]["minimum"] and x["allocation_rules"]["target_variants"] > 1 for x in course["generation_families"])

def test_deterministic_serialization_and_no_canonical_claim():
    first = build_mathematics_reference_pack(); second = build_mathematics_reference_pack()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True) and first["deterministic_sha256"] == second["deterministic_sha256"]
    assert first["noncanonical"] and first["human_review_required"] and not first["canonical_authority"]

def test_invalid_canonical_claim_is_rejected():
    pack = build_mathematics_reference_pack(); pack["canonical_authority"] = True
    with pytest.raises(ValueError): validate_mathematics_reference_pack(pack)

@pytest.mark.parametrize("mutation", ["missing_skill", "unsupported_engine", "invalid_blueprint", "duplicate_family"])
def test_invalid_resolution_engine_blueprint_and_identity_fail_closed(mutation):
    pack = build_mathematics_reference_pack(); course = pack["courses"]["ALGEBRA_I"]
    if mutation == "missing_skill": course["procedures"][0]["micro_skill_ids"] = ["MISSING"]
    elif mutation == "unsupported_engine": course["generation_families"][0]["answer_engine"] = "NO_ENGINE"
    elif mutation == "invalid_blueprint": course["assessment_blueprints"][0]["question_count"] = 0
    else: course["generation_families"][1]["family_id"] = course["generation_families"][0]["family_id"]
    with pytest.raises((ValueError, TypeError)): validate_mathematics_reference_pack(pack)

def test_all_skills_reach_procedures_and_blueprints_are_satisfiable():
    for course in build_mathematics_reference_pack()["courses"].values():
        skills={x["micro_skill_id"] for x in course["micro_skills"]}; reachable={x for p in course["procedures"] for x in p["micro_skill_ids"]}
        assert reachable == skills
        assert all(b["question_count"] >= len(b["micro_skill_coverage"]) for b in course["assessment_blueprints"])

@pytest.mark.parametrize("kind", ["topic_weight", "unit_scope", "prerequisite", "difficulty_model"])
def test_blueprint_relationships_and_allocation_models_fail_closed(kind):
    pack=build_mathematics_reference_pack(); course=pack["courses"]["ALGEBRA_I"]
    if kind=="topic_weight": course["assessment_blueprints"][0]["topic_weights"]={"MISSING_TOPIC":.2}
    elif kind=="unit_scope": course["assessment_blueprints"][0]["unit_scope"]=["MISSING_UNIT"]
    elif kind=="prerequisite": course["assessment_blueprints"][0]["prerequisite_coverage"]=["MISSING_REL"]
    else: course["difficulty_model"]=[]
    with pytest.raises(ValueError): validate_mathematics_reference_pack(pack)

@pytest.mark.parametrize("kind",["difficulty","question_type","negative","blueprint_id","relationship_id","failure_signal"])
def test_distribution_identity_and_signal_resolution_fail_closed(kind):
    pack=build_mathematics_reference_pack(); c=pack["courses"]["ALGEBRA_I"]
    if kind=="difficulty": c["assessment_blueprints"][0]["difficulty_distribution"]={"UNKNOWN":1.0}
    elif kind=="question_type": c["assessment_blueprints"][0]["question_type_distribution"]={"UNKNOWN":1.0}
    elif kind=="negative": c["assessment_blueprints"][0]["topic_weights"]={c["topics"][0]["topic_id"]:-1.0,c["topics"][1]["topic_id"]:2.0}
    elif kind=="blueprint_id": c["assessment_blueprints"][1]["blueprint_id"]=c["assessment_blueprints"][0]["blueprint_id"]
    elif kind=="relationship_id": c["relationships"][1]["relationship_id"]=c["relationships"][0]["relationship_id"]
    else: c["generation_families"][0]["failure_signals"]=["UNKNOWN"]
    with pytest.raises(ValueError): validate_mathematics_reference_pack(pack)

@pytest.mark.parametrize("kind",["empty_units","empty_prerequisites","boolean_weight","single_variant","blank_signal"])
def test_scopes_weight_types_variants_and_signal_ids_fail_closed(kind):
    pack=build_mathematics_reference_pack(); c=pack["courses"]["ALGEBRA_I"]
    if kind=="empty_units": c["assessment_blueprints"][0]["unit_scope"]=[]
    elif kind=="empty_prerequisites": c["assessment_blueprints"][0]["prerequisite_coverage"]=[]
    elif kind=="boolean_weight": c["assessment_blueprints"][0]["topic_weights"]={x["topic_id"]:(True if i==0 else 0) for i,x in enumerate(c["topics"])}
    elif kind=="single_variant": c["generation_families"][0]["parameter_domains"]["variant"]={"type":"integer","minimum":1,"maximum":1}
    else: c["failure_signal_allocations"]=[""]; [family.update(failure_signals=[""]) for family in c["generation_families"]]
    with pytest.raises(ValueError): validate_mathematics_reference_pack(pack)
