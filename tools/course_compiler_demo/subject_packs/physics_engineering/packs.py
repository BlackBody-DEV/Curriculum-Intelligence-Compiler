"""Deterministic physics and engineering reference curriculum."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
from typing import Any
from tools.course_compiler_demo.universal_core import AssessmentBlueprintV1, SubjectPackDescriptorV1

ROOT = Path(__file__).resolve().parents[4]
STATICS_AREAS = ["Centroids", "Vector Operations", "Force Systems", "Moments and Couples", "equilibrium", "distributed loading", "trusses", "frames"]
EM_AREAS = ["electric charge", "Coulomb force", "electric field", "electric potential", "Gauss's law", "capacitance", "current and resistance", "DC circuits", "magnetic force", "magnetic field", "electromagnetic induction", "Maxwell relationships"]
AUTHORITY_FILE = "tools/course_compiler_demo/sample_inputs/real_statics/STATICS_REAL_SOURCE_ME_2301_CURRICULUM_EXTRACTION_V1/original/me_2301_statics_curriculum_extraction.md"

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _course(course_id: str, areas: list[str]) -> dict[str, Any]:
    units = [{"unit_id": f"{course_id}_UNIT_{i:02d}", "title": areas[(i-1) % len(areas)]} for i in range(1, 9)]
    topics = [{"topic_id": f"{course_id}_TOPIC_{i:03d}", "unit_id": units[(i-1)%8]["unit_id"], "title": f"{areas[(i-1)%len(areas)]} {i}"} for i in range(1, 26)]
    skills = [{"micro_skill_id": f"{course_id}_SKILL_{i:03d}", "topic_id": topics[(i-1)%25]["topic_id"], "title": f"Resolve {areas[(i-1)%len(areas)]} case {i}"} for i in range(1, 51)]
    procedures = [{"procedure_id": f"{course_id}_PROC_{i:03d}", "micro_skill_ids": [skill["micro_skill_id"] for position, skill in enumerate(skills) if position % 15 == i-1], "steps": ["Declare units and coordinate convention.", "Apply the governing relationship.", "Check dimensions and signs."], "unit_policy": "SI_EXPLICIT", "vector_convention": "RIGHT_HANDED_CARTESIAN"} for i in range(1, 16)]
    families = [{"family_id": f"{course_id}_FAMILY_{i:03d}", "procedure_id": procedures[(i-1)%15]["procedure_id"], "answer_engine": "numeric_vector" if i%3==0 else "numeric_scalar", "parameter_domains": {"magnitude": [1, 1000], "angle_degrees": [0, 359]}, "allocation_rules": {"target_variants": 20, "unit_consistent": True}, "failure_signals": ["unit_mismatch", "axis_confusion", "sign_error"]} for i in range(1,16)]
    relationships = [{"relationship_id": f"{course_id}_PREREQ_{i:03d}", "source_node_id": skills[i-1]["micro_skill_id"], "target_node_id": skills[i]["micro_skill_id"], "relationship_type": "PREREQUISITE"} for i in range(1,50)]
    blueprints = [AssessmentBlueprintV1(f"{course_id}_{role}", course_id, count, {t["topic_id"]: .04 for t in topics}, {"FOUNDATIONAL":.4,"DEVELOPING":.4,"ADVANCED":.2}, {"numeric":1.0}, minutes, unit_scope=tuple(u["unit_id"] for u in units), micro_skill_coverage=tuple(s["micro_skill_id"] for s in skills[:15]), prerequisite_coverage=tuple(r["relationship_id"] for r in relationships[:10]), review_status="PROPOSED").to_dict() for role,count,minutes in (("PRACTICE",25,50),("SUMMATIVE",40,100))]
    return {"course_id":course_id,"units":units,"topics":topics,"micro_skills":skills,"procedures":procedures,"generation_families":families,"relationships":relationships,"unit_policy":{"system":"SI","dimensional_analysis_required":True},"vector_convention":{"basis":"RIGHT_HANDED_CARTESIAN","angle_reference":"POSITIVE_X_CCW"},"failure_signals":["unit_mismatch","axis_confusion","sign_error"],"assessment_blueprints":blueprints,"target_validated_question_count":300}

def build_physics_engineering_reference_pack() -> dict[str, Any]:
    authority_path = ROOT / AUTHORITY_FILE
    refs = [{"authority_identity": area.upper().replace(" ","_"), "relative_path": AUTHORITY_FILE, "sha256": _sha(authority_path), "access":"READ_ONLY_REFERENCE"} for area in STATICS_AREAS[:4]]
    descriptor = SubjectPackDescriptorV1("PHYSICS_ENGINEERING_REFERENCE_PACK_V1","PHYSICS_ENGINEERING","1.0",("numeric_scalar","numeric_vector","multiple_choice"),review_status="PROPOSED").to_dict()
    pack={"pack_id":"PHYSICS_ENGINEERING_REFERENCE_PACK_V1","version":"1.0","noncanonical":True,"human_review_required":True,"canonical_authority":False,"descriptor":descriptor,"statics_authority_references":refs,"courses":{"STATICS":_course("STATICS",STATICS_AREAS),"ELECTRICITY_AND_MAGNETISM":_course("ELECTRICITY_AND_MAGNETISM",EM_AREAS)}}
    pack["deterministic_sha256"]=hashlib.sha256(json.dumps(pack,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return pack

def validate_physics_engineering_reference_pack(pack: dict[str, Any]) -> None:
    if not pack.get("noncanonical") or not pack.get("human_review_required") or pack.get("canonical_authority") is not False: raise ValueError("pack boundary invalid")
    if set(pack.get("courses",{}))!={"STATICS","ELECTRICITY_AND_MAGNETISM"}: raise ValueError("required courses missing")
    expected_authorities={"CENTROIDS","VECTOR_OPERATIONS","FORCE_SYSTEMS","MOMENTS_AND_COUPLES"}
    if {ref.get("authority_identity") for ref in pack.get("statics_authority_references",[])}!=expected_authorities or len(pack["statics_authority_references"])!=4: raise ValueError("complete Statics authority references are required")
    for ref in pack["statics_authority_references"]:
        if ref.get("relative_path")!=AUTHORITY_FILE or ref.get("access")!="READ_ONLY_REFERENCE": raise ValueError("unsafe Statics authority reference")
        path=ROOT/ref["relative_path"]
        if not path.is_file() or _sha(path)!=ref["sha256"]: raise ValueError("Statics authority reference does not resolve")
    for course in pack["courses"].values():
        if len(course["units"])<8 or len(course["topics"])<25 or len(course["micro_skills"])<50 or len(course["procedures"])<15 or len(course["generation_families"])<15: raise ValueError("course coverage incomplete")
        units={x["unit_id"] for x in course["units"]}; topics={x["topic_id"] for x in course["topics"]}; skills={x["micro_skill_id"] for x in course["micro_skills"]}; procedures={x["procedure_id"] for x in course["procedures"]}; families={x["family_id"] for x in course["generation_families"]}; relationships={x["relationship_id"] for x in course["relationships"]}
        if any(len(ids)!=count for ids,count in ((units,len(course["units"])),(topics,len(course["topics"])),(skills,len(course["micro_skills"])),(procedures,len(course["procedures"])),(families,len(course["generation_families"])),(relationships,len(course["relationships"])))): raise ValueError("duplicate identity")
        if any(x["unit_id"] not in units for x in course["topics"]) or any(x["topic_id"] not in topics for x in course["micro_skills"]): raise ValueError("hierarchy unresolved")
        if any(not p["micro_skill_ids"] or any(x not in skills for x in p["micro_skill_ids"]) for p in course["procedures"]): raise ValueError("procedure unresolved")
        if {x for p in course["procedures"] for x in p["micro_skill_ids"]}!=skills: raise ValueError("skill coverage incomplete")
        if any(r.get("relationship_type")!="PREREQUISITE" or r.get("source_node_id") not in skills or r.get("target_node_id") not in skills or r.get("source_node_id")==r.get("target_node_id") for r in course["relationships"]): raise ValueError("prerequisite relationship invalid")
        if any(x["procedure_id"] not in procedures or x["answer_engine"] not in {"numeric_scalar","numeric_vector"} or not x["parameter_domains"] or not x["allocation_rules"] for x in course["generation_families"]): raise ValueError("generation family incomplete")
        if course["unit_policy"]!={"system":"SI","dimensional_analysis_required":True} or course["vector_convention"]!={"basis":"RIGHT_HANDED_CARTESIAN","angle_reference":"POSITIVE_X_CCW"}: raise ValueError("unit/vector policy invalid")
        if len(course["assessment_blueprints"])!=2 or course["target_validated_question_count"]!=300: raise ValueError("assessment coverage incomplete")
        relationship_ids=relationships
        for payload in course["assessment_blueprints"]:
            blueprint=AssessmentBlueprintV1.from_dict(payload)
            if blueprint.course_node_id!=course["course_id"] or blueprint.question_count<len(blueprint.micro_skill_coverage) or any(x not in skills for x in blueprint.micro_skill_coverage): raise ValueError("blueprint invalid")
            distributions=(blueprint.topic_weights,blueprint.difficulty_distribution,blueprint.question_type_distribution)
            if any(any(not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 for value in d.values()) or abs(sum(d.values())-1)>1e-9 for d in distributions): raise ValueError("blueprint distributions invalid")
            if set(blueprint.topic_weights)!=topics or set(blueprint.difficulty_distribution)!={"FOUNDATIONAL","DEVELOPING","ADVANCED"} or set(blueprint.question_type_distribution)!={"numeric"} or not blueprint.unit_scope or not blueprint.prerequisite_coverage or any(x not in units for x in blueprint.unit_scope) or any(x not in relationship_ids for x in blueprint.prerequisite_coverage): raise ValueError("blueprint scope invalid")
