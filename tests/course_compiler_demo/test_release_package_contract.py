import json
import re
from pathlib import Path

import pytest

from tools.course_compiler_demo.release_package.manifest.integrity import (
    CONTRACT_SEMVER,
    PACKAGE_CONTRACT,
    canonical_json_bytes,
    finalize_manifest,
    manifest_sha256,
    sha256_file,
)


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_DIR = ROOT / "tools/course_compiler_demo/release_package/contracts"
FIXTURE_DIR = ROOT / "tools/course_compiler_demo/release_package/golden_packages"

VALID_FIXTURES = [
    "minimal_valid",
    "normal_multi_artifact",
    "known_nonblocking_gaps",
]
INVALID_FIXTURES = [
    "deliberately_invalid",
    "safety_boundary_violation",
]
REQUIRED_CATEGORIES = {
    "source_metadata",
    "source_interpretation",
    "curriculum_extraction",
    "procedure_candidate",
    "question_candidate",
    "generation_family_candidate",
    "signal_mapping",
    "performance_tracking_target",
    "review_record",
    "validation_report",
}
FORBIDDEN_VALID_TEXT = [
    "/Users/fanarichardson/adaptive-platform",
    "database_url",
    "canonical_approved",
    "production_ready",
    "live_ready",
]


def load_json(path: Path):
    return json.loads(path.read_text())


def manifest_path(name: str) -> Path:
    return FIXTURE_DIR / name / "manifest.json"


def manifest(name: str):
    return load_json(manifest_path(name))


def assert_relative_contained(path_value: str):
    path = Path(path_value)
    assert not path.is_absolute(), path_value
    assert "\\" not in path_value, path_value
    assert ".." not in path.parts, path_value
    assert not path_value.startswith("/"), path_value


def validate_manifest_shape(data: dict, package_root: Path):
    assert data["package_contract"] == PACKAGE_CONTRACT
    assert data["package_contract_semver"] == CONTRACT_SEMVER
    assert data["content_status"] == "non_live_candidate"
    assert data["review_status"] == "human_review_required"
    assert data["promotion_recommendation"] in {
        "hold_for_human_review",
        "eligible_for_protected_integration_review",
        "reject",
    }

    safety = data["safety_boundary"]
    assert safety == {
        "non_live": True,
        "non_canonical": True,
        "human_review_required": True,
        "student_visible": False,
        "database_contact_required": False,
        "adaptive_platform_contact_required": False,
        "runtime_route_required": False,
        "learner_state_mutation_required": False,
        "canonical_promotion_performed": False,
    }

    artifact_ids = [item["artifact_id"] for item in data["artifact_inventory"]]
    assert len(artifact_ids) == len(set(artifact_ids)), "artifact IDs must be unique"
    assert artifact_ids == sorted(artifact_ids), "artifact ordering must be deterministic by id"

    for source in data["source_references"]:
        assert source["rights_status"] in {
            "axiomiq_authored",
            "synthetic_fixture",
            "rights_review_required",
        }
        assert source["privacy_status"] in {"no_personal_data", "privacy_review_required"}

    for item in data["artifact_inventory"]:
        assert_relative_contained(item["relative_path"])
        artifact_path = package_root / item["relative_path"]
        assert artifact_path.exists(), item["relative_path"]
        assert item["sha256"] == sha256_file(artifact_path)
        assert item["byte_size"] == len(artifact_path.read_bytes())
        assert item["status"] == "human_review_required"
        assert item["artifact_type"] in {
            "source_metadata",
            "source_interpretation",
            "curriculum_extraction",
            "procedure_candidate",
            "question_candidate",
            "generation_family_candidate",
            "signal_mapping",
            "performance_tracking_target",
            "review_record",
            "validation_report",
            "asset_reference",
            "known_gap_report",
        }

    declared = {item["relative_path"] for item in data["artifact_inventory"]}
    actual = {
        path.relative_to(package_root).as_posix()
        for path in package_root.rglob("*")
        if path.is_file() and path.name not in {"manifest.json", "README.md"}
    }
    assert declared == actual
    assert data["integrity"]["package_manifest_sha256"] == manifest_sha256(data)


def test_all_schema_files_parse_as_json():
    expected = {
        "release_package.schema.json",
        "release_manifest.schema.json",
        "artifact_descriptor.schema.json",
        "source_reference.schema.json",
        "review_state.schema.json",
        "safety_boundary.schema.json",
    }
    found = {path.name for path in CONTRACT_DIR.glob("*.schema.json")}
    assert expected.issubset(found)
    for path in CONTRACT_DIR.glob("*.json"):
        load_json(path)


def test_contract_version_is_stable():
    assert (CONTRACT_DIR / "PACKAGE_CONTRACT_VERSION").read_text().strip().splitlines() == [
        "contract_id=compiler_release_package_v1",
        "semantic_version=1.0.0",
    ]
    assert PACKAGE_CONTRACT == "compiler_release_package_v1"
    assert CONTRACT_SEMVER == "1.0.0"


def test_all_five_fixture_directories_exist():
    for name in VALID_FIXTURES + INVALID_FIXTURES:
        assert (FIXTURE_DIR / name).is_dir()
        assert (FIXTURE_DIR / name / "manifest.json").is_file()
        assert (FIXTURE_DIR / name / "README.md").is_file()


@pytest.mark.parametrize("name", VALID_FIXTURES)
def test_valid_fixture_manifests_satisfy_structural_contract(name):
    validate_manifest_shape(manifest(name), FIXTURE_DIR / name)


def test_minimal_fixture_contains_every_required_artifact_category():
    categories = {item["artifact_type"] for item in manifest("minimal_valid")["artifact_inventory"]}
    assert REQUIRED_CATEGORIES.issubset(categories)


def test_multi_artifact_fixture_contains_multiple_linked_objects():
    data = manifest("normal_multi_artifact")
    assert len(data["procedure_artifact_ids"]) >= 2
    assert len(data["question_artifact_ids"]) >= 2
    assert len(data["generation_family_artifact_ids"]) >= 2
    dependencies = [
        dep
        for item in data["artifact_inventory"]
        for dep in item.get("depends_on_artifact_ids", [])
    ]
    assert dependencies


def test_known_gap_fixture_remains_structurally_valid():
    data = manifest("known_nonblocking_gaps")
    assert data["promotion_recommendation"] == "hold_for_human_review"
    assert data["known_gaps"]
    validate_manifest_shape(data, FIXTURE_DIR / "known_nonblocking_gaps")


def test_invalid_fixture_demonstrably_violates_contract():
    data = manifest("deliberately_invalid")
    assert data["fixture_metadata"]["expected_verdict"] == "reject"
    ids = [item["artifact_id"] for item in data["artifact_inventory"]]
    assert len(ids) != len(set(ids))
    with pytest.raises(AssertionError):
        validate_manifest_shape(data, FIXTURE_DIR / "deliberately_invalid")


def test_safety_fixture_demonstrably_violates_safety_contract():
    data = manifest("safety_boundary_violation")
    assert data["fixture_metadata"]["expected_verdict"] == "reject"
    assert data["fixture_metadata"]["unsafe_fixture"] is True
    assert data["safety_boundary"]["student_visible"] is True
    with pytest.raises(AssertionError):
        validate_manifest_shape(data, FIXTURE_DIR / "safety_boundary_violation")


@pytest.mark.parametrize("name", VALID_FIXTURES)
def test_valid_fixture_paths_are_relative_and_contained(name):
    for item in manifest(name)["artifact_inventory"]:
        assert_relative_contained(item["relative_path"])


@pytest.mark.parametrize("name", VALID_FIXTURES)
def test_valid_fixtures_contain_no_forbidden_paths_or_claims(name):
    text = (FIXTURE_DIR / name).read_text() if (FIXTURE_DIR / name).is_file() else ""
    text += "\n".join(path.read_text() for path in (FIXTURE_DIR / name).rglob("*") if path.is_file())
    for forbidden in FORBIDDEN_VALID_TEXT:
        assert forbidden not in text
    assert not re.search(r'"student_visible"\s*:\s*true', text)
    assert "db_password" not in text
    assert "connection_string" not in text


@pytest.mark.parametrize("name", VALID_FIXTURES)
def test_manifest_generation_is_deterministic(name):
    data = manifest(name)
    first = canonical_json_bytes(finalize_manifest(data))
    second = canonical_json_bytes(finalize_manifest(data))
    assert first == second
    assert finalize_manifest(data)["integrity"]["package_manifest_sha256"] == data["integrity"]["package_manifest_sha256"]


@pytest.mark.parametrize("name", VALID_FIXTURES)
def test_no_fixture_contains_unresolved_external_path_references(name):
    text = "\n".join(path.read_text() for path in (FIXTURE_DIR / name).rglob("*") if path.is_file())
    assert "/Users/" not in text
    assert "adaptive-platform" not in text
    assert "TODO_EXTERNAL_PATH" not in text
