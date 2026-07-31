"""Static contract for the maintained compiler certification workflow."""

from pathlib import Path
import re


WORKFLOW = Path(".github/workflows/compiler-continuous-clean-room.yml")
LEGACY_WORKFLOW = Path(".github/workflows/wave056-validation.yml")


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_workflow_replaces_task_specific_trigger_with_main_and_pull_request_certification():
    text = workflow_text()
    assert WORKFLOW.is_file()
    assert not LEGACY_WORKFLOW.exists()
    assert re.search(r"(?m)^  pull_request:\n    branches:\n      - main$", text)
    assert re.search(
        r'(?m)^  push:\n    branches:\n      - main\n      - "validation/compiler-continuous-clean-room-\*"$',
        text,
    )
    assert re.search(r"(?m)^  workflow_dispatch:$", text)
    assert "task/compiler-" not in text


def test_workflow_runs_each_expensive_suite_exactly_once_without_filters_or_weakening():
    text = workflow_text()
    command = "python -m pytest -p no:cacheprovider tests/course_compiler_demo"
    assert text.count(command) == 2
    assert "Full compiler suite" in text
    assert "Git-less clean-room full suite" in text
    for weakening in ("continue-on-error", "|| true", "--ignore", "--deselect", "pytest -k", "pytest -m", "--maxfail"):
        assert weakening not in text
    assert "PHASE_E_PROTECTED_INTEGRATION" not in text


def test_clean_room_uses_the_exact_tracked_tree_without_git_metadata():
    text = workflow_text()
    assert "git archive --format=tar HEAD" in text
    assert 'test ! -e "$clean_root/.git"' in text
    assert 'cd "$clean_root"' in text
    assert "cp -R" not in text
    assert "PYTHONDONTWRITEBYTECODE" in text


def test_storage_concurrency_permissions_and_portability_fail_closed():
    text = workflow_text()
    assert 'df -Pk "$RUNNER_TEMP"' in text
    assert "4 * 1024 * 1024" in text
    assert "set -euo pipefail" in text
    assert "cancel-in-progress: true" in text
    assert "github.event.pull_request.number || github.ref" in text
    assert re.search(r"(?m)^permissions:\n  contents: read$", text)
    assert "runs-on: ubuntu-latest" in text
    for forbidden in ("/Users/", "/home/", "self-hosted", "secrets.", "protected Phase E"):
        assert forbidden not in text
