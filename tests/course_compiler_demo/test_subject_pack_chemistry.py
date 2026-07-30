import hashlib,json
import pytest
from tools.course_compiler_demo.subject_packs.chemistry import build_general_chemistry_pack,validate_general_chemistry_pack

def _rehash(pack):
    material={k:v for k,v in pack.items() if k!="deterministic_sha256"}
    pack["deterministic_sha256"]=hashlib.sha256(json.dumps(material,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def test_contract_counts_and_assessments():
    pack=build_general_chemistry_pack(); validate_general_chemistry_pack(pack); c=pack["course"]
    assert len(c["units"])>=8 and len(c["topics"])>=25 and len(c["micro_skills"])>=50
    assert len(c["procedures"])>=15 and len(c["generation_families"])>=15 and len(c["assessment_blueprints"])==2 and c["target_validated_question_count"]==300

def test_units_significant_figures_formula_and_stoichiometry_structure():
    c=build_general_chemistry_pack()["course"]
    assert c["unit_policy"]["dimensional_analysis_required"] and c["significant_figure_policy"]["round_at_end"]
    assert all(x["formula_contract"]["charge_balance_required"] and "stoichiometric_ratio_error" in x["failure_signals"] for x in c["generation_families"])
    assert all("mole or conservation" in x["steps"][1] for x in c["procedures"])

def test_procedures_families_and_disabled_reaction_engine():
    pack=build_general_chemistry_pack(); c=pack["course"]; procedures={x["procedure_id"] for x in c["procedures"]}
    assert all(x["procedure_id"] in procedures and x["allocation_rules"]["target_variants"]>1 for x in c["generation_families"])
    assert pack["disabled_engine"]["status"]=="UNSUPPORTED"
    reaction=[x for x in c["generation_families"] if x["answer_engine"]=="chemical_reaction"]
    assert reaction and all(not x["engine_enabled"] and not x["reaction_contract"]["execution_enabled"] for x in reaction)
    reaction[0]["engine_enabled"]=True
    with pytest.raises(ValueError): validate_general_chemistry_pack(pack)

def test_deterministic_and_no_canonical_claim():
    a=build_general_chemistry_pack(); b=build_general_chemistry_pack()
    assert json.dumps(a,sort_keys=True)==json.dumps(b,sort_keys=True) and a["deterministic_sha256"]==b["deterministic_sha256"]
    assert a["noncanonical"] and a["human_review_required"] and not a["canonical_authority"]

@pytest.mark.parametrize("kind",["skill","relationship","family","policy","blueprint","engine","capacity","areas","unreachable_skill"])
def test_contract_relationship_family_policy_blueprint_and_integrity_fail_closed(kind):
    pack=build_general_chemistry_pack(); c=pack["course"]
    if kind=="skill": c["procedures"][0]["micro_skill_ids"]=["MISSING"]
    elif kind=="relationship": c["relationships"][0]["target_node_id"]="MISSING"
    elif kind=="family": c["generation_families"][0]["formula_contract"]={}
    elif kind=="policy": c["significant_figure_policy"]["round_at_end"]=False
    elif kind=="blueprint": c["assessment_blueprints"][0]["difficulty_distribution"]={"UNKNOWN":1.0}
    elif kind=="engine": c["generation_families"][0]["answer_engine"]="NO_ENGINE"
    elif kind=="capacity": c["generation_families"][0]["engine_enabled"]=False
    elif kind=="areas":
        for topic in c["topics"]: topic["title"]="generic"
    else: c["assessment_blueprints"][0]["micro_skill_coverage"][0]=c["procedures"][4]["micro_skill_ids"][0]
    _rehash(pack)
    with pytest.raises(ValueError): validate_general_chemistry_pack(pack)

def test_stale_integrity_hash_rejects():
    pack=build_general_chemistry_pack(); pack["course"]["topics"][0]["title"]="mutated"
    with pytest.raises(ValueError): validate_general_chemistry_pack(pack)
