import copy
import hashlib
import json

import pytest

from tools.course_compiler_demo.subject_packs.chemistry import build_general_chemistry_pack
from tools.course_compiler_demo.subject_packs.life_sciences import build_life_chemistry_catalog, validate_life_chemistry_catalog
from tools.course_compiler_demo.subject_packs.life_sciences.catalog import COURSES, UNSUPPORTED


def test_exact_three_requested_courses_pass_all_common_gates():
    pack = build_life_chemistry_catalog(); validate_life_chemistry_catalog(pack)
    assert set(pack["courses"]) == {"BIOLOGY", "ORGANIC_CHEMISTRY", "BIOCHEMISTRY"}
    for course in pack["courses"].values():
        assert len(course["units"]) >= 8 and len(course["topics"]) >= 25 and len(course["micro_skills"]) >= 50
        assert len(course["procedures"]) >= 15 and len(course["generation_families"]) >= 15
        assert len(course["assessment_blueprints"]) == 2 and course["target_production_count"] == 300
        assert course["noncanonical"] and course["human_review_required"] and not course["canonical_authority"]


def test_general_chemistry_content_and_evidence_hash_are_preserved():
    pack = build_general_chemistry_pack()
    assert pack["course"]["course_id"] == "GENERAL_CHEMISTRY"
    assert pack["deterministic_sha256"] == "8f93a3d83e73d255a510a515dc9025c9b8107e958b274bdc8c627742c6d76d7e"


def test_no_molecular_drawing_image_interpretation_or_unrestricted_mechanism_claims():
    pack = build_life_chemistry_catalog()
    assert tuple(pack["unsupported_capabilities"]) == UNSUPPORTED
    for course in pack["courses"].values():
        assert tuple(course["unsupported_capabilities"]) == UNSUPPORTED
        assert course["asset_policy"]["molecular_drawing_grading"] is False
        assert course["asset_policy"]["image_interpretation"] is False
        assert "molecular_drawing" not in course["supported_response_modes"]
        for family in course["generation_families"]:
            if family["answer_engine"] == "chemical_reaction":
                assert family["answer_contract"]["reaction_schema"]["declared_reaction_only"] is True


def test_required_answer_engine_allocations_are_used_as_applicable():
    pack = build_life_chemistry_catalog()
    biology = set(pack["courses"]["BIOLOGY"]["answer_engine_allocations"])
    chemistry = set(pack["courses"]["ORGANIC_CHEMISTRY"]["answer_engine_allocations"])
    assert biology == {"scientific_structured_response", "rubric_scored_explanation", "numeric_scalar", "multiple_choice"}
    assert {"chemical_formula", "chemical_reaction"} <= chemistry
    for course in pack["courses"].values():
        assert set(course["answer_engine_allocations"]) == {family["answer_engine"] for family in course["generation_families"]}


@pytest.mark.parametrize("course_id", sorted(COURSES))
def test_hierarchy_procedures_families_prerequisites_and_blueprints_resolve(course_id):
    course = build_life_chemistry_catalog()["courses"][course_id]
    units = {item["unit_id"] for item in course["units"]}; topics = {item["topic_id"] for item in course["topics"]}; skills = {item["micro_skill_id"] for item in course["micro_skills"]}
    procedures = {item["procedure_id"]: set(item["micro_skill_ids"]) for item in course["procedures"]}; relationships = {item["relationship_id"] for item in course["relationships"]}
    assert all(item["unit_id"] in units for item in course["topics"])
    assert all(item["topic_id"] in topics for item in course["micro_skills"])
    assert set().union(*procedures.values()) == skills
    assert all(family["micro_skill_id"] in procedures[family["procedure_id"]] for family in course["generation_families"])
    assert all(set(blueprint["prerequisite_coverage"]) <= relationships for blueprint in course["assessment_blueprints"])


def test_catalog_serialization_and_hash_are_deterministic():
    first, second = build_life_chemistry_catalog(), build_life_chemistry_catalog()
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(second, sort_keys=True, separators=(",", ":"))
    assert first["deterministic_sha256"] == second["deterministic_sha256"]


def _rehash(pack):
    material = {key: value for key, value in pack.items() if key != "deterministic_sha256"}
    pack["deterministic_sha256"] = hashlib.sha256(json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@pytest.mark.parametrize("mutation", [
    "canonical", "unsupported", "course_set", "course_identity", "course_prerequisite", "drawing_claim", "coverage", "duplicate_id",
    "hierarchy", "procedure", "procedure_coverage", "relationship", "difficulty", "engine_allocation", "asset", "family_procedure",
    "family_skill", "answer_engine", "answer_contract", "structured_unbounded", "formula_unbounded", "reaction_unbounded", "response_overclaim", "difficulty_distribution",
    "parameters", "duplicates", "failure", "assessment_role", "blueprints", "target", "topic_weights", "unit_scope", "blueprint_skill", "hash",
])
def test_invalid_or_overclaiming_catalogs_fail_closed(mutation):
    pack = build_life_chemistry_catalog(); course = pack["courses"]["ORGANIC_CHEMISTRY"]; family = course["generation_families"][0]; blueprint = course["assessment_blueprints"][0]
    if mutation == "canonical": pack["canonical_authority"] = True
    elif mutation == "unsupported": pack["unsupported_capabilities"] = []
    elif mutation == "course_set": pack["courses"].pop("BIOLOGY")
    elif mutation == "course_identity": course["subject"] = "UNKNOWN"
    elif mutation == "course_prerequisite": course["prerequisite_courses"] = ["UNKNOWN"]
    elif mutation == "drawing_claim": course["asset_policy"]["molecular_drawing_grading"] = True
    elif mutation == "coverage": course["units"] = []
    elif mutation == "duplicate_id": course["topics"][1]["topic_id"] = course["topics"][0]["topic_id"]
    elif mutation == "hierarchy": course["topics"][0]["unit_id"] = "MISSING"
    elif mutation == "procedure": course["procedures"][0]["steps"] = []
    elif mutation == "procedure_coverage": course["procedures"][0]["micro_skill_ids"] = []
    elif mutation == "relationship": course["relationships"][0]["target_node_id"] = "MISSING"
    elif mutation == "difficulty": course["difficulty_model"] = ["UNKNOWN"]
    elif mutation == "engine_allocation": course["answer_engine_allocations"] = ["multiple_choice"]
    elif mutation == "asset": course["asset_policy"]["allowed_media_types"] = []
    elif mutation == "family_procedure": family["procedure_id"] = "MISSING"
    elif mutation == "family_skill": family["micro_skill_id"] = course["procedures"][1]["micro_skill_ids"][0]
    elif mutation == "answer_engine": family["answer_engine"] = "UNKNOWN"
    elif mutation == "answer_contract": family["answer_contract"]["engine_type"] = "numeric_scalar"
    elif mutation == "structured_unbounded": family["answer_contract"].pop("bounded_evidence_schema")
    elif mutation == "formula_unbounded":
        target = next(item for item in course["generation_families"] if item["answer_engine"] == "chemical_formula"); target["answer_contract"].pop("formula_schema")
    elif mutation == "reaction_unbounded":
        target = next(item for item in course["generation_families"] if item["answer_engine"] == "chemical_reaction"); target["answer_contract"]["reaction_schema"]["declared_reaction_only"] = False
    elif mutation == "response_overclaim": course["supported_response_modes"].append("molecular_drawing")
    elif mutation == "difficulty_distribution": family["difficulty_allocation"] = {"FOUNDATIONAL": 1.1, "DEVELOPING": -.1, "ADVANCED": 0}
    elif mutation == "parameters": family["parameter_domains"]["variant"]["maximum"] = 1
    elif mutation == "duplicates": family["duplicate_constraints"]["unique_parameter_sets"] = False
    elif mutation == "failure": family["failure_signals"] = ["UNKNOWN"]
    elif mutation == "assessment_role": family["assessment_role"] = "UNKNOWN"
    elif mutation == "blueprints": course["assessment_blueprints"].pop()
    elif mutation == "target": course["target_production_count"] = 299
    elif mutation == "topic_weights": blueprint["topic_weights"] = {"MISSING": 1.0}
    elif mutation == "unit_scope": blueprint["unit_scope"] = ["MISSING"]
    elif mutation == "blueprint_skill": blueprint["micro_skill_coverage"] = ["MISSING"]
    else: pack["deterministic_sha256"] = "0" * 64
    if mutation != "hash": _rehash(pack)
    with pytest.raises((ValueError, TypeError, KeyError)):
        validate_life_chemistry_catalog(pack)


def test_deep_copy_drift_is_detected_by_integrity_hash():
    altered = copy.deepcopy(build_life_chemistry_catalog()); altered["courses"]["BIOLOGY"]["title"] = "Changed"
    with pytest.raises(ValueError, match="hash"):
        validate_life_chemistry_catalog(altered)
