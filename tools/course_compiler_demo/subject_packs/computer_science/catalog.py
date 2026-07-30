"""Expanded, noncanonical computer-science course catalog."""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from tools.course_compiler_demo.universal_core import AssessmentBlueprintV1, SubjectPackDescriptorV1
from .pack import build_programming_fundamentals_pack


COURSE_UNITS={
    "DATA_STRUCTURES":["Abstract data types","Arrays and linked lists","Stacks and queues","Hash tables","Trees","Heaps","Graphs","Data-structure selection"],
    "ALGORITHMS":["Algorithm analysis","Searching","Sorting","Divide and conquer","Greedy methods","Dynamic programming","Graph algorithms","Correctness and limits"],
    "COMPUTATIONAL_THINKING":["Problem decomposition","Pattern recognition","Abstraction","Algorithm design","Data representation","Simulation","Testing and debugging","Impacts and tradeoffs"],
}
COURSE_IDS=tuple(COURSE_UNITS)
ENGINE_ALLOCATIONS=("code_execution","multiple_choice","numeric_vector","rubric_scored_explanation")
FAILURE_SIGNALS=("syntax_error","logic_error","boundary_case_error","complexity_error","trace_error","invariant_error","unsupported_freeform")


def _answer_contract(engine:str)->dict[str,Any]:
    return {
        "code_execution":{"language":"python","entrypoint":"solve","sandbox":"BOUNDED_NO_IO_NO_NETWORK","unit_tests_required":True},
        "multiple_choice":{"shape":"single_declared_option","exactly_one_correct":True},
        "numeric_vector":{"shape":"ordered_numeric_trace","maximum_length":20,"tolerance":0},
        "rubric_scored_explanation":{"shape":"structured_rubric_fields","freeform_prose":False,"partial_credit":"DETERMINISTIC"},
    }[engine]


def _course(course_id:str,titles:list[str])->dict[str,Any]:
    units=[{"unit_id":f"{course_id}_UNIT_{i:02d}","title":title,"sequence":i} for i,title in enumerate(titles,1)]
    topics=[{"topic_id":f"{course_id}_TOPIC_{i:03d}","unit_id":units[(i-1)%8]["unit_id"],"title":f"{titles[(i-1)%8]} topic {i}"} for i in range(1,26)]
    skills=[{"micro_skill_id":f"{course_id}_SKILL_{i:03d}","topic_id":topics[(i-1)%25]["topic_id"],"title":f"Construct or analyze {topics[(i-1)%25]['title']} case {i}","difficulty":("FOUNDATIONAL","DEVELOPING","ADVANCED")[(i-1)%3]} for i in range(1,51)]
    procedures=[{"procedure_id":f"{course_id}_PROC_{i:03d}","micro_skill_ids":[s["micro_skill_id"] for p,s in enumerate(skills) if p%15==i-1],"steps":["Declare input, output, and preconditions.","Trace or construct the bounded algorithm.","Check invariants and edge cases.","Evaluate result and complexity."],"independent_check":"REQUIRED","review_status":"PROPOSED"} for i in range(1,16)]
    families=[]
    for i in range(1,16):
        engine=ENGINE_ALLOCATIONS[(i-1)%4]
        family={"family_id":f"{course_id}_FAMILY_{i:03d}","micro_skill_id":skills[i-1]["micro_skill_id"],"procedure_id":procedures[i-1]["procedure_id"],"parameter_domains":{"input_size":{"type":"integer","minimum":1,"maximum":100},"variant":{"type":"integer","minimum":1,"maximum":20}},"difficulty_allocation":{"FOUNDATIONAL":.4,"DEVELOPING":.4,"ADVANCED":.2},"answer_contract":_answer_contract(engine),"answer_engine":engine,"failure_signals":[FAILURE_SIGNALS[(i-1)%len(FAILURE_SIGNALS)],"boundary_case_error"],"assessment_role":"PRACTICE_AND_SUMMATIVE","duplicate_constraints":{"parameter_fingerprint":"REQUIRED","maximum_exact_duplicates":0},"allocation_rules":{"target_variants":20,"unique_parameter_sets":True}}
        if engine=="code_execution": family["bounded_execution"]={"language":"python","entrypoint":"solve","timeout_ms":1000,"memory_mb":64,"network":False,"filesystem":False,"imports":[]}
        families.append(family)
    relationships=[{"relationship_id":f"{course_id}_PREREQ_{i:03d}","relationship_type":"PREREQUISITE","source_node_id":skills[i-1]["micro_skill_id"],"target_node_id":skills[i]["micro_skill_id"]} for i in range(1,50)]
    qtypes={"code":.25,"multiple_choice":.25,"numeric_trace":.25,"rubric":.25}
    blueprints=[AssessmentBlueprintV1(f"{course_id}_{role}",course_id,count,{t["topic_id"]:.04 for t in topics},{"FOUNDATIONAL":.4,"DEVELOPING":.4,"ADVANCED":.2},qtypes,minutes,unit_scope=tuple(u["unit_id"] for u in units),micro_skill_coverage=tuple(s["micro_skill_id"] for s in skills[:15]),prerequisite_coverage=tuple(r["relationship_id"] for r in relationships[:10]),reuse_policy={"allow_reuse":False},variant_policy={"deterministic":True},scoring_rules={"default_points":1},review_status="PROPOSED").to_dict() for role,count,minutes in (("PRACTICE",25,45),("SUMMATIVE",40,90))]
    return {"course_id":course_id,"course_identity":{"course_id":course_id,"title":course_id.replace("_"," ").title(),"version":"1.0"},"domain":"COMPUTER_SCIENCE","subject":course_id.replace("_"," ").title(),"noncanonical":True,"human_review_required":True,"canonical_authority":False,"units":units,"topics":topics,"micro_skills":skills,"procedures":procedures,"generation_families":families,"relationships":relationships,"difficulty_model":{"levels":["FOUNDATIONAL","DEVELOPING","ADVANCED"],"basis":"input_size_abstraction_and_algorithmic_complexity"},"answer_engine_allocations":list(ENGINE_ALLOCATIONS),"failure_signal_allocations":list(FAILURE_SIGNALS),"asset_policy":{"requirement":"OPTIONAL","allowed_media_types":["trace_table","data_structure_diagram","flowchart"],"rights_evidence_required":True,"student_performance_data":False},"assessment_blueprints":blueprints,"target_production_count":300,"target_validated_question_count":300}


def build_computer_science_course_catalog()->dict[str,Any]:
    legacy=build_programming_fundamentals_pack()
    descriptor=SubjectPackDescriptorV1("COMPUTER_SCIENCE_COURSE_CATALOG_V1","COMPUTER_SCIENCE","1.0",ENGINE_ALLOCATIONS,review_status="PROPOSED").to_dict()
    courses={"PROGRAMMING_FUNDAMENTALS":legacy["course"]}; courses.update({cid:_course(cid,titles) for cid,titles in COURSE_UNITS.items()})
    pack={"pack_id":"COMPUTER_SCIENCE_COURSE_CATALOG_V1","version":"1.0","noncanonical":True,"human_review_required":True,"canonical_authority":False,"descriptor":descriptor,"programming_fundamentals_reference":{"pack_id":legacy["pack_id"],"deterministic_sha256":legacy["deterministic_sha256"],"access":"PRESERVED_READ_ONLY_PAYLOAD"},"courses":courses}
    pack["deterministic_sha256"]=hashlib.sha256(json.dumps(pack,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return pack


def validate_computer_science_course_catalog(pack:dict[str,Any])->None:
    if pack.get("noncanonical") is not True or pack.get("human_review_required") is not True or pack.get("canonical_authority") is not False: raise ValueError("catalog boundary invalid")
    if set(pack.get("courses",{}))!={"PROGRAMMING_FUNDAMENTALS",*COURSE_IDS}: raise ValueError("required courses missing")
    legacy=build_programming_fundamentals_pack()
    if pack["courses"]["PROGRAMMING_FUNDAMENTALS"]!=legacy["course"] or pack.get("programming_fundamentals_reference")!={"pack_id":legacy["pack_id"],"deterministic_sha256":legacy["deterministic_sha256"],"access":"PRESERVED_READ_ONLY_PAYLOAD"}: raise ValueError("Programming Fundamentals changed")
    for course_id in COURSE_IDS:
        course=pack["courses"][course_id]; required={"course_identity","domain","subject","units","topics","micro_skills","procedures","generation_families","relationships","difficulty_model","answer_engine_allocations","failure_signal_allocations","asset_policy","assessment_blueprints","target_production_count"}
        if not required.issubset(course) or course.get("course_id")!=course_id or not course.get("noncanonical") or not course.get("human_review_required") or course.get("canonical_authority") is not False: raise ValueError("course common contract incomplete")
        if len(course["units"])<8 or len(course["topics"])<25 or len(course["micro_skills"])<50 or len(course["procedures"])<15 or len(course["generation_families"])<15 or len(course["assessment_blueprints"])!=2 or course.get("target_production_count")!=300: raise ValueError("course coverage incomplete")
        units={x["unit_id"] for x in course["units"]}; topics={x["topic_id"] for x in course["topics"]}; skills={x["micro_skill_id"] for x in course["micro_skills"]}; procedures={x["procedure_id"] for x in course["procedures"]}; relationships={x["relationship_id"] for x in course["relationships"]}
        for values,count in ((units,len(course["units"])),(topics,len(course["topics"])),(skills,len(course["micro_skills"])),(procedures,len(course["procedures"])),(relationships,len(course["relationships"]))):
            if len(values)!=count: raise ValueError("duplicate identity")
        if any(t["unit_id"] not in units for t in course["topics"]) or any(s["topic_id"] not in topics for s in course["micro_skills"]): raise ValueError("hierarchy unresolved")
        if {x for p in course["procedures"] for x in p["micro_skill_ids"]}!=skills or any(not p["micro_skill_ids"] or p.get("independent_check")!="REQUIRED" for p in course["procedures"]): raise ValueError("procedure coverage incomplete")
        if any(r.get("relationship_type")!="PREREQUISITE" or r.get("source_node_id") not in skills or r.get("target_node_id") not in skills for r in course["relationships"]): raise ValueError("prerequisite unresolved")
        if tuple(course["answer_engine_allocations"])!=ENGINE_ALLOCATIONS or set(course["failure_signal_allocations"])!=set(FAILURE_SIGNALS) or not course["asset_policy"] or course["asset_policy"].get("student_performance_data") is not False: raise ValueError("allocation or asset policy invalid")
        family_ids=set(); allocated=set()
        for family in course["generation_families"]:
            family_required={"family_id","micro_skill_id","procedure_id","parameter_domains","difficulty_allocation","answer_contract","answer_engine","failure_signals","assessment_role","duplicate_constraints"}
            if not family_required.issubset(family) or family["family_id"] in family_ids or family["micro_skill_id"] not in skills or family["procedure_id"] not in procedures: raise ValueError("generation family incomplete")
            family_ids.add(family["family_id"]); allocated.add(family["answer_engine"])
            if family["answer_engine"] not in ENGINE_ALLOCATIONS or family["answer_contract"]!=_answer_contract(family["answer_engine"]): raise ValueError("answer contract invalid")
            if set(family["difficulty_allocation"])!={"FOUNDATIONAL","DEVELOPING","ADVANCED"} or abs(sum(family["difficulty_allocation"].values())-1)>1e-9 or not family["parameter_domains"]: raise ValueError("parameter or difficulty allocation invalid")
            if not set(family["failure_signals"]).issubset(FAILURE_SIGNALS) or family["assessment_role"]!="PRACTICE_AND_SUMMATIVE" or family["duplicate_constraints"]!={"parameter_fingerprint":"REQUIRED","maximum_exact_duplicates":0}: raise ValueError("family policy invalid")
            if family["answer_engine"]=="code_execution" and family.get("bounded_execution")!={"language":"python","entrypoint":"solve","timeout_ms":1000,"memory_mb":64,"network":False,"filesystem":False,"imports":[]}: raise ValueError("bounded code contract invalid")
        if allocated!=set(ENGINE_ALLOCATIONS): raise ValueError("all required engines must be allocated")
        for payload in course["assessment_blueprints"]:
            blueprint=AssessmentBlueprintV1.from_dict(payload)
            if blueprint.course_node_id!=course_id or not blueprint.unit_scope or not blueprint.prerequisite_coverage or any(x not in units for x in blueprint.unit_scope) or any(x not in skills for x in blueprint.micro_skill_coverage) or any(x not in relationships for x in blueprint.prerequisite_coverage): raise ValueError("blueprint unresolved")
            for distribution in (blueprint.topic_weights,blueprint.difficulty_distribution,blueprint.question_type_distribution):
                if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in distribution.values()) or abs(sum(distribution.values())-1)>1e-9: raise ValueError("blueprint distribution invalid")
