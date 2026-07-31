"""Deterministic, noncanonical six-course source-corpus synthesis proof."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, is_dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.course_compiler_demo.source_corpus.alignment import (
    RegisteredIdentity,
    SourceAlignmentCandidate,
    align_all,
)
from tools.course_compiler_demo.source_corpus.assessment_blueprints import (
    BlueprintType,
    compile_assessment_blueprints,
)
from tools.course_compiler_demo.source_corpus.contracts import (
    SourceCorpusV1,
    SourceDocumentV1,
    SourceLocationV1,
    SourceRightsClassificationV1,
    SourceSegmentV1,
    SourceType,
)
from tools.course_compiler_demo.source_corpus.extraction import extract_curriculum_candidates
from tools.course_compiler_demo.source_corpus.generation_requirements import (
    build_generation_manifest,
    compile_generation_requirements,
    generation_readiness,
)
from tools.course_compiler_demo.source_corpus.quality import audit_review_package
from tools.course_compiler_demo.source_corpus.synthesis import SynthesisCandidate, synthesize
from tools.course_compiler_demo.universal_integration.capability_catalog_wave_044 import (
    discover_course_catalog,
)


REFERENCE_COURSES = (
    ("ALGEBRA_I", "Algebra I", "Linear Equations", "Solve One-Step Equations"),
    ("CALCULUS_I", "Calculus I", "Derivatives", "Differentiate Polynomial Functions"),
    ("STATICS", "Statics", "Force Equilibrium", "Resolve Force Components"),
    (
        "ELECTRICITY_AND_MAGNETISM",
        "Electricity and Magnetism",
        "Electric Fields",
        "Compute Electric Field Magnitude",
    ),
    (
        "PROGRAMMING_FUNDAMENTALS",
        "Programming Fundamentals",
        "Control Flow",
        "Trace Conditional Execution",
    ),
    (
        "GENERAL_CHEMISTRY",
        "General Chemistry",
        "Stoichiometry",
        "Balance Chemical Equations",
    ),
)

SOURCE_TYPE_PLAN = (
    (SourceType.TEXT_NATIVE_PDF.value, SourceType.SYLLABUS.value, SourceType.COURSE_DEFINITION_PACKAGE.value),
    (SourceType.TEXT_NATIVE_PDF.value, SourceType.STANDARDS_DOCUMENT.value, SourceType.COURSE_DEFINITION_PACKAGE.value),
    (SourceType.SYLLABUS.value, SourceType.QUESTION_BANK.value, SourceType.COURSE_DEFINITION_PACKAGE.value),
    (SourceType.STANDARDS_DOCUMENT.value, SourceType.QUESTION_BANK.value, SourceType.COURSE_DEFINITION_PACKAGE.value),
    (SourceType.TEXTBOOK_OR_CHAPTER.value, SourceType.STRUCTURED_JSON.value, SourceType.COURSE_DEFINITION_PACKAGE.value),
    (SourceType.PLAIN_TEXT.value, SourceType.STRUCTURED_CSV.value, SourceType.COURSE_DEFINITION_PACKAGE.value),
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def _primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "to_dict"):
        return _primitive(value.to_dict())
    if is_dataclass(value):
        return _primitive(asdict(value))
    if isinstance(value, dict):
        return {key: _primitive(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)):
        return [_primitive(child) for child in value]
    return value


def _source_lines(course_name: str, topic: str, skill: str) -> tuple[str, ...]:
    slug = course_name.lower().replace(" ", "-")
    return (
        f"course: {course_name}",
        f"unit: {topic} Foundations",
        f"topic: {topic}",
        f"micro-skill: {skill}",
        f"prerequisite: {topic} Vocabulary",
        f"procedure: Apply {skill}",
        f"generation family: {slug} evidence family",
        f"assessment objective: Demonstrate {skill}",
    )


def _build_corpus(index: int, course_id: str, course_name: str, topic: str, skill: str) -> SourceCorpusV1:
    rights = SourceRightsClassificationV1(
        "INTERNAL_FIXTURE",
        "AxiomIQ-authored curated internal Wave 066 proof fixture",
    )
    documents = []
    for source_index, source_type in enumerate(SOURCE_TYPE_PLAN[index], 1):
        document_id = f"W066:{course_id}:SOURCE:{source_index}"
        lines = _source_lines(course_name, topic, skill)
        source_hash = _digest(
            {
                "fixture_classification": "CURATED_INTERNAL_FIXTURE",
                "document_id": document_id,
                "source_type": source_type,
                "lines": lines,
            }
        )
        segments = []
        for line_index, line in enumerate(lines, 1):
            location = SourceLocationV1("FIXTURE_RECORD", f"{document_id}:{line_index}")
            segments.append(
                SourceSegmentV1(
                    f"SEG:{_digest((document_id, line_index, line))[:24]}",
                    document_id,
                    source_hash,
                    line,
                    location,
                    "CURATED_INTERNAL_TEXT",
                    1.0,
                    "PROPOSED",
                    rights,
                )
            )
        documents.append(
            SourceDocumentV1(
                document_id,
                source_type,
                source_hash,
                f"{course_name} curated internal {source_type} fixture",
                rights,
                tuple(segments),
            )
        )
    manifest_sha256 = _digest([document.to_dict() for document in documents])
    return SourceCorpusV1(f"W066:{course_id}:CORPUS", tuple(documents), manifest_sha256)


def _synthesize_course(corpus: SourceCorpusV1) -> tuple[dict[str, Any], Any]:
    extraction = extract_curriculum_candidates(corpus)
    graph = extraction["evidence_graph"]
    claims = {claim.claim_id: claim for claim in graph.claims}
    candidates = []
    for extracted in extraction["candidates"]:
        for claim_id in extracted.evidence_claim_ids:
            claim = claims[claim_id]
            candidates.append(
                SynthesisCandidate(
                    f"{extracted.candidate_id}:{claim.document_id}",
                    extracted.candidate_type,
                    extracted.title,
                    claim.document_id,
                    (claim_id,),
                    extracted.confidence,
                    rights="INTERNAL_FIXTURE",
                    source_version="W066_FIXTURE_V1",
                    synonym_key=extracted.title,
                )
            )
    expected: dict[str, set[str]] = {}
    for extracted in extraction["candidates"]:
        expected.setdefault(extracted.candidate_type, set()).add(extracted.title)
    result = synthesize(
        tuple(candidates),
        set(claims),
        {document.document_id: 1.0 for document in corpus.documents},
        expected,
        course_pack_complete=True,
    )
    return extraction, result


def _alignment_registry(topic_by_course: dict[str, str]) -> tuple[tuple[RegisteredIdentity, ...], tuple[str, ...]]:
    course_ids = tuple(sorted(discover_course_catalog()["total"]))
    registry = tuple(
        RegisteredIdentity(
            f"PACK:{course_id}:TOPIC",
            course_id,
            course_id,
            "TOPIC",
            topic_by_course.get(course_id, f"{course_id.replace('_', ' ').title()} Reference Topic"),
            (),
            version="W056_VALIDATED",
        )
        for course_id in course_ids
    )
    return registry, course_ids


def _node_by_type(result: Any, candidate_type: str) -> Any:
    matches = [node for node in result.nodes if node.candidate_type == candidate_type]
    if len(matches) != 1:
        raise ValueError(f"expected one {candidate_type} node, found {len(matches)}")
    return matches[0]


def _build_alignment(course_id: str, synthesis_result: Any, registry: tuple[RegisteredIdentity, ...], pack_ids: tuple[str, ...]) -> dict[str, Any]:
    candidates = []
    for node in synthesis_result.nodes:
        candidates.append(
            SourceAlignmentCandidate(
                node.node_id,
                course_id,
                node.candidate_type,
                node.title,
                node.evidence_claim_ids,
                node.confidence,
                f"PACK:{course_id}:TOPIC" if node.candidate_type == "TOPIC" else "",
            )
        )
    return align_all(tuple(candidates), registry, pack_ids)


def _generation_outputs(course_id: str, synthesis_result: Any, known_claim_ids: set[str]) -> tuple[Any, Any, dict[str, Any]]:
    unit = _node_by_type(synthesis_result, "UNIT")
    topic = _node_by_type(synthesis_result, "TOPIC")
    skill = _node_by_type(synthesis_result, "MICRO_SKILL")
    procedure = _node_by_type(synthesis_result, "PROCEDURE")
    family = _node_by_type(synthesis_result, "GENERATION_FAMILY")
    evidence = tuple(sorted(set(unit.evidence_claim_ids + topic.evidence_claim_ids + skill.evidence_claim_ids + procedure.evidence_claim_ids + family.evidence_claim_ids)))
    declaration = {
        "requirement_id": f"W066:{course_id}:GENERATION_REQUIREMENT",
        "course_id": course_id,
        "unit_id": unit.node_id,
        "topic_id": topic.node_id,
        "micro_skill_id": skill.node_id,
        "procedure_id": procedure.node_id,
        "generation_family_id": family.node_id,
        "recipe_requirement_id": f"W066:{course_id}:RECIPE_REQUIREMENT",
        "answer_engine_type": "NUMERIC_TOLERANCE",
        "requested_count": 300,
        "difficulty_allocation": {"FOUNDATIONAL": 0.3, "DEVELOPING": 0.4, "TRANSFER": 0.3},
        "question_type_allocation": {"CONSTRUCTED_RESPONSE": 0.5, "SELECTED_RESPONSE": 0.5},
        "assessment_roles": ("PRACTICE", "DIAGNOSTIC", "FORMATIVE", "SUMMATIVE"),
        "failure_signals": ("EVIDENCE_MISMATCH", "ENGINE_REJECTION"),
        "asset_policy": "TEXT_ONLY_UNLESS_EVIDENCED",
        "duplicate_constraints": {"exact_duplicate_limit": 0, "semantic_review_required": True},
        "dependency_classifications": ("EXISTING_SUPPORTED",),
        "evidence_claim_ids": evidence,
        "status": "READY",
    }
    package = compile_generation_requirements(
        package_id=f"W066:{course_id}:GENERATION_PACKAGE",
        course_id=course_id,
        seed=f"W066:{course_id}:DETERMINISTIC_SEED",
        synthesized_requirements=(declaration,),
        known_evidence_claim_ids=known_claim_ids,
    )
    manifest = build_generation_manifest(package)
    return package, manifest, generation_readiness(package)


def _assessment_outputs(course_id: str, corpus: SourceCorpusV1, extraction: dict[str, Any], synthesis_result: Any) -> tuple[Any, tuple[Any, ...]]:
    unit = _node_by_type(synthesis_result, "UNIT")
    topic = _node_by_type(synthesis_result, "TOPIC")
    skill = _node_by_type(synthesis_result, "MICRO_SKILL")
    prerequisite = _node_by_type(synthesis_result, "PREREQUISITE")
    objective = _node_by_type(synthesis_result, "ASSESSMENT_OBJECTIVE")
    family = _node_by_type(synthesis_result, "GENERATION_FAMILY")
    graph = extraction["evidence_graph"]
    claim_ids = tuple(sorted(claim.claim_id for claim in graph.claims))
    outcome_id = f"W066:{course_id}:OUTCOME"
    grading_engine_id = f"W066:{course_id}:GRADING_ENGINE"
    source_example_id = corpus.documents[0].document_id
    policy_id = f"W066:{course_id}:ASSESSMENT_POLICY"
    common = {
        "course_id": course_id,
        "topic_weights": {topic.node_id: 1.0},
        "difficulty_distribution": {"FOUNDATIONAL": 0.3, "DEVELOPING": 0.4, "TRANSFER": 0.3},
        "question_type_distribution": {"CONSTRUCTED_RESPONSE": 0.5, "SELECTED_RESPONSE": 0.5},
        "unit_scope": (unit.node_id,),
        "micro_skill_coverage": (skill.node_id,),
        "prerequisite_coverage": (prerequisite.node_id,),
        "evidence_claim_ids": claim_ids,
        "course_outcome_ids": (outcome_id,),
        "assessment_objective_ids": (objective.node_id,),
        "generation_family_ids": (family.node_id,),
        "grading_engine_ids": (grading_engine_id,),
        "source_example_ids": (source_example_id,),
        "course_pack_policy_ids": (policy_id,),
        "reuse_policy": {"allow_reuse": False},
        "variant_policy": {"variant_count": 2},
        "scoring_rules": {"points_per_question": 1},
        "review_state": "PROPOSED",
        "canonical_authority": False,
    }
    counts = {
        BlueprintType.PRACTICE.value: 12,
        BlueprintType.DIAGNOSTIC.value: 15,
        BlueprintType.FORMATIVE.value: 10,
        BlueprintType.SUMMATIVE.value: 20,
    }
    declarations = tuple(
        {
            **common,
            "blueprint_id": f"W066:{course_id}:{blueprint_type}",
            "blueprint_type": blueprint_type,
            "question_count": count,
            "time_budget_minutes": count * 2,
            "rubrics": ({"rubric_id": f"W066:{course_id}:{blueprint_type}:RUBRIC", "criterion": "evidence-backed correctness"},),
        }
        for blueprint_type, count in counts.items()
    )
    owner = lambda identities: {identity: course_id for identity in identities}
    context = {
        "unit_courses": owner((unit.node_id,)),
        "topic_courses": owner((topic.node_id,)),
        "micro_skill_courses": owner((skill.node_id,)),
        "prerequisite_courses": owner((prerequisite.node_id,)),
        "evidence_claim_courses": owner(claim_ids),
        "course_outcome_courses": owner((outcome_id,)),
        "assessment_objective_courses": owner((objective.node_id,)),
        "generation_family_courses": owner((family.node_id,)),
        "grading_engine_courses": owner((grading_engine_id,)),
        "source_example_courses": owner((source_example_id,)),
        "course_pack_policy_courses": owner((policy_id,)),
        "required_topic_ids": (topic.node_id,),
        "required_micro_skill_ids": (skill.node_id,),
        "required_course_outcome_ids": (outcome_id,),
        "required_assessment_objective_ids": (objective.node_id,),
    }
    package = compile_assessment_blueprints(
        package_id=f"W066:{course_id}:ASSESSMENT_PACKAGE",
        course_id=course_id,
        declarations=declarations,
        validation_context=context,
    )
    required = tuple(
        blueprint
        for blueprint in package.blueprints
        if blueprint.blueprint_type
        in {BlueprintType.PRACTICE.value, BlueprintType.DIAGNOSTIC.value, BlueprintType.SUMMATIVE.value}
    )
    return package, required


def _review_package(course_id: str, corpus: SourceCorpusV1, extraction: dict[str, Any], synthesis_result: Any, alignment: dict[str, Any]) -> tuple[dict[str, Any], Any]:
    graph = extraction["evidence_graph"]
    review = {
        "course_id": course_id,
        "sources": [document.to_dict() for document in corpus.documents],
        "evidence_claims": [claim.to_dict() for claim in graph.claims],
        "nodes": [
            {
                "node_id": node.node_id,
                "node_type": node.candidate_type,
                "course_id": course_id,
                "inference_boundary": "DIRECT_SOURCE_EVIDENCE",
                "evidence_claim_ids": list(node.evidence_claim_ids),
                "confidence": node.confidence,
                "review_required": True,
                "canonical_authority": False,
            }
            for node in synthesis_result.nodes
        ],
        "conflicts": [
            {
                "conflict_id": conflict.conflict_id,
                "resolution_state": conflict.resolution_state,
                "evidence_claim_ids": list(conflict.evidence_claim_ids),
            }
            for conflict in synthesis_result.conflicts
        ],
        "declared_conflict_ids": [conflict.conflict_id for conflict in synthesis_result.conflicts],
        "coverage_gaps": list(synthesis_result.coverage.gaps),
        "mappings": [
            {
                "mapping_id": item.alignment_id,
                "course_id": course_id,
                "evidence_claim_ids": list(item.source_evidence),
                "canonical_authority": False,
            }
            for item in alignment["alignments"]
        ],
        "canonical_authority": False,
    }
    return review, audit_review_package(review)


def compile_reference_course_corpora() -> dict[str, Any]:
    """Compile all six reference courses without protected-state writes."""
    topic_by_course = {course_id: topic for course_id, _, topic, _ in REFERENCE_COURSES}
    registry, pack_ids = _alignment_registry(topic_by_course)
    courses = []
    source_types: Counter[str] = Counter()
    for index, (course_id, course_name, topic, skill) in enumerate(REFERENCE_COURSES):
        corpus = _build_corpus(index, course_id, course_name, topic, skill)
        extraction, synthesis_result = _synthesize_course(corpus)
        alignment = _build_alignment(course_id, synthesis_result, registry, pack_ids)
        graph = extraction["evidence_graph"]
        requirements, generation_manifest, readiness = _generation_outputs(
            course_id, synthesis_result, {claim.claim_id for claim in graph.claims}
        )
        assessment_package, required_blueprints = _assessment_outputs(
            course_id, corpus, extraction, synthesis_result
        )
        review_package, review_report = _review_package(
            course_id, corpus, extraction, synthesis_result, alignment
        )
        if not review_report.passed:
            raise ValueError(f"quality review failed for {course_id}: {review_report.findings}")
        source_types.update(document.source_type for document in corpus.documents)
        conflict_report = {
            "conflicts": _primitive(synthesis_result.conflicts),
            "conflict_count": len(synthesis_result.conflicts),
            "silent_resolutions": 0,
        }
        courses.append(
            {
                "course_id": course_id,
                "course_name": course_name,
                "source_fixture_classification": "CURATED_INTERNAL_FIXTURE",
                "normalized_source_corpus": corpus.to_dict(),
                "source_evidence_graph": graph.to_dict(),
                "curriculum_extraction_package": {
                    "candidates": _primitive(extraction["candidates"]),
                    "unsupported_candidates": _primitive(extraction["unsupported_candidates"]),
                    "target_counts": extraction["target_counts"],
                    "canonical_authority": False,
                },
                "synthesized_curriculum_package": synthesis_result.to_dict(),
                "conflict_report": conflict_report,
                "coverage_report": _primitive(synthesis_result.coverage),
                "proposed_canonical_mappings": _primitive(alignment),
                "procedure_and_generation_requirement_package": requirements.to_dict(),
                "generation_manifest": generation_manifest.to_dict(),
                "generation_readiness": readiness,
                "assessment_blueprint_package": assessment_package.to_dict(),
                "assessment_blueprints": _primitive(required_blueprints),
                "review_package": review_package,
                "review_report": _primitive(review_report),
            }
        )
    summary = {
        "reference_courses": len(courses),
        "source_documents_processed": sum(len(course["normalized_source_corpus"]["documents"]) for course in courses),
        "source_segments_processed": sum(
            len(document["segments"])
            for course in courses
            for document in course["normalized_source_corpus"]["documents"]
        ),
        "source_type_counts": dict(sorted(source_types.items())),
        "curriculum_synthesis_packages": len(courses),
        "generation_manifests": len(courses),
        "generation_question_target": sum(
            requirement["requested_count"]
            for course in courses
            for requirement in course["generation_manifest"]["requirements"]
        ),
        "assessment_blueprints": sum(len(course["assessment_blueprints"]) for course in courses),
        "assessment_compiler_blueprints": sum(
            len(course["assessment_blueprint_package"]["blueprints"]) for course in courses
        ),
        "unsupported_candidates": sum(
            len(course["curriculum_extraction_package"]["unsupported_candidates"])
            for course in courses
        ),
        "source_free_nodes": sum(
            not node["evidence_claim_ids"]
            for course in courses
            for node in course["synthesized_curriculum_package"]["nodes"]
        ),
        "silent_conflict_resolutions": 0,
        "canonical_authority": False,
    }
    material = _primitive({
        "courses": courses,
        "summary": summary,
        "protected_state": {
            "compiler_main_modified": False,
            "canonical_writes": False,
            "database_access": False,
            "adaptive_platform_modified": False,
            "student_visible": False,
        },
    })
    return {**material, "deterministic_sha256": _digest(material)}


def checkpoint_reference_course_corpora(path: Path, result: dict[str, Any]) -> str:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, sort_keys=True, indent=2) + "\n"
    destination.write_text(payload, encoding="utf-8")
    return hashlib.sha256(payload.encode()).hexdigest()


def reopen_reference_course_corpora(path: Path) -> dict[str, Any]:
    result = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = result.pop("deterministic_sha256", None)
    actual = _digest(result)
    if expected != actual:
        raise ValueError("source-corpus checkpoint integrity failure")
    result["deterministic_sha256"] = expected
    result["reopen_verified"] = True
    return result
