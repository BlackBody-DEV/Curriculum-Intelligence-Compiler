"""Deterministic noncanonical engineering-mathematics course packs."""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from tools.course_compiler_demo.universal_core import AssessmentBlueprintV1, SubjectPackDescriptorV1


COURSE_UNITS = {
    "NUMERICAL_METHODS": ["Error and conditioning", "Root finding", "Linear systems", "Interpolation", "Numerical differentiation", "Numerical integration", "Initial-value problems", "Boundary-value problems"],
    "ENGINEERING_ANALYSIS": ["Engineering models", "Complex variables", "Linear algebraic models", "Ordinary differential equations", "Transforms", "Partial differential equations", "Vector analysis", "Approximation methods"],
    "APPLIED_MATHEMATICS": ["Mathematical modeling", "Discrete models", "Continuous models", "Optimization", "Probability models", "Dynamical systems", "Fields and operators", "Asymptotic analysis"],
}
COURSE_IDS = tuple(COURSE_UNITS)
ENGINE_ALLOCATIONS = ("numeric_scalar", "symbolic_expression", "matrix", "graph_diagram", "scientific_structured_response")
FAILURE_SIGNALS = ("model_selection_error", "algebra_error", "convergence_error", "dimension_error", "representation_error", "unsupported_assumption")


def _answer_contract(engine: str) -> dict[str, Any]:
    contracts = {
        "numeric_scalar":{"shape":"finite_scalar","tolerance":"DECLARED_PER_FAMILY","units":"DECLARED_OR_DIMENSIONLESS"},
        "symbolic_expression":{"shape":"bounded_symbolic_expression","equivalence":"ALGEBRAIC_WITH_DOMAIN"},
        "matrix":{"shape":"bounded_matrix","maximum_dimension":4,"entry_domain":"REAL"},
        "graph_diagram":{"shape":"coordinate_graph","required_features":["axes","scale","labeled_series"]},
        "scientific_structured_response":{"shape":"structured_fields","required_fields":["concepts","relationships","evidence"]},
    }
    return contracts[engine]


def _course(course_id: str, titles: list[str]) -> dict[str, Any]:
    units=[{"unit_id":f"{course_id}_UNIT_{i:02d}","title":title,"sequence":i} for i,title in enumerate(titles,1)]
    topics=[{"topic_id":f"{course_id}_TOPIC_{i:03d}","unit_id":units[(i-1)%8]["unit_id"],"title":f"{titles[(i-1)%8]} topic {i}"} for i in range(1,26)]
    skills=[{"micro_skill_id":f"{course_id}_SKILL_{i:03d}","topic_id":topics[(i-1)%25]["topic_id"],"title":f"Formulate and solve {topics[(i-1)%25]['title']} case {i}","difficulty":("FOUNDATIONAL","DEVELOPING","ADVANCED")[(i-1)%3]} for i in range(1,51)]
    procedures=[]
    for i in range(1,16):
        procedures.append({"procedure_id":f"{course_id}_PROC_{i:03d}","micro_skill_ids":[s["micro_skill_id"] for position,s in enumerate(skills) if position%15==i-1],"steps":["State variables, assumptions, and dimensions.","Select the declared mathematical representation.","Compute or transform using the bounded procedure.","Verify residual, dimensions, and limiting behavior."],"independent_check":"REQUIRED","review_status":"PROPOSED"})
    families=[]
    for i in range(1,16):
        engine=ENGINE_ALLOCATIONS[(i-1)%len(ENGINE_ALLOCATIONS)]
        families.append({"family_id":f"{course_id}_FAMILY_{i:03d}","micro_skill_id":skills[i-1]["micro_skill_id"],"procedure_id":procedures[i-1]["procedure_id"],"parameter_domains":{"scale":{"type":"number","minimum":0.1,"maximum":100.0},"order":{"type":"integer","minimum":1,"maximum":4},"variant":{"type":"integer","minimum":1,"maximum":20}},"difficulty_allocation":{"FOUNDATIONAL":.4,"DEVELOPING":.4,"ADVANCED":.2},"answer_contract":_answer_contract(engine),"answer_engine":engine,"failure_signals":[FAILURE_SIGNALS[(i-1)%len(FAILURE_SIGNALS)],"dimension_error"],"assessment_role":"PRACTICE_AND_SUMMATIVE","duplicate_constraints":{"parameter_fingerprint":"REQUIRED","maximum_exact_duplicates":0},"allocation_rules":{"target_variants":20,"unique_parameter_sets":True}})
    relationships=[{"relationship_id":f"{course_id}_PREREQ_{i:03d}","relationship_type":"PREREQUISITE","source_node_id":skills[i-1]["micro_skill_id"],"target_node_id":skills[i]["micro_skill_id"]} for i in range(1,50)]
    question_types={"numeric":.2,"symbolic":.2,"matrix":.2,"graph":.2,"structured_response":.2}
    blueprints=[AssessmentBlueprintV1(f"{course_id}_{role}",course_id,count,{t["topic_id"]:.04 for t in topics},{"FOUNDATIONAL":.4,"DEVELOPING":.4,"ADVANCED":.2},question_types,minutes,unit_scope=tuple(u["unit_id"] for u in units),micro_skill_coverage=tuple(s["micro_skill_id"] for s in skills[:15]),prerequisite_coverage=tuple(r["relationship_id"] for r in relationships[:10]),reuse_policy={"allow_reuse":False},variant_policy={"deterministic":True},scoring_rules={"default_points":1},review_status="PROPOSED").to_dict() for role,count,minutes in (("PRACTICE",25,50),("SUMMATIVE",40,100))]
    return {"course_id":course_id,"course_identity":{"course_id":course_id,"title":course_id.replace("_"," ").title(),"version":"1.0"},"domain":"ENGINEERING_MATHEMATICS","subject":course_id.replace("_"," ").title(),"noncanonical":True,"human_review_required":True,"canonical_authority":False,"units":units,"topics":topics,"micro_skills":skills,"procedures":procedures,"generation_families":families,"relationships":relationships,"difficulty_model":{"levels":["FOUNDATIONAL","DEVELOPING","ADVANCED"],"basis":"representation_complexity_conditioning_and_coupling"},"answer_engine_allocations":list(ENGINE_ALLOCATIONS),"failure_signal_allocations":list(FAILURE_SIGNALS),"asset_policy":{"requirement":"OPTIONAL","allowed_media_types":["coordinate_graph","matrix_table","engineering_schematic"],"rights_evidence_required":True,"student_performance_data":False},"unit_policy":{"dimensional_analysis_required":True,"unit_system":"DECLARED_PER_PROBLEM"},"assessment_blueprints":blueprints,"target_production_count":300,"target_validated_question_count":300}


def build_engineering_mathematics_catalog() -> dict[str, Any]:
    descriptor=SubjectPackDescriptorV1("ENGINEERING_MATHEMATICS_CATALOG_V1","ENGINEERING_MATHEMATICS","1.0",ENGINE_ALLOCATIONS,review_status="PROPOSED").to_dict()
    pack={"pack_id":"ENGINEERING_MATHEMATICS_CATALOG_V1","version":"1.0","noncanonical":True,"human_review_required":True,"canonical_authority":False,"descriptor":descriptor,"source_evidence":[{"source":"BOUNDED_ENGINEERING_MATHEMATICS_DESIGN","use":"NONCANONICAL_HUMAN_REVIEW_REQUIRED"}],"courses":{course_id:_course(course_id,titles) for course_id,titles in COURSE_UNITS.items()}}
    pack["deterministic_sha256"]=hashlib.sha256(json.dumps(pack,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return pack


def validate_engineering_mathematics_catalog(pack: dict[str, Any]) -> None:
    if pack.get("noncanonical") is not True or pack.get("human_review_required") is not True or pack.get("canonical_authority") is not False: raise ValueError("catalog boundary invalid")
    if set(pack.get("courses",{}))!=set(COURSE_IDS): raise ValueError("three engineering mathematics courses required")
    for course_id,course in pack["courses"].items():
        required={"course_identity","domain","subject","units","topics","micro_skills","procedures","generation_families","relationships","difficulty_model","answer_engine_allocations","failure_signal_allocations","asset_policy","assessment_blueprints","target_production_count"}
        if not required.issubset(course) or course.get("course_id")!=course_id or not course.get("noncanonical") or not course.get("human_review_required") or course.get("canonical_authority") is not False: raise ValueError("course common contract incomplete")
        if len(course["units"])<8 or len(course["topics"])<25 or len(course["micro_skills"])<50 or len(course["procedures"])<15 or len(course["generation_families"])<15 or len(course["assessment_blueprints"])!=2 or course["target_production_count"]!=300: raise ValueError("course coverage incomplete")
        units={x["unit_id"] for x in course["units"]}; topics={x["topic_id"] for x in course["topics"]}; skills={x["micro_skill_id"] for x in course["micro_skills"]}; procedures={x["procedure_id"] for x in course["procedures"]}; relationships={x["relationship_id"] for x in course["relationships"]}
        identities=(units,topics,skills,procedures,relationships)
        counts=(len(course["units"]),len(course["topics"]),len(course["micro_skills"]),len(course["procedures"]),len(course["relationships"]))
        if any(len(values)!=count for values,count in zip(identities,counts)): raise ValueError("duplicate identity")
        if any(t["unit_id"] not in units for t in course["topics"]) or any(s["topic_id"] not in topics for s in course["micro_skills"]): raise ValueError("hierarchy unresolved")
        if {x for p in course["procedures"] for x in p["micro_skill_ids"]}!=skills or any(not p["micro_skill_ids"] or p.get("independent_check")!="REQUIRED" for p in course["procedures"]): raise ValueError("procedure coverage incomplete")
        if any(r.get("relationship_type")!="PREREQUISITE" or r.get("source_node_id") not in skills or r.get("target_node_id") not in skills for r in course["relationships"]): raise ValueError("prerequisite unresolved")
        if tuple(course["answer_engine_allocations"])!=ENGINE_ALLOCATIONS or set(course["failure_signal_allocations"])!=set(FAILURE_SIGNALS) or not course["asset_policy"] or course["asset_policy"].get("student_performance_data") is not False: raise ValueError("allocation or asset policy invalid")
        family_ids=set(); allocated=set()
        for family in course["generation_families"]:
            family_required={"family_id","micro_skill_id","procedure_id","parameter_domains","difficulty_allocation","answer_contract","answer_engine","failure_signals","assessment_role","duplicate_constraints"}
            if not family_required.issubset(family) or family["family_id"] in family_ids or family["micro_skill_id"] not in skills or family["procedure_id"] not in procedures: raise ValueError("generation family incomplete")
            family_ids.add(family["family_id"]); allocated.add(family["answer_engine"])
            if family["answer_engine"] not in ENGINE_ALLOCATIONS or family["answer_contract"]!=_answer_contract(family["answer_engine"]): raise ValueError("answer engine contract invalid")
            if set(family["difficulty_allocation"])!={"FOUNDATIONAL","DEVELOPING","ADVANCED"} or abs(sum(family["difficulty_allocation"].values())-1)>1e-9: raise ValueError("difficulty allocation invalid")
            if not family["parameter_domains"] or not set(family["failure_signals"]).issubset(FAILURE_SIGNALS) or family["assessment_role"]!="PRACTICE_AND_SUMMATIVE" or family["duplicate_constraints"]!={"parameter_fingerprint":"REQUIRED","maximum_exact_duplicates":0}: raise ValueError("generation policy invalid")
        if allocated!=set(ENGINE_ALLOCATIONS): raise ValueError("all required answer engines must be allocated")
        for payload in course["assessment_blueprints"]:
            blueprint=AssessmentBlueprintV1.from_dict(payload)
            if blueprint.course_node_id!=course_id or not blueprint.unit_scope or not blueprint.prerequisite_coverage or any(x not in units for x in blueprint.unit_scope) or any(x not in skills for x in blueprint.micro_skill_coverage) or any(x not in relationships for x in blueprint.prerequisite_coverage): raise ValueError("assessment blueprint unresolved")
            for distribution in (blueprint.topic_weights,blueprint.difficulty_distribution,blueprint.question_type_distribution):
                if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in distribution.values()) or abs(sum(distribution.values())-1)>1e-9: raise ValueError("assessment distribution invalid")
