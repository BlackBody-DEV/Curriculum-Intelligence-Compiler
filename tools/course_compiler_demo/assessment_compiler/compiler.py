"""Fail-closed blueprint constraint solver for assessments."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import random
from typing import Any, Iterable, Mapping

from tools.course_compiler_demo.universal_core import AssessmentBlueprintV1, ValidatedQuestionReferenceV1


class AssessmentCompilationError(ValueError):
    """The validated bank cannot satisfy the complete blueprint."""


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return value.to_dict()


def _allocation(distribution: Mapping[str, float], count: int, name: str) -> dict[str, int]:
    if not distribution or any(not isinstance(v, (int, float)) or v < 0 for v in distribution.values()):
        raise AssessmentCompilationError(f"{name} must contain nonnegative weights")
    total = sum(distribution.values())
    if abs(total - 1.0) > 1e-9:
        raise AssessmentCompilationError(f"{name} weights must sum to 1")
    raw = {k: float(v) * count for k, v in distribution.items()}
    result = {k: int(v) for k, v in raw.items()}
    for key in sorted(raw, key=lambda k: (-(raw[k] - result[k]), k))[: count - sum(result.values())]:
        result[key] += 1
    return result


@dataclass(frozen=True)
class CompiledAssessment:
    assessment_id: str
    blueprint_id: str
    seed: str
    variant_index: int
    question_references: tuple[dict[str, Any], ...]
    total_time_minutes: float
    allocation: dict[str, dict[str, int]]
    scoring_rules: dict[str, Any]
    rubrics: tuple[dict[str, Any], ...]
    variant_policy: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id, "blueprint_id": self.blueprint_id,
            "seed": self.seed, "variant_index": self.variant_index,
            "question_references": list(self.question_references),
            "total_time_minutes": self.total_time_minutes, "allocation": self.allocation,
            "scoring_rules": self.scoring_rules, "rubrics": list(self.rubrics),
            "variant_policy": self.variant_policy,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


def compile_assessment(
    blueprint: AssessmentBlueprintV1 | Mapping[str, Any],
    bank: Iterable[ValidatedQuestionReferenceV1 | Mapping[str, Any]],
    seed: str,
    *,
    variant_index: int = 0,
    previously_used_question_ids: Iterable[str] = (),
) -> CompiledAssessment:
    """Select a complete deterministic assessment or raise without partial output."""
    bp = blueprint if isinstance(blueprint, AssessmentBlueprintV1) else AssessmentBlueprintV1.from_dict(blueprint)
    if not isinstance(seed, str) or not seed:
        raise AssessmentCompilationError("seed is required")
    if variant_index < 0:
        raise AssessmentCompilationError("variant_index must be nonnegative")
    targets = {
        "topic": _allocation(bp.topic_weights, bp.question_count, "topic_weights"),
        "difficulty": _allocation(bp.difficulty_distribution, bp.question_count, "difficulty_distribution"),
        "question_type": _allocation(bp.question_type_distribution, bp.question_count, "question_type_distribution"),
    }
    used = set(previously_used_question_ids)
    allow_reuse = bool(bp.reuse_policy.get("allow_reuse", False))
    refs = []
    for item in bank:
        ref = item if isinstance(item, ValidatedQuestionReferenceV1) else ValidatedQuestionReferenceV1.from_dict(item)
        data = ref.to_dict()
        mapping = data["curriculum_mapping"]
        if mapping.get("course_id") != bp.course_node_id:
            continue
        if bp.unit_scope and mapping.get("unit_id") not in bp.unit_scope:
            continue
        if not allow_reuse and data["question_id"] in used:
            continue
        refs.append(data)
    identity_pairs = [(r["question_id"], r["question_revision"]) for r in refs]
    if len(identity_pairs) != len(set(identity_pairs)):
        raise AssessmentCompilationError("question bank contains duplicate identities")
    rng = random.Random(f"{seed}:{variant_index}")
    refs.sort(key=lambda r: (r["question_id"], r["question_revision"]))
    rng.shuffle(refs)

    selected: list[dict[str, Any]] = []
    remaining = {axis: dict(values) for axis, values in targets.items()}
    required_micro = set(bp.micro_skill_coverage)
    required_prereq = set(bp.prerequisite_coverage)
    # Preserve seeded order within priority groups while putting rare mandatory
    # coverage evidence in front of otherwise interchangeable candidates.
    refs.sort(key=lambda r: -(
        len(required_micro.intersection(map(str, r["curriculum_mapping"].get("micro_skill_ids", []))))
        + len(required_prereq.intersection(map(str, r["curriculum_mapping"].get("prerequisite_ids", []))))
    ))

    def labels(ref: Mapping[str, Any]) -> tuple[str, str, str]:
        mapping = ref["curriculum_mapping"]
        return str(mapping.get("topic_id", "")), str(ref.get("difficulty", "")), str(ref["version_data"].get("question_type", ""))

    def search(pool: list[dict[str, Any]], chosen: list[dict[str, Any]], elapsed: float) -> bool:
        if len(chosen) == bp.question_count:
            found_micro = {str(x) for r in chosen for x in r["curriculum_mapping"].get("micro_skill_ids", [])}
            found_prereq = {str(x) for r in chosen for x in r["curriculum_mapping"].get("prerequisite_ids", [])}
            return (all(v == 0 for axis in remaining.values() for v in axis.values())
                    and required_micro.issubset(found_micro)
                    and required_prereq.issubset(found_prereq)
                    and elapsed <= bp.time_budget_minutes)
        if len(pool) < bp.question_count - len(chosen):
            return False
        slots = bp.question_count - len(chosen)
        durations = sorted(float(r["version_data"].get("estimated_minutes", 0)) for r in pool)
        if any(value < 0 for value in durations) or elapsed + sum(durations[:slots]) > bp.time_budget_minutes:
            return False
        covered_micro = {str(x) for r in chosen for x in r["curriculum_mapping"].get("micro_skill_ids", [])}
        covered_prereq = {str(x) for r in chosen for x in r["curriculum_mapping"].get("prerequisite_ids", [])}
        available_micro = covered_micro | {str(x) for r in pool for x in r["curriculum_mapping"].get("micro_skill_ids", [])}
        available_prereq = covered_prereq | {str(x) for r in pool for x in r["curriculum_mapping"].get("prerequisite_ids", [])}
        if not required_micro.issubset(available_micro) or not required_prereq.issubset(available_prereq):
            return False
        for index, ref in enumerate(pool):
            if any(existing["question_id"] == ref["question_id"] for existing in chosen):
                continue
            duration = float(ref["version_data"].get("estimated_minutes", 0))
            if duration < 0 or elapsed + duration > bp.time_budget_minutes:
                continue
            vals = labels(ref)
            axes = ("topic", "difficulty", "question_type")
            if any(vals[i] not in remaining[a] or remaining[a][vals[i]] <= 0 for i, a in enumerate(axes)):
                continue
            for i, axis in enumerate(axes): remaining[axis][vals[i]] -= 1
            chosen.append(ref)
            if search(pool[index + 1:], chosen, elapsed + duration): return True
            chosen.pop()
            for i, axis in enumerate(axes): remaining[axis][vals[i]] += 1
        return False

    if not search(refs, selected, 0.0):
        raise AssessmentCompilationError("question bank cannot satisfy allocations, coverage, uniqueness, and time budget")
    found_micro = {str(x) for r in selected for x in r["curriculum_mapping"].get("micro_skill_ids", [])}
    found_prereq = {str(x) for r in selected for x in r["curriculum_mapping"].get("prerequisite_ids", [])}
    if not required_micro.issubset(found_micro):
        raise AssessmentCompilationError(f"missing micro-skill coverage: {sorted(required_micro - found_micro)}")
    if not required_prereq.issubset(found_prereq):
        raise AssessmentCompilationError(f"missing prerequisite coverage: {sorted(required_prereq - found_prereq)}")
    total_time = sum(float(r["version_data"].get("estimated_minutes", 0)) for r in selected)
    if total_time > bp.time_budget_minutes:
        raise AssessmentCompilationError("selected questions exceed time budget")
    digest = hashlib.sha256(f"{bp.blueprint_id}:{seed}:{variant_index}".encode()).hexdigest()[:16]
    assessment_id = f"assessment-{digest}"
    enriched = tuple({**r, "assessment_identity": assessment_id,
                      "assessment_role": str(bp.variant_policy.get("assessment_role", "ASSESSMENT"))} for r in selected)
    return CompiledAssessment(assessment_id, bp.blueprint_id, seed, variant_index, enriched,
                              total_time, targets, dict(bp.scoring_rules), tuple(dict(x) for x in bp.rubrics),
                              dict(bp.variant_policy))
