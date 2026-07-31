from __future__ import annotations

import copy
import hashlib
import json
import shutil

import pytest

from tools.course_compiler_demo.canonical_promotion import preparation_mode
from tools.course_compiler_demo.canonical_promotion.reconciliation import (
    CanonicalPromotionPreparationError,
    _load_banks,
)
from tools.course_compiler_demo.production_questions import ProductionQuestionBankV1
from tools.course_compiler_demo.testing import canonical_promotion_portable
from tools.course_compiler_demo.testing.canonical_promotion_portable import (
    MANIFEST_PATH,
    PORTABLE_AUTHORITY_ROOT,
    REQUIRED_SAFETY,
    build_portable_production_banks,
    validate_portable_canonical_fixture,
)


pytestmark = pytest.mark.portable_baseline


def test_authority_fixture_has_exact_inventory_digests_and_safety_contract():
    manifest = validate_portable_canonical_fixture()
    assert all(manifest[key] == value for key, value in REQUIRED_SAFETY.items())
    assert manifest["provenance"] == "newly_authored_public_contract_equivalent"
    listed = {item["path"]: item["sha256"] for item in manifest["authority_files"]}
    assert len(listed) == 4
    for relative, expected in listed.items():
        path = MANIFEST_PATH.parent / relative
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
        assert "TEST_FIXTURE" in path.read_text(encoding="utf-8")


def test_authority_snapshot_preserves_identity_and_integrity(tmp_path):
    root = tmp_path / "preparation"
    summary = preparation_mode.run_preparation_pilot("PORTABLE_AUTHORITY_SNAPSHOT", preparation_root=root)
    references = summary["authority_snapshot"]["references"]
    assert len(references) == 4
    assert all(item["reference_type"] == "HISTORICAL_EXTERNAL_CONTRACT_REFERENCE" for item in references)
    assert all(item["source_sha256"] == item["snapshot_sha256"] for item in references)
    assert all(str(PORTABLE_AUTHORITY_ROOT) in item["source_path"] for item in references)
    reopened = preparation_mode.reopen_preparation_run("PORTABLE_AUTHORITY_SNAPSHOT", preparation_root=root)
    assert reopened["packet_count"] == 10 and reopened["prepared_count"] == 3


def test_authority_mutation_and_unexpected_files_fail_closed(tmp_path, monkeypatch):
    copied = tmp_path / "canonical"
    shutil.copytree(MANIFEST_PATH.parent, copied)
    target = copied / "authority" / "CANONICAL_SEED_BANK_CONTRACT_v1.md"
    target.write_text(target.read_text() + "unreviewed mutation\n")
    monkeypatch.setattr(canonical_promotion_portable, "PORTABLE_CANONICAL_ROOT", copied)
    monkeypatch.setattr(canonical_promotion_portable, "PORTABLE_AUTHORITY_ROOT", copied / "authority")
    monkeypatch.setattr(canonical_promotion_portable, "MANIFEST_PATH", copied / "fixture_manifest.json")
    with pytest.raises(ValueError, match="digest mismatch"):
        canonical_promotion_portable.validate_portable_canonical_fixture()

    shutil.copytree(MANIFEST_PATH.parent, tmp_path / "unexpected")
    unexpected = tmp_path / "unexpected"
    (unexpected / "undeclared.txt").write_text("TEST_FIXTURE undeclared\n")
    monkeypatch.setattr(canonical_promotion_portable, "PORTABLE_CANONICAL_ROOT", unexpected)
    monkeypatch.setattr(canonical_promotion_portable, "PORTABLE_AUTHORITY_ROOT", unexpected / "authority")
    monkeypatch.setattr(canonical_promotion_portable, "MANIFEST_PATH", unexpected / "fixture_manifest.json")
    with pytest.raises(ValueError, match="unexpected file"):
        canonical_promotion_portable.validate_portable_canonical_fixture()


def test_production_bank_factory_is_deterministic_and_contract_complete(tmp_path):
    first = build_portable_production_banks(tmp_path / "first")
    second = build_portable_production_banks(tmp_path / "second")
    first_files = sorted(first.glob("*/banks/*.json"))
    second_files = sorted(second.glob("*/banks/*.json"))
    assert len(first_files) == len(second_files) == 6
    first_hashes = []
    all_ids = set()
    for left, right in zip(first_files, second_files):
        left_payload = json.loads(left.read_text())
        right_payload = json.loads(right.read_text())
        ProductionQuestionBankV1(**left_payload)
        assert left_payload == right_payload
        assert left_payload["bank_sha256"] == right_payload["bank_sha256"]
        assert left_payload["locked"] is True
        assert len(left_payload["candidates"]) == len(left_payload["derivations"]) == len(left_payload["validations"]) == 100
        candidate_ids = {item["candidate_id"] for item in left_payload["candidates"]}
        assert len(candidate_ids) == 100 and not candidate_ids.intersection(all_ids)
        assert {item["candidate_id"] for item in left_payload["derivations"]} == candidate_ids
        assert {item["candidate_id"] for item in left_payload["validations"]} == candidate_ids
        all_ids.update(candidate_ids)
        first_hashes.append(left_payload["bank_sha256"])
    assert len(all_ids) == 600 and len(set(first_hashes)) == 6


def test_production_bank_checksum_and_provenance_fail_closed(portable_production_root):
    path = next(portable_production_root.glob("algebra_i/banks/*.json"))
    payload = json.loads(path.read_text())
    candidate = payload["candidates"][0]
    assert candidate["authority"]["source_evidence"]
    assert candidate["safety"]["synthetic_fixture"] is False
    assert candidate["safety"]["production_candidate"] is True
    mutated = copy.deepcopy(payload)
    mutated["candidates"][0]["prompt"] += " changed"
    with pytest.raises(ValueError, match="bank hash mismatch"):
        ProductionQuestionBankV1(**mutated)


def test_production_bank_count_fails_closed(portable_production_root, tmp_path):
    copied = tmp_path / "five-banks"
    shutil.copytree(portable_production_root, copied)
    next(copied.glob("general_chemistry/banks/*.json")).unlink()
    with pytest.raises(CanonicalPromotionPreparationError, match="exactly six unique production banks"):
        _load_banks(copied)


def test_portable_canonical_dependencies_exclude_private_and_performance_data(portable_production_root):
    encoded = MANIFEST_PATH.read_text() + "".join(path.read_text() for path in portable_production_root.glob("*/banks/*.json"))
    assert "/Users/" not in encoded
    assert "AxiomIQ_Work/phase_e" not in encoded
    assert "student_id" not in encoded
    assert "performance_history" not in encoded
    assert '"student_visible": true' not in encoded
    assert '"database_write_authorized": true' not in encoded
