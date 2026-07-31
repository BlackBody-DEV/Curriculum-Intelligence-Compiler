import pytest
from jsonschema import Draft202012Validator
from pathlib import Path
import json

from tools.course_compiler_demo.source_corpus.contracts import (
    ContractError, ExtractedCurriculumCandidateV1, SourceDocumentV1,
    SourceLocationV1, SourceRightsClassificationV1, SourceSegmentV1,
    SynthesizedCurriculumNodeV1,
)


def rights():
    return SourceRightsClassificationV1("INTERNAL_FIXTURE", "curated test fixture", verified=True)


def location():
    return SourceLocationV1("SECTION", "unit-1", section="Unit 1")


def test_document_preserves_complete_segment_provenance_and_round_trips_deterministically():
    sha = "a" * 64
    segment = SourceSegmentV1("seg", "doc", sha, "Vectors", location(), "TEXT_NATIVE", .99, "PROPOSED", rights())
    doc = SourceDocumentV1("doc", "SYLLABUS", sha, "Course", rights(), (segment,))
    assert doc.to_json() == doc.to_json()
    assert doc.to_dict()["segments"][0]["location"]["section"] == "Unit 1"


def test_document_rejects_segment_from_different_source():
    segment = SourceSegmentV1("seg", "other", "a" * 64, "text", location(), "TEXT_NATIVE", 1, "PROPOSED", rights())
    with pytest.raises(ContractError): SourceDocumentV1("doc", "PLAIN_TEXT", "a" * 64, "T", rights(), (segment,))


@pytest.mark.parametrize("field", ["student_id", "studentScore", "student-score", "Student Score", "attempt", "score", "mastery", "progress", "performanceHistory", "adaptive_assignment", "student_analytics"])
def test_performance_fields_fail_closed_recursively(field):
    from tools.course_compiler_demo.source_corpus.contracts import reject_performance_fields
    with pytest.raises(ContractError): reject_performance_fields({"nested": {field: 1}})


def test_supported_candidate_requires_source_evidence():
    with pytest.raises(ContractError):
        ExtractedCurriculumCandidateV1("c", "TOPIC", "Vectors", (), .8, "PROPOSED")


def test_inferred_prerequisite_requires_evidence_and_rationale():
    with pytest.raises(ContractError):
        SynthesizedCurriculumNodeV1("n", "PREREQUISITE", "Algebra", "INFERRED_PREREQUISITE", ("claim",), "", .7)


def test_unsupported_node_is_explicit_not_silently_invented():
    node = SynthesizedCurriculumNodeV1("n", "TOPIC", "Unknown", "UNSUPPORTED", (), "not present", 0)
    assert node.inference_boundary == "UNSUPPORTED"


def test_invalid_hash_source_type_confidence_and_canonical_authority_fail_closed():
    with pytest.raises(ContractError): SourceDocumentV1("d", "VIDEO", "a" * 64, "T", rights())
    with pytest.raises(ContractError): SourceDocumentV1("d", "PLAIN_TEXT", "truthy", "T", rights())
    with pytest.raises(ContractError): SourceSegmentV1("s", "d", "a" * 64, "T", location(), "NATIVE", 2, "P", rights())
    from tools.course_compiler_demo.source_corpus.contracts import SourceProcessingDecisionV1
    with pytest.raises(ContractError): SourceProcessingDecisionV1("d", "n", "ACCEPT", "ok", "human", True)


def test_public_schemas_are_strict_and_valid():
    root = Path(__file__).parents[2] / "schemas" / "course_compiler_demo"
    for name in ("source_document_v1.schema.json", "source_corpus_v1.schema.json", "source_evidence_graph_v1.schema.json", "curriculum_synthesis_v1.schema.json"):
        schema = json.loads((root / name).read_text())
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False
    corpus_schema = json.loads((root / "source_corpus_v1.schema.json").read_text())
    assert list(Draft202012Validator(corpus_schema).iter_errors({"corpus_id":"c", "documents":[{}], "manifest_sha256":"a"*64}))
    synthesis_schema = json.loads((root / "curriculum_synthesis_v1.schema.json").read_text())
    bogus = {"package_id":"p","course_id":"c","evidence_graph":{},"nodes":[{"node_id":"n","node_type":"T","title":"T","inference_boundary":"BOGUS","evidence_claim_ids":[],"rationale":"","confidence":9,"review_required":True,"extra":1}],"conflicts":[{}],"coverage_gaps":[{}],"completeness":"SOURCE_COMPLETE","canonical_authority":False}
    assert list(Draft202012Validator(synthesis_schema).iter_errors(bogus))


def test_graph_and_synthesis_schemas_accept_valid_runtime_contracts():
    from tools.course_compiler_demo.source_corpus.contracts import (
        CurriculumSynthesisPackageV1,
        SourceCorpusV1,
        SourceEvidenceClaimV1,
        SourceEvidenceGraphV1,
    )

    root = Path(__file__).parents[2] / "schemas" / "course_compiler_demo"
    graph_schema = json.loads((root / "source_evidence_graph_v1.schema.json").read_text())
    synthesis_schema = json.loads((root / "curriculum_synthesis_v1.schema.json").read_text())
    sha = "a" * 64
    segment = SourceSegmentV1(
        "segment", "document", sha, "topic: Vectors", location(),
        "TEXT_NATIVE", 1, "PROPOSED", rights(),
    )
    document = SourceDocumentV1(
        "document", "SYLLABUS", sha, "Course", rights(), (segment,),
    )
    corpus = SourceCorpusV1("corpus", (document,), "b" * 64)
    claim = SourceEvidenceClaimV1(
        "claim", "document", sha, location(), "segment", "TEXT_NATIVE",
        1, "PROPOSED", rights(), "topic: Vectors",
    )
    graph = SourceEvidenceGraphV1("graph", corpus, (claim,), ())
    node = SynthesizedCurriculumNodeV1(
        "node", "TOPIC", "Vectors", "DIRECT_SOURCE_EVIDENCE",
        ("claim",), "direct source evidence", 1,
    )
    package = CurriculumSynthesisPackageV1(
        "package", "course", graph, (node,), (), (), "SOURCE_COMPLETE",
    )
    Draft202012Validator(graph_schema).validate(graph.to_dict())
    Draft202012Validator(synthesis_schema).validate(package.to_dict())


def test_nested_runtime_contracts_fail_closed():
    with pytest.raises(ContractError):
        SourceDocumentV1("d", "PLAIN_TEXT", "a" * 64, "T", {"not": "rights"})


def test_graph_resolves_claim_to_exact_corpus_segment_and_rejects_duplicate_ids():
    from tools.course_compiler_demo.source_corpus.contracts import SourceCorpusV1, SourceEvidenceClaimV1, SourceEvidenceGraphV1
    sha = "a" * 64
    segment = SourceSegmentV1("s", "d", sha, "text", location(), "TEXT_NATIVE", 1, "P", rights())
    doc = SourceDocumentV1("d", "PLAIN_TEXT", sha, "T", rights(), (segment,))
    corpus = SourceCorpusV1("c", (doc,), "b" * 64)
    claim = SourceEvidenceClaimV1("claim", "d", sha, location(), "s", "TEXT_NATIVE", 1, "P", rights(), "text")
    SourceEvidenceGraphV1("g", corpus, (claim,), ())
    with pytest.raises(ContractError): SourceEvidenceGraphV1("g", corpus, (claim, claim), ())
    bad = SourceEvidenceClaimV1("bad", "missing", sha, location(), "s", "TEXT_NATIVE", 1, "P", rights(), "text")
    with pytest.raises(ContractError): SourceEvidenceGraphV1("g", corpus, (bad,), ())
