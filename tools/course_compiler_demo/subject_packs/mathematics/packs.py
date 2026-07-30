"""Deterministic, evidence-labeled mathematics curriculum reference packs."""
from __future__ import annotations
import hashlib
import json
import math
from typing import Any
from tools.course_compiler_demo.universal_core import AssessmentBlueprintV1, SubjectPackDescriptorV1

COURSES = {
    "ALGEBRA_I": ["expressions", "linear equations", "inequalities", "functions", "systems", "exponents", "polynomials", "factoring", "quadratics", "data and modeling"],
    "CALCULUS_I": ["functions and limits", "continuity", "derivatives", "derivative rules", "implicit differentiation", "applications of derivatives", "optimization", "antiderivatives", "definite integrals", "Fundamental Theorem of Calculus", "integration applications"],
}

def _slug(value: str) -> str:
    return "_".join(value.lower().replace("'", "").split())

def _course(course_id: str, areas: list[str]) -> dict[str, Any]:
    units = [{"unit_id": f"{course_id}_UNIT_{i:02d}", "title": areas[(i - 1) % len(areas)]} for i in range(1, 9)]
    topics = [{"topic_id": f"{course_id}_TOPIC_{i:03d}", "unit_id": units[(i - 1) % 8]["unit_id"], "title": f"{areas[(i - 1) % len(areas)]} topic {i}"} for i in range(1, 26)]
    skills = [{"micro_skill_id": f"{course_id}_SKILL_{i:03d}", "topic_id": topics[(i - 1) % 25]["topic_id"], "title": f"Apply {_slug(areas[(i - 1) % len(areas)])} skill {i}"} for i in range(1, 51)]
    procedures = [{"procedure_id": f"{course_id}_PROC_{i:03d}", "micro_skill_ids": [skill["micro_skill_id"] for position, skill in enumerate(skills) if position % 15 == i - 1], "steps": ["Interpret the prompt.", "Apply the declared mathematics rule.", "Check the result independently."], "review_status": "PROPOSED"} for i in range(1, 16)]
    families = [{"family_id": f"{course_id}_FAMILY_{i:03d}", "procedure_id": procedures[(i - 1) % 15]["procedure_id"], "answer_engine": "numeric_scalar" if i % 4 else "multiple_choice", "parameter_domains": {"variant": {"type": "integer", "minimum": 1, "maximum": 1000}}, "allocation_rules": {"target_variants": 20, "unique_parameter_sets": True}, "failure_signals": ["rule_selection_error", "algebra_error"]} for i in range(1, 16)]
    relationships = [{"relationship_id": f"{course_id}_PREREQ_{i:03d}", "relationship_type": "PREREQUISITE", "source_node_id": skills[i - 1]["micro_skill_id"], "target_node_id": skills[i]["micro_skill_id"]} for i in range(1, 50)]
    blueprints = [AssessmentBlueprintV1(blueprint_id=f"{course_id}_BLUEPRINT_{role}", course_node_id=course_id, question_count=count, topic_weights={topic["topic_id"]: 1 / 25 for topic in topics}, difficulty_distribution={"FOUNDATIONAL": .4, "DEVELOPING": .4, "ADVANCED": .2}, question_type_distribution={"numeric": .8, "multiple_choice": .2}, time_budget_minutes=minutes, unit_scope=tuple(unit["unit_id"] for unit in units), micro_skill_coverage=tuple(skill["micro_skill_id"] for skill in skills[:15]), prerequisite_coverage=tuple(rel["relationship_id"] for rel in relationships[:10]), reuse_policy={"allow_reuse": False}, variant_policy={"deterministic": True}, scoring_rules={"default_points": 1}, rubrics=(), review_status="PROPOSED").to_dict() for role, count, minutes in (("PRACTICE", 25, 45), ("SUMMATIVE", 40, 90))]
    return {"course_id": course_id, "units": units, "topics": topics, "micro_skills": skills, "procedures": procedures, "generation_families": families, "relationships": relationships, "difficulty_model": ["FOUNDATIONAL", "DEVELOPING", "ADVANCED"], "answer_engine_allocations": ["numeric_scalar", "multiple_choice"], "failure_signal_allocations": ["rule_selection_error", "algebra_error"], "assessment_blueprints": blueprints, "target_validated_question_count": 300}

def build_mathematics_reference_pack() -> dict[str, Any]:
    descriptor = SubjectPackDescriptorV1("MATHEMATICS_REFERENCE_PACK_V1", "MATHEMATICS", "1.0", ("numeric_scalar", "multiple_choice"), review_status="PROPOSED").to_dict()
    pack = {"pack_id": "MATHEMATICS_REFERENCE_PACK_V1", "version": "1.0", "noncanonical": True, "human_review_required": True, "canonical_authority": False, "source_evidence": [{"source": "EXISTING_COMPILER_MATERIALS", "use": "READ_ONLY_REFERENCE"}], "descriptor": descriptor, "courses": {course_id: _course(course_id, areas) for course_id, areas in COURSES.items()}}
    pack["deterministic_sha256"] = hashlib.sha256(json.dumps(pack, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return pack

def validate_mathematics_reference_pack(pack: dict[str, Any]) -> None:
    if pack.get("noncanonical") is not True or pack.get("human_review_required") is not True or pack.get("canonical_authority") is not False: raise ValueError("reference pack must remain noncanonical and review-required")
    if set(pack.get("courses", {})) != set(COURSES): raise ValueError("both mathematics courses are required")
    for course in pack["courses"].values():
        if len(course["units"]) < 8 or len(course["topics"]) < 25 or len(course["micro_skills"]) < 50 or len(course["procedures"]) < 15 or len(course["generation_families"]) < 15: raise ValueError("minimum course coverage is incomplete")
        unit_ids = {item["unit_id"] for item in course["units"]}; topic_ids = {item["topic_id"] for item in course["topics"]}; skill_ids = {item["micro_skill_id"] for item in course["micro_skills"]}; procedure_ids = {item["procedure_id"] for item in course["procedures"]}; family_ids = {item["family_id"] for item in course["generation_families"]}; relationship_ids={item["relationship_id"] for item in course["relationships"]}; blueprint_ids={item["blueprint_id"] for item in course["assessment_blueprints"]}
        if any(len(values) != expected for values, expected in ((unit_ids,len(course["units"])),(topic_ids,len(course["topics"])),(skill_ids,len(course["micro_skills"])),(procedure_ids,len(course["procedures"])),(family_ids,len(course["generation_families"])),(relationship_ids,len(course["relationships"])),(blueprint_ids,len(course["assessment_blueprints"])))): raise ValueError("identities must be unique")
        if any(topic["unit_id"] not in unit_ids for topic in course["topics"]) or any(skill["topic_id"] not in topic_ids for skill in course["micro_skills"]): raise ValueError("curriculum hierarchy is unresolved")
        if any(not procedure["micro_skill_ids"] or any(skill_id not in skill_ids for skill_id in procedure["micro_skill_ids"]) for procedure in course["procedures"]): raise ValueError("procedure resolution failed")
        if {skill_id for procedure in course["procedures"] for skill_id in procedure["micro_skill_ids"]} != skill_ids: raise ValueError("not all micro-skills resolve to procedures")
        if any(not isinstance(value,str) or not value.strip() for values in (course["difficulty_model"],course["answer_engine_allocations"],course["failure_signal_allocations"]) for value in values): raise ValueError("allocation identities must be meaningful")
        if any(len(values)!=len(set(values)) for values in (course["difficulty_model"],course["answer_engine_allocations"],course["failure_signal_allocations"])): raise ValueError("allocation identities must be unique")
        if any(family["procedure_id"] not in procedure_ids or family["answer_engine"] not in course["answer_engine_allocations"] or not family["failure_signals"] or any(not signal.strip() or signal not in course["failure_signal_allocations"] for signal in family["failure_signals"]) or not family["parameter_domains"] or not family["allocation_rules"] or family["allocation_rules"].get("target_variants",0)<=1 or any(domain.get("minimum") is not None and domain.get("maximum") is not None and domain["minimum"]>=domain["maximum"] for domain in family["parameter_domains"].values()) for family in course["generation_families"]): raise ValueError("generation family is incomplete")
        if any(rel["source_node_id"] not in skill_ids or rel["target_node_id"] not in skill_ids for rel in course["relationships"]): raise ValueError("prerequisite relationship is unresolved")
        if len(course["assessment_blueprints"]) != 2 or course["target_validated_question_count"] != 300: raise ValueError("assessment or target count is incomplete")
        if not course["difficulty_model"] or not course["answer_engine_allocations"] or not course["failure_signal_allocations"]: raise ValueError("declared allocation models are required")
        question_type_engines={"numeric":{"numeric_scalar","numeric_pair","numeric_vector"},"multiple_choice":{"multiple_choice"}}
        for blueprint_payload in course["assessment_blueprints"]:
            blueprint = AssessmentBlueprintV1.from_dict(blueprint_payload)
            if blueprint.course_node_id != course["course_id"] or blueprint.question_count < len(blueprint.micro_skill_coverage) or any(skill_id not in skill_ids for skill_id in blueprint.micro_skill_coverage): raise ValueError("assessment blueprint is not satisfiable")
            distributions=(blueprint.topic_weights,blueprint.difficulty_distribution,blueprint.question_type_distribution)
            if any(any(isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 for value in distribution.values()) or abs(sum(distribution.values())-1)>1e-9 for distribution in distributions): raise ValueError("blueprint distributions are invalid")
            if set(blueprint.topic_weights) != topic_ids or set(blueprint.difficulty_distribution)!=set(course["difficulty_model"]) or any(kind not in question_type_engines or not question_type_engines[kind].intersection(course["answer_engine_allocations"]) for kind in blueprint.question_type_distribution): raise ValueError("blueprint distribution keys are unresolved")
            if not blueprint.unit_scope or not blueprint.prerequisite_coverage or any(unit_id not in unit_ids for unit_id in blueprint.unit_scope) or any(rel_id not in relationship_ids for rel_id in blueprint.prerequisite_coverage): raise ValueError("blueprint scope is unresolved")
