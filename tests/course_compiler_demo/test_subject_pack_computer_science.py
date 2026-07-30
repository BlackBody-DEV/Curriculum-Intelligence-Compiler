import hashlib,json
import pytest
from tools.course_compiler_demo.subject_packs.computer_science import build_programming_fundamentals_pack,validate_programming_fundamentals_pack

def test_contract_counts_and_coverage():
    pack=build_programming_fundamentals_pack(); validate_programming_fundamentals_pack(pack); c=pack["course"]
    assert len(c["units"])>=8 and len(c["topics"])>=25 and len(c["micro_skills"])>=50 and len(c["procedures"])>=15 and len(c["generation_families"])>=15
    assert len(c["assessment_blueprints"])==2 and c["target_validated_question_count"]==300

def test_code_io_test_contracts_and_procedures_resolve():
    c=build_programming_fundamentals_pack()["course"]; procedures={x["procedure_id"] for x in c["procedures"]}
    assert all(x["procedure_id"] in procedures and x["input_output_contract"] and x["unit_test_grading"]["cases"] for x in c["generation_families"])

def test_code_execution_is_explicitly_disabled_and_fails_closed():
    pack=build_programming_fundamentals_pack(); assert pack["disabled_engine"]["status"]=="UNSUPPORTED"
    assert all(not x["engine_enabled"] and not x["code_answer_contract"]["executable_grading_enabled"] for x in pack["course"]["generation_families"] if x["answer_engine"]=="code_execution")
    pack["course"]["generation_families"][4]["engine_enabled"]=True
    with pytest.raises(ValueError): validate_programming_fundamentals_pack(pack)

def test_generation_variants_determinism_and_no_canonical_claim():
    a=build_programming_fundamentals_pack(); b=build_programming_fundamentals_pack()
    assert all(x["allocation_rules"]["target_variants"]>1 for x in a["course"]["generation_families"])
    assert json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True) and a["deterministic_sha256"]==b["deterministic_sha256"]
    assert a["noncanonical"] and a["human_review_required"] and not a["canonical_authority"]

@pytest.mark.parametrize("kind",["skill","duplicate","blueprint","scope"])
def test_invalid_resolution_identity_and_blueprint_fail_closed(kind):
    pack=build_programming_fundamentals_pack(); c=pack["course"]
    if kind=="skill": c["procedures"][0]["micro_skill_ids"]=["MISSING"]
    elif kind=="duplicate": c["generation_families"][1]["family_id"]=c["generation_families"][0]["family_id"]
    elif kind=="blueprint": c["assessment_blueprints"][0]["topic_weights"]={"MISSING":1.0}
    else: c["assessment_blueprints"][0]["unit_scope"]=["MISSING"]
    with pytest.raises((ValueError,TypeError)): validate_programming_fundamentals_pack(pack)

@pytest.mark.parametrize("kind",["relationship","case","io","difficulty","integrity"])
def test_relationship_contract_blueprint_and_integrity_fail_closed(kind):
    pack=build_programming_fundamentals_pack(); c=pack["course"]
    if kind=="relationship": c["relationships"][0]["target_node_id"]="MISSING"
    elif kind=="case": c["generation_families"][0]["unit_test_grading"]["cases"]=[True]
    elif kind=="io": c["generation_families"][0]["input_output_contract"]={"input_schema":"anything","output_schema":False}
    elif kind=="difficulty": c["assessment_blueprints"][0]["difficulty_distribution"]={"UNKNOWN":9.0}
    else: c["topics"][0]["title"]="mutated"
    with pytest.raises(ValueError): validate_programming_fundamentals_pack(pack)

def _rehash(pack):
    material={k:v for k,v in pack.items() if k!="deterministic_sha256"}; pack["deterministic_sha256"]=hashlib.sha256(json.dumps(material,sort_keys=True,separators=(",",":")).encode()).hexdigest()

@pytest.mark.parametrize("kind",["relationship_type","relationship_id","blank_relationship_id","code_contract","blank_code_contract"])
def test_relationship_types_identity_and_code_contract_fail_closed(kind):
    pack=build_programming_fundamentals_pack(); c=pack["course"]
    if kind=="relationship_type": c["relationships"][0]["relationship_type"]="CANONICAL_AUTHORITY"
    elif kind=="relationship_id": c["relationships"][1]["relationship_id"]=c["relationships"][0]["relationship_id"]
    elif kind=="blank_relationship_id": c["relationships"][0]["relationship_id"]=""
    elif kind=="code_contract": c["generation_families"][0]["code_answer_contract"]={"executable_grading_enabled":False}
    else: c["generation_families"][0]["code_answer_contract"].update(language="   ",entrypoint="\t")
    _rehash(pack)
    with pytest.raises(ValueError): validate_programming_fundamentals_pack(pack)
