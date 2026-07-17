"""Reusable subject-profile loader and deterministic profile-run builder."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


COMPILER_ROOT = Path(__file__).resolve().parents[3]
PROTECTED_ALPHA_ROOT = Path("/Users/fanarichardson/adaptive-platform").resolve()
PROFILE_STATUS = "compiler_profile_review_pending"


class ProfileValidationError(ValueError):
    """Raised when a subject ingestion profile is malformed or unsafe."""


class SubjectProfileRunError(ValueError):
    """Raised when a profile cannot safely process a source."""


@dataclass(frozen=True)
class ProfileRunResult:
    outputs: dict[str, Any]
    release_seed: dict[str, Any]
    semantic_digest: str


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


def pretty_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_profile(path: Path | str) -> dict[str, Any]:
    profile_path = Path(path)
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ProfileValidationError(f"malformed JSON: {exc}") from exc
    if not isinstance(profile, dict):
        raise ProfileValidationError("profile must be a JSON object")
    validate_profile(profile)
    return profile


def validate_profile(profile: dict[str, Any]) -> None:
    required = {
        "profile_id",
        "profile_version",
        "profile_status",
        "subject_code",
        "subject_name",
        "supported_course_levels",
        "supported_source_types",
        "primary_use_modes",
        "rights_defaults",
        "privacy_defaults",
        "topic_rules",
        "micro_skill_rules",
        "dependency_rules",
        "procedure_candidate_templates",
        "question_candidate_templates",
        "generation_family_templates",
        "practice_module_blueprint",
        "practice_assessment_blueprint",
        "performance_tracking_blueprint",
        "content_gap_rules",
        "review_requirements",
        "non_live_boundary",
    }
    missing = sorted(required - set(profile))
    if missing:
        raise ProfileValidationError(f"missing required profile fields: {missing}")
    if profile.get("profile_status") != PROFILE_STATUS:
        raise ProfileValidationError("unsupported profile status")
    _require_text(profile, "profile_id")
    _require_text(profile, "profile_version")
    _require_text(profile, "subject_code")
    if not _list(profile, "supported_course_levels"):
        raise ProfileValidationError("missing supported course level")
    topics = _list(profile, "topic_rules")
    skills = _list(profile, "micro_skill_rules")
    if not topics:
        raise ProfileValidationError("missing topic rules")
    if not skills:
        raise ProfileValidationError("missing micro-skill rules")

    topic_codes = _unique_codes(topics, "topic_code", "topic")
    skill_codes = _unique_codes(skills, "micro_skill_code", "micro-skill")
    for skill in skills:
        topic_code = skill.get("topic_code")
        if topic_code not in topic_codes:
            raise ProfileValidationError(f"micro-skill references unknown topic: {topic_code}")
        for prereq in skill.get("prerequisite_micro_skill_codes", []):
            if prereq not in skill_codes:
                raise ProfileValidationError(f"unknown prerequisite reference: {prereq}")
    edges = []
    for edge in _list(profile, "dependency_rules"):
        source = edge.get("from_micro_skill_code")
        target = edge.get("to_micro_skill_code")
        if source not in skill_codes or target not in skill_codes:
            raise ProfileValidationError("unknown dependency reference")
        edges.append((source, target))
    _assert_acyclic(skill_codes, edges)

    for field in [
        "procedure_candidate_templates",
        "question_candidate_templates",
        "generation_family_templates",
    ]:
        templates = _list(profile, field)
        if not templates:
            raise ProfileValidationError(f"missing {field}")
        for template in templates:
            if template.get("micro_skill_code") not in skill_codes:
                raise ProfileValidationError(f"{field} references unknown micro-skill")
    for field in [
        "practice_module_blueprint",
        "practice_assessment_blueprint",
        "performance_tracking_blueprint",
    ]:
        if not isinstance(profile.get(field), dict) or not profile[field]:
            raise ProfileValidationError(f"missing {field}")
    _validate_boundary(profile.get("non_live_boundary", {}))
    rights = profile.get("rights_defaults")
    privacy = profile.get("privacy_defaults")
    if not isinstance(rights, dict) or not rights.get("rights_status"):
        raise ProfileValidationError("missing rights defaults")
    if not isinstance(privacy, dict) or not privacy.get("privacy_status"):
        raise ProfileValidationError("missing privacy defaults")


def _validate_boundary(boundary: dict[str, Any]) -> None:
    expected = {
        "canonical_approved": False,
        "live_eligible": False,
        "eligible_for_alpha_import": False,
        "human_review_required": True,
        "db_access_allowed": False,
        "student_visible_publish_allowed": False,
    }
    if not isinstance(boundary, dict):
        raise ProfileValidationError("missing non-live boundary")
    for key, value in expected.items():
        if boundary.get(key) is not value:
            raise ProfileValidationError(f"unsafe profile boundary field: {key}")


def _require_text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProfileValidationError(f"missing {key}")
    return value.strip()


def _list(data: dict[str, Any], key: str) -> list[Any]:
    value = data.get(key)
    return value if isinstance(value, list) else []


def _unique_codes(items: list[Any], key: str, label: str) -> set[str]:
    codes = []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get(key), str) or not item[key].strip():
            raise ProfileValidationError(f"missing {label} code")
        codes.append(item[key].strip())
    if len(codes) != len(set(codes)):
        raise ProfileValidationError(f"duplicate {label} codes")
    return set(codes)


def _assert_acyclic(nodes: set[str], edges: list[tuple[str, str]]) -> None:
    outgoing = {node: [] for node in nodes}
    for source, target in edges:
        outgoing[source].append(target)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise ProfileValidationError("dependency cycle detected")
        if node in visited:
            return
        visiting.add(node)
        for target in outgoing[node]:
            visit(target)
        visiting.remove(node)
        visited.add(node)

    for node in sorted(nodes):
        visit(node)


def safe_output_dir(output: Path | str) -> Path:
    raw = Path(output)
    if any(part == ".." for part in raw.parts):
        raise SubjectProfileRunError("output path traversal is forbidden")
    resolved = raw.expanduser().resolve()
    try:
        resolved.relative_to(PROTECTED_ALPHA_ROOT)
    except ValueError:
        return resolved
    raise SubjectProfileRunError("output inside adaptive-platform is forbidden")


def build_profile_run(
    *,
    profile: dict[str, Any],
    source_text: str,
    source_path: Path,
    selected_micro_skill: str,
) -> ProfileRunResult:
    validate_profile(profile)
    if selected_micro_skill not in {item["micro_skill_code"] for item in profile["micro_skill_rules"]}:
        raise SubjectProfileRunError("selected micro-skill absent from profile")
    _validate_source_compatibility(profile, source_text)
    selected_rule = _find(profile["micro_skill_rules"], "micro_skill_code", selected_micro_skill)
    procedure_template = _first_template(profile["procedure_candidate_templates"], selected_micro_skill)
    question_templates = [
        template for template in profile["question_candidate_templates"] if template.get("micro_skill_code") == selected_micro_skill
    ]
    if not procedure_template:
        raise SubjectProfileRunError("missing procedure template for selected skill")
    if not question_templates:
        raise SubjectProfileRunError("missing question templates for selected skill")

    source_id = _source_id(profile, source_path)
    source_document = _source_document(profile, source_id, source_path, source_text)
    interpretation = _source_interpretation(profile, source_text)
    feature_flags = _source_feature_flags(profile, source_text)
    topics = _topic_candidates(profile, source_text, source_id)
    micro_skills = _micro_skill_candidates(profile, source_text, source_id)
    dependencies = _dependency_candidates(profile)
    gaps = _content_gaps(profile, topics, micro_skills)
    procedure = _procedure_candidate(profile, selected_rule, procedure_template)
    questions = [_question_candidate(profile, selected_rule, procedure, template) for template in question_templates]
    families = [_generation_family(profile, selected_rule, procedure, questions, template) for template in profile["generation_family_templates"] if template.get("micro_skill_code") == selected_micro_skill]
    release_seed = _release_seed(
        profile=profile,
        source_document=source_document,
        interpretation=interpretation,
        selected_rule=selected_rule,
        selected_micro_skill=selected_micro_skill,
        dependencies=dependencies,
        procedure=procedure,
        questions=questions,
        families=families,
        gaps=gaps,
    )
    digest = semantic_seed_digest(release_seed)
    release_seed["semantic_seed_digest"] = digest
    validation = _profile_validation(profile, interpretation, topics, micro_skills, dependencies, release_seed, digest)
    package = {
        "package_id": f"{profile['profile_id']}_extraction_package",
        "profile_id": profile["profile_id"],
        "detected_subject": interpretation["detected_subject"],
        "detected_course_level": interpretation["detected_course_level"],
        "topic_candidates": topics,
        "micro_skill_candidates": micro_skills,
        "dependency_candidates": dependencies,
        "source_evidence": _all_evidence(topics, micro_skills),
        "practice_target_candidates": _practice_targets(profile, selected_micro_skill, questions),
        "assessment_target_candidates": _assessment_targets(profile, selected_micro_skill, questions),
        "performance_tracking_targets": _performance_targets(profile, selected_micro_skill, questions),
        "content_gaps": gaps,
        "rights_summary": release_seed["rights_summary"],
        "status": "compiler_profile_review_pending",
        "created_at": now_iso(),
    }
    output_names = profile.get("output_names", {})
    release_seed_name = output_names.get("release_seed", f"{profile['profile_id'].lower()}_release_seed_v1.json")
    report_name = output_names.get("markdown_report", f"{profile['profile_id']}_PROFILE_RUN_V1.md")
    outputs = {
        "source_document.json": source_document,
        "source_interpretation.json": interpretation,
        "source_feature_flags.json": feature_flags,
        "curriculum_extraction_package.json": package,
        "topic_candidates.json": {"topic_candidates": topics},
        "micro_skill_candidates.json": {"micro_skill_candidates": micro_skills},
        "dependency_candidates.json": {"dependency_candidates": dependencies},
        "content_gaps.json": {"content_gaps": gaps},
        release_seed_name: release_seed,
        "profile_validation_v1.json": validation,
        report_name: _markdown_report(profile, interpretation, selected_micro_skill, digest),
    }
    return ProfileRunResult(outputs=outputs, release_seed=release_seed, semantic_digest=digest)


def semantic_seed_digest(seed: dict[str, Any]) -> str:
    clone = copy.deepcopy(seed)
    for key in ["created_at", "semantic_seed_digest"]:
        clone.pop(key, None)
    validation = clone.get("validation_summary")
    if isinstance(validation, dict):
        validation.pop("validated_at", None)
    return hashlib.sha256(canonical_json(clone).encode("utf-8")).hexdigest()


def write_profile_run(result: ProfileRunResult, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in result.outputs.items():
        path = output_dir / name
        if name.endswith(".json"):
            path.write_text(pretty_json(payload), encoding="utf-8")
        else:
            path.write_text(str(payload), encoding="utf-8")


def _validate_source_compatibility(profile: dict[str, Any], text: str) -> None:
    lowered = text.lower()
    explicit_subject = re.search(r"subject(?:\s+signal)?\s*:\s*([A-Za-z0-9_ &-]+)", text, flags=re.I)
    if explicit_subject:
        declared = explicit_subject.group(1).strip().lower()
        expected_codes = {profile["subject_code"].lower(), profile["subject_name"].lower()}
        if declared not in expected_codes:
            raise SubjectProfileRunError("source subject incompatible with profile")
    subject_terms = [profile["subject_code"].lower(), profile["subject_name"].lower()]
    course_terms = [str(item).lower() for item in profile["supported_course_levels"]]
    if not any(term.replace("_", " ") in lowered or term in lowered for term in subject_terms):
        raise SubjectProfileRunError("source subject incompatible with profile")
    if not any(term.replace("_", " ") in lowered or term in lowered for term in course_terms):
        raise SubjectProfileRunError("source course level incompatible with profile")
    if not isinstance(profile.get("rights_defaults"), dict) or not isinstance(profile.get("privacy_defaults"), dict):
        raise SubjectProfileRunError("missing provenance")


def _source_id(profile: dict[str, Any], source_path: Path) -> str:
    stem = re.sub(r"[^A-Za-z0-9]+", "_", source_path.stem).strip("_").upper()
    return f"SRC_{profile['subject_code']}_{stem}"


def _source_document(profile: dict[str, Any], source_id: str, source_path: Path, text: str) -> dict[str, Any]:
    title = next((line.strip("# ").strip() for line in text.splitlines() if line.strip()), source_path.stem)
    return {
        "source_id": source_id,
        "source_title": title,
        "source_path": source_path.as_posix(),
        "source_type": profile["supported_source_types"][0],
        "subject_code": profile["subject_code"],
        "course_profile": profile["supported_course_levels"][0],
        "rights_status": profile["rights_defaults"]["rights_status"],
        "privacy_status": profile["privacy_defaults"]["privacy_status"],
        "byte_size": len(text.encode("utf-8")),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }


def _source_interpretation(profile: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "detected_subject": profile["subject_code"],
        "detected_course_level": profile["supported_course_levels"][0],
        "subject_confidence": "high",
        "course_level_confidence": "high",
        "practice_potential": _contains_any(text, ["practice", "problem"]),
        "assessment_potential": _contains_any(text, ["assessment", "check"]),
        "interpretation_basis": "subject ingestion profile rules",
    }


def _source_feature_flags(profile: dict[str, Any], text: str) -> dict[str, Any]:
    return {
        "contains_formula": bool(re.search(r"=|\\bformula\\b", text, flags=re.I)),
        "contains_prerequisite_relationship": _contains_any(text, ["prerequisite", "before", "depends"]),
        "contains_practice_items": _contains_any(text, ["practice", "problem"]),
        "contains_learning_objectives": _contains_any(text, ["objective", "students will"]),
        "profile_id": profile["profile_id"],
    }


def _topic_candidates(profile: dict[str, Any], text: str, source_id: str) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": f"TOPIC_{index:03d}",
            "topic_code": rule["topic_code"],
            "topic_name": rule["topic_name"],
            "subject_code": profile["subject_code"],
            "confidence": _confidence(text, rule.get("evidence_patterns", [])),
            "source_evidence": _evidence(text, source_id, rule.get("evidence_patterns", []), f"TOPIC_{index:03d}"),
            "status": "compiler_profile_review_pending",
        }
        for index, rule in enumerate(profile["topic_rules"], start=1)
    ]


def _micro_skill_candidates(profile: dict[str, Any], text: str, source_id: str) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": f"MS_{index:03d}",
            "micro_skill_code": rule["micro_skill_code"],
            "micro_skill_name": rule["micro_skill_name"],
            "topic_code": rule["topic_code"],
            "subject_code": profile["subject_code"],
            "prerequisite_micro_skill_codes": rule.get("prerequisite_micro_skill_codes", []),
            "confidence": _confidence(text, rule.get("evidence_patterns", [])),
            "source_evidence": _evidence(text, source_id, rule.get("evidence_patterns", []), f"MS_{index:03d}"),
            "practice_target_candidate": True,
            "assessment_target_candidate": True,
            "performance_tracking_target": True,
            "status": "compiler_profile_review_pending",
        }
        for index, rule in enumerate(profile["micro_skill_rules"], start=1)
    ]


def _dependency_candidates(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": f"DEP_{index:03d}",
            "from_micro_skill_code": edge["from_micro_skill_code"],
            "to_micro_skill_code": edge["to_micro_skill_code"],
            "relationship": edge.get("relationship", "prerequisite"),
            "confidence": edge.get("confidence", "high"),
            "status": "compiler_profile_review_pending",
        }
        for index, edge in enumerate(profile["dependency_rules"], start=1)
    ]


def _content_gaps(profile: dict[str, Any], topics: list[dict[str, Any]], skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps = []
    if len(topics) < len(profile["topic_rules"]):
        gaps.append({"gap_id": "TOPIC_COVERAGE_GAP", "severity": "blocking"})
    if len(skills) < len(profile["micro_skill_rules"]):
        gaps.append({"gap_id": "MICRO_SKILL_COVERAGE_GAP", "severity": "blocking"})
    if not gaps:
        gaps.append({"gap_id": "NO_PROFILE_GAPS_DECLARED", "severity": "none", "description": "Profile proof has explicit coverage for required demo sequence."})
    return gaps


def _procedure_candidate(profile: dict[str, Any], rule: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    procedure_id = template["procedure_id"]
    return {
        "candidate_id": procedure_id,
        "procedure_id": procedure_id,
        "subject_code": profile["subject_code"],
        "topic_code": rule["topic_code"],
        "micro_skill_code": rule["micro_skill_code"],
        "description": template["description"],
        "steps": template["steps"],
        "formula_refs": template.get("formula_refs", []),
        "status": "human_review_required",
        "human_review_required": True,
    }


def _question_candidate(profile: dict[str, Any], rule: dict[str, Any], procedure: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": template["question_id"],
        "question_id": template["question_id"],
        "subject_code": profile["subject_code"],
        "topic_code": rule["topic_code"],
        "micro_skill_code": rule["micro_skill_code"],
        "procedure_id": procedure["procedure_id"],
        "question_type": template.get("question_type", "numeric"),
        "prompt": template["prompt"],
        "answer": template["answer"],
        "unit": template.get("unit"),
        "answer_structure": template.get("answer_structure", "numeric_with_unit"),
        "source_evidence_ref": template.get("source_evidence_ref"),
        "student_visible": False,
        "status": "human_review_required",
        "human_review_required": True,
    }


def _generation_family(profile: dict[str, Any], rule: dict[str, Any], procedure: dict[str, Any], questions: list[dict[str, Any]], template: dict[str, Any]) -> dict[str, Any]:
    return {
        "family_id": template["family_id"],
        "subject_code": profile["subject_code"],
        "topic_code": rule["topic_code"],
        "micro_skill_code": rule["micro_skill_code"],
        "procedure_id": procedure["procedure_id"],
        "question_ids": [question["question_id"] for question in questions],
        "family_type": template.get("family_type"),
        "variable_fields": template.get("variable_fields", []),
        "variation_rules": template.get("variation_rules", {}),
        "status": "human_review_required",
        "human_review_required": True,
    }


def _release_seed(
    *,
    profile: dict[str, Any],
    source_document: dict[str, Any],
    interpretation: dict[str, Any],
    selected_rule: dict[str, Any],
    selected_micro_skill: str,
    dependencies: list[dict[str, Any]],
    procedure: dict[str, Any],
    questions: list[dict[str, Any]],
    families: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
) -> dict[str, Any]:
    question_ids = [question["question_id"] for question in questions]
    procedure_ids = [procedure["procedure_id"]]
    prereqs = selected_rule.get("prerequisite_micro_skill_codes", [])
    return {
        "package_id": f"{profile['profile_id']}_release_seed_v1",
        "created_at": now_iso(),
        "subject_code": profile["subject_code"],
        "topic_code": selected_rule["topic_code"],
        "selected_micro_skill_code": selected_micro_skill,
        "prerequisite_micro_skill_codes": prereqs,
        "dependency_references": [
            edge for edge in dependencies if edge["to_micro_skill_code"] == selected_micro_skill or edge["from_micro_skill_code"] in prereqs
        ],
        "source_artifacts": [{"path": source_document["source_path"], "ref_id": source_document["source_id"]}],
        "source_provenance": {
            "source_id": source_document["source_id"],
            "source_title": source_document["source_title"],
            "detected_subject": interpretation["detected_subject"],
            "detected_course_level": interpretation["detected_course_level"],
            "evidence_refs": [{"path": source_document["source_path"], "ref_id": source_document["source_id"]}],
            "privacy_status": profile["privacy_defaults"],
        },
        "rights_summary": {
            "rights_status": profile["rights_defaults"]["rights_status"],
            "privacy_status": profile["privacy_defaults"]["privacy_status"],
            "source_basis": "axiomiq_owned_synthetic_profile_source",
            "third_party_copying": "not_used",
        },
        "review_state": {"review_status": "review_pending", "human_review_required": True, "status": "human_review_required"},
        "procedure_candidates": [procedure],
        "question_candidates": questions,
        "generation_family_candidates": families,
        "practice_module_package": _practice_module(profile, selected_micro_skill, question_ids, procedure_ids),
        "practice_assessment_package": _assessment_package(profile, selected_micro_skill, question_ids),
        "performance_tracking_package": _performance_package(profile, selected_micro_skill, question_ids),
        "content_gaps": gaps,
        "known_limitations": [
            "Compiler-side profile proof only.",
            "No Alpha import, DB contact, or student-visible publishing is authorized.",
            "Physics source and questions are AxiomIQ-authored synthetic proof content.",
        ],
        "validation_summary": {},
        "integration_boundary": {
            "internal_preview_only": True,
            "live_eligible": False,
            "eligible_for_alpha_import": False,
            "canonical_approved": False,
            "canonical_promotion_performed": False,
            "db_read_performed": False,
            "db_write_performed": False,
            "adaptive_platform_write_performed": False,
            "student_visible_publish_performed": False,
            "deployment_performed": False,
            "human_review_required": True,
        },
    }


def _practice_module(profile: dict[str, Any], skill: str, question_ids: list[str], procedure_ids: list[str]) -> dict[str, Any]:
    blueprint = profile["practice_module_blueprint"]
    return {
        "package_id": blueprint.get("package_id", f"PM_{skill.upper()}_001"),
        "selected_micro_skill_code": skill,
        "question_ids": question_ids,
        "procedure_ids": procedure_ids,
        "status": "human_review_required",
        "student_visible": False,
    }


def _assessment_package(profile: dict[str, Any], skill: str, question_ids: list[str]) -> dict[str, Any]:
    blueprint = profile["practice_assessment_blueprint"]
    return {
        "package_id": blueprint.get("package_id", f"PA_{skill.upper()}_001"),
        "selected_micro_skill_code": skill,
        "assessment_type": blueprint.get("assessment_type", "single_micro_skill_internal_check"),
        "question_ids": question_ids,
        "status": "human_review_required",
        "student_visible": False,
    }


def _performance_package(profile: dict[str, Any], skill: str, question_ids: list[str]) -> dict[str, Any]:
    blueprint = profile["performance_tracking_blueprint"]
    return {
        "package_id": blueprint.get("package_id", f"PERF_{skill.upper()}_001"),
        "selected_micro_skill_code": skill,
        "tracked_question_ids": question_ids,
        "tracked_micro_skill_codes": [skill],
        "status": "human_review_required",
        "student_visible": False,
    }


def _profile_validation(
    profile: dict[str, Any],
    interpretation: dict[str, Any],
    topics: list[dict[str, Any]],
    skills: list[dict[str, Any]],
    dependencies: list[dict[str, Any]],
    seed: dict[str, Any],
    digest: str,
) -> dict[str, Any]:
    return {
        "validation_status": "pass",
        "profile_id": profile["profile_id"],
        "detected_subject": interpretation["detected_subject"],
        "detected_course_level": interpretation["detected_course_level"],
        "topic_count": len(topics),
        "micro_skill_count": len(skills),
        "dependency_count": len(dependencies),
        "selected_micro_skill_code": seed["selected_micro_skill_code"],
        "semantic_seed_digest": digest,
        "non_live_boundary": seed["integration_boundary"],
        "errors": [],
        "warnings": [],
    }


def _markdown_report(profile: dict[str, Any], interpretation: dict[str, Any], selected: str, digest: str) -> str:
    return "\n".join(
        [
            f"# {profile['subject_name']} Profile Run",
            "",
            f"- profile_id: {profile['profile_id']}",
            f"- detected_subject: {interpretation['detected_subject']}",
            f"- detected_course_level: {interpretation['detected_course_level']}",
            f"- selected_micro_skill_code: {selected}",
            f"- semantic_seed_digest: {digest}",
            "- status: compiler_profile_review_pending",
            "- non_live: true",
            "- adaptive_platform_write_performed: false",
            "",
        ]
    )


def _find(items: list[dict[str, Any]], key: str, value: str) -> dict[str, Any]:
    for item in items:
        if item.get(key) == value:
            return item
    raise SubjectProfileRunError(f"missing {key}: {value}")


def _first_template(items: list[dict[str, Any]], micro_skill: str) -> dict[str, Any] | None:
    return next((item for item in items if item.get("micro_skill_code") == micro_skill), None)


def _contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _confidence(text: str, patterns: list[str]) -> str:
    hits = sum(1 for pattern in patterns if pattern.lower() in text.lower())
    if hits >= 2:
        return "high"
    if hits == 1:
        return "medium"
    return "low"


def _evidence(text: str, source_id: str, patterns: list[str], prefix: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    found = []
    for pattern in patterns:
        lowered = pattern.lower()
        for index, line in enumerate(lines, start=1):
            if lowered in line.lower():
                found.append(
                    {
                        "evidence_id": f"EV_{prefix}_{len(found)+1:03d}",
                        "source_id": source_id,
                        "line_start": index,
                        "line_end": index,
                        "short_excerpt": line.strip()[:180],
                        "matched_pattern": pattern,
                        "confidence": "high",
                    }
                )
                break
    return found or [
        {
            "evidence_id": f"EV_{prefix}_001",
            "source_id": source_id,
            "line_start": None,
            "line_end": None,
            "short_excerpt": "Profile rule retained pending human review.",
            "matched_pattern": None,
            "confidence": "low",
        }
    ]


def _all_evidence(topics: list[dict[str, Any]], skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for item in topics + skills:
        evidence.extend(item.get("source_evidence", []))
    return evidence


def _practice_targets(profile: dict[str, Any], selected: str, questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"target_type": "practice", "selected_micro_skill_code": selected, "question_ids": [q["question_id"] for q in questions], "status": "human_review_required"}]


def _assessment_targets(profile: dict[str, Any], selected: str, questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"target_type": "assessment", "selected_micro_skill_code": selected, "question_ids": [q["question_id"] for q in questions], "status": "human_review_required"}]


def _performance_targets(profile: dict[str, Any], selected: str, questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"target_type": "performance_tracking", "selected_micro_skill_code": selected, "tracked_question_ids": [q["question_id"] for q in questions], "status": "human_review_required"}]
