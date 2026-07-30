from pathlib import Path
import json
import os

import pytest

from tools.course_compiler_demo.batch_generation import BatchGenerationPlan, BatchOrchestrator, DeterministicFixtureProvider, GenerationJob, OutputRootError
from tools.course_compiler_demo.batch_generation.models import BatchContractError


def plan(count=10, workers=3, regenerations=1):
    return BatchGenerationPlan("plan-1", "manifest-1", ("family-1",), count, "seed-1", workers, regenerations)


def test_manifest_expansion_and_seed_are_deterministic():
    assert BatchOrchestrator.expand(plan()) == BatchOrchestrator.expand(plan())
    assert len(BatchOrchestrator.expand(plan())) == 10
    assert len({x.question_identity for x in BatchOrchestrator.expand(plan())}) == 10


def test_contract_round_trip_and_strict_validation():
    job = BatchOrchestrator.expand(plan(1))[0]
    assert GenerationJob.from_json(job.to_json()) == job
    with pytest.raises(BatchContractError): GenerationJob.from_dict({**job.to_dict(), "extra": True})
    with pytest.raises(BatchContractError): GenerationJob("", "family", "question", 1)
    with pytest.raises(BatchContractError): GenerationJob("job", "family", "question", 1, version="2.0")
    assert BatchGenerationPlan.from_json(plan().to_json()) == plan()


def test_checkpoint_restart_idempotency_and_deterministic_manifest(tmp_path):
    root = tmp_path / "external"
    runner = BatchOrchestrator(root, DeterministicFixtureProvider())
    assert runner.run(plan(30), interrupt_after=7) is None
    checkpoint = json.loads((root / "checkpoint.json").read_text())
    assert len(checkpoint["completed_job_ids"]) >= 7
    summary = BatchOrchestrator(root, DeterministicFixtureProvider()).run(plan(30))
    assert summary.restarted and summary.generation_jobs == summary.derivation_jobs == summary.validation_outcomes == 30
    reopened = BatchOrchestrator(root, DeterministicFixtureProvider()).run(plan(30))
    assert reopened.manifest_sha256 == summary.manifest_sha256


def test_bounded_regeneration_lineage_and_failed_job_isolation(tmp_path):
    jobs = BatchOrchestrator.expand(plan(3))
    provider = DeterministicFixtureProvider(frozenset({jobs[0].job_id}), frozenset({jobs[1].job_id}))
    summary = BatchOrchestrator(tmp_path / "out", provider).run(plan(3))
    manifest = json.loads((tmp_path / "out/final_manifest.json").read_text())
    assert summary.accepted == 2 and summary.review_items == 1
    assert max(x["attempts"] for x in manifest["outcomes"]) == 2
    assert any(x["replacement_job_ids"] for x in manifest["lineages"])


def test_external_absolute_root_and_symlink_escape_rejected(tmp_path):
    with pytest.raises(OutputRootError): BatchOrchestrator(Path("relative"), DeterministicFixtureProvider())
    target = tmp_path / "target"; target.mkdir()
    link = tmp_path / "link"; link.symlink_to(target, target_is_directory=True)
    with pytest.raises(OutputRootError): BatchOrchestrator(link, DeterministicFixtureProvider())
    root = tmp_path / "root"; runner = BatchOrchestrator(root, DeterministicFixtureProvider())
    (root / "checkpoint.json").symlink_to(tmp_path / "escaped")
    with pytest.raises(OutputRootError): runner.run(plan(1))
    repository = tmp_path / "repository"; repository.mkdir(); (repository / ".git").mkdir()
    with pytest.raises(OutputRootError): BatchOrchestrator(repository / "outputs", DeterministicFixtureProvider())


def test_provider_exception_isolated_as_failed_job(tmp_path):
    class RaisingProvider(DeterministicFixtureProvider):
        def derive(self, generated):
            if generated["question_identity"].endswith(BatchOrchestrator.expand(plan(3))[0].question_identity[-6:]):
                raise RuntimeError("fixture provider failure")
            return super().derive(generated)
    summary = BatchOrchestrator(tmp_path / "exception-output", RaisingProvider()).run(plan(3))
    manifest = json.loads((tmp_path / "exception-output/final_manifest.json").read_text())
    assert summary.generation_jobs == 3 and summary.accepted == 2 and summary.review_items == 1
    assert any(item.get("failure_stage") == "DERIVATION_EXCEPTION:RuntimeError" for item in manifest["outcomes"])
    assert sum("derivation_job" in item for item in manifest["outcomes"]) == 2


def test_500_job_gitless_external_dry_run(tmp_path):
    root = tmp_path / "external-output"
    runner = BatchOrchestrator(root, DeterministicFixtureProvider())
    assert runner.run(plan(500, workers=8), interrupt_after=113) is None
    summary = BatchOrchestrator(root, DeterministicFixtureProvider()).run(plan(500, workers=8))
    assert summary.generation_jobs == summary.derivation_jobs == summary.validation_outcomes == 500
    assert summary.accepted == 500 and len(set(summary.final_identities)) == 500
    assert summary.max_workers == 8 and 1 <= summary.peak_concurrency <= 8 and summary.restarted
    assert not (root / ".git").exists()
    manifest = json.loads((root / "final_manifest.json").read_text())
    assert sum("derivation_job" in item for item in manifest["outcomes"]) == 500
    assert sum("validation_job" in item for item in manifest["outcomes"]) == 500
    fresh = BatchOrchestrator(tmp_path / "fresh-output", DeterministicFixtureProvider()).run(plan(500, workers=8))
    assert fresh.manifest_sha256 == summary.manifest_sha256
