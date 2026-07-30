"""Repository-portable seam for newly authored public-schema Phase E artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tools.course_compiler_demo.phase_e_production.family_adapters import (
    ForceSystemsFamilyAdapter,
    PhaseEFamilyAdapter,
    VectorOperationsFamilyAdapter,
)


FIXTURE_TYPE = "PORTABLE_SYNTHETIC_PHASE_E_TEST_FIXTURE"
REQUIRED_SAFETY = {
    "fixture_type": FIXTURE_TYPE,
    "noncanonical": True,
    "student_visible": False,
    "eligible_for_alpha_import": False,
    "canonical_promotion_authorized": False,
    "database_write_authorized": False,
    "contains_protected_content": False,
}
COMMON_PUBLIC_FIELDS = {
    "author_status": str,
    "question_id": str,
    "ordinal": int,
    "answer_type": str,
    "question_type": str,
    "reserved_canonical_path": str,
    "procedure_id": str,
    "procedure_sha256": str,
    "procedure_steps_verbatim": list,
    "frozen_manifest_row": dict,
    "answer_parts_contract": dict,
    "prompt": str,
    "solution": list,
    "review_evidence": dict,
    "independent_derivation": dict,
    "lineage": dict,
}
FORBIDDEN_TEXT = ("/Users/", "AxiomIQ_Source_Inbox", "AxiomIQ_Work/phase_e", "adaptive-platform")
FORBIDDEN_KEYS = {"student_id", "student_email", "private_source_path", "protected_record_id"}


def _canonical_steps_sha256(steps: list[str]) -> str:
    encoded = json.dumps(steps, separators=(",", ":"), ensure_ascii=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _scan_safe(value: Any, *, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in FORBIDDEN_KEYS:
                raise ValueError(f"forbidden private fixture key at {path}.{key}")
            _scan_safe(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _scan_safe(item, path=f"{path}[{index}]")
    elif isinstance(value, str) and any(fragment in value for fragment in FORBIDDEN_TEXT):
        raise ValueError(f"host or protected path in portable fixture at {path}")


def _validate_public_schema(payload: dict[str, Any], path: Path) -> None:
    for field, expected_type in COMMON_PUBLIC_FIELDS.items():
        if not isinstance(payload.get(field), expected_type):
            raise ValueError(f"invalid {field} in portable artifact: {path.name}")
    if payload["author_status"] != "AUTHOR_COMPLETE":
        raise ValueError(f"portable artifact is not author-complete: {path.name}")
    steps = payload["procedure_steps_verbatim"]
    if not steps or not all(isinstance(step, str) and step.strip() for step in steps):
        raise ValueError(f"portable artifact lacks signed procedure steps: {path.name}")
    if payload["procedure_sha256"] != _canonical_steps_sha256(steps):
        raise ValueError(f"portable artifact procedure digest mismatch: {path.name}")
    answer_type = payload["answer_type"]
    required = {
        "multiple_choice": {"answer": dict, "correct_option_id": str},
        "numeric": {"answers": list},
        "numeric_pair": {"givens": dict, "answer_parts": list},
    }.get(answer_type)
    if required is None:
        raise ValueError(f"unsupported portable answer type: {answer_type}")
    for field, expected_type in required.items():
        if not isinstance(payload.get(field), expected_type):
            raise ValueError(f"invalid {answer_type} field {field}: {path.name}")


def _validate(root: Path) -> dict[str, Any]:
    resolved_root = root.resolve()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("portable Phase E fixture root must be a regular directory")
    for candidate in root.rglob("*"):
        if candidate.is_symlink():
            raise ValueError(f"portable Phase E fixture cannot contain symlinks: {candidate}")
    config_path = root / "fixture_config.json"
    if config_path.is_symlink() or not config_path.is_file():
        raise ValueError("portable Phase E fixture config must be a regular file")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if any(config.get(key) != value for key, value in REQUIRED_SAFETY.items()):
        raise ValueError("portable Phase E fixture safety flags are incomplete")
    _scan_safe(config)

    listed = {item["path"]: item["sha256"] for item in config.get("files", [])}
    artifacts = sorted(root.glob("*/approved/*.json"))
    actual = {path.relative_to(root).as_posix(): path for path in artifacts}
    if set(listed) != set(actual) or len(actual) != 15:
        raise ValueError("portable Phase E fixture inventory must contain exactly 15 artifacts")
    for relative, path in actual.items():
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(resolved_root):
            raise ValueError(f"portable artifact must be a regular file: {relative}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != listed[relative]:
            raise ValueError(f"portable artifact digest mismatch: {relative}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if any(payload.get(key) != value for key, value in REQUIRED_SAFETY.items()):
            raise ValueError(f"unsafe portable artifact: {path.name}")
        _scan_safe(payload)
        _validate_public_schema(payload, path)
    all_files = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if all_files != set(listed) | {"fixture_config.json"}:
        raise ValueError("portable Phase E fixture contains an unexpected file")
    return config


def portable_adapters(root: Path) -> dict[str, PhaseEFamilyAdapter]:
    _validate(root)
    force = ForceSystemsFamilyAdapter()
    vector = VectorOperationsFamilyAdapter()
    object.__setattr__(force, "workspace", root / "force_systems")
    object.__setattr__(vector, "workspace", root / "vector_operations")
    return {"force_systems": force, "vector_operations": vector}
