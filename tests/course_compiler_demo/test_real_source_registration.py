import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ID = "STATICS_REAL_SOURCE_ME_2301_CURRICULUM_EXTRACTION_V1"
SOURCE_DIR = (
    REPO_ROOT
    / "tools"
    / "course_compiler_demo"
    / "sample_inputs"
    / "real_statics"
    / SOURCE_ID
)
REGISTRATION = SOURCE_DIR / "source_registration.json"
PRESERVED_SOURCE = SOURCE_DIR / "original" / "me_2301_statics_curriculum_extraction.md"
REPORT = (
    REPO_ROOT
    / "reports"
    / "course_compiler_demo"
    / "integration_readiness"
    / "real_source"
    / "real_statics_source_acquisition_001.json"
)
EXPECTED_SHA256 = "1ff2de06f051cb591599551c9f2434cf691c34daca59463a6ad25dc7c9fbcf40"
EXPECTED_SIZE = 33478


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_real_statics_source_registration_metadata() -> None:
    data = json.loads(REGISTRATION.read_text())

    assert data["schema_version"] == "REAL_SOURCE_REGISTRATION_v1"
    assert data["source_id"] == SOURCE_ID
    assert data["source_type"] == "user_authored_statics_curriculum_extraction"
    assert data["subject"] == "STATICS"
    assert data["source_format"] == "md"
    assert data["synthetic_source"] is False
    assert data["rights"]["rights_status"] == "owned_by_user"
    assert data["rights"]["repository_storage_permitted"] is True
    assert data["rights"]["internal_processing_permitted"] is True
    assert data["rights"]["public_redistribution_permitted"] is False
    assert data["rights"]["textbook_source_used"] is False


def test_real_statics_source_integrity_preserved() -> None:
    data = json.loads(REGISTRATION.read_text())

    assert PRESERVED_SOURCE.exists()
    assert PRESERVED_SOURCE.stat().st_size == EXPECTED_SIZE
    assert sha256(PRESERVED_SOURCE) == EXPECTED_SHA256
    assert data["integrity"]["source_size_bytes"] == EXPECTED_SIZE
    assert data["integrity"]["preserved_size_bytes"] == EXPECTED_SIZE
    assert data["integrity"]["source_sha256"] == EXPECTED_SHA256
    assert data["integrity"]["preserved_sha256"] == EXPECTED_SHA256
    assert data["integrity"]["integrity_match"] is True


def test_real_statics_source_boundaries_are_non_live() -> None:
    data = json.loads(REGISTRATION.read_text())
    report = json.loads(REPORT.read_text())

    assert data["registration"]["curriculum_extraction_performed"] is False
    assert data["registration"]["package_generation_performed"] is False
    assert data["registration"]["alpha_contact_performed"] is False
    assert data["registration"]["database_contact_performed"] is False
    assert data["registration"]["canonical_promotion_performed"] is False
    assert data["registration"]["student_visible_publishing_performed"] is False
    assert data["boundaries"]["textbook_accessed"] is False
    assert data["boundaries"]["textbook_copied"] is False

    assert report["boundaries"]["compiler_repository_only"] is True
    assert report["boundaries"]["adaptive_platform_accessed"] is False
    assert report["boundaries"]["textbook_accessed"] is False
    assert report["boundaries"]["curriculum_extraction_performed"] is False
    assert report["boundaries"]["package_generation_performed"] is False
    assert report["boundaries"]["database_contact_performed"] is False
    assert report["boundaries"]["operational_alpha_contact_performed"] is False
