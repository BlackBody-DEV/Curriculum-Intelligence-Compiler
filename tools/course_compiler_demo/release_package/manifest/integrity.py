"""Deterministic manifest helpers for portable compiler release packages.

This module intentionally performs only structural packaging work. It does not
decide whether a package is semantically acceptable for integration.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


PACKAGE_CONTRACT = "compiler_release_package_v1"
CONTRACT_SEMVER = "1.0.0"


def canonical_json_bytes(payload: Any) -> bytes:
    """Return stable UTF-8 JSON bytes for hashing and comparison."""
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def relative_package_path(path: Path, package_root: Path) -> str:
    rel = path.relative_to(package_root).as_posix()
    if rel.startswith("../") or rel.startswith("/") or "/../" in rel:
        raise ValueError(f"Path escapes package root: {path}")
    return rel


def artifact_descriptor(
    *,
    package_root: Path,
    relative_path: str,
    artifact_id: str,
    artifact_type: str,
    media_type: str = "application/json",
    schema_ref: str,
    required: bool = True,
    status: str = "human_review_required",
    source_reference_ids: list[str] | None = None,
    depends_on_artifact_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build a descriptor for an artifact already written below package_root."""
    artifact_path = package_root / relative_path
    data = artifact_path.read_bytes()
    return {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "relative_path": relative_path,
        "media_type": media_type,
        "schema_ref": schema_ref,
        "sha256": sha256_bytes(data),
        "byte_size": len(data),
        "required": required,
        "status": status,
        "source_reference_ids": source_reference_ids or [],
        "depends_on_artifact_ids": depends_on_artifact_ids or [],
    }


def ordered_artifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(artifacts, key=lambda item: item["artifact_id"])


def manifest_for_checksum(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a manifest copy with recursive checksum fields removed."""
    clone = copy.deepcopy(manifest)
    integrity = clone.setdefault("integrity", {})
    integrity.pop("package_manifest_sha256", None)
    return clone


def manifest_sha256(manifest: dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(manifest_for_checksum(manifest)))


def finalize_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    finalized = copy.deepcopy(manifest)
    inventory = finalized.get("artifact_inventory", [])
    finalized["artifact_inventory"] = ordered_artifacts(inventory)
    finalized.setdefault("integrity", {})
    finalized["integrity"]["package_manifest_sha256"] = manifest_sha256(finalized)
    return finalized


def write_canonical_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(payload))
