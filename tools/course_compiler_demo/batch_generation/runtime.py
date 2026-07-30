"""Filesystem-safe deterministic batch execution with checkpoint recovery."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
from threading import Lock
from typing import Protocol

from .models import BatchCheckpoint, BatchGenerationPlan, BatchRunSummary, DerivationJob, GenerationJob, ValidationJob


class OutputRootError(ValueError):
    pass


class Provider(Protocol):
    def generate(self, job: GenerationJob, attempt: int) -> dict: ...
    def derive(self, generated: dict) -> dict: ...
    def validate(self, generated: dict, derived: dict) -> dict: ...


class DeterministicFixtureProvider:
    """Offline provider. ``fail_first`` job IDs exercise regeneration."""
    def __init__(self, fail_first: frozenset[str] = frozenset(), fail_always: frozenset[str] = frozenset()):
        self.fail_first, self.fail_always = fail_first, fail_always

    def generate(self, job: GenerationJob, attempt: int) -> dict:
        digest = hashlib.sha256(f"{job.seed}:{attempt}".encode()).hexdigest()
        return {"question_identity": job.question_identity, "job_id": job.job_id, "attempt": attempt, "content_hash": digest}

    def derive(self, generated: dict) -> dict:
        return {"question_identity": generated["question_identity"], "answer_hash": hashlib.sha256((generated["content_hash"] + ":answer").encode()).hexdigest()}

    def validate(self, generated: dict, derived: dict) -> dict:
        job_id, attempt = generated["job_id"], generated["attempt"]
        passed = job_id not in self.fail_always and not (job_id in self.fail_first and attempt == 0)
        return {"question_identity": generated["question_identity"], "passed": passed, "reason": "PASS" if passed else "FIXTURE_REJECTION"}


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


class BatchOrchestrator:
    def __init__(self, output_root: Path, provider: Provider):
        self.root = Path(output_root)
        if not self.root.is_absolute(): raise OutputRootError("output root must be absolute")
        if self.root.exists() and self.root.is_symlink(): raise OutputRootError("output root cannot be a symlink")
        probe = self.root if self.root.exists() else self.root.parent
        for ancestor in (probe, *probe.parents):
            if (ancestor / ".git").exists():
                raise OutputRootError("output root must be outside repositories and protected worktrees")
        self.root.mkdir(parents=True, exist_ok=True)
        self.root = self.root.resolve(strict=True)
        self.provider = provider
        self._lock = Lock()
        self._active = 0
        self._peak = 0

    def _provider_call(self, operation, *args):
        with self._lock:
            self._active += 1
            self._peak = max(self._peak, self._active)
        try:
            return operation(*args)
        finally:
            with self._lock:
                self._active -= 1

    def _path(self, name: str) -> Path:
        candidate = self.root / name
        parent = candidate.parent.resolve(strict=True)
        if parent != self.root or candidate.is_symlink(): raise OutputRootError("path escapes output root")
        return candidate

    @staticmethod
    def expand(plan: BatchGenerationPlan) -> tuple[GenerationJob, ...]:
        jobs = []
        for family in sorted(plan.family_ids):
            for index in range(plan.jobs_per_family):
                token = hashlib.sha256(f"{plan.seed}:{family}:{index}".encode()).hexdigest()
                jobs.append(GenerationJob(f"job-{token[:20]}", family, f"question-{token[:24]}", int(token[:16], 16)))
        return tuple(jobs)

    def _checkpoint(self, plan_hash: str, outcomes: list[dict], lineages: list[dict]) -> None:
        checkpoint = BatchCheckpoint(plan_hash, tuple(sorted(x["job_id"] for x in outcomes)), tuple(sorted(outcomes, key=lambda x: x["job_id"])), tuple(sorted(lineages, key=lambda x: x["original_job_id"])))
        target, temporary = self._path("checkpoint.json"), self._path("checkpoint.tmp")
        temporary.write_bytes(_canonical(checkpoint.to_dict()))
        os.replace(temporary, target)

    def run(self, plan: BatchGenerationPlan, interrupt_after: int | None = None) -> BatchRunSummary | None:
        plan_hash = hashlib.sha256(_canonical(plan.to_dict())).hexdigest()
        checkpoint_path = self._path("checkpoint.json")
        outcomes: list[dict] = []
        lineages: list[dict] = []
        restarted = checkpoint_path.exists()
        if restarted:
            saved = json.loads(checkpoint_path.read_text())
            if saved["plan_hash"] != plan_hash: raise ValueError("checkpoint plan mismatch")
            outcomes, lineages = saved["outcomes"], saved["lineages"]
        completed = {item["job_id"] for item in outcomes}
        pending = [job for job in self.expand(plan) if job.job_id not in completed]

        processed = 0
        attempts = {job.job_id: 0 for job in pending}
        replacements = {job.job_id: [] for job in pending}
        generation_queue = list(pending)
        while generation_queue:
            generated_queue: list[tuple[GenerationJob, dict]] = []
            failed_stage: list[tuple[GenerationJob, str]] = []
            with ThreadPoolExecutor(max_workers=plan.max_workers) as pool:
                futures = {pool.submit(self._provider_call, self.provider.generate, job, attempts[job.job_id]): job for job in generation_queue}
                for future in as_completed(futures):
                    job = futures[future]
                    try: generated_queue.append((job, future.result()))
                    except Exception as exc: failed_stage.append((job, f"GENERATION_EXCEPTION:{type(exc).__name__}"))

            derivation_queue: list[tuple[GenerationJob, dict, DerivationJob]] = []
            for job, generated in generated_queue:
                derivation_queue.append((job, generated, DerivationJob(f"derive-{job.job_id}-{attempts[job.job_id]}", job.job_id, job.question_identity)))
            derived_queue: list[tuple[GenerationJob, dict, DerivationJob, dict]] = []
            with ThreadPoolExecutor(max_workers=plan.max_workers) as pool:
                futures = {pool.submit(self._provider_call, self.provider.derive, generated): (job, generated, djob) for job, generated, djob in derivation_queue}
                for future in as_completed(futures):
                    job, generated, djob = futures[future]
                    try: derived_queue.append((job, generated, djob, future.result()))
                    except Exception as exc: failed_stage.append((job, f"DERIVATION_EXCEPTION:{type(exc).__name__}"))

            validation_queue: list[tuple[GenerationJob, dict, DerivationJob, dict, ValidationJob]] = []
            for job, generated, djob, derived in derived_queue:
                validation_queue.append((job, generated, djob, derived, ValidationJob(f"validate-{job.job_id}-{attempts[job.job_id]}", job.job_id, djob.job_id, job.question_identity)))
            validated: list[tuple[GenerationJob, dict, DerivationJob, dict, ValidationJob, dict]] = []
            with ThreadPoolExecutor(max_workers=plan.max_workers) as pool:
                futures = {pool.submit(self._provider_call, self.provider.validate, generated, derived): (job, generated, djob, derived, vjob) for job, generated, djob, derived, vjob in validation_queue}
                for future in as_completed(futures):
                    job, generated, djob, derived, vjob = futures[future]
                    try: validated.append((job, generated, djob, derived, vjob, future.result()))
                    except Exception as exc: failed_stage.append((job, f"VALIDATION_EXCEPTION:{type(exc).__name__}"))

            retry_queue: list[GenerationJob] = []
            for job, generated, djob, derived, vjob, validation in validated:
                if validation["passed"]:
                    outcome = {"job_id": job.job_id, "question_identity": job.question_identity, "attempts": attempts[job.job_id] + 1, "accepted": True, "generation": generated, "derivation_job": djob.to_dict(), "derivation": derived, "validation_job": vjob.to_dict(), "validation": validation}
                elif attempts[job.job_id] < plan.max_regenerations:
                    attempts[job.job_id] += 1
                    replacements[job.job_id].append(f"{job.job_id}-replacement-{attempts[job.job_id]}")
                    retry_queue.append(job); continue
                else:
                    outcome = {"job_id": job.job_id, "question_identity": job.question_identity, "attempts": attempts[job.job_id] + 1, "accepted": False, "generation": generated, "derivation_job": djob.to_dict(), "derivation": derived, "validation_job": vjob.to_dict(), "validation": validation}
                outcomes.append(outcome); lineages.append({"original_job_id": job.job_id, "replacement_job_ids": replacements[job.job_id]}); processed += 1
                self._checkpoint(plan_hash, outcomes, lineages)
                if interrupt_after is not None and processed >= interrupt_after: return None
            for job, reason in failed_stage:
                outcome = {"job_id": job.job_id, "question_identity": job.question_identity, "attempts": attempts[job.job_id] + 1, "accepted": False, "failure_stage": reason}
                outcomes.append(outcome); lineages.append({"original_job_id": job.job_id, "replacement_job_ids": replacements[job.job_id]}); processed += 1
                self._checkpoint(plan_hash, outcomes, lineages)
                if interrupt_after is not None and processed >= interrupt_after: return None
            generation_queue = retry_queue
        ordered = sorted(outcomes, key=lambda x: x["job_id"])
        final_ids = tuple(sorted(x["question_identity"] for x in ordered if x["accepted"]))
        if len(final_ids) != len(set(final_ids)): raise RuntimeError("duplicate final identity")
        manifest = {"plan_id": plan.plan_id, "outcomes": ordered, "lineages": sorted(lineages, key=lambda x: x["original_job_id"])}
        manifest_bytes = _canonical(manifest)
        self._path("final_manifest.json").write_bytes(manifest_bytes)
        return BatchRunSummary(plan.plan_id, len(ordered), len(ordered), len(ordered), len(final_ids), len(ordered) - len(final_ids), final_ids, hashlib.sha256(manifest_bytes).hexdigest(), restarted, plan.max_workers, self._peak)
