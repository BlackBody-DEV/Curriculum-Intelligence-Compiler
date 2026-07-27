"""Shared IO helpers for canonical promotion preparation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json_bytes(data: Any) -> bytes:
    return (json.dumps(data, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("utf-8")


def write_json(path: Path, data: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=True).encode("utf-8") + b"\n"
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def ensure_beneath(root: Path, target: Path) -> Path:
    root_real = root.resolve()
    target_real = target.resolve()
    if target_real != root_real and root_real not in target_real.parents:
        raise ValueError(f"path escape rejected: {target}")
    return target_real


def root_relative(root: Path, path: Path) -> str:
    return ensure_beneath(root, path).relative_to(root.resolve()).as_posix()


def stable_hash(data: Any) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8") + b"\n"
    return sha256_bytes(payload)
