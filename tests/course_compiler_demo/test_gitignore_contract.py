"""Contract tests for the repository's deliberately narrow ignore policy."""

from __future__ import annotations

from pathlib import Path
import subprocess


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_RULES = (
    "**pycache**/",
    "*.py[cod]",
    "/reports/course_compiler_demo/dashboard_runs/",
    ".worktrees/",
)
TRACKED_VISIBILITY_SAMPLES = (
    "docs/course_compiler_demo/releases/COMPILER_MILESTONE_093_CHECKPOINT.md",
    "reports/course_compiler_demo/alpha2_reference_census_001/ALPHA2_REFERENCE_CENSUS_REPORT.md",
    "reports/course_compiler_demo/dashboard_runs/dashboard_acceptance_physics_20260718_001/acceptance_proof.json",
    "compiler_output/intake_runs/INTAKE_20260630_041840_001/demo_report.md",
)


def _git(repository: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ("git", *arguments),
        cwd=repository,
        check=check,
        text=True,
        capture_output=True,
    )


def _write(repository: Path, relative_path: str) -> None:
    path = repository / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("contract fixture\n", encoding="utf-8")


def _repository_with_tracked_samples(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "--quiet")
    for relative_path in TRACKED_VISIBILITY_SAMPLES:
        _write(tmp_path, relative_path)
    _git(tmp_path, "add", *TRACKED_VISIBILITY_SAMPLES)
    (tmp_path / ".gitignore").write_text(
        (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    return tmp_path


def _is_ignored(repository: Path, relative_path: str) -> bool:
    result = _git(repository, "check-ignore", "--quiet", "--no-index", "--", relative_path, check=False)
    assert result.returncode in (0, 1), result.stderr
    return result.returncode == 0


def test_gitignore_contains_only_the_four_authorized_rules() -> None:
    rules = tuple((REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines())
    assert rules == EXPECTED_RULES


def test_python_bytecode_and_pycache_directories_are_ignored(tmp_path: Path) -> None:
    repository = _repository_with_tracked_samples(tmp_path)
    for relative_path in (
        "src/__pycache__/module.cache",
        "src/module.pyc",
        "src/module.pyo",
        "src/module.pyd",
    ):
        _write(repository, relative_path)
        assert _is_ignored(repository, relative_path)
    for relative_path in ("src/module.py", "src/module.pya"):
        _write(repository, relative_path)
        assert not _is_ignored(repository, relative_path)


def test_only_root_dashboard_runtime_outputs_are_ignored(tmp_path: Path) -> None:
    repository = _repository_with_tracked_samples(tmp_path)
    ignored = "reports/course_compiler_demo/dashboard_runs/local-runtime/run.json"
    broader_report = "reports/course_compiler_demo/operator-review/report.json"
    nested_dashboard = "nested/reports/course_compiler_demo/dashboard_runs/run.json"
    for relative_path in (ignored, broader_report, nested_dashboard):
        _write(repository, relative_path)
    assert _is_ignored(repository, ignored)
    assert not _is_ignored(repository, broader_report)
    assert not _is_ignored(repository, nested_dashboard)


def test_tracked_release_reports_dashboard_fixtures_and_compiler_artifacts_remain_visible(
    tmp_path: Path,
) -> None:
    for relative_path in TRACKED_VISIBILITY_SAMPLES:
        assert (REPOSITORY_ROOT / relative_path).is_file()
    repository = _repository_with_tracked_samples(tmp_path)
    tracked = set(_git(repository, "ls-files").stdout.splitlines())
    assert set(TRACKED_VISIBILITY_SAMPLES) <= tracked
