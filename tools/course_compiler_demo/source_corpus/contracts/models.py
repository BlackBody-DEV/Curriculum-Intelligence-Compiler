"""Strict, deterministic contracts for evidence-backed curriculum synthesis."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
import re
from typing import Any, Mapping


class ContractError(ValueError):
    pass


class SourceType(str, Enum):
    TEXT_NATIVE_PDF = "TEXT_NATIVE_PDF"
    PLAIN_TEXT = "PLAIN_TEXT"
    SYLLABUS = "SYLLABUS"
    STANDARDS_DOCUMENT = "STANDARDS_DOCUMENT"
    TEXTBOOK_OR_CHAPTER = "TEXTBOOK_OR_CHAPTER"
    QUESTION_BANK = "QUESTION_BANK"
    COURSE_DEFINITION_PACKAGE = "COURSE_DEFINITION_PACKAGE"
    STRUCTURED_JSON = "STRUCTURED_JSON"
    STRUCTURED_CSV = "STRUCTURED_CSV"


class EvidenceBoundary(str, Enum):
    DIRECT_SOURCE_EVIDENCE = "DIRECT_SOURCE_EVIDENCE"
    MULTI_SOURCE_SYNTHESIS = "MULTI_SOURCE_SYNTHESIS"
    INFERRED_PREREQUISITE = "INFERRED_PREREQUISITE"
    COURSE_PACK_REFERENCE = "COURSE_PACK_REFERENCE"
    UNSUPPORTED = "UNSUPPORTED"


FORBIDDEN_PERFORMANCE_FIELDS = frozenset({
    "student_id", "attempt", "score", "mastery", "progress",
    "performance_history", "adaptive_assignment", "student_analytics",
})


def reject_performance_fields(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        normalized = {re.sub(r"[^a-z0-9]+", "_", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(key)).lower()).strip("_"): key for key in value}
        bad = FORBIDDEN_PERFORMANCE_FIELDS.intersection(normalized)
        sensitive_tokens = {"student", "attempt", "score", "mastery", "progress", "performance", "adaptive", "analytics"}
        bad_tokens = {name for name in normalized if sensitive_tokens.intersection(name.split("_"))}
        bad = bad.union(bad_tokens)
        if bad:
            raise ContractError(f"forbidden performance field at {path}: {normalized[sorted(bad)[0]]}")
        for key, child in value.items():
            reject_performance_fields(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            reject_performance_fields(child, f"{path}[{index}]")


def _required(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{name} is required")


def _hash(value: str, name: str) -> None:
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ContractError(f"{name} must be a lowercase SHA-256")


@dataclass(frozen=True)
class StrictV1:
    def __post_init__(self) -> None:
        reject_performance_fields(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        def primitive(value: Any) -> Any:
            if isinstance(value, Enum): return value.value
            if hasattr(value, "to_dict"): return value.to_dict()
            if isinstance(value, (tuple, list)): return [primitive(v) for v in value]
            if isinstance(value, dict): return {k: primitive(v) for k, v in value.items()}
            return value
        return primitive(asdict(self))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class SourceLocationV1(StrictV1):
    locator_type: str
    locator: str
    page: int | None = None
    section: str = ""
    def __post_init__(self):
        _required(self.locator_type, "locator_type"); _required(self.locator, "locator")
        if self.page is not None and self.page < 1: raise ContractError("page must be positive")
        super().__post_init__()


@dataclass(frozen=True)
class SourceAssetReferenceV1(StrictV1):
    asset_id: str
    asset_sha256: str
    media_type: str
    role: str
    def __post_init__(self):
        _required(self.asset_id, "asset_id"); _hash(self.asset_sha256, "asset_sha256")
        _required(self.media_type, "media_type"); _required(self.role, "role"); super().__post_init__()


@dataclass(frozen=True)
class SourceRightsClassificationV1(StrictV1):
    classification: str
    evidence: str
    restrictions: tuple[str, ...] = ()
    verified: bool = False
    def __post_init__(self):
        if self.classification not in {"EXPLICIT_APPROVAL_EVIDENCE", "INTERNAL_FIXTURE", "PUBLIC_DOMAIN", "RESTRICTED", "UNKNOWN"}:
            raise ContractError("unsupported rights classification")
        _required(self.evidence, "evidence")
        if type(self.verified) is not bool: raise ContractError("verified must be boolean")
        super().__post_init__()


@dataclass(frozen=True)
class SourceSegmentV1(StrictV1):
    segment_id: str
    source_document_id: str
    source_hash: str
    text: str
    location: SourceLocationV1
    extraction_method: str
    confidence: float
    review_state: str
    rights_classification: SourceRightsClassificationV1
    assets: tuple[SourceAssetReferenceV1, ...] = ()
    def __post_init__(self):
        _required(self.segment_id, "segment_id"); _required(self.source_document_id, "source_document_id")
        _hash(self.source_hash, "source_hash"); _required(self.text, "text"); _required(self.extraction_method, "extraction_method")
        if not 0 <= self.confidence <= 1: raise ContractError("confidence must be between 0 and 1")
        _required(self.review_state, "review_state")
        if not isinstance(self.location, SourceLocationV1) or not isinstance(self.rights_classification, SourceRightsClassificationV1):
            raise ContractError("segment location and rights must be typed contracts")
        if any(not isinstance(asset, SourceAssetReferenceV1) for asset in self.assets): raise ContractError("invalid segment asset")
        super().__post_init__()


@dataclass(frozen=True)
class SourceDocumentV1(StrictV1):
    document_id: str
    source_type: str
    source_hash: str
    title: str
    rights_classification: SourceRightsClassificationV1
    segments: tuple[SourceSegmentV1, ...] = ()
    assets: tuple[SourceAssetReferenceV1, ...] = ()
    def __post_init__(self):
        _required(self.document_id, "document_id")
        try:
            SourceType(self.source_type)
        except ValueError as exc:
            raise ContractError(f"unsupported source type: {self.source_type}") from exc
        _hash(self.source_hash, "source_hash")
        _required(self.title, "title")
        if not isinstance(self.rights_classification, SourceRightsClassificationV1): raise ContractError("document rights must be a typed contract")
        if any(not isinstance(s, SourceSegmentV1) for s in self.segments): raise ContractError("invalid document segment")
        if any(not isinstance(asset, SourceAssetReferenceV1) for asset in self.assets): raise ContractError("invalid document asset")
        if any(s.source_document_id != self.document_id or s.source_hash != self.source_hash for s in self.segments):
            raise ContractError("segment provenance does not match document")
        super().__post_init__()


@dataclass(frozen=True)
class SourceCorpusV1(StrictV1):
    corpus_id: str
    documents: tuple[SourceDocumentV1, ...]
    manifest_sha256: str
    def __post_init__(self):
        _required(self.corpus_id, "corpus_id"); _hash(self.manifest_sha256, "manifest_sha256")
        if any(not isinstance(d, SourceDocumentV1) for d in self.documents): raise ContractError("invalid corpus document")
        ids = [d.document_id for d in self.documents]
        if len(ids) != len(set(ids)): raise ContractError("duplicate document identity")
        super().__post_init__()


@dataclass(frozen=True)
class SourceEvidenceClaimV1(StrictV1):
    claim_id: str
    document_id: str
    source_hash: str
    location: SourceLocationV1
    segment_id: str
    extraction_method: str
    confidence: float
    review_state: str
    rights_classification: SourceRightsClassificationV1
    claim_text: str
    def __post_init__(self):
        for name in ("claim_id", "document_id", "segment_id", "extraction_method", "review_state", "claim_text"): _required(getattr(self, name), name)
        _hash(self.source_hash, "source_hash")
        if not 0 <= self.confidence <= 1: raise ContractError("confidence must be between 0 and 1")
        if not isinstance(self.location, SourceLocationV1) or not isinstance(self.rights_classification, SourceRightsClassificationV1):
            raise ContractError("claim location and rights must be typed contracts")
        super().__post_init__()


@dataclass(frozen=True)
class SourceEvidenceLinkV1(StrictV1):
    link_id: str
    claim_id: str
    target_id: str
    relationship: str
    def __post_init__(self):
        for name in ("link_id", "claim_id", "target_id", "relationship"): _required(getattr(self, name), name)
        super().__post_init__()


@dataclass(frozen=True)
class SourceEvidenceGraphV1(StrictV1):
    graph_id: str
    corpus: SourceCorpusV1
    claims: tuple[SourceEvidenceClaimV1, ...]
    links: tuple[SourceEvidenceLinkV1, ...]
    def __post_init__(self):
        _required(self.graph_id, "graph_id")
        if not isinstance(self.corpus, SourceCorpusV1): raise ContractError("evidence graph requires typed corpus")
        if any(not isinstance(c, SourceEvidenceClaimV1) for c in self.claims) or any(not isinstance(link, SourceEvidenceLinkV1) for link in self.links):
            raise ContractError("invalid evidence graph member")
        claim_list = [c.claim_id for c in self.claims]
        link_list = [link.link_id for link in self.links]
        if len(claim_list) != len(set(claim_list)) or len(link_list) != len(set(link_list)): raise ContractError("duplicate evidence identity")
        claim_ids = {c.claim_id for c in self.claims}
        if any(link.claim_id not in claim_ids for link in self.links): raise ContractError("evidence link references missing claim")
        documents = {d.document_id: d for d in self.corpus.documents}
        for claim in self.claims:
            document = documents.get(claim.document_id)
            if document is None or document.source_hash != claim.source_hash: raise ContractError("claim source does not resolve in corpus")
            segment = next((s for s in document.segments if s.segment_id == claim.segment_id), None)
            if segment is None or segment.location != claim.location: raise ContractError("claim segment/location does not resolve in corpus")
        super().__post_init__()


@dataclass(frozen=True)
class ExtractedCurriculumCandidateV1(StrictV1):
    candidate_id: str
    candidate_type: str
    title: str
    evidence_claim_ids: tuple[str, ...]
    confidence: float
    review_state: str
    inference_boundary: str = EvidenceBoundary.DIRECT_SOURCE_EVIDENCE.value
    rationale: str = ""
    def __post_init__(self):
        for name in ("candidate_id", "candidate_type", "title", "review_state"): _required(getattr(self, name), name)
        boundary = EvidenceBoundary(self.inference_boundary)
        if boundary != EvidenceBoundary.UNSUPPORTED and not self.evidence_claim_ids: raise ContractError("supported candidate requires evidence")
        if boundary == EvidenceBoundary.INFERRED_PREREQUISITE and not self.rationale: raise ContractError("inference requires rationale")
        if not 0 <= self.confidence <= 1: raise ContractError("confidence must be between 0 and 1")
        super().__post_init__()


@dataclass(frozen=True)
class SynthesizedCurriculumNodeV1(StrictV1):
    node_id: str
    node_type: str
    title: str
    inference_boundary: str
    evidence_claim_ids: tuple[str, ...]
    rationale: str
    confidence: float
    review_required: bool = True
    def __post_init__(self):
        for name in ("node_id", "node_type", "title"): _required(getattr(self, name), name)
        boundary = EvidenceBoundary(self.inference_boundary)
        if boundary != EvidenceBoundary.UNSUPPORTED and not self.evidence_claim_ids: raise ContractError("curriculum node requires evidence")
        if boundary in {EvidenceBoundary.MULTI_SOURCE_SYNTHESIS, EvidenceBoundary.INFERRED_PREREQUISITE} and not self.rationale:
            raise ContractError("synthesis or inference requires rationale")
        if not 0 <= self.confidence <= 1: raise ContractError("confidence must be between 0 and 1")
        super().__post_init__()


@dataclass(frozen=True)
class CurriculumConflictV1(StrictV1):
    conflict_id: str
    conflict_class: str
    node_ids: tuple[str, ...]
    evidence_claim_ids: tuple[str, ...]
    resolution_state: str = "UNRESOLVED"
    def __post_init__(self):
        _required(self.conflict_id, "conflict_id"); _required(self.conflict_class, "conflict_class")
        if len(self.node_ids) < 2 or not self.evidence_claim_ids: raise ContractError("conflict requires nodes and evidence")
        super().__post_init__()


@dataclass(frozen=True)
class CurriculumCoverageGapV1(StrictV1):
    gap_id: str
    gap_type: str
    scope_id: str
    rationale: str
    evidence_claim_ids: tuple[str, ...] = ()
    def __post_init__(self):
        for name in ("gap_id", "gap_type", "scope_id", "rationale"): _required(getattr(self, name), name)
        super().__post_init__()


@dataclass(frozen=True)
class CurriculumSynthesisPackageV1(StrictV1):
    package_id: str
    course_id: str
    evidence_graph: SourceEvidenceGraphV1
    nodes: tuple[SynthesizedCurriculumNodeV1, ...]
    conflicts: tuple[CurriculumConflictV1, ...]
    coverage_gaps: tuple[CurriculumCoverageGapV1, ...]
    completeness: str
    canonical_authority: bool = False
    def __post_init__(self):
        _required(self.package_id, "package_id"); _required(self.course_id, "course_id")
        if not isinstance(self.evidence_graph, SourceEvidenceGraphV1): raise ContractError("synthesis requires typed evidence graph")
        if any(not isinstance(n, SynthesizedCurriculumNodeV1) for n in self.nodes): raise ContractError("invalid synthesis node")
        if any(not isinstance(c, CurriculumConflictV1) for c in self.conflicts): raise ContractError("invalid conflict")
        if any(not isinstance(g, CurriculumCoverageGapV1) for g in self.coverage_gaps): raise ContractError("invalid coverage gap")
        known_claims = {claim.claim_id for claim in self.evidence_graph.claims}
        referenced = [claim for node in self.nodes for claim in node.evidence_claim_ids]
        referenced += [claim for conflict in self.conflicts for claim in conflict.evidence_claim_ids]
        referenced += [claim for gap in self.coverage_gaps for claim in gap.evidence_claim_ids]
        if any(claim not in known_claims for claim in referenced): raise ContractError("synthesis evidence does not resolve")
        if self.completeness not in {"SOURCE_COMPLETE", "COURSE_PACK_COMPLETE", "SYNTHESIZED_WITH_GAPS", "INSUFFICIENT_EVIDENCE", "CONFLICT_BLOCKED"}:
            raise ContractError("unsupported completeness")
        if self.canonical_authority: raise ContractError("synthesis cannot grant canonical authority")
        super().__post_init__()


@dataclass(frozen=True)
class SourceProcessingDecisionV1(StrictV1):
    decision_id: str
    target_id: str
    action: str
    rationale: str
    reviewer: str
    canonical_authority: bool = False
    def __post_init__(self):
        for name in ("decision_id", "target_id", "action", "rationale", "reviewer"): _required(getattr(self, name), name)
        if self.canonical_authority: raise ContractError("review decision cannot grant canonical authority")
        super().__post_init__()
