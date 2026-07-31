"""Compile proposed, evidence-backed assessment blueprints without generating questions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Mapping

from tools.course_compiler_demo.source_corpus.contracts import ContractError, StrictV1
from tools.course_compiler_demo.universal_core import AssessmentBlueprintV1


class BlueprintType(str, Enum):
    PRACTICE = "PRACTICE"
    DIAGNOSTIC = "DIAGNOSTIC"
    FORMATIVE = "FORMATIVE"
    SUMMATIVE = "SUMMATIVE"


def _text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} is required")


def _texts(value: object, name: str) -> None:
    if (
        not isinstance(value, tuple)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
        or len(value) != len(set(value))
    ):
        raise ContractError(f"{name} must contain unique, nonempty identities")


def _mapping(value: object, name: str) -> None:
    if (
        not isinstance(value, dict)
        or not value
        or any(not isinstance(key, str) or not key.strip() for key in value)
    ):
        raise ContractError(f"{name} must be a nonempty string-keyed mapping")


def _distribution(value: object, name: str) -> None:
    _mapping(value, name)
    assert isinstance(value, dict)
    if any(
        type(weight) not in {int, float}
        or not math.isfinite(weight)
        or weight < 0
        for weight in value.values()
    ) or not math.isclose(sum(value.values()), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ContractError(
            f"{name} must be a finite nonnegative distribution summing to one"
        )


def _positive_number(value: object, name: str) -> None:
    if type(value) not in {int, float} or not math.isfinite(value) or value <= 0:
        raise ContractError(f"{name} must be a finite positive number")


@dataclass(frozen=True)
class SourceAssessmentBlueprintV1(StrictV1):
    blueprint_id: str
    blueprint_type: str
    course_id: str
    question_count: int
    time_budget_minutes: int
    topic_weights: dict[str, float]
    difficulty_distribution: dict[str, float]
    question_type_distribution: dict[str, float]
    unit_scope: tuple[str, ...]
    micro_skill_coverage: tuple[str, ...]
    prerequisite_coverage: tuple[str, ...]
    evidence_claim_ids: tuple[str, ...]
    course_outcome_ids: tuple[str, ...]
    assessment_objective_ids: tuple[str, ...]
    generation_family_ids: tuple[str, ...]
    grading_engine_ids: tuple[str, ...]
    source_example_ids: tuple[str, ...]
    course_pack_policy_ids: tuple[str, ...]
    reuse_policy: dict[str, Any]
    variant_policy: dict[str, Any]
    scoring_rules: dict[str, Any]
    rubrics: tuple[dict[str, Any], ...]
    review_state: str = "PROPOSED"
    canonical_authority: bool = False
    version: str = "1.0"

    def __post_init__(self) -> None:
        for name in ("blueprint_id", "course_id"):
            _text(getattr(self, name), name)
        try:
            BlueprintType(self.blueprint_type)
        except (TypeError, ValueError) as exc:
            raise ContractError("unsupported blueprint type") from exc
        if (
            self.version != "1.0"
            or type(self.question_count) is not int
            or self.question_count < 1
            or type(self.time_budget_minutes) is not int
            or self.time_budget_minutes < 1
        ):
            raise ContractError("invalid blueprint version, count, or time budget")
        for value, name in (
            (self.topic_weights, "topic_weights"),
            (self.difficulty_distribution, "difficulty_distribution"),
            (self.question_type_distribution, "question_type_distribution"),
        ):
            _distribution(value, name)
        for name in (
            "unit_scope",
            "micro_skill_coverage",
            "prerequisite_coverage",
            "evidence_claim_ids",
            "course_outcome_ids",
            "assessment_objective_ids",
            "generation_family_ids",
            "grading_engine_ids",
            "source_example_ids",
            "course_pack_policy_ids",
        ):
            _texts(getattr(self, name), name)
        for name in ("reuse_policy", "variant_policy", "scoring_rules"):
            _mapping(getattr(self, name), name)
        if type(self.reuse_policy.get("allow_reuse")) is not bool:
            raise ContractError("reuse_policy.allow_reuse must be boolean")
        variant_count = self.variant_policy.get("variant_count")
        if type(variant_count) is not int or variant_count < 1:
            raise ContractError("variant_policy.variant_count must be a positive integer")
        _positive_number(
            self.scoring_rules.get("points_per_question"),
            "scoring_rules.points_per_question",
        )
        if (
            not isinstance(self.rubrics, tuple)
            or not self.rubrics
            or any(not isinstance(rubric, dict) or not rubric for rubric in self.rubrics)
        ):
            raise ContractError("rubrics must contain nonempty mappings")
        rubric_ids = [rubric.get("rubric_id") for rubric in self.rubrics]
        if any(not isinstance(item, str) or not item.strip() for item in rubric_ids) or len(
            rubric_ids
        ) != len(set(rubric_ids)):
            raise ContractError("rubric identities must be present and unique")
        minimum_required_questions = max(
            len(self.micro_skill_coverage),
            *(
                sum(weight > 0 for weight in distribution.values())
                for distribution in (
                    self.topic_weights,
                    self.difficulty_distribution,
                    self.question_type_distribution,
                )
            ),
        )
        if self.question_count < minimum_required_questions:
            raise ContractError("question count cannot satisfy declared coverage")
        if self.review_state != "PROPOSED" or self.canonical_authority is not False:
            raise ContractError("blueprint must remain proposed and noncanonical")
        super().__post_init__()


@dataclass(frozen=True)
class SourceAssessmentBlueprintPackageV1(StrictV1):
    package_id: str
    course_id: str
    blueprints: tuple[SourceAssessmentBlueprintV1, ...]
    review_state: str = "PROPOSED"
    canonical_authority: bool = False
    version: str = "1.0"

    def __post_init__(self) -> None:
        _text(self.package_id, "package_id")
        _text(self.course_id, "course_id")
        if (
            not isinstance(self.blueprints, tuple)
            or any(not isinstance(item, SourceAssessmentBlueprintV1) for item in self.blueprints)
        ):
            raise ContractError("package blueprints must be typed contracts")
        identities = [item.blueprint_id for item in self.blueprints]
        blueprint_types = [item.blueprint_type for item in self.blueprints]
        if len(identities) != len(set(identities)):
            raise ContractError("duplicate blueprint identity")
        if set(blueprint_types) != {item.value for item in BlueprintType} or len(
            blueprint_types
        ) != len(BlueprintType):
            raise ContractError("package requires exactly one blueprint of each supported type")
        if any(item.course_id != self.course_id for item in self.blueprints):
            raise ContractError("blueprint package contains a course mismatch")
        if (
            self.review_state != "PROPOSED"
            or self.canonical_authority is not False
            or self.version != "1.0"
        ):
            raise ContractError("blueprint package must remain proposed and noncanonical")
        super().__post_init__()


def _owned_ids(
    identifiers: tuple[str, ...],
    owners: Mapping[str, str],
    course_id: str,
    missing_error: str,
    foreign_error: str,
    errors: list[str],
) -> None:
    if not isinstance(owners, Mapping):
        errors.append(missing_error)
        return
    if any(identifier not in owners for identifier in identifiers):
        errors.append(missing_error)
    if any(
        identifier in owners and owners.get(identifier) != course_id
        for identifier in identifiers
    ):
        errors.append(foreign_error)


def validate_blueprint_blocking(
    blueprint: SourceAssessmentBlueprintV1,
    *,
    course_id: str,
    unit_courses: Mapping[str, str],
    topic_courses: Mapping[str, str],
    micro_skill_courses: Mapping[str, str],
    prerequisite_courses: Mapping[str, str],
    evidence_claim_courses: Mapping[str, str],
    course_outcome_courses: Mapping[str, str],
    assessment_objective_courses: Mapping[str, str],
    generation_family_courses: Mapping[str, str],
    grading_engine_courses: Mapping[str, str],
    source_example_courses: Mapping[str, str],
    course_pack_policy_courses: Mapping[str, str],
    required_topic_ids: tuple[str, ...],
    required_micro_skill_ids: tuple[str, ...],
    required_course_outcome_ids: tuple[str, ...],
    required_assessment_objective_ids: tuple[str, ...],
    minimum_minutes_per_question: float = 1.0,
    blocking_conflicts: tuple[str, ...] = (),
    coverage_gaps: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Validate source resolution, ownership, coverage, and feasibility fail closed."""
    if not isinstance(blueprint, SourceAssessmentBlueprintV1):
        raise ContractError("blueprint must be a typed source assessment blueprint")
    errors: list[str] = []
    if blueprint.course_id != course_id:
        errors.append("COURSE_MISMATCH")
    ownership_checks = (
        (blueprint.unit_scope, unit_courses, "UNKNOWN_UNIT", "CROSS_COURSE_UNIT"),
        (tuple(blueprint.topic_weights), topic_courses, "UNKNOWN_TOPIC", "CROSS_COURSE_TOPIC"),
        (blueprint.micro_skill_coverage, micro_skill_courses, "UNKNOWN_MICRO_SKILL", "CROSS_COURSE_MICRO_SKILL"),
        (blueprint.prerequisite_coverage, prerequisite_courses, "UNKNOWN_PREREQUISITE", "CROSS_COURSE_PREREQUISITE"),
        (blueprint.evidence_claim_ids, evidence_claim_courses, "UNRESOLVED_EVIDENCE", "CROSS_COURSE_EVIDENCE"),
        (blueprint.course_outcome_ids, course_outcome_courses, "UNSUPPORTED_COURSE_OUTCOME", "CROSS_COURSE_OUTCOME"),
        (blueprint.assessment_objective_ids, assessment_objective_courses, "UNSUPPORTED_OBJECTIVE", "CROSS_COURSE_OBJECTIVE"),
        (blueprint.generation_family_ids, generation_family_courses, "MISSING_GENERATION_FAMILY", "CROSS_COURSE_GENERATION_FAMILY"),
        (blueprint.grading_engine_ids, grading_engine_courses, "MISSING_GRADING_ENGINE", "CROSS_COURSE_GRADING_ENGINE"),
        (blueprint.source_example_ids, source_example_courses, "MISSING_SOURCE_EXAMPLE", "CROSS_COURSE_SOURCE_EXAMPLE"),
        (blueprint.course_pack_policy_ids, course_pack_policy_courses, "MISSING_COURSE_PACK_POLICY", "CROSS_COURSE_POLICY"),
    )
    for identifiers, owners, missing, foreign in ownership_checks:
        _owned_ids(identifiers, owners, course_id, missing, foreign, errors)
    if set(blueprint.topic_weights) != set(required_topic_ids):
        errors.append("TOPIC_DISTRIBUTION_INCOMPLETE")
    if not set(required_micro_skill_ids) <= set(blueprint.micro_skill_coverage):
        errors.append("MICRO_SKILL_COVERAGE_INSUFFICIENT")
    if set(blueprint.course_outcome_ids) != set(required_course_outcome_ids):
        errors.append("COURSE_OUTCOME_COVERAGE_INSUFFICIENT")
    if set(blueprint.assessment_objective_ids) != set(required_assessment_objective_ids):
        errors.append("ASSESSMENT_OBJECTIVE_COVERAGE_INSUFFICIENT")
    if (
        type(minimum_minutes_per_question) not in {int, float}
        or not math.isfinite(minimum_minutes_per_question)
        or minimum_minutes_per_question <= 0
        or blueprint.time_budget_minutes
        < blueprint.question_count * minimum_minutes_per_question
    ):
        errors.append("IMPOSSIBLE_TIME_BUDGET")
    if blocking_conflicts:
        errors.append("SOURCE_CONFLICT_BLOCKED")
    if coverage_gaps:
        errors.append("SOURCE_COVERAGE_GAP_BLOCKED")
    if errors:
        raise ContractError(";".join(sorted(set(errors))))
    return {
        "blueprint_id": blueprint.blueprint_id,
        "blueprint_type": blueprint.blueprint_type,
        "valid": True,
        "blocking_errors": [],
        "canonical_authority": False,
    }


def compile_assessment_blueprints(
    *,
    package_id: str,
    course_id: str,
    declarations: tuple[dict[str, Any], ...],
    validation_context: Mapping[str, Any],
) -> SourceAssessmentBlueprintPackageV1:
    """Compile four source declarations into a deterministic review package."""
    if not isinstance(declarations, tuple):
        raise ContractError("blueprint declarations must be a tuple")
    if not isinstance(validation_context, Mapping):
        raise ContractError("validation_context must be a mapping")
    try:
        blueprints = tuple(SourceAssessmentBlueprintV1(**item) for item in declarations)
    except (TypeError, ContractError) as exc:
        raise ContractError(f"invalid source assessment blueprint: {exc}") from exc
    for blueprint in blueprints:
        try:
            validate_blueprint_blocking(
                blueprint,
                course_id=course_id,
                **dict(validation_context),
            )
        except (TypeError, ContractError) as exc:
            raise ContractError(
                f"blueprint {blueprint.blueprint_id} failed validation: {exc}"
            ) from exc
    ordered = tuple(sorted(blueprints, key=lambda item: item.blueprint_id))
    return SourceAssessmentBlueprintPackageV1(package_id, course_id, ordered)


def to_universal_blueprint(
    blueprint: SourceAssessmentBlueprintV1,
) -> AssessmentBlueprintV1:
    """Project a validated source blueprint into the existing proposed contract."""
    return AssessmentBlueprintV1(
        blueprint.blueprint_id,
        blueprint.course_id,
        blueprint.question_count,
        dict(blueprint.topic_weights),
        dict(blueprint.difficulty_distribution),
        dict(blueprint.question_type_distribution),
        blueprint.time_budget_minutes,
        blueprint.unit_scope,
        blueprint.micro_skill_coverage,
        blueprint.prerequisite_coverage,
        dict(blueprint.reuse_policy),
        dict(blueprint.variant_policy),
        dict(blueprint.scoring_rules),
        blueprint.rubrics,
        "PROPOSED",
        "1.0",
    )
