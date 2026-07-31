import copy
import json
from pathlib import Path

import pytest

from tools.course_compiler_demo.release_checkpoint import (
    AUTHORIZED_BASELINE,
    AUTHORIZED_TREE,
    MANIFEST_PATH,
    REPORT_PATH,
    MilestoneValidationError,
    collect_repository_evidence,
    load_manifest,
    render_checkpoint_report,
    validate_manifest,
)


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def manifest():
    return load_manifest(ROOT)


@pytest.fixture(scope="module")
def evidence():
    return collect_repository_evidence(ROOT)


def test_manifest_counts_and_hashes_match_repository_state(manifest, evidence):
    validate_manifest(manifest, ROOT)
    assert manifest["compiler_snapshot"] == {
        "commit": AUTHORIZED_BASELINE,
        "tracked_tree_sha1": AUTHORIZED_TREE,
    }
    assert manifest["capabilities"] == evidence["capabilities"]
    assert manifest["production_banks"] == evidence["production_banks"]
    assert manifest["source_corpus_wave_066"] == evidence["source_corpus_wave_066"]
    assert manifest["canonical_execution_beta_projection_wave_048"] == evidence[
        "canonical_execution_beta_projection_wave_048"
    ]


def test_protected_state_and_tag_candidate_remain_non_live(manifest):
    assert manifest["protected_state"]
    assert all(value is False for value in manifest["protected_state"].values())
    assert manifest["release_candidate"] == {
        "proposed_annotated_tag": "compiler-milestone-093-v1",
        "tag_created": False,
        "tag_pushed": False,
        "separate_authorization_required": True,
    }


def test_human_checkpoint_report_is_exact_manifest_render(manifest):
    report = (ROOT / REPORT_PATH).read_text(encoding="utf-8")
    assert report == render_checkpoint_report(manifest)
    assert json.loads((ROOT / MANIFEST_PATH).read_text()) == manifest


def test_unsupported_capability_identifier_fails_closed(manifest):
    altered = copy.deepcopy(manifest)
    altered["capabilities"]["enabled_answer_capabilities"]["identifiers"].append(
        "unsupported_future_engine"
    )
    with pytest.raises(MilestoneValidationError, match="manifest section drift|unsupported"):
        validate_manifest(altered, ROOT)


def test_true_protected_state_or_created_tag_fails_closed(manifest):
    altered = copy.deepcopy(manifest)
    altered["protected_state"]["student_visible"] = True
    with pytest.raises(MilestoneValidationError, match="protected-state"):
        validate_manifest(altered, ROOT)
    altered = copy.deepcopy(manifest)
    altered["release_candidate"]["tag_created"] = True
    with pytest.raises(MilestoneValidationError, match="uncreated"):
        validate_manifest(altered, ROOT)


def test_malformed_or_failed_ci_evidence_fails_closed(manifest):
    altered = copy.deepcopy(manifest)
    altered["ci_evidence"]["successful_runs"][0]["head_sha"] = "not-a-sha"
    with pytest.raises(MilestoneValidationError, match="CI evidence|CI head"):
        validate_manifest(altered, ROOT)
    altered = copy.deepcopy(manifest)
    altered["ci_evidence"]["successful_runs"][1]["repository_checkout_suite"] = "FAIL"
    with pytest.raises(MilestoneValidationError, match="CI evidence"):
        validate_manifest(altered, ROOT)


def test_audit_identity_or_tip_drift_fails_closed(manifest):
    altered = copy.deepcopy(manifest)
    altered["independent_audit_references"][0]["audit_id"] = "UNRELATED_AUDIT"
    with pytest.raises(MilestoneValidationError, match="audit references"):
        validate_manifest(altered, ROOT)
    altered = copy.deepcopy(manifest)
    altered["independent_audit_references"][0]["validated_tip"] = "0" * 40
    with pytest.raises(MilestoneValidationError, match="audit references"):
        validate_manifest(altered, ROOT)
