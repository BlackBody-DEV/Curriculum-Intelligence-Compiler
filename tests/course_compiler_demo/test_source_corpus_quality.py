from tools.course_compiler_demo.source_corpus.quality import ReviewAction, audit_review_package


def valid_package():
    return {
        "course_id": "course-a",
        "sources": [{"document_id":"doc", "source_hash":"a"*64, "segments":[{"segment_id":"seg", "location":{"section":"1"}}], "rights_classification":{"classification":"INTERNAL_FIXTURE","evidence":"curated"}}],
        "evidence_claims": [{"claim_id":"claim", "document_id":"doc", "source_hash":"a"*64, "segment_id":"seg", "location":{"section":"1"}, "rights_classification":{"classification":"INTERNAL_FIXTURE","evidence":"curated"}}],
        "nodes": [{"node_id":"node", "node_type":"TOPIC", "course_id":"course-a", "inference_boundary":"DIRECT_SOURCE_EVIDENCE", "evidence_claim_ids":["claim"], "confidence":1, "review_required":True}],
        "conflicts": [], "declared_conflict_ids": [], "coverage_gaps": [],
        "mappings": [{"mapping_id":"map", "course_id":"course-a", "evidence_claim_ids":["claim"], "canonical_authority":False}],
    }


def test_complete_package_is_accepted_for_review_without_canonical_authority():
    report = audit_review_package(valid_package())
    assert report.passed and report.action == ReviewAction.ACCEPT_SYNTHESIS_FOR_REVIEW
    assert report.canonical_authority is False and len(report.gates) == 10


def test_source_free_node_and_mapping_fail_closed():
    package = valid_package(); package["nodes"][0]["evidence_claim_ids"] = []
    package["mappings"][0]["evidence_claim_ids"] = []
    report = audit_review_package(package)
    assert not report.passed
    assert {f.code for f in report.findings} >= {"SOURCE_FREE_NODE", "SOURCE_FREE_MAPPING"}


def test_inference_requires_rationale_confidence_and_review():
    package = valid_package(); package["nodes"][0].update(inference_boundary="INFERRED_PREREQUISITE", rationale="", confidence=None, review_required=False)
    assert "UNSUPPORTED_INFERENCE" in {f.code for f in audit_review_package(package).findings}
    assert "MISSING_CONFIDENCE" in {f.code for f in audit_review_package(package).findings}


def test_cross_course_and_canonical_mapping_are_blocked():
    package = valid_package(); package["mappings"][0].update(course_id="other", canonical_authority=True)
    assert "UNSAFE_MAPPING" in {f.code for f in audit_review_package(package).findings}


def test_rights_conflict_and_coverage_route_to_explicit_review_actions():
    package = valid_package(); package["sources"][0]["rights_classification"] = {}
    assert audit_review_package(package).action == ReviewAction.ESCALATE_RIGHTS
    package = valid_package(); package["conflicts"] = [{"conflict_id":"c", "resolution_state":"UNRESOLVED"}]
    assert audit_review_package(package).action == ReviewAction.ESCALATE_CONFLICT
    package = valid_package(); package["coverage_gaps"] = [{"gap_id":"", "rationale":""}]
    assert audit_review_package(package).action == ReviewAction.ESCALATE_COVERAGE


def test_silent_conflict_removal_and_broken_provenance_are_found():
    package = valid_package(); package["declared_conflict_ids"] = ["missing"]
    package["evidence_claims"][0]["document_id"] = "missing"
    codes = {f.code for f in audit_review_package(package).findings}
    assert {"MISSING_CONFLICT", "BROKEN_PROVENANCE"} <= codes


def test_authority_unsupported_nodes_duplicate_ids_and_truthy_rights_fail_closed():
    package = valid_package(); package["canonical_authority"] = True
    package["nodes"][0]["canonical_authority"] = True
    package["nodes"][0]["inference_boundary"] = "UNSUPPORTED"
    package["nodes"].append(dict(package["nodes"][0]))
    package["sources"][0]["rights_classification"] = {"classification": True, "evidence": True}
    codes = {f.code for f in audit_review_package(package).findings}
    assert {"CANONICAL_AUTHORITY_FORBIDDEN", "UNSUPPORTED_NODE", "DUPLICATE_OR_MISSING_NODE_IDENTITY", "RIGHTS_INCOMPLETE"} <= codes


def test_claim_must_match_exact_document_hash_segment_and_location():
    package = valid_package(); package["evidence_claims"][0]["source_hash"] = "b"*64
    assert "BROKEN_PROVENANCE" in {f.code for f in audit_review_package(package).findings}
    package = valid_package(); package["evidence_claims"][0]["segment_id"] = "missing"
    assert "BROKEN_PROVENANCE" in {f.code for f in audit_review_package(package).findings}


def test_all_review_routes_are_reachable_without_granting_authority():
    package = valid_package(); package["sources"] = []
    assert audit_review_package(package).action == ReviewAction.REQUEST_ADDITIONAL_SOURCE
    package = valid_package(); package["sources"][0]["segments"] = []
    assert audit_review_package(package).action == ReviewAction.REJECT_SOURCE
    package = valid_package(); package["evidence_claims"][0]["rights_classification"] = {}
    assert audit_review_package(package).action == ReviewAction.ESCALATE_RIGHTS


def test_unknown_boundary_invalid_hash_source_authority_mapping_identity_and_confidence_fail():
    package = valid_package()
    package["nodes"][0].update(inference_boundary="MADE_UP", confidence="high")
    package["sources"][0].update(source_hash="x", canonical_authority=True)
    package["evidence_claims"][0]["source_hash"] = "x"
    package["mappings"].append(dict(package["mappings"][0]))
    codes = {f.code for f in audit_review_package(package).findings}
    assert {"UNKNOWN_INFERENCE_BOUNDARY", "MISSING_CONFIDENCE", "SOURCE_INCOMPLETE", "CANONICAL_AUTHORITY_FORBIDDEN", "BROKEN_PROVENANCE", "DUPLICATE_OR_MISSING_MAPPING_IDENTITY"} <= codes


def test_restricted_unknown_unverified_and_restricted_rights_never_pass():
    for rights in (
        {"classification":"RESTRICTED", "evidence":"license"},
        {"classification":"UNKNOWN", "evidence":"unknown"},
        {"classification":"EXPLICIT_APPROVAL_EVIDENCE", "evidence":"approval", "verified":False},
        {"classification":"PUBLIC_DOMAIN", "evidence":"record", "restrictions":["no derivatives"]},
    ):
        package = valid_package(); package["sources"][0]["rights_classification"] = rights
        assert not audit_review_package(package).passed
        package = valid_package(); package["evidence_claims"][0]["rights_classification"] = rights
        assert not audit_review_package(package).passed


def test_empty_nodes_and_mappings_fail_coverage_and_mapping_gates():
    package = valid_package(); package["nodes"] = []; package["mappings"] = []
    codes = {f.code for f in audit_review_package(package).findings}
    assert {"NO_CURRICULUM_NODES", "NO_PROPOSED_MAPPINGS"} <= codes


def test_canonical_authority_is_rejected_at_every_nested_location():
    for collection in ("evidence_claims", "conflicts", "coverage_gaps"):
        package = valid_package()
        if not package[collection]: package[collection].append({"conflict_id":"c"} if collection == "conflicts" else {"gap_id":"g", "rationale":"gap"})
        package[collection][0]["canonical_authority"] = True
        assert "CANONICAL_AUTHORITY_FORBIDDEN" in {f.code for f in audit_review_package(package).findings}
    package = valid_package(); package["sources"][0]["segments"][0]["canonical_authority"] = True
    assert "CANONICAL_AUTHORITY_FORBIDDEN" in {f.code for f in audit_review_package(package).findings}


def test_rights_verified_and_restrictions_types_fail_closed_for_every_classification():
    for malformed in ({"verified":"yes"}, {"verified":1}, {"restrictions":""}, {"restrictions":{}}):
        package = valid_package()
        rights = dict(package["sources"][0]["rights_classification"]); rights.update(malformed)
        package["sources"][0]["rights_classification"] = rights
        package["evidence_claims"][0]["rights_classification"] = dict(rights)
        assert not audit_review_package(package).passed
