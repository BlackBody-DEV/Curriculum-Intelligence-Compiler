"""Sealed benchmark storage for Phase E golden replay."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .common import ensure_beneath, load_json, sha256_file, write_json

AUTHORIZED_READER = "golden_comparator"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class SealedBenchmarkAccessError(PermissionError):
    """Raised when a sealed benchmark access violates the blind boundary."""


def _append_access_log(log_path: Path, event: dict[str, Any]) -> None:
    event = {"benchmark_access_timestamp": utc_now(), **event}
    existing: list[dict[str, Any]] = []
    if log_path.exists():
        existing = load_json(log_path)
    existing.append(event)
    write_json(log_path, existing)


def load_sealed_benchmark(
    *,
    store_root: Path,
    benchmark_identifier: str,
    sealed_benchmark_path: Path,
    reader_component: str,
    access_reason: str,
    log_path: Path,
) -> dict[str, Any]:
    try:
        sealed_path = ensure_beneath(store_root, sealed_benchmark_path)
    except ValueError as exc:
        _append_access_log(
            log_path,
            {
                "benchmark_identifier": benchmark_identifier,
                "reader_component": reader_component,
                "outcome": "rejected_path_escape",
                "reason": str(exc),
            },
        )
        raise SealedBenchmarkAccessError(str(exc)) from exc
    if reader_component != AUTHORIZED_READER:
        _append_access_log(
            log_path,
            {
                "benchmark_identifier": benchmark_identifier,
                "reader_component": reader_component,
                "outcome": f"rejected_{reader_component}_access",
                "reason": "sealed benchmarks may be read only by golden_comparator",
            },
        )
        raise SealedBenchmarkAccessError("sealed benchmark access rejected")
    if not sealed_path.exists():
        _append_access_log(
            log_path,
            {
                "benchmark_identifier": benchmark_identifier,
                "reader_component": reader_component,
                "outcome": "rejected_unknown_benchmark_identifier",
            },
        )
        raise SealedBenchmarkAccessError("unknown benchmark identifier")
    data = load_json(sealed_path)
    if data.get("benchmark_identifier") != benchmark_identifier:
        _append_access_log(
            log_path,
            {
                "benchmark_identifier": benchmark_identifier,
                "reader_component": reader_component,
                "outcome": "rejected_unknown_benchmark_identifier",
                "reason": "identifier mismatch",
            },
        )
        raise SealedBenchmarkAccessError("benchmark identifier mismatch")
    _append_access_log(
        log_path,
        {
            "benchmark_identifier": benchmark_identifier,
            "reader_component": reader_component,
            "outcome": "authorized_comparator_access",
            "sealed_benchmark_sha256": sha256_file(sealed_path),
            "benchmark_access_reason": access_reason,
        },
    )
    return data
