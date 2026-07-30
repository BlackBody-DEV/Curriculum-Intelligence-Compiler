"""Deterministic Programming Fundamentals curriculum reference pack."""
from __future__ import annotations
import hashlib,json
import math
from typing import Any
from tools.course_compiler_demo.universal_core import AssessmentBlueprintV1, SubjectPackDescriptorV1, SupportDecisionV1

AREAS=["variables and types","expressions","conditionals","loops","functions","scope","collections","strings","input and output","exceptions","testing","debugging","basic recursion","basic algorithmic complexity"]

def build_programming_fundamentals_pack()->dict[str,Any]:
    course_id="PROGRAMMING_FUNDAMENTALS"
    units=[{"unit_id":f"{course_id}_UNIT_{i:02d}","title":AREAS[(i-1)%len(AREAS)]} for i in range(1,9)]
    topics=[{"topic_id":f"{course_id}_TOPIC_{i:03d}","unit_id":units[(i-1)%8]["unit_id"],"title":f"{AREAS[(i-1)%len(AREAS)]} {i}"} for i in range(1,26)]
    skills=[{"micro_skill_id":f"{course_id}_SKILL_{i:03d}","topic_id":topics[(i-1)%25]["topic_id"],"title":f"Implement {AREAS[(i-1)%len(AREAS)]} task {i}"} for i in range(1,51)]
    procedures=[{"procedure_id":f"{course_id}_PROC_{i:03d}","micro_skill_ids":[skill["micro_skill_id"] for position,skill in enumerate(skills) if position%15==i-1],"steps":["Read the input contract.","Trace or construct the algorithm.","Check outputs against declared cases."],"review_status":"PROPOSED"} for i in range(1,16)]
    families=[]
    for i in range(1,16):
        executable=i%5==0
        families.append({"family_id":f"{course_id}_FAMILY_{i:03d}","procedure_id":procedures[(i-1)%15]["procedure_id"],"answer_engine":"code_execution" if executable else "multiple_choice","engine_enabled":not executable,"parameter_domains":{"input_size":{"minimum":1,"maximum":100}},"allocation_rules":{"target_variants":20},"code_answer_contract":{"language":"python","entrypoint":"solve","executable_grading_enabled":False},"input_output_contract":{"input_schema":{"type":"array"},"output_schema":{"type":"string"}},"unit_test_grading":{"cases":[{"input":[1],"expected":"1"}],"execution_enabled":False},"failure_signals":["syntax_reasoning_error","control_flow_error","boundary_case_error"]})
    relationships=[{"relationship_id":f"{course_id}_PREREQ_{i:03d}","source_node_id":skills[i-1]["micro_skill_id"],"target_node_id":skills[i]["micro_skill_id"],"relationship_type":"PREREQUISITE"} for i in range(1,50)]
    blueprints=[AssessmentBlueprintV1(f"{course_id}_{role}",course_id,count,{t["topic_id"]:.04 for t in topics},{"FOUNDATIONAL":.4,"DEVELOPING":.4,"ADVANCED":.2},{"multiple_choice":1.0},minutes,unit_scope=tuple(u["unit_id"] for u in units),micro_skill_coverage=tuple(s["micro_skill_id"] for s in skills[:15]),review_status="PROPOSED").to_dict() for role,count,minutes in (("PRACTICE",25,45),("SUMMATIVE",40,90))]
    descriptor=SubjectPackDescriptorV1("PROGRAMMING_FUNDAMENTALS_PACK_V1","COMPUTER_SCIENCE","1.0",("multiple_choice",),review_status="PROPOSED").to_dict()
    disabled=SupportDecisionV1("CODE_EXECUTION_DISABLED","code_execution","UNSUPPORTED","Executable grading is not production validated.","code_execution",review_status="PROPOSED").to_dict()
    pack={"pack_id":"PROGRAMMING_FUNDAMENTALS_PACK_V1","version":"1.0","noncanonical":True,"human_review_required":True,"canonical_authority":False,"descriptor":descriptor,"disabled_engine":disabled,"course":{"course_id":course_id,"units":units,"topics":topics,"micro_skills":skills,"procedures":procedures,"generation_families":families,"relationships":relationships,"assessment_blueprints":blueprints,"target_validated_question_count":300}}
    pack["deterministic_sha256"]=hashlib.sha256(json.dumps(pack,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return pack

def validate_programming_fundamentals_pack(pack:dict[str,Any])->None:
    material={key:value for key,value in pack.items() if key!="deterministic_sha256"}
    if pack.get("deterministic_sha256")!=hashlib.sha256(json.dumps(material,sort_keys=True,separators=(",",":")).encode()).hexdigest(): raise ValueError("pack integrity hash mismatch")
    if not pack.get("noncanonical") or not pack.get("human_review_required") or pack.get("canonical_authority") is not False: raise ValueError("pack boundary invalid")
    course=pack.get("course",{})
    if len(course.get("units",[]))<8 or len(course.get("topics",[]))<25 or len(course.get("micro_skills",[]))<50 or len(course.get("procedures",[]))<15 or len(course.get("generation_families",[]))<15: raise ValueError("coverage incomplete")
    units={x["unit_id"] for x in course["units"]}; topics={x["topic_id"] for x in course["topics"]}; skills={x["micro_skill_id"] for x in course["micro_skills"]}; procedures={x["procedure_id"] for x in course["procedures"]}; families={x["family_id"] for x in course["generation_families"]}; relationships={x["relationship_id"] for x in course["relationships"]}
    if any(len(ids)!=count for ids,count in ((units,len(course["units"])),(topics,len(course["topics"])),(skills,len(course["micro_skills"])),(procedures,len(course["procedures"])),(families,len(course["generation_families"])),(relationships,len(course["relationships"])))) or any(not isinstance(identity,str) or not identity.strip() for identity in relationships): raise ValueError("duplicate or blank identity")
    if any(x["unit_id"] not in units for x in course["topics"]) or any(x["topic_id"] not in topics for x in course["micro_skills"]): raise ValueError("hierarchy unresolved")
    if any(not p["micro_skill_ids"] or any(x not in skills for x in p["micro_skill_ids"]) for p in course["procedures"]) or {x for p in course["procedures"] for x in p["micro_skill_ids"]}!=skills: raise ValueError("procedure coverage unresolved")
    if any(rel.get("relationship_type")!="PREREQUISITE" or rel.get("source_node_id") not in skills or rel.get("target_node_id") not in skills or rel.get("source_node_id")==rel.get("target_node_id") for rel in course["relationships"]): raise ValueError("relationship unresolved")
    for family in course["generation_families"]:
        if family["procedure_id"] not in procedures or not family["parameter_domains"] or not family["allocation_rules"]: raise ValueError("family incomplete")
        if family["answer_engine"]=="code_execution" and (family["engine_enabled"] or family["code_answer_contract"]["executable_grading_enabled"] or family["unit_test_grading"]["execution_enabled"]): raise ValueError("disabled code engine cannot execute")
        code=family.get("code_answer_contract")
        if not isinstance(code,dict) or set(code)!={"language","entrypoint","executable_grading_enabled"} or not isinstance(code["language"],str) or not code["language"].strip() or not isinstance(code["entrypoint"],str) or not code["entrypoint"].strip() or not isinstance(code["executable_grading_enabled"],bool): raise ValueError("code answer contract invalid")
        cases=family["unit_test_grading"].get("cases")
        io=family.get("input_output_contract")
        if not isinstance(cases,list) or not cases or any(not isinstance(case,dict) or set(case)!={"input","expected"} for case in cases): raise ValueError("test case structure invalid")
        if not isinstance(io,dict) or set(io)!={"input_schema","output_schema"} or any(not isinstance(io[key],dict) or not isinstance(io[key].get("type"),str) or not io[key]["type"] for key in io): raise ValueError("input/output contract invalid")
    if pack["disabled_engine"]["status"]!="UNSUPPORTED" or len(course["assessment_blueprints"])!=2 or course["target_validated_question_count"]!=300: raise ValueError("disabled engine or assessment policy invalid")
    for payload in course["assessment_blueprints"]:
        blueprint=AssessmentBlueprintV1.from_dict(payload)
        distributions=(blueprint.topic_weights,blueprint.difficulty_distribution,blueprint.question_type_distribution)
        if blueprint.course_node_id!=course["course_id"] or blueprint.question_count<len(blueprint.micro_skill_coverage) or any(any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in d.values()) or abs(sum(d.values())-1)>1e-9 for d in distributions) or set(blueprint.topic_weights)!=topics or set(blueprint.difficulty_distribution)!={"FOUNDATIONAL","DEVELOPING","ADVANCED"} or set(blueprint.question_type_distribution)!={"multiple_choice"} or any(x not in units for x in blueprint.unit_scope) or any(x not in skills for x in blueprint.micro_skill_coverage): raise ValueError("blueprint invalid")
