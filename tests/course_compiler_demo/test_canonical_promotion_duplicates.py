import copy

from tools.course_compiler_demo.canonical_promotion import preparation_mode as mode
from tools.course_compiler_demo.canonical_promotion.common import write_json


def candidates_and_fingerprints():
    first = mode.DocumentCompilerInputAdapter().normalize(mode.synthetic_document_candidates()[0], ordinal=1)
    second = copy.deepcopy(first)
    second["candidate_identity"] = "SAME_RUN_COPY"
    return [first, second], [mode._fingerprint_report(first), mode._fingerprint_report(second)]


def test_same_run_exact_duplicate_detected_and_evidence_persistable():
    candidates, fingerprints = candidates_and_fingerprints()
    report = mode._duplicate_report(candidates[0], fingerprints[0], candidates, fingerprints, [])
    assert report["classification"] == "EXACT_DUPLICATE"
    assert report["blockers"]
    assert report["comparison_evidence"][0]["inventory_source"] == "same_preparation_run"


def test_same_run_structural_match_detected():
    candidates, fingerprints = candidates_and_fingerprints()
    candidates[1]["question_payload"]["prompt"] += " structurally varied"
    fingerprints[1] = mode._fingerprint_report(candidates[1])
    report = mode._duplicate_report(candidates[0], fingerprints[0], candidates, fingerprints, [])
    assert report["classification"] == "STRUCTURAL_MATCH_REVIEW"
    assert report["comparison_evidence"][0]["matching_fingerprint_type"] == "structural_fingerprint"


def test_prior_packet_exact_and_structural_matches(tmp_path):
    candidate = mode.DocumentCompilerInputAdapter().normalize(mode.synthetic_document_candidates()[0], ordinal=1)
    fingerprint = mode._fingerprint_report(candidate)
    packet_path = tmp_path / "prepared" / "PRIOR" / "prior.json"
    write_json(packet_path, {"proposed_identity": {"external_preparation_id": "PRIOR_001"}, "review": {"candidate_identity": "PRIOR_CANDIDATE"}, "fingerprints": fingerprint})
    inventory = mode._load_prior_packet_inventory(tmp_path, "CURRENT")
    exact = mode._duplicate_report(candidate, fingerprint, [candidate], [fingerprint], inventory)
    assert exact["classification"] == "EXACT_DUPLICATE"
    assert exact["comparison_evidence"][0]["inventory_source"] == "prior_external_preparation_packet"
    inventory[0]["fingerprints"]["exact_fingerprint"] = "different"
    inventory[0]["fingerprints"]["canonical_content_hash"] = "different"
    structural = mode._duplicate_report(candidate, fingerprint, [candidate], [fingerprint], inventory)
    assert structural["classification"] == "STRUCTURAL_MATCH_REVIEW"


def test_fingerprint_conflict_blocks():
    candidate = mode.DocumentCompilerInputAdapter().normalize(mode.synthetic_document_candidates()[0], ordinal=1)
    fingerprint = mode._fingerprint_report(candidate)
    inventory = [{"inventory_source": "canonical_source_inventory", "candidate_identity": "CONFLICT", "fingerprints": {**fingerprint, "exact_fingerprint": "different"}}]
    report = mode._duplicate_report(candidate, fingerprint, [candidate], [fingerprint], inventory)
    assert report["classification"] == "FINGERPRINT_CONFLICT"
    assert report["blockers"]


def test_all_classifications_remain_supported_and_never_auto_merge():
    assert mode.DUPLICATE_CLASSES == {"DISTINCT", "EXACT_DUPLICATE", "STRUCTURAL_MATCH_REVIEW", "PARAMETERIZED_SIBLING", "REVISION_RELATED", "CONTENT_EQUIVALENT_LEGACY_PROJECTION", "INSUFFICIENT_EVIDENCE", "FINGERPRINT_CONFLICT"}
    candidates, fingerprints = candidates_and_fingerprints()
    assert mode._duplicate_report(candidates[0], fingerprints[0], candidates, fingerprints, [])["auto_merge"] is False
