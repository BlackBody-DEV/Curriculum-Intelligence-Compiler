"""Versioned, student-data-free contracts for the universal curriculum compiler."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from enum import Enum
import json
from typing import Any, ClassVar, Mapping


FORBIDDEN_PERFORMANCE_FIELDS = frozenset({
    "student_id", "student_attempt", "student_score", "mastery", "progress",
    "performance_history", "adaptive_assignment",
})


class ContractError(ValueError):
    """Raised when a public contract is structurally or semantically invalid."""


class ReviewStatus(str, Enum):
    PROPOSED = "PROPOSED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class HierarchyLevel(str, Enum):
    DOMAIN = "DOMAIN"
    SUBJECT = "SUBJECT"
    COURSE = "COURSE"
    UNIT = "UNIT"
    TOPIC = "TOPIC"
    SUBTOPIC = "SUBTOPIC"
    MICRO_SKILL = "MICRO_SKILL"
    PROCEDURE = "PROCEDURE"
    GENERATION_FAMILY = "GENERATION_FAMILY"
    QUESTION = "QUESTION"
    ASSESSMENT = "ASSESSMENT"


class MappingStatus(str, Enum):
    PROPOSED = "PROPOSED"
    REVIEWED = "REVIEWED"
    REJECTED = "REJECTED"


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SupportStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"


def _reject_performance_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        prohibited = FORBIDDEN_PERFORMANCE_FIELDS.intersection(value)
        if prohibited:
            raise ContractError(f"forbidden student-performance field at {path}: {sorted(prohibited)[0]}")
        for key, child in value.items():
            _reject_performance_fields(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_performance_fields(child, f"{path}[{index}]")


def _require_identity(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} is required")


def _primitive(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, ContractV1):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_primitive(item) for item in value]
    if isinstance(value, list):
        return [_primitive(item) for item in value]
    if isinstance(value, dict):
        return {key: _primitive(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class ContractV1:
    """Strict JSON contract base with stable, compact serialization."""

    CONTRACT_VERSION: ClassVar[str] = "1.0"

    def __post_init__(self) -> None:
        if getattr(self, "version", None) != self.CONTRACT_VERSION:
            raise ContractError(f"version must be exactly {self.CONTRACT_VERSION}")
        review_status = getattr(self, "review_status", None)
        if review_status is None:
            raise ContractError(f"{type(self).__name__} must include review_status")
        try:
            ReviewStatus(review_status)
        except ValueError as exc:
            raise ContractError(f"unsupported review status: {review_status}") from exc
        if type(self).__name__ != "SourceEvidenceV1" and hasattr(self, "source_evidence"):
            evidence_items = getattr(self, "source_evidence")
            if not isinstance(evidence_items, (tuple, list)):
                raise ContractError("source_evidence must be an array")
            for evidence in evidence_items:
                if isinstance(evidence, SourceEvidenceV1):
                    continue
                SourceEvidenceV1.from_dict(evidence)
        _reject_performance_fields(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        result = {item.name: _primitive(getattr(self, item.name)) for item in fields(self)}
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]):
        if not isinstance(payload, Mapping):
            raise ContractError(f"{cls.__name__} requires an object")
        _reject_performance_fields(payload)
        allowed = {item.name for item in fields(cls)}
        unknown = set(payload) - allowed
        if unknown:
            raise ContractError(f"unknown fields for {cls.__name__}: {sorted(unknown)}")
        return cls(**dict(payload))

    @classmethod
    def from_json(cls, payload: str):
        return cls.from_dict(json.loads(payload))


@dataclass(frozen=True)
class SourceEvidenceV1(ContractV1):
    evidence_id: str
    source_type: str
    source_identity: str
    source_hash: str
    locator: str = ""
    excerpt: str = ""
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"

    def __post_init__(self) -> None:
        for name in ("evidence_id", "source_type", "source_identity", "source_hash"):
            _require_identity(getattr(self, name), name)
        super().__post_init__()


@dataclass(frozen=True)
class CurriculumNodeV1(ContractV1):
    node_id: str
    level: str
    title: str
    source_evidence: tuple[dict[str, Any], ...] = ()
    review_status: str = ReviewStatus.PROPOSED.value
    description: str = ""
    version: str = "1.0"

    def __post_init__(self) -> None:
        _require_identity(self.node_id, "node_id")
        _require_identity(self.title, "title")
        try: HierarchyLevel(self.level)
        except ValueError as exc: raise ContractError(f"unsupported hierarchy level: {self.level}") from exc
        try: ReviewStatus(self.review_status)
        except ValueError as exc: raise ContractError(f"unsupported review status: {self.review_status}") from exc
        super().__post_init__()


@dataclass(frozen=True)
class CurriculumRelationshipV1(ContractV1):
    relationship_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    source_evidence: tuple[dict[str, Any], ...] = ()
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"

    def __post_init__(self) -> None:
        for name in ("relationship_id", "source_node_id", "target_node_id"):
            _require_identity(getattr(self, name), name)
        if self.source_node_id == self.target_node_id:
            raise ContractError("relationship endpoints must differ")
        if self.relationship_type not in {"CONTAINS", "PREREQUISITE", "ALIGNS_TO", "IMPLEMENTS"}:
            raise ContractError(f"unsupported relationship type: {self.relationship_type}")
        try: ReviewStatus(self.review_status)
        except ValueError as exc: raise ContractError(f"unsupported review status: {self.review_status}") from exc
        super().__post_init__()


@dataclass(frozen=True)
class CanonicalMappingCandidateV1(ContractV1):
    candidate_id: str
    curriculum_node_id: str
    proposed_canonical_identity: str
    source_evidence: tuple[dict[str, Any], ...]
    review_status: str = ReviewStatus.PROPOSED.value
    mapping_status: str = MappingStatus.PROPOSED.value
    canonical_authority: bool = False
    version: str = "1.0"

    def __post_init__(self) -> None:
        for name in ("candidate_id", "curriculum_node_id", "proposed_canonical_identity"):
            _require_identity(getattr(self, name), name)
        if self.canonical_authority:
            raise ContractError("mapping candidates cannot grant canonical authority")
        try: MappingStatus(self.mapping_status); ReviewStatus(self.review_status)
        except ValueError as exc: raise ContractError("unsupported mapping or review status") from exc
        super().__post_init__()


@dataclass(frozen=True)
class ProcedureDescriptorV1(ContractV1):
    procedure_id: str
    title: str
    steps: tuple[str, ...]
    source_evidence: tuple[dict[str, Any], ...] = ()
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"
    def __post_init__(self):
        _require_identity(self.procedure_id, "procedure_id"); _require_identity(self.title, "title")
        if not self.steps or any(not str(step).strip() for step in self.steps): raise ContractError("steps are required")
        super().__post_init__()


@dataclass(frozen=True)
class GenerationFamilyDescriptorV1(ContractV1):
    family_id: str
    procedure_id: str
    answer_contract_id: str
    failure_signal_ids: tuple[str, ...] = ()
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"
    def __post_init__(self):
        for name in ("family_id", "procedure_id", "answer_contract_id"): _require_identity(getattr(self, name), name)
        super().__post_init__()


@dataclass(frozen=True)
class AnswerContractV1(ContractV1):
    answer_contract_id: str
    engine_type: str
    grading_contract: dict[str, Any]
    normalization_contract: dict[str, Any] = field(default_factory=dict)
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"
    def __post_init__(self):
        _require_identity(self.answer_contract_id, "answer_contract_id"); _require_identity(self.engine_type, "engine_type")
        super().__post_init__()


@dataclass(frozen=True)
class FailureSignalDescriptorV1(ContractV1):
    failure_signal_id: str
    code: str
    description: str
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"
    def __post_init__(self):
        for name in ("failure_signal_id", "code", "description"): _require_identity(getattr(self, name), name)
        super().__post_init__()


@dataclass(frozen=True)
class AssetPolicyV1(ContractV1):
    policy_id: str
    requirement: str
    allowed_media_types: tuple[str, ...] = ()
    rights_evidence_required: bool = True
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"
    def __post_init__(self):
        _require_identity(self.policy_id, "policy_id")
        if self.requirement not in {"REQUIRED", "OPTIONAL", "NOT_APPLICABLE"}: raise ContractError("unsupported asset requirement")
        super().__post_init__()


@dataclass(frozen=True)
class SubjectPackDescriptorV1(ContractV1):
    subject_pack_id: str
    subject: str
    pack_version: str
    supported_answer_engines: tuple[str, ...]
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"
    def __post_init__(self):
        for name in ("subject_pack_id", "subject", "pack_version"): _require_identity(getattr(self, name), name)
        super().__post_init__()


@dataclass(frozen=True)
class UniversalCurriculumPackageV1(ContractV1):
    package_id: str
    nodes: tuple[dict[str, Any], ...]
    relationships: tuple[dict[str, Any], ...]
    source_evidence: tuple[dict[str, Any], ...]
    canonical_mapping_candidates: tuple[dict[str, Any], ...] = ()
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"
    def __post_init__(self):
        _require_identity(self.package_id, "package_id")
        for node in self.nodes:
            if not isinstance(node, CurriculumNodeV1): CurriculumNodeV1.from_dict(node)
        for relationship in self.relationships:
            if not isinstance(relationship, CurriculumRelationshipV1): CurriculumRelationshipV1.from_dict(relationship)
        for mapping in self.canonical_mapping_candidates:
            if not isinstance(mapping, CanonicalMappingCandidateV1): CanonicalMappingCandidateV1.from_dict(mapping)
        node_ids = {node.get("node_id") for node in self.nodes}
        if None in node_ids or len(node_ids) != len(self.nodes): raise ContractError("node identities must be present and unique")
        for rel in self.relationships:
            if rel.get("source_node_id") not in node_ids or rel.get("target_node_id") not in node_ids: raise ContractError("relationship endpoint is not in package")
        super().__post_init__()


@dataclass(frozen=True)
class GenerationManifestV1(ContractV1):
    manifest_id: str
    package_id: str
    generation_family_ids: tuple[str, ...]
    requested_count: int
    seed: str
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"
    def __post_init__(self):
        for name in ("manifest_id", "package_id", "seed"): _require_identity(getattr(self, name), name)
        if self.requested_count < 1: raise ContractError("requested_count must be positive")
        super().__post_init__()


@dataclass(frozen=True)
class AssessmentBlueprintV1(ContractV1):
    blueprint_id: str
    course_node_id: str
    question_count: int
    topic_weights: dict[str, float]
    difficulty_distribution: dict[str, float]
    question_type_distribution: dict[str, float]
    time_budget_minutes: int
    unit_scope: tuple[str, ...] = ()
    micro_skill_coverage: tuple[str, ...] = ()
    prerequisite_coverage: tuple[str, ...] = ()
    reuse_policy: dict[str, Any] = field(default_factory=dict)
    variant_policy: dict[str, Any] = field(default_factory=dict)
    scoring_rules: dict[str, Any] = field(default_factory=dict)
    rubrics: tuple[dict[str, Any], ...] = ()
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"
    def __post_init__(self):
        for name in ("blueprint_id", "course_node_id"): _require_identity(getattr(self, name), name)
        if self.question_count < 1 or self.time_budget_minutes < 1: raise ContractError("counts and time budget must be positive")
        super().__post_init__()


@dataclass(frozen=True)
class ValidatedQuestionReferenceV1(ContractV1):
    question_id: str
    question_revision: str
    procedure_id: str
    generation_family_id: str
    answer_contract_id: str
    validation_result_id: str
    source_evidence: tuple[dict[str, Any], ...] = ()
    curriculum_mapping: dict[str, Any] = field(default_factory=dict)
    proposed_canonical_mapping_status: str = MappingStatus.PROPOSED.value
    difficulty: str = ""
    grading_contract: dict[str, Any] = field(default_factory=dict)
    failure_signals: tuple[dict[str, Any], ...] = ()
    assessment_identity: str = ""
    assessment_role: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    asset_references: tuple[dict[str, Any], ...] = ()
    version_data: dict[str, Any] = field(default_factory=dict)
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"
    def __post_init__(self):
        for item in fields(self):
            if item.name.endswith("_id") or item.name == "question_revision": _require_identity(getattr(self, item.name), item.name)
        try: MappingStatus(self.proposed_canonical_mapping_status)
        except ValueError as exc: raise ContractError("unsupported proposed canonical mapping status") from exc
        super().__post_init__()


@dataclass(frozen=True)
class BetaExportPackageV1(ContractV1):
    export_id: str
    curriculum_package_id: str
    question_references: tuple[dict[str, Any], ...]
    assessment_blueprints: tuple[dict[str, Any], ...] = ()
    proposed_canonical_mappings: tuple[dict[str, Any], ...] = ()
    source_evidence: tuple[dict[str, Any], ...] = ()
    canonical_authority: bool = False
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"
    def __post_init__(self):
        for name in ("export_id", "curriculum_package_id"): _require_identity(getattr(self, name), name)
        if self.canonical_authority: raise ContractError("Beta exports cannot grant canonical authority")
        for question in self.question_references:
            if not isinstance(question, ValidatedQuestionReferenceV1): ValidatedQuestionReferenceV1.from_dict(question)
        for blueprint in self.assessment_blueprints:
            if not isinstance(blueprint, AssessmentBlueprintV1): AssessmentBlueprintV1.from_dict(blueprint)
        for mapping in self.proposed_canonical_mappings:
            if not isinstance(mapping, CanonicalMappingCandidateV1): CanonicalMappingCandidateV1.from_dict(mapping)
        super().__post_init__()


@dataclass(frozen=True)
class ValidationResultV1(ContractV1):
    validation_result_id: str
    subject_identity: str
    status: str
    validator: str
    reasons: tuple[str, ...] = ()
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"
    def __post_init__(self):
        for name in ("validation_result_id", "subject_identity", "validator"): _require_identity(getattr(self, name), name)
        try: ValidationStatus(self.status)
        except ValueError as exc: raise ContractError(f"unsupported validation status: {self.status}") from exc
        super().__post_init__()


@dataclass(frozen=True)
class SupportDecisionV1(ContractV1):
    decision_id: str
    contract_identity: str
    status: str
    reason: str
    engine_type: str = ""
    review_status: str = ReviewStatus.PROPOSED.value
    version: str = "1.0"
    def __post_init__(self):
        for name in ("decision_id", "contract_identity", "reason"): _require_identity(getattr(self, name), name)
        try: SupportStatus(self.status)
        except ValueError as exc: raise ContractError(f"unsupported support status: {self.status}") from exc
        super().__post_init__()
