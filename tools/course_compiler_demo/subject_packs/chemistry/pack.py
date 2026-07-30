"""Deterministic General Chemistry curriculum reference pack."""
from __future__ import annotations
import hashlib,json
import math
from typing import Any
from tools.course_compiler_demo.universal_core import AssessmentBlueprintV1,SubjectPackDescriptorV1,SupportDecisionV1

AREAS=["measurement and units","atomic structure","periodic trends","chemical bonding","molecular geometry","nomenclature","chemical reactions","stoichiometry","thermochemistry","gases","solutions","equilibrium","acids and bases","electrochemistry"]

def build_general_chemistry_pack()->dict[str,Any]:
    cid="GENERAL_CHEMISTRY"
    units=[{"unit_id":f"{cid}_UNIT_{i:02d}","title":AREAS[(i-1)%len(AREAS)]} for i in range(1,9)]
    topics=[{"topic_id":f"{cid}_TOPIC_{i:03d}","unit_id":units[(i-1)%8]["unit_id"],"title":f"{AREAS[(i-1)%len(AREAS)]} {i}"} for i in range(1,26)]
    skills=[{"micro_skill_id":f"{cid}_SKILL_{i:03d}","topic_id":topics[(i-1)%25]["topic_id"],"title":f"Solve {AREAS[(i-1)%len(AREAS)]} case {i}"} for i in range(1,51)]
    procedures=[{"procedure_id":f"{cid}_PROC_{i:03d}","micro_skill_ids":[skill["micro_skill_id"] for position,skill in enumerate(skills) if position%15==i-1],"steps":["Write known quantities with units.","Apply mole or conservation relationships.","Round only after the final calculation."],"unit_policy":"SI_OR_DECLARED_CHEMICAL_UNIT","significant_figure_policy":"LEAST_PRECISE_MEASUREMENT"} for i in range(1,16)]
    families=[]
    for i in range(1,16):
        reaction=i%5==0
        families.append({"family_id":f"{cid}_FAMILY_{i:03d}","procedure_id":procedures[(i-1)%15]["procedure_id"],"answer_engine":"chemical_reaction" if reaction else "numeric_scalar","engine_enabled":not reaction,"parameter_domains":{"coefficient":{"minimum":1,"maximum":20},"magnitude":{"minimum":1,"maximum":1000}},"allocation_rules":{"target_variants":25,"significant_figures":[2,3,4]},"formula_contract":{"species":["reactant","product"],"charge_balance_required":True},"reaction_contract":{"atom_balance_required":True,"charge_balance_required":True,"execution_enabled":False},"failure_signals":["unit_conversion_error","significant_figure_error","stoichiometric_ratio_error","unbalanced_reaction"]})
    relationships=[{"relationship_id":f"{cid}_PREREQ_{i:03d}","source_node_id":skills[i-1]["micro_skill_id"],"target_node_id":skills[i]["micro_skill_id"],"relationship_type":"PREREQUISITE"} for i in range(1,50)]
    enabled_skill_ids=[skill_id for procedure,family in zip(procedures,families) if family["engine_enabled"] for skill_id in procedure["micro_skill_ids"]]
    blueprints=[AssessmentBlueprintV1(f"{cid}_{role}",cid,count,{t["topic_id"]:.04 for t in topics},{"FOUNDATIONAL":.4,"DEVELOPING":.4,"ADVANCED":.2},{"numeric":1.0},minutes,unit_scope=tuple(u["unit_id"] for u in units),micro_skill_coverage=tuple(enabled_skill_ids[:15]),prerequisite_coverage=tuple(r["relationship_id"] for r in relationships[:10]),review_status="PROPOSED").to_dict() for role,count,minutes in (("PRACTICE",25,50),("SUMMATIVE",40,100))]
    descriptor=SubjectPackDescriptorV1("GENERAL_CHEMISTRY_PACK_V1","CHEMISTRY","1.0",("numeric_scalar","multiple_choice"),review_status="PROPOSED").to_dict()
    disabled=SupportDecisionV1("CHEMICAL_REACTION_DISABLED","chemical_reaction","UNSUPPORTED","Reaction grading is not production validated.","chemical_reaction",review_status="PROPOSED").to_dict()
    pack={"pack_id":"GENERAL_CHEMISTRY_PACK_V1","version":"1.0","noncanonical":True,"human_review_required":True,"canonical_authority":False,"descriptor":descriptor,"disabled_engine":disabled,"course":{"course_id":cid,"units":units,"topics":topics,"micro_skills":skills,"procedures":procedures,"generation_families":families,"relationships":relationships,"unit_policy":{"dimensional_analysis_required":True,"allowed_systems":["SI","DECLARED_CHEMICAL"]},"significant_figure_policy":{"round_at_end":True,"rule":"LEAST_PRECISE_MEASUREMENT"},"assessment_blueprints":blueprints,"target_validated_question_count":300}}
    pack["deterministic_sha256"]=hashlib.sha256(json.dumps(pack,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return pack

def validate_general_chemistry_pack(pack:dict[str,Any])->None:
    material={key:value for key,value in pack.items() if key!="deterministic_sha256"}
    if pack.get("deterministic_sha256")!=hashlib.sha256(json.dumps(material,sort_keys=True,separators=(",",":")).encode()).hexdigest(): raise ValueError("pack integrity hash mismatch")
    if not pack.get("noncanonical") or not pack.get("human_review_required") or pack.get("canonical_authority") is not False: raise ValueError("pack boundary invalid")
    c=pack.get("course",{})
    if len(c.get("units",[]))<8 or len(c.get("topics",[]))<25 or len(c.get("micro_skills",[]))<50 or len(c.get("procedures",[]))<15 or len(c.get("generation_families",[]))<15: raise ValueError("coverage incomplete")
    units={x["unit_id"] for x in c["units"]}; topics={x["topic_id"] for x in c["topics"]}; skills={x["micro_skill_id"] for x in c["micro_skills"]}; procedures={x["procedure_id"] for x in c["procedures"]}; families={x["family_id"] for x in c["generation_families"]}; relationships={x["relationship_id"] for x in c["relationships"]}
    if any(len(ids)!=count for ids,count in ((units,len(c["units"])),(topics,len(c["topics"])),(skills,len(c["micro_skills"])),(procedures,len(c["procedures"])),(families,len(c["generation_families"])),(relationships,len(c["relationships"])))): raise ValueError("duplicate identity")
    if any(x["unit_id"] not in units for x in c["topics"]) or any(x["topic_id"] not in topics for x in c["micro_skills"]): raise ValueError("hierarchy unresolved")
    topic_text=" ".join(str(x.get("title","")) for x in c["topics"]).lower()
    if any(area not in topic_text for area in AREAS): raise ValueError("required chemistry area missing")
    if any(not p["micro_skill_ids"] or any(x not in skills for x in p["micro_skill_ids"]) for p in c["procedures"]) or {x for p in c["procedures"] for x in p["micro_skill_ids"]}!=skills: raise ValueError("procedure coverage unresolved")
    if any(r.get("relationship_type")!="PREREQUISITE" or r.get("source_node_id") not in skills or r.get("target_node_id") not in skills or r.get("source_node_id")==r.get("target_node_id") for r in c["relationships"]): raise ValueError("relationship invalid")
    for family in c["generation_families"]:
        if family["procedure_id"] not in procedures or not family["parameter_domains"] or family["allocation_rules"].get("target_variants",0)<=1 or not family["formula_contract"] or not isinstance(family["formula_contract"].get("species"),list) or not family["formula_contract"]["species"] or not family["failure_signals"] or any(not isinstance(x,str) or not x for x in family["failure_signals"]): raise ValueError("family incomplete")
        if family["answer_engine"]=="chemical_reaction" and (family["engine_enabled"] or family["reaction_contract"]["execution_enabled"]): raise ValueError("disabled reaction engine cannot pass")
        if family["answer_engine"] not in {"numeric_scalar","chemical_reaction"} or (family["answer_engine"]=="numeric_scalar" and family["engine_enabled"] is not True): raise ValueError("answer engine invalid")
    enabled_capacity=sum(f["allocation_rules"]["target_variants"] for f in c["generation_families"] if f["engine_enabled"] is True)
    if enabled_capacity<c.get("target_validated_question_count",0): raise ValueError("enabled generation capacity insufficient")
    if c["unit_policy"]!={"dimensional_analysis_required":True,"allowed_systems":["SI","DECLARED_CHEMICAL"]} or c["significant_figure_policy"]!={"round_at_end":True,"rule":"LEAST_PRECISE_MEASUREMENT"}: raise ValueError("unit/significant-figure policy invalid")
    if pack["disabled_engine"]["status"]!="UNSUPPORTED" or len(c["assessment_blueprints"])!=2 or c["target_validated_question_count"]!=300: raise ValueError("engine or assessment policy invalid")
    for payload in c["assessment_blueprints"]:
        b=AssessmentBlueprintV1.from_dict(payload); distributions=(b.topic_weights,b.difficulty_distribution,b.question_type_distribution)
        if b.course_node_id!=c["course_id"] or b.question_count<len(b.micro_skill_coverage) or any(any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in d.values()) or abs(sum(d.values())-1)>1e-9 for d in distributions) or set(b.topic_weights)!=topics or set(b.difficulty_distribution)!={"FOUNDATIONAL","DEVELOPING","ADVANCED"} or set(b.question_type_distribution)!={"numeric"} or not b.unit_scope or not b.prerequisite_coverage or any(x not in units for x in b.unit_scope) or any(x not in skills for x in b.micro_skill_coverage) or any(x not in relationships for x in b.prerequisite_coverage): raise ValueError("blueprint invalid")
        enabled_procedures={f["procedure_id"] for f in c["generation_families"] if f["engine_enabled"] is True and f["answer_engine"]=="numeric_scalar"}
        reachable_skills={skill_id for p in c["procedures"] if p["procedure_id"] in enabled_procedures for skill_id in p["micro_skill_ids"]}
        if any(skill_id not in reachable_skills for skill_id in b.micro_skill_coverage): raise ValueError("blueprint skill has no compatible enabled family")
