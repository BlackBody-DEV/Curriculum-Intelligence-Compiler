"""Public version-one contracts for batch generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import json
from typing import Any


class BatchContractError(ValueError):
    pass


class JsonContract:
    version: str

    def __post_init__(self) -> None:
        if self.version != "1.0":
            raise BatchContractError("version must be 1.0")
        for item in fields(self):
            if item.name == "version" or not (item.name.endswith("_id") or item.name in {"question_identity", "reason", "output_hash"}):
                continue
            _identity(getattr(self, item.name), item.name)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, value: dict[str, Any]):
        if not isinstance(value, dict):
            raise BatchContractError("contract payload must be an object")
        allowed = {item.name for item in fields(cls)}
        unknown = set(value) - allowed
        if unknown:
            raise BatchContractError(f"unknown fields: {sorted(unknown)}")
        normalized = dict(value)
        for name in {"family_ids", "replacement_job_ids", "completed_job_ids", "outcomes", "lineages", "final_identities"}:
            if name in normalized and isinstance(normalized[name], list):
                normalized[name] = tuple(normalized[name])
        return cls(**normalized)

    @classmethod
    def from_json(cls, value: str):
        return cls.from_dict(json.loads(value))


def _identity(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise BatchContractError(f"{field_name} is required")


@dataclass(frozen=True)
class BatchGenerationPlan(JsonContract):
    plan_id: str
    manifest_id: str
    family_ids: tuple[str, ...]
    jobs_per_family: int
    seed: str
    max_workers: int = 4
    max_regenerations: int = 1
    version: str = "1.0"

    def __post_init__(self):
        super().__post_init__()
        for value, name in ((self.plan_id, "plan_id"), (self.manifest_id, "manifest_id"), (self.seed, "seed")):
            _identity(value, name)
        if not self.family_ids or len(set(self.family_ids)) != len(self.family_ids): raise BatchContractError("family_ids must be unique and nonempty")
        if self.jobs_per_family < 1: raise BatchContractError("jobs_per_family must be positive")
        if self.max_workers < 1: raise BatchContractError("max_workers must be positive")
        if self.max_regenerations < 0: raise BatchContractError("max_regenerations cannot be negative")


@dataclass(frozen=True)
class GenerationJob(JsonContract):
    job_id: str
    family_id: str
    question_identity: str
    seed: int
    version: str = "1.0"


@dataclass(frozen=True)
class DerivationJob(JsonContract):
    job_id: str
    generation_job_id: str
    question_identity: str
    version: str = "1.0"


@dataclass(frozen=True)
class ValidationJob(JsonContract):
    job_id: str
    generation_job_id: str
    derivation_job_id: str
    question_identity: str
    version: str = "1.0"


@dataclass(frozen=True)
class ReviewQueueItem(JsonContract):
    item_id: str
    generation_job_id: str
    reason: str
    terminal: bool
    version: str = "1.0"


@dataclass(frozen=True)
class GenerationAttempt(JsonContract):
    attempt_id: str
    generation_job_id: str
    attempt_number: int
    output_hash: str
    accepted: bool
    version: str = "1.0"

    def __post_init__(self):
        super().__post_init__()
        if self.attempt_number < 0: raise BatchContractError("attempt_number cannot be negative")


@dataclass(frozen=True)
class RegenerationLineage(JsonContract):
    original_job_id: str
    replacement_job_ids: tuple[str, ...] = ()
    version: str = "1.0"


@dataclass(frozen=True)
class BatchCheckpoint(JsonContract):
    plan_hash: str
    completed_job_ids: tuple[str, ...] = ()
    outcomes: tuple[dict[str, Any], ...] = ()
    lineages: tuple[dict[str, Any], ...] = ()
    version: str = "1.0"


@dataclass(frozen=True)
class BatchRunSummary(JsonContract):
    plan_id: str
    generation_jobs: int
    derivation_jobs: int
    validation_outcomes: int
    accepted: int
    review_items: int
    final_identities: tuple[str, ...]
    manifest_sha256: str
    restarted: bool
    max_workers: int
    peak_concurrency: int
    version: str = "1.0"
