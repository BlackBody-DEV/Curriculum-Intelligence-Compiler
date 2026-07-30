"""Deterministic Biology, Organic Chemistry, and Biochemistry packs."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping

from tools.course_compiler_demo.universal_core import AssessmentBlueprintV1, SubjectPackDescriptorV1


COURSES = {
    "BIOLOGY": {
        "title": "Biology", "subject": "LIFE_SCIENCES", "prerequisites": [],
        "areas": ("scientific inquiry", "chemistry of life", "cell structure", "cellular energetics", "cell division", "genetics", "gene expression", "evolution", "ecology", "organismal systems"),
        "engines": ("scientific_structured_response", "rubric_scored_explanation", "numeric_scalar", "multiple_choice"),
    },
    "ORGANIC_CHEMISTRY": {
        "title": "Organic Chemistry", "subject": "CHEMISTRY", "prerequisites": ["GENERAL_CHEMISTRY"],
        "areas": ("structure and bonding", "functional groups", "acid-base chemistry", "stereochemistry", "substitution", "elimination", "alkenes and alkynes", "spectroscopy", "carbonyl chemistry", "aromatic chemistry"),
        "engines": ("scientific_structured_response", "rubric_scored_explanation", "numeric_scalar", "multiple_choice", "chemical_formula", "chemical_reaction"),
    },
    "BIOCHEMISTRY": {
        "title": "Biochemistry", "subject": "LIFE_SCIENCES", "prerequisites": ["BIOLOGY", "ORGANIC_CHEMISTRY"],
        "areas": ("water and buffers", "amino acids", "protein structure", "enzyme kinetics", "carbohydrates", "lipids and membranes", "nucleic acids", "bioenergetics", "metabolism", "molecular information flow"),
        "engines": ("scientific_structured_response", "rubric_scored_explanation", "numeric_scalar", "multiple_choice", "chemical_formula", "chemical_reaction"),
    },
}

DIFFICULTIES = ("FOUNDATIONAL", "DEVELOPING", "ADVANCED")
FAILURES = ("concept_omission", "causal_sequence_error", "unit_error", "formula_error", "conservation_error", "unsupported_mechanism_claim")
UNSUPPORTED = ("molecular_drawing", "unrestricted_mechanism_grading", "freeform_essay_grading", "image_structure_interpretation")


def _course(course_id: str, spec: Mapping[str, Any]) -> dict[str, Any]:
    areas, engines = spec["areas"], spec["engines"]
    units = [{"unit_id": f"{course_id}_UNIT_{i:02d}", "title": areas[i - 1], "sequence": i} for i in range(1, 9)]
    topics = [{"topic_id": f"{course_id}_TOPIC_{i:03d}", "unit_id": units[(i - 1) % 8]["unit_id"], "title": f"{areas[(i - 1) % len(areas)]}: concept {i}"} for i in range(1, 26)]
    skills = [{"micro_skill_id": f"{course_id}_SKILL_{i:03d}", "topic_id": topics[(i - 1) % 25]["topic_id"], "title": f"Analyze {areas[(i - 1) % len(areas)]} evidence {i}"} for i in range(1, 51)]
    procedures = []
    for i in range(1, 16):
        procedures.append({"procedure_id": f"{course_id}_PROC_{i:03d}", "micro_skill_ids": [skill["micro_skill_id"] for position, skill in enumerate(skills) if position % 15 == i - 1], "steps": ["Identify the bounded evidence and requested quantity or concept.", "Apply the declared scientific relationship or conservation rule.", "Check units, contradictions, and biological or chemical plausibility."], "review_status": "PROPOSED"})
    families = []
    for i, procedure in enumerate(procedures, 1):
        engine = engines[(i - 1) % len(engines)]
        answer_contract = {"answer_contract_id": f"{course_id}_ANSWER_{i:03d}", "engine_type": engine, "normalization_required": True, "independent_derivation_required": True}
        if engine in {"scientific_structured_response", "rubric_scored_explanation"}:
            answer_contract["bounded_evidence_schema"] = {"required_concepts": [areas[(i - 1) % len(areas)]], "forbidden_contradictions": True, "minimum_evidence_count": 1}
        elif engine == "chemical_formula":
            answer_contract["formula_schema"] = {"element_counts_required": True, "charge_required_when_applicable": True}
        elif engine == "chemical_reaction":
            answer_contract["reaction_schema"] = {"atom_balance_required": True, "charge_balance_required": True, "declared_reaction_only": True}
        families.append({
            "family_id": f"{course_id}_FAMILY_{i:03d}", "micro_skill_id": procedure["micro_skill_ids"][0], "procedure_id": procedure["procedure_id"],
            "parameter_domains": {"variant": {"type": "integer", "minimum": 1, "maximum": 1000}, "evidence_count": {"type": "integer", "minimum": 1, "maximum": 6}},
            "difficulty_allocation": {"FOUNDATIONAL": .4, "DEVELOPING": .4, "ADVANCED": .2}, "answer_contract": answer_contract,
            "answer_engine": engine, "failure_signals": [FAILURES[(i - 1) % len(FAILURES)], "concept_omission"], "assessment_role": "PRACTICE" if i <= 8 else "SUMMATIVE",
            "duplicate_constraints": {"unique_parameter_sets": True, "semantic_fingerprint_required": True, "maximum_stem_similarity": .85},
            "allocation_rules": {"target_variants": 20, "unique_parameter_sets": True},
        })
    relationships = [{"relationship_id": f"{course_id}_PREREQ_{i:03d}", "relationship_type": "PREREQUISITE", "source_node_id": skills[i - 1]["micro_skill_id"], "target_node_id": skills[i]["micro_skill_id"]} for i in range(1, 50)]
    topic_weights = {topic["topic_id"]: 1 / 25 for topic in topics}
    blueprints = [AssessmentBlueprintV1(
        blueprint_id=f"{course_id}_BLUEPRINT_{role}", course_node_id=course_id, question_count=count,
        topic_weights=topic_weights, difficulty_distribution={"FOUNDATIONAL": .4, "DEVELOPING": .4, "ADVANCED": .2},
        question_type_distribution={"structured": .4, "numeric": .2, "multiple_choice": .4}, time_budget_minutes=minutes,
        unit_scope=tuple(unit["unit_id"] for unit in units), micro_skill_coverage=tuple(skill["micro_skill_id"] for skill in skills[:15]),
        prerequisite_coverage=tuple(rel["relationship_id"] for rel in relationships[:10]), reuse_policy={"allow_reuse": False},
        variant_policy={"deterministic": True}, scoring_rules={"default_points": 1}, rubrics=(), review_status="PROPOSED",
    ).to_dict() for role, count, minutes in (("PRACTICE", 25, 50), ("SUMMATIVE", 40, 100))]
    return {
        "course_id": course_id, "title": spec["title"], "domain": "STEM", "subject": spec["subject"], "prerequisite_courses": list(spec["prerequisites"]),
        "units": units, "topics": topics, "micro_skills": skills, "procedures": procedures, "generation_families": families, "relationships": relationships,
        "difficulty_model": list(DIFFICULTIES), "answer_engine_allocations": list(engines), "failure_signal_allocations": list(FAILURES),
        "asset_policy": {"required": False, "allowed_media_types": ["image/svg+xml", "application/json"], "rights_evidence_required": True, "molecular_drawing_grading": False, "image_interpretation": False},
        "supported_response_modes": ["structured_concepts", "declared_relationships", "bounded_rubric", "numeric", "multiple_choice"] + (["machine_readable_formula", "declared_reaction"] if "chemical_formula" in engines else []),
        "unsupported_capabilities": list(UNSUPPORTED), "assessment_blueprints": blueprints, "target_production_count": 300,
        "noncanonical": True, "human_review_required": True, "canonical_authority": False,
    }


def build_life_chemistry_catalog() -> dict[str, Any]:
    engines = tuple(sorted({engine for spec in COURSES.values() for engine in spec["engines"]}))
    descriptor = SubjectPackDescriptorV1("LIFE_CHEMISTRY_CATALOG_V1", "LIFE_SCIENCES_AND_CHEMISTRY", "1.0", engines, review_status="PROPOSED").to_dict()
    pack = {"pack_id": "LIFE_CHEMISTRY_CATALOG_V1", "version": "1.0", "noncanonical": True, "human_review_required": True, "canonical_authority": False, "unsupported_capabilities": list(UNSUPPORTED), "descriptor": descriptor, "courses": {course_id: _course(course_id, spec) for course_id, spec in COURSES.items()}}
    pack["deterministic_sha256"] = hashlib.sha256(json.dumps(pack, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return pack


def _distribution(values: Mapping[str, Any], expected: set[str]) -> bool:
    return set(values) == expected and all(not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0 for value in values.values()) and abs(sum(values.values()) - 1) <= 1e-9


def validate_life_chemistry_catalog(pack: dict[str, Any]) -> None:
    if not isinstance(pack, dict) or pack.get("noncanonical") is not True or pack.get("human_review_required") is not True or pack.get("canonical_authority") is not False or tuple(pack.get("unsupported_capabilities", ())) != UNSUPPORTED:
        raise ValueError("catalog authority or unsupported-capability boundary is invalid")
    if set(pack.get("courses", {})) != set(COURSES): raise ValueError("exactly three requested courses are required")
    for course_id, course in pack["courses"].items():
        spec = COURSES[course_id]
        if course.get("course_id") != course_id or course.get("domain") != "STEM" or course.get("subject") != spec["subject"] or course.get("noncanonical") is not True or course.get("human_review_required") is not True or course.get("canonical_authority") is not False:
            raise ValueError("course identity or authority boundary is invalid")
        if course.get("prerequisite_courses") != spec["prerequisites"] or any(item not in set(COURSES) | {"GENERAL_CHEMISTRY"} for item in course["prerequisite_courses"]): raise ValueError("course prerequisites are unresolved")
        if tuple(course.get("unsupported_capabilities", ())) != UNSUPPORTED or course.get("asset_policy", {}).get("molecular_drawing_grading") is not False or course.get("asset_policy", {}).get("image_interpretation") is not False: raise ValueError("unsupported grading boundary is invalid")
        expected_modes = ["structured_concepts", "declared_relationships", "bounded_rubric", "numeric", "multiple_choice"] + (["machine_readable_formula", "declared_reaction"] if "chemical_formula" in spec["engines"] else [])
        if course.get("supported_response_modes") != expected_modes: raise ValueError("supported response modes overclaim allocated capabilities")
        if len(course.get("units", [])) < 8 or len(course.get("topics", [])) < 25 or len(course.get("micro_skills", [])) < 50 or len(course.get("procedures", [])) < 15 or len(course.get("generation_families", [])) < 15: raise ValueError("course coverage is incomplete")
        fields = (("units", "unit_id"), ("topics", "topic_id"), ("micro_skills", "micro_skill_id"), ("procedures", "procedure_id"), ("generation_families", "family_id"), ("relationships", "relationship_id"), ("assessment_blueprints", "blueprint_id"))
        ids: dict[str, set[str]] = {}
        for name, identity in fields:
            values = [item.get(identity) for item in course.get(name, [])]
            if any(not isinstance(value, str) or not value for value in values) or len(values) != len(set(values)): raise ValueError(f"{name} identities are invalid")
            ids[name] = set(values)
        if any(item["unit_id"] not in ids["units"] for item in course["topics"]) or any(item["topic_id"] not in ids["topics"] for item in course["micro_skills"]): raise ValueError("course hierarchy is unresolved")
        procedure_skills = {item["procedure_id"]: set(item["micro_skill_ids"]) for item in course["procedures"]}
        if any(not item.get("steps") or not procedure_skills[item["procedure_id"]] or not procedure_skills[item["procedure_id"]] <= ids["micro_skills"] for item in course["procedures"]) or set().union(*procedure_skills.values()) != ids["micro_skills"]: raise ValueError("procedure coverage is unresolved")
        if any(item.get("relationship_type") != "PREREQUISITE" or item.get("source_node_id") not in ids["micro_skills"] or item.get("target_node_id") not in ids["micro_skills"] for item in course["relationships"]): raise ValueError("prerequisite relationship is unresolved")
        if set(course.get("difficulty_model", ())) != set(DIFFICULTIES) or set(course.get("answer_engine_allocations", ())) != set(spec["engines"]) or set(course.get("failure_signal_allocations", ())) != set(FAILURES): raise ValueError("allocation model is invalid")
        if course.get("asset_policy", {}).get("rights_evidence_required") is not True or not course["asset_policy"].get("allowed_media_types"): raise ValueError("asset policy is incomplete")
        for family in course["generation_families"]:
            required = {"micro_skill_id", "procedure_id", "parameter_domains", "difficulty_allocation", "answer_contract", "answer_engine", "failure_signals", "assessment_role", "duplicate_constraints"}
            if not required <= set(family) or family["procedure_id"] not in procedure_skills or family["micro_skill_id"] not in procedure_skills[family["procedure_id"]]: raise ValueError("family references are unresolved")
            if family["answer_engine"] not in spec["engines"] or family["answer_contract"].get("engine_type") != family["answer_engine"] or not family["answer_contract"].get("answer_contract_id"): raise ValueError("family answer contract is invalid")
            if not _distribution(family["difficulty_allocation"], set(DIFFICULTIES)) or family["assessment_role"] not in {"PRACTICE", "SUMMATIVE"}: raise ValueError("family allocation is invalid")
            if not family["parameter_domains"] or any(domain.get("minimum") >= domain.get("maximum") for domain in family["parameter_domains"].values()) or not family["duplicate_constraints"].get("unique_parameter_sets"): raise ValueError("family parameter or duplicate constraints are invalid")
            if not family["failure_signals"] or any(signal not in FAILURES for signal in family["failure_signals"]): raise ValueError("family failure signals are unresolved")
            if family["answer_engine"] in {"scientific_structured_response", "rubric_scored_explanation"} and "bounded_evidence_schema" not in family["answer_contract"]: raise ValueError("structured response must remain bounded")
            if family["answer_engine"] == "chemical_formula" and family["answer_contract"].get("formula_schema", {}).get("element_counts_required") is not True: raise ValueError("formula grading must remain machine-readable")
            if family["answer_engine"] == "chemical_reaction" and family["answer_contract"].get("reaction_schema", {}).get("declared_reaction_only") is not True: raise ValueError("reaction grading must remain declared and bounded")
        if len(course.get("assessment_blueprints", [])) != 2 or course.get("target_production_count") != 300: raise ValueError("assessment or target count is incomplete")
        for payload in course["assessment_blueprints"]:
            blueprint = AssessmentBlueprintV1.from_dict(payload)
            if blueprint.course_node_id != course_id or not _distribution(blueprint.topic_weights, ids["topics"]) or not _distribution(blueprint.difficulty_distribution, set(DIFFICULTIES)) or not _distribution(blueprint.question_type_distribution, {"structured", "numeric", "multiple_choice"}): raise ValueError("blueprint distribution is invalid")
            if not blueprint.unit_scope or any(item not in ids["units"] for item in blueprint.unit_scope) or not blueprint.prerequisite_coverage or any(item not in ids["relationships"] for item in blueprint.prerequisite_coverage) or any(item not in ids["micro_skills"] for item in blueprint.micro_skill_coverage) or blueprint.question_count < len(blueprint.micro_skill_coverage): raise ValueError("blueprint scope is unresolved")
    material = {key: value for key, value in pack.items() if key != "deterministic_sha256"}
    if pack.get("deterministic_sha256") != hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest(): raise ValueError("catalog integrity hash is invalid")
