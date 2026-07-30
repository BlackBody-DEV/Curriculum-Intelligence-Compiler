import copy
import hashlib
import json

import pytest

from tools.course_compiler_demo.subject_packs.mathematics import (
    build_mathematics_reference_pack,
    build_remaining_mathematics_catalog,
    validate_remaining_mathematics_catalog,
)
from tools.course_compiler_demo.subject_packs.mathematics.catalog import COURSE_SPECS


def test_exact_nine_courses_and_common_pack_gates():
    pack = build_remaining_mathematics_catalog()
    validate_remaining_mathematics_catalog(pack)
    assert set(pack["courses"]) == set(COURSE_SPECS)
    assert len(pack["courses"]) == 9
    for course in pack["courses"].values():
        assert course["domain"] == "STEM" and course["subject"] == "MATHEMATICS"
        assert len(course["units"]) >= 8 and len(course["topics"]) >= 25
        assert len(course["micro_skills"]) >= 50 and len(course["procedures"]) >= 15
        assert len(course["generation_families"]) >= 15 and len(course["assessment_blueprints"]) == 2
        assert course["target_production_count"] == 300
        assert course["noncanonical"] and course["human_review_required"]


def test_algebra_i_and_calculus_i_content_and_hash_are_unchanged():
    legacy = build_mathematics_reference_pack()
    assert set(legacy["courses"]) == {"ALGEBRA_I", "CALCULUS_I"}
    assert legacy["deterministic_sha256"] == "8110a572e3355ad51c3387a82cba41ec73b7cf93ef2c4299953e2fff37fdcc02"


def test_every_generation_family_has_complete_common_contract():
    required = {"micro_skill_id", "procedure_id", "parameter_domains", "difficulty_allocation", "answer_contract", "answer_engine", "failure_signals", "assessment_role", "duplicate_constraints"}
    for course in build_remaining_mathematics_catalog()["courses"].values():
        skills = {item["micro_skill_id"] for item in course["micro_skills"]}
        procedures = {item["procedure_id"] for item in course["procedures"]}
        for family in course["generation_families"]:
            assert required <= set(family)
            assert family["micro_skill_id"] in skills and family["procedure_id"] in procedures
            assert family["answer_contract"]["engine_type"] == family["answer_engine"]
            assert sum(family["difficulty_allocation"].values()) == pytest.approx(1)


def test_catalog_is_deterministic_and_mutation_safe():
    first, second = build_remaining_mathematics_catalog(), build_remaining_mathematics_catalog()
    assert json.dumps(first, sort_keys=True, separators=(",", ":")) == json.dumps(second, sort_keys=True, separators=(",", ":"))
    first["courses"]["PRE_ALGEBRA"]["units"][0]["title"] = "changed"
    assert second["courses"]["PRE_ALGEBRA"]["units"][0]["title"] != "changed"


@pytest.mark.parametrize("course_id", sorted(COURSE_SPECS))
def test_each_course_hierarchy_procedures_prerequisites_and_blueprints_resolve(course_id):
    course = build_remaining_mathematics_catalog()["courses"][course_id]
    units = {item["unit_id"] for item in course["units"]}
    topics = {item["topic_id"] for item in course["topics"]}
    skills = {item["micro_skill_id"] for item in course["micro_skills"]}
    relationships = {item["relationship_id"] for item in course["relationships"]}
    assert all(item["unit_id"] in units for item in course["topics"])
    assert all(item["topic_id"] in topics for item in course["micro_skills"])
    assert {skill for procedure in course["procedures"] for skill in procedure["micro_skill_ids"]} == skills
    assert all(set(item["prerequisite_coverage"]) <= relationships for item in course["assessment_blueprints"])


@pytest.mark.parametrize("mutation", [
    "canonical", "course_set", "identity", "hierarchy", "procedure", "skill_coverage",
    "prerequisite", "difficulty", "engine", "answer_contract", "family_skill", "parameters",
    "duplicates", "failure", "asset", "blueprints", "production", "topic_weights",
    "unit_scope", "blueprint_skills", "hash",
])
def test_malformed_catalogs_fail_closed(mutation):
    pack = build_remaining_mathematics_catalog()
    course = pack["courses"]["ALGEBRA_II"]
    family = course["generation_families"][0]
    blueprint = course["assessment_blueprints"][0]
    if mutation == "canonical": pack["canonical_authority"] = True
    elif mutation == "course_set": pack["courses"].pop("GEOMETRY")
    elif mutation == "identity": course["units"][1]["unit_id"] = course["units"][0]["unit_id"]
    elif mutation == "hierarchy": course["topics"][0]["unit_id"] = "MISSING"
    elif mutation == "procedure": course["procedures"][0]["steps"] = []
    elif mutation == "skill_coverage": course["procedures"][0]["micro_skill_ids"] = []
    elif mutation == "prerequisite": course["relationships"][0]["target_node_id"] = "MISSING"
    elif mutation == "difficulty": course["difficulty_model"] = ["UNKNOWN"]
    elif mutation == "engine": family["answer_engine"] = "UNKNOWN"
    elif mutation == "answer_contract": family["answer_contract"]["engine_type"] = "matrix"
    elif mutation == "family_skill": family["micro_skill_id"] = "MISSING"
    elif mutation == "parameters": family["parameter_domains"]["variant"]["maximum"] = 1
    elif mutation == "duplicates": family["duplicate_constraints"]["unique_parameter_sets"] = False
    elif mutation == "failure": family["failure_signals"] = ["UNKNOWN"]
    elif mutation == "asset": course["asset_policy"]["allowed_media_types"] = []
    elif mutation == "blueprints": course["assessment_blueprints"].pop()
    elif mutation == "production": course["target_production_count"] = 299
    elif mutation == "topic_weights": blueprint["topic_weights"] = {"MISSING": 1.0}
    elif mutation == "unit_scope": blueprint["unit_scope"] = ["MISSING"]
    elif mutation == "blueprint_skills": blueprint["micro_skill_coverage"] = ["MISSING"]
    else: pack["deterministic_sha256"] = "0" * 64
    with pytest.raises((ValueError, TypeError, KeyError)):
        validate_remaining_mathematics_catalog(pack)


def test_deep_copy_mutation_does_not_mask_hash_validation():
    pack = build_remaining_mathematics_catalog()
    altered = copy.deepcopy(pack)
    altered["courses"]["GEOMETRY"]["title"] = "Altered"
    with pytest.raises(ValueError, match="hash"):
        validate_remaining_mathematics_catalog(altered)


def _refresh_hash(pack):
    payload = {key: value for key, value in pack.items() if key != "deterministic_sha256"}
    pack["deterministic_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@pytest.mark.parametrize("mutation", ["wrong_procedure_skill", "unknown_course_prerequisite"])
def test_recomputed_hash_cannot_mask_cross_reference_failures(mutation):
    pack = build_remaining_mathematics_catalog()
    course = pack["courses"]["CALCULUS_III"]
    if mutation == "wrong_procedure_skill":
        family = course["generation_families"][0]
        family["micro_skill_id"] = course["procedures"][1]["micro_skill_ids"][0]
    else:
        course["prerequisite_courses"] = ["DOES_NOT_EXIST"]
    _refresh_hash(pack)
    with pytest.raises(ValueError):
        validate_remaining_mathematics_catalog(pack)
