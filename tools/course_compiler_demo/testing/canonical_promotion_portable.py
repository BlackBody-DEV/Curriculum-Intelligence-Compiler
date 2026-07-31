"""Test-only portable dependencies for canonical-promotion validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tools.course_compiler_demo.production_question_packs.algebra_i import build_bank as algebra
from tools.course_compiler_demo.production_question_packs.calculus_i import build_bank as calculus
from tools.course_compiler_demo.production_question_packs.electricity_magnetism import build_bank as electromagnetism
from tools.course_compiler_demo.production_question_packs.general_chemistry import build_general_chemistry_bank as chemistry
from tools.course_compiler_demo.production_question_packs.programming_fundamentals import build_programming_fundamentals_bank as programming
from tools.course_compiler_demo.production_question_packs.statics import build_bank as statics
from tools.course_compiler_demo.production_questions import ProductionQuestionBankV1


PORTABLE_CANONICAL_ROOT = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "fixtures"
    / "course_compiler_demo"
    / "canonical_promotion_portable"
)
PORTABLE_AUTHORITY_ROOT = PORTABLE_CANONICAL_ROOT / "authority"
MANIFEST_PATH = PORTABLE_CANONICAL_ROOT / "fixture_manifest.json"
REQUIRED_SAFETY = {
    "fixture_type": "PORTABLE_SYNTHETIC_CANONICAL_PROMOTION_TEST_FIXTURE",
    "noncanonical": True,
    "student_visible": False,
    "eligible_for_alpha_import": False,
    "canonical_promotion_authorized": False,
    "database_write_authorized": False,
    "contains_private_content": False,
    "contains_protected_content": False,
}
FORBIDDEN_TEXT = ("/Users/", "AxiomIQ_Work/phase_e", "adaptive-platform", "canonical_seed_bank/projection_dry_run")
BUILDERS = (
    ("algebra_i", algebra),
    ("calculus_i", calculus),
    ("statics", statics),
    ("electricity_magnetism", electromagnetism),
    ("programming_fundamentals", programming),
    ("general_chemistry", chemistry),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_portable_canonical_fixture() -> dict[str, Any]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if any(manifest.get(key) != value for key, value in REQUIRED_SAFETY.items()):
        raise ValueError("portable canonical fixture safety contract is incomplete")
    if PORTABLE_CANONICAL_ROOT.is_symlink() or any(path.is_symlink() for path in PORTABLE_CANONICAL_ROOT.rglob("*")):
        raise ValueError("portable canonical fixture cannot contain symlinks")
    listed = {item["path"]: item["sha256"] for item in manifest.get("authority_files", [])}
    actual = {
        path.relative_to(PORTABLE_CANONICAL_ROOT).as_posix(): path
        for path in PORTABLE_AUTHORITY_ROOT.iterdir()
        if path.is_file()
    }
    if set(listed) != set(actual) or len(actual) != 4:
        raise ValueError("portable canonical authority inventory must contain exactly four files")
    all_files = {
        path.relative_to(PORTABLE_CANONICAL_ROOT).as_posix()
        for path in PORTABLE_CANONICAL_ROOT.rglob("*")
        if path.is_file()
    }
    if all_files != set(listed) | {"fixture_manifest.json"}:
        raise ValueError("portable canonical fixture contains an unexpected file")
    manifest_text = MANIFEST_PATH.read_text(encoding="utf-8")
    if any(value in manifest_text for value in FORBIDDEN_TEXT):
        raise ValueError("portable canonical manifest contains a host or protected path")
    for relative, path in actual.items():
        if not path.resolve().is_relative_to(PORTABLE_CANONICAL_ROOT.resolve()):
            raise ValueError("portable canonical authority escapes fixture root")
        if _sha256(path) != listed[relative]:
            raise ValueError(f"portable canonical authority digest mismatch: {relative}")
        text = path.read_text(encoding="utf-8")
        if "TEST_FIXTURE" not in text or any(value in text for value in FORBIDDEN_TEXT):
            raise ValueError(f"unsafe portable canonical authority content: {relative}")
    return manifest


def build_portable_production_banks(root: Path) -> Path:
    manifest = validate_portable_canonical_fixture()
    expected_slugs = manifest["production_bank_factory"]["course_slugs"]
    if expected_slugs != [slug for slug, _ in BUILDERS]:
        raise ValueError("portable production-bank builder inventory mismatch")
    root.mkdir(parents=True, exist_ok=True)
    course_ids = set()
    candidate_ids = set()
    for slug, builder in BUILDERS:
        result = builder()
        bank = result[0]
        payload = bank.to_dict()
        ProductionQuestionBankV1(**payload)
        course_ids.add(payload["course_id"])
        current_ids = {item["candidate_id"] for item in payload["candidates"]}
        if len(current_ids) != 100 or candidate_ids.intersection(current_ids):
            raise ValueError("portable production-bank candidate identities are invalid")
        candidate_ids.update(current_ids)
        bank_dir = root / slug / "banks"
        bank_dir.mkdir(parents=True, exist_ok=True)
        (bank_dir / "portable_locked_bank.json").write_text(
            json.dumps(payload, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    if len(course_ids) != 6 or len(candidate_ids) != 600:
        raise ValueError("portable production-bank count contract failed")
    return root
