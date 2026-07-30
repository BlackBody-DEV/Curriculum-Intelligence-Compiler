"""Noncanonical catalog packs for the remaining mathematics curriculum."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any, Mapping

from tools.course_compiler_demo.universal_core import AssessmentBlueprintV1, SubjectPackDescriptorV1


COURSE_SPECS = {
    "PRE_ALGEBRA": ("Pre-Algebra", ("whole-number reasoning", "integer operations", "fractions and decimals", "ratios and rates", "proportions", "percent", "expressions", "equations and inequalities", "geometry and measurement", "data and probability"), ()),
    "ALGEBRA_II": ("Algebra II", ("equations and inequalities", "functions", "quadratic functions", "polynomial functions", "rational functions", "radical functions", "exponential functions", "logarithmic functions", "sequences and series", "probability and statistics"), ("ALGEBRA_I",)),
    "GEOMETRY": ("Geometry", ("foundations and constructions", "transformations", "congruence", "similarity", "triangle relationships", "polygons", "circles", "coordinate geometry", "area and volume", "geometric probability"), ("ALGEBRA_I",)),
    "TRIGONOMETRY": ("Trigonometry", ("angle measure", "right-triangle trigonometry", "unit circle", "trigonometric functions", "graphs and transformations", "identities", "equations", "inverse functions", "laws of sines and cosines", "vectors and polar form"), ("ALGEBRA_II", "GEOMETRY")),
    "PRE_CALCULUS": ("Pre-Calculus", ("function analysis", "polynomial and rational models", "exponential and logarithmic models", "trigonometric models", "analytic trigonometry", "systems and matrices", "conic sections", "parametric equations", "polar coordinates", "sequences and limits"), ("ALGEBRA_II", "TRIGONOMETRY")),
    "CALCULUS_II": ("Calculus II", ("integration techniques", "improper integrals", "applications of integration", "differential equations models", "parametric curves", "polar curves", "sequences", "infinite series", "power series", "Taylor series"), ("CALCULUS_I",)),
    "CALCULUS_III": ("Calculus III", ("vectors and geometry of space", "vector-valued functions", "partial derivatives", "multiple integrals", "cylindrical and spherical coordinates", "vector fields", "line integrals", "surface integrals", "Green's theorem", "Stokes and divergence theorems"), ("CALCULUS_II",)),
    "DIFFERENTIAL_EQUATIONS": ("Differential Equations", ("first-order equations", "qualitative methods", "existence and uniqueness", "second-order linear equations", "higher-order equations", "Laplace transforms", "linear systems", "phase-plane analysis", "series solutions", "numerical approximations"), ("CALCULUS_II", "LINEAR_ALGEBRA")),
    "LINEAR_ALGEBRA": ("Linear Algebra", ("linear systems", "matrix algebra", "vector equations", "linear transformations", "subspaces", "basis and dimension", "determinants", "eigenvalues and eigenvectors", "orthogonality", "diagonalization and applications"), ("ALGEBRA_II",)),
}

ENGINES = ("numeric_scalar", "multiple_choice", "symbolic_expression", "equation_system", "coordinate_graph", "matrix")
FAILURES = ("representation_error", "procedure_selection_error", "algebra_error", "domain_restriction_error", "verification_error")
DIFFICULTIES = ("FOUNDATIONAL", "DEVELOPING", "ADVANCED")


def _slug(text: str) -> str:
    return "_".join(text.lower().replace("'", "").replace("-", " ").split())


def _engine(course_id: str, index: int) -> str:
    if course_id == "LINEAR_ALGEBRA" and index % 3 == 0:
        return "matrix"
    if course_id in {"GEOMETRY", "TRIGONOMETRY", "PRE_CALCULUS", "CALCULUS_III", "DIFFERENTIAL_EQUATIONS"} and index % 5 == 0:
        return "coordinate_graph"
    if index % 4 == 0:
        return "symbolic_expression"
    if index % 6 == 0:
        return "equation_system"
    return "multiple_choice" if index % 3 == 0 else "numeric_scalar"


def _course(course_id: str, title: str, areas: tuple[str, ...], prerequisites: tuple[str, ...]) -> dict[str, Any]:
    units = [{"unit_id": f"{course_id}_UNIT_{i:02d}", "title": area, "sequence": i} for i, area in enumerate(areas[:8], 1)]
    topics = [{"topic_id": f"{course_id}_TOPIC_{i:03d}", "unit_id": units[(i - 1) % 8]["unit_id"], "title": f"{areas[(i - 1) % len(areas)]}: concept {i}"} for i in range(1, 26)]
    skills = [{"micro_skill_id": f"{course_id}_SKILL_{i:03d}", "topic_id": topics[(i - 1) % 25]["topic_id"], "title": f"Analyze {_slug(areas[(i - 1) % len(areas)])} case {i}"} for i in range(1, 51)]
    procedures = []
    for i in range(1, 16):
        assigned = [skill["micro_skill_id"] for position, skill in enumerate(skills) if position % 15 == i - 1]
        procedures.append({"procedure_id": f"{course_id}_PROC_{i:03d}", "title": f"Solve and verify {areas[(i - 1) % len(areas)]}", "micro_skill_ids": assigned, "steps": ["Identify givens, unknowns, and restrictions.", "Select and apply the declared mathematical representation.", "Independently verify the result and its domain."], "review_status": "PROPOSED"})
    families = []
    for i, procedure in enumerate(procedures, 1):
        engine = _engine(course_id, i)
        skill_id = procedure["micro_skill_ids"][0]
        families.append({
            "family_id": f"{course_id}_FAMILY_{i:03d}", "micro_skill_id": skill_id,
            "procedure_id": procedure["procedure_id"],
            "parameter_domains": {"variant": {"type": "integer", "minimum": 1, "maximum": 1000}, "coefficient_scale": {"type": "integer", "minimum": 1, "maximum": 12}},
            "difficulty_allocation": {"FOUNDATIONAL": .4, "DEVELOPING": .4, "ADVANCED": .2},
            "answer_contract": {"answer_contract_id": f"{course_id}_ANSWER_{i:03d}", "engine_type": engine, "normalization_required": True, "independent_derivation_required": True},
            "answer_engine": engine, "failure_signals": [FAILURES[(i - 1) % len(FAILURES)], "verification_error"],
            "assessment_role": "PRACTICE" if i <= 8 else "SUMMATIVE",
            "duplicate_constraints": {"unique_parameter_sets": True, "semantic_fingerprint_required": True, "maximum_stem_similarity": .85},
            "allocation_rules": {"target_variants": 20, "unique_parameter_sets": True},
        })
    relationships = [{"relationship_id": f"{course_id}_PREREQ_{i:03d}", "relationship_type": "PREREQUISITE", "source_node_id": skills[i - 1]["micro_skill_id"], "target_node_id": skills[i]["micro_skill_id"]} for i in range(1, 50)]
    weights = {topic["topic_id"]: 1 / 25 for topic in topics}
    blueprints = [AssessmentBlueprintV1(
        blueprint_id=f"{course_id}_BLUEPRINT_{role}", course_node_id=course_id,
        question_count=count, topic_weights=weights,
        difficulty_distribution={"FOUNDATIONAL": .4, "DEVELOPING": .4, "ADVANCED": .2},
        question_type_distribution={"numeric": .5, "multiple_choice": .2, "structured_mathematics": .3},
        time_budget_minutes=minutes, unit_scope=tuple(unit["unit_id"] for unit in units),
        micro_skill_coverage=tuple(skill["micro_skill_id"] for skill in skills[:15]),
        prerequisite_coverage=tuple(rel["relationship_id"] for rel in relationships[:10]),
        reuse_policy={"allow_reuse": False}, variant_policy={"deterministic": True, "unique_parameters": True},
        scoring_rules={"default_points": 1}, rubrics=(), review_status="PROPOSED",
    ).to_dict() for role, count, minutes in (("PRACTICE", 25, 45), ("SUMMATIVE", 40, 90))]
    return {
        "course_id": course_id, "title": title, "domain": "STEM", "subject": "MATHEMATICS",
        "prerequisite_courses": list(prerequisites), "units": units, "topics": topics, "micro_skills": skills,
        "procedures": procedures, "generation_families": families, "relationships": relationships,
        "difficulty_model": list(DIFFICULTIES), "answer_engine_allocations": list(ENGINES),
        "failure_signal_allocations": list(FAILURES),
        "asset_policy": {"required": False, "allowed_media_types": ["image/svg+xml", "application/json"], "rights_evidence_required": True, "machine_readable_only": True},
        "assessment_blueprints": blueprints, "target_production_count": 300,
        "noncanonical": True, "human_review_required": True,
    }


def build_remaining_mathematics_catalog() -> dict[str, Any]:
    descriptor = SubjectPackDescriptorV1("MATHEMATICS_REMAINING_CATALOG_V1", "MATHEMATICS", "1.0", ENGINES, review_status="PROPOSED").to_dict()
    pack = {"pack_id": "MATHEMATICS_REMAINING_CATALOG_V1", "version": "1.0", "domain": "STEM", "subject": "MATHEMATICS", "noncanonical": True, "human_review_required": True, "canonical_authority": False, "descriptor": descriptor, "courses": {key: _course(key, *spec) for key, spec in COURSE_SPECS.items()}}
    pack["deterministic_sha256"] = hashlib.sha256(json.dumps(pack, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return pack


def _distribution(values: Mapping[str, Any], keys: set[str]) -> bool:
    return set(values) == keys and all(not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0 for value in values.values()) and abs(sum(values.values()) - 1) <= 1e-9


def validate_remaining_mathematics_catalog(pack: dict[str, Any]) -> None:
    if not isinstance(pack, dict) or pack.get("noncanonical") is not True or pack.get("human_review_required") is not True or pack.get("canonical_authority") is not False:
        raise ValueError("catalog must remain noncanonical and human-review-required")
    if set(pack.get("courses", {})) != set(COURSE_SPECS):
        raise ValueError("exactly nine remaining mathematics courses are required")
    for course_id, course in pack["courses"].items():
        if course.get("course_id") != course_id or course.get("domain") != "STEM" or course.get("subject") != "MATHEMATICS" or not course.get("title"):
            raise ValueError("course identity, domain, and subject are required")
        if course.get("noncanonical") is not True or course.get("human_review_required") is not True:
            raise ValueError("course authority boundary is invalid")
        if len(course.get("units", [])) < 8 or len(course.get("topics", [])) < 25 or len(course.get("micro_skills", [])) < 50 or len(course.get("procedures", [])) < 15 or len(course.get("generation_families", [])) < 15:
            raise ValueError("minimum course coverage is incomplete")
        collections = (("unit_id", "units"), ("topic_id", "topics"), ("micro_skill_id", "micro_skills"), ("procedure_id", "procedures"), ("family_id", "generation_families"), ("relationship_id", "relationships"), ("blueprint_id", "assessment_blueprints"))
        identities = {}
        for identity, name in collections:
            values = [item.get(identity) for item in course.get(name, [])]
            if any(not isinstance(value, str) or not value for value in values) or len(values) != len(set(values)):
                raise ValueError(f"{name} identities must be unique and meaningful")
            identities[name] = set(values)
        if any(topic.get("unit_id") not in identities["units"] for topic in course["topics"]) or any(skill.get("topic_id") not in identities["topics"] for skill in course["micro_skills"]):
            raise ValueError("curriculum hierarchy is unresolved")
        if any(not procedure.get("steps") or not procedure.get("micro_skill_ids") or any(skill not in identities["micro_skills"] for skill in procedure["micro_skill_ids"]) for procedure in course["procedures"]):
            raise ValueError("procedures are incomplete")
        if {skill for procedure in course["procedures"] for skill in procedure["micro_skill_ids"]} != identities["micro_skills"]:
            raise ValueError("every micro-skill must resolve to a procedure")
        declared_prerequisites = set(COURSE_SPECS[course_id][2])
        if set(course.get("prerequisite_courses", [])) != declared_prerequisites:
            raise ValueError("course prerequisite references are unresolved")
        if any(value not in set(COURSE_SPECS) | {"ALGEBRA_I", "CALCULUS_I"} for value in declared_prerequisites):
            raise ValueError("course prerequisite target is unknown")
        if any(rel.get("source_node_id") not in identities["micro_skills"] or rel.get("target_node_id") not in identities["micro_skills"] or rel.get("relationship_type") != "PREREQUISITE" for rel in course["relationships"]):
            raise ValueError("prerequisite relationship is unresolved")
        if set(course.get("difficulty_model", [])) != set(DIFFICULTIES) or set(course.get("answer_engine_allocations", [])) != set(ENGINES) or set(course.get("failure_signal_allocations", [])) != set(FAILURES):
            raise ValueError("allocation model is incomplete")
        asset = course.get("asset_policy")
        if not isinstance(asset, dict) or asset.get("rights_evidence_required") is not True or not asset.get("allowed_media_types"):
            raise ValueError("asset policy is incomplete")
        procedure_skills = {procedure["procedure_id"]: set(procedure["micro_skill_ids"]) for procedure in course["procedures"]}
        for family in course["generation_families"]:
            required = {"micro_skill_id", "procedure_id", "parameter_domains", "difficulty_allocation", "answer_contract", "answer_engine", "failure_signals", "assessment_role", "duplicate_constraints"}
            if not required <= set(family) or family["micro_skill_id"] not in identities["micro_skills"] or family["procedure_id"] not in identities["procedures"]:
                raise ValueError("generation family references are incomplete")
            if family["micro_skill_id"] not in procedure_skills[family["procedure_id"]]:
                raise ValueError("generation family micro-skill does not belong to its procedure")
            if family["answer_engine"] not in course["answer_engine_allocations"] or family["answer_contract"].get("engine_type") != family["answer_engine"] or not family["answer_contract"].get("answer_contract_id"):
                raise ValueError("answer contract is unresolved")
            if not _distribution(family["difficulty_allocation"], set(DIFFICULTIES)) or family["assessment_role"] not in {"PRACTICE", "SUMMATIVE"}:
                raise ValueError("family allocation is invalid")
            if not family["parameter_domains"] or any(spec.get("minimum") >= spec.get("maximum") for spec in family["parameter_domains"].values()) or not family["duplicate_constraints"].get("unique_parameter_sets"):
                raise ValueError("parameter or duplicate constraints are invalid")
            if not family["failure_signals"] or any(signal not in course["failure_signal_allocations"] for signal in family["failure_signals"]):
                raise ValueError("failure-signal allocation is unresolved")
        if len(course.get("assessment_blueprints", [])) != 2 or course.get("target_production_count") != 300:
            raise ValueError("assessment or production target is incomplete")
        for payload in course["assessment_blueprints"]:
            blueprint = AssessmentBlueprintV1.from_dict(payload)
            if blueprint.course_node_id != course_id or not _distribution(blueprint.topic_weights, identities["topics"]) or not _distribution(blueprint.difficulty_distribution, set(DIFFICULTIES)):
                raise ValueError("blueprint distributions are unresolved")
            if not blueprint.unit_scope or any(value not in identities["units"] for value in blueprint.unit_scope) or not blueprint.prerequisite_coverage or any(value not in identities["relationships"] for value in blueprint.prerequisite_coverage):
                raise ValueError("blueprint scope is unresolved")
            if any(value not in identities["micro_skills"] for value in blueprint.micro_skill_coverage) or blueprint.question_count < len(blueprint.micro_skill_coverage):
                raise ValueError("blueprint coverage is unsatisfiable")
    expected_hash = hashlib.sha256(json.dumps({key: value for key, value in pack.items() if key != "deterministic_sha256"}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if pack.get("deterministic_sha256") != expected_hash:
        raise ValueError("catalog integrity hash is invalid")


def clone_catalog(pack: dict[str, Any]) -> dict[str, Any]:
    """Return a mutation-safe deep copy for validators and consumers."""
    return copy.deepcopy(pack)
