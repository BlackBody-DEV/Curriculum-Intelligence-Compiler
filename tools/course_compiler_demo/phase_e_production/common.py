"""Shared primitives for Phase E blind replay.

This module intentionally contains only generic IO and hashing helpers. It must
not contain benchmark prompts, answers, correct options, or worked solutions.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PROHIBITED_BENCHMARK_FIELDS = {
    "benchmark_prompt",
    "expected_answer",
    "worked_solution",
    "correct_option",
    "correct_option_id",
    "answer_parameters",
    "answer_bearing_parameters",
    "review_conclusions",
    "content_fingerprint",
    "content_fingerprints",
    "canary",
    "benchmark_canary",
}


def canonical_json_bytes(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, indent=2).encode("utf-8") + b"\n"


def write_json(path: Path, data: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(data)
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


def scan_for_values(path: Path, values: list[str]) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return [value for value in values if value and value in text]



def parse_component_vectors(text: str) -> list[tuple[float, float]]:
    """Extract 2D component vectors like <65,20> from prompt text."""
    import re

    vectors: list[tuple[float, float]] = []
    for x_raw, y_raw in re.findall(r"<\s*([-+]?\d+(?:\.\d+)?)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*>", text):
        vectors.append((float(x_raw), float(y_raw)))
    return vectors


def resultant_magnitude_from_text(text: str) -> float:
    vectors = parse_component_vectors(text)
    if not vectors:
        raise ValueError("no component vectors found")
    rx = sum(x for x, _y in vectors)
    ry = sum(y for _x, y in vectors)
    return round((rx * rx + ry * ry) ** 0.5, 6)
