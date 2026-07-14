"""Read-only package safety and manifest loading helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.course_compiler_demo.reference_consumer.models import (
    COMPILER_ROOT,
    FIXTURE_ROOT,
    FROZEN_CONTRACT_ROOT,
    FROZEN_VALIDATOR_ROOT,
)


def _contains_parent_traversal(path: Path) -> bool:
    return any(part == ".." for part in path.parts)


def _reject_adaptive_path(path: Path | str) -> None:
    text = str(path)
    if "adaptive-platform" in text or "AxiomIQ_Alpha2.0" in text:
        raise ValueError("Path must not reference adaptive-platform.")


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_package_root(package_root: Path | str) -> Path:
    raw = Path(package_root)
    _reject_adaptive_path(raw)
    if _contains_parent_traversal(raw):
        raise ValueError("Package path must not contain parent traversal.")
    resolved = raw.resolve()
    _reject_adaptive_path(resolved)
    if not resolved.is_dir():
        raise ValueError("Package directory does not exist.")
    if not _inside(resolved, COMPILER_ROOT):
        raise ValueError("Package path must stay inside the compiler repository.")
    return resolved


def safe_output_dir(output: Path | str | None, package_root: Path) -> Path | None:
    if output is None:
        return None
    raw = Path(output)
    _reject_adaptive_path(raw)
    if _contains_parent_traversal(raw):
        raise ValueError("Output path must not contain parent traversal.")
    resolved = raw.resolve()
    _reject_adaptive_path(resolved)
    if not _inside(resolved, COMPILER_ROOT):
        raise ValueError("Output path must stay inside the compiler repository.")
    for forbidden, message in [
        (package_root, "Output path must not overlap the package being consumed."),
        (FIXTURE_ROOT, "Output path must not overlap frozen fixture paths."),
        (FROZEN_CONTRACT_ROOT, "Output path must not overlap frozen contract paths."),
        (FROZEN_VALIDATOR_ROOT, "Output path must not overlap frozen validator paths."),
    ]:
        if _inside(resolved, forbidden):
            raise ValueError(message)
    if resolved.exists() and resolved.is_symlink() and not _inside(resolved.resolve(), COMPILER_ROOT):
        raise ValueError("Output symlink must not escape compiler repository.")
    return resolved


def load_manifest(package_root: Path) -> dict[str, Any]:
    path = package_root / "manifest.json"
    if not path.is_file():
        raise ValueError("Manifest missing after validation handoff.")
    return json.loads(path.read_text())


def load_artifact_payload(package_root: Path, descriptor: dict[str, Any]) -> Any:
    path = package_root / str(descriptor.get("relative_path", ""))
    if descriptor.get("media_type") == "application/json" and path.is_file():
        return json.loads(path.read_text())
    return None
