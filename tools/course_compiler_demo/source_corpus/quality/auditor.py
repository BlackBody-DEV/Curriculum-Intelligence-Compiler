"""Fail-closed quality gates for proposed source curriculum packages."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import re
from typing import Any, Mapping


class ReviewAction(str, Enum):
    ACCEPT_SYNTHESIS_FOR_REVIEW = "ACCEPT_SYNTHESIS_FOR_REVIEW"
    RETURN_TO_EXTRACTION = "RETURN_TO_EXTRACTION"
    REJECT_SOURCE = "REJECT_SOURCE"
    ESCALATE_CONFLICT = "ESCALATE_CONFLICT"
    ESCALATE_RIGHTS = "ESCALATE_RIGHTS"
    ESCALATE_COVERAGE = "ESCALATE_COVERAGE"
    REQUEST_ADDITIONAL_SOURCE = "REQUEST_ADDITIONAL_SOURCE"


@dataclass(frozen=True)
class AuditFinding:
    gate: str
    target_id: str
    code: str
    detail: str


@dataclass(frozen=True)
class AuditReport:
    passed: bool
    action: ReviewAction
    findings: tuple[AuditFinding, ...]
    gates: tuple[str, ...]
    canonical_authority: bool = False


GATES = (
    "source-integrity", "evidence-completeness", "unsupported-inference",
    "hierarchy-consistency", "cross-course-contamination", "procedure-evidence",
    "mapping-evidence", "conflict-completeness", "coverage", "rights-provenance",
)


def _finding(items: list[AuditFinding], gate: str, target: str, code: str, detail: str) -> None:
    items.append(AuditFinding(gate, target or "UNKNOWN", code, detail))


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _rights_ok(rights: Mapping[str, Any]) -> bool:
    classification = rights.get("classification")
    if type(rights.get("verified", False)) is not bool:
        return False
    restrictions = rights.get("restrictions", ())
    if not isinstance(restrictions, (list, tuple)) or any(not isinstance(item, str) for item in restrictions):
        return False
    if classification in {"RESTRICTED", "UNKNOWN"} or not _text(rights.get("evidence")):
        return False
    if classification == "EXPLICIT_APPROVAL_EVIDENCE" and rights.get("verified") is not True:
        return False
    if restrictions:
        return False
    return classification in {"EXPLICIT_APPROVAL_EVIDENCE", "INTERNAL_FIXTURE", "PUBLIC_DOMAIN"}


def _authority_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key == "canonical_authority" and child is not None and child is not False:
                found.append(child_path)
            found.extend(_authority_paths(child, child_path))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value): found.extend(_authority_paths(child, f"{path}[{index}]") )
    return found


def audit_review_package(package: Mapping[str, Any]) -> AuditReport:
    """Audit a proposed package without assigning canonical authority."""
    findings: list[AuditFinding] = []
    sources_list = list(package.get("sources", ()))
    claims_list = list(package.get("evidence_claims", ()))
    nodes_list = list(package.get("nodes", ()))
    claims = {c.get("claim_id"): c for c in claims_list if c.get("claim_id")}
    sources = {s.get("document_id"): s for s in sources_list if s.get("document_id")}
    source_ids = set(sources)
    course_id = package.get("course_id", "")

    for authority_path in _authority_paths(package):
        _finding(findings, "mapping-evidence", authority_path, "CANONICAL_AUTHORITY_FORBIDDEN", "no nested record can grant canonical authority")

    if package.get("canonical_authority") is not None and package.get("canonical_authority") is not False:
        _finding(findings, "mapping-evidence", course_id, "CANONICAL_AUTHORITY_FORBIDDEN", "review package cannot grant canonical authority")
    mappings_list = list(package.get("mappings", ()))
    conflicts_list = list(package.get("conflicts", ()))
    gaps_list = list(package.get("coverage_gaps", ()))
    for values, label in ((sources_list, "SOURCE"), (claims_list, "CLAIM"), (nodes_list, "NODE"), (mappings_list, "MAPPING"), (conflicts_list, "CONFLICT"), (gaps_list, "GAP")):
        key = {"SOURCE":"document_id", "CLAIM":"claim_id", "NODE":"node_id", "MAPPING":"mapping_id", "CONFLICT":"conflict_id", "GAP":"gap_id"}[label]
        identities = [item.get(key) for item in values]
        if any(not _text(identity) for identity in identities) or len(identities) != len(set(identities)):
            _finding(findings, "source-integrity", course_id, f"DUPLICATE_OR_MISSING_{label}_IDENTITY", "identities must be present and unique")
    if not sources_list:
        _finding(findings, "coverage", course_id, "NO_SOURCE", "at least one source is required")
    if not nodes_list:
        _finding(findings, "coverage", course_id, "NO_CURRICULUM_NODES", "at least one evidence-backed node is required")
    if not mappings_list:
        _finding(findings, "mapping-evidence", course_id, "NO_PROPOSED_MAPPINGS", "at least one proposed mapping result is required")

    for source in package.get("sources", ()):
        target = source.get("document_id", "")
        if not _sha256(source.get("source_hash")) or not source.get("segments"):
            _finding(findings, "source-integrity", target, "SOURCE_INCOMPLETE", "source hash and segments are required")
        if source.get("canonical_authority") is not None and source.get("canonical_authority") is not False:
            _finding(findings, "source-integrity", target, "CANONICAL_AUTHORITY_FORBIDDEN", "source cannot grant canonical authority")
        rights = source.get("rights_classification", {})
        if not _rights_ok(rights):
            _finding(findings, "rights-provenance", target, "RIGHTS_INCOMPLETE", "rights classification and evidence are required")

    for claim_id, claim in claims.items():
        document = sources.get(claim.get("document_id"))
        segment = next((s for s in (document or {}).get("segments", ()) if s.get("segment_id") == claim.get("segment_id")), None)
        if document is None or not _sha256(claim.get("source_hash")) or claim.get("source_hash") != document.get("source_hash") or segment is None or not claim.get("location") or segment.get("location") != claim.get("location"):
            _finding(findings, "evidence-completeness", claim_id, "BROKEN_PROVENANCE", "claim must resolve to a source and location")
        rights = claim.get("rights_classification", {})
        if not _rights_ok(rights):
            _finding(findings, "rights-provenance", claim_id, "CLAIM_RIGHTS_INCOMPLETE", "claim rights and provenance are required")
        if document is not None and rights != document.get("rights_classification"):
            _finding(findings, "rights-provenance", claim_id, "CLAIM_RIGHTS_MISMATCH", "claim rights must match source rights")

    node_ids = {n.get("node_id") for n in nodes_list}
    for node in nodes_list:
        target = node.get("node_id", "")
        boundary = node.get("inference_boundary")
        evidence = node.get("evidence_claim_ids") or ()
        if not evidence or any(item not in claims for item in evidence):
            _finding(findings, "evidence-completeness", target, "SOURCE_FREE_NODE", "node evidence must resolve")
        if boundary == "UNSUPPORTED":
            _finding(findings, "unsupported-inference", target, "UNSUPPORTED_NODE", "unsupported nodes cannot pass review")
        if boundary not in {"DIRECT_SOURCE_EVIDENCE", "MULTI_SOURCE_SYNTHESIS", "INFERRED_PREREQUISITE", "COURSE_PACK_REFERENCE", "UNSUPPORTED"}:
            _finding(findings, "unsupported-inference", target, "UNKNOWN_INFERENCE_BOUNDARY", "inference boundary must be recognized")
        if node.get("canonical_authority") is not None and node.get("canonical_authority") is not False:
            _finding(findings, "mapping-evidence", target, "CANONICAL_AUTHORITY_FORBIDDEN", "node cannot grant canonical authority")
        confidence = node.get("confidence")
        if type(confidence) not in {int, float} or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            _finding(findings, "unsupported-inference", target, "MISSING_CONFIDENCE", "every node requires confidence")
        if boundary in {"MULTI_SOURCE_SYNTHESIS", "INFERRED_PREREQUISITE"} and (not node.get("rationale") or node.get("confidence") is None or not node.get("review_required")):
            _finding(findings, "unsupported-inference", target, "UNSUPPORTED_INFERENCE", "inference requires rationale, confidence, and review")
        parent = node.get("parent_id")
        if parent and parent not in node_ids:
            _finding(findings, "hierarchy-consistency", target, "MISSING_PARENT", "parent must exist in package")
        if node.get("course_id", course_id) != course_id:
            _finding(findings, "cross-course-contamination", target, "COURSE_MISMATCH", "node belongs to another course")
        if node.get("node_type") == "PROCEDURE" and not evidence:
            _finding(findings, "procedure-evidence", target, "SOURCE_FREE_PROCEDURE", "procedure requires evidence")

    unresolved_conflicts = {c.get("conflict_id") for c in package.get("conflicts", ()) if c.get("resolution_state") in {None, "UNRESOLVED"}}
    declared = set(package.get("declared_conflict_ids", ()))
    if declared - {c.get("conflict_id") for c in package.get("conflicts", ())}:
        _finding(findings, "conflict-completeness", course_id, "MISSING_CONFLICT", "declared conflict was silently removed")

    for mapping in mappings_list:
        target = mapping.get("mapping_id", "")
        if not mapping.get("evidence_claim_ids") or any(c not in claims for c in mapping.get("evidence_claim_ids", ())):
            _finding(findings, "mapping-evidence", target, "SOURCE_FREE_MAPPING", "mapping evidence must resolve")
        if mapping.get("course_id", course_id) != course_id or mapping.get("canonical_authority"):
            _finding(findings, "cross-course-contamination", target, "UNSAFE_MAPPING", "mapping crosses course or grants authority")

    for gap in package.get("coverage_gaps", ()):
        if not gap.get("gap_id") or not gap.get("rationale"):
            _finding(findings, "coverage", gap.get("gap_id", ""), "INVALID_GAP", "coverage gaps require identity and rationale")

    codes = {f.code for f in findings}
    if {"RIGHTS_INCOMPLETE", "CLAIM_RIGHTS_INCOMPLETE"}.intersection(codes): action = ReviewAction.ESCALATE_RIGHTS
    elif unresolved_conflicts or "MISSING_CONFLICT" in codes: action = ReviewAction.ESCALATE_CONFLICT
    elif "NO_SOURCE" in codes: action = ReviewAction.REQUEST_ADDITIONAL_SOURCE
    elif "SOURCE_INCOMPLETE" in codes: action = ReviewAction.REJECT_SOURCE
    elif any(f.gate == "coverage" for f in findings): action = ReviewAction.ESCALATE_COVERAGE
    elif findings: action = ReviewAction.RETURN_TO_EXTRACTION
    else: action = ReviewAction.ACCEPT_SYNTHESIS_FOR_REVIEW
    return AuditReport(not findings and not unresolved_conflicts, action, tuple(findings), GATES)
