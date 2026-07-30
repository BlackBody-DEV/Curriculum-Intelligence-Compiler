"""Resolve rights-safe source-inbox fixtures without requiring a host path."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


SOURCE_INBOX_ENV = "AXIOMIQ_SOURCE_INBOX_ROOT"
HOST_SOURCE_INBOX_OPT_IN_ENV = "AXIOMIQ_HOST_SOURCE_INBOX_INTEGRATION"
HOST_SOURCE_INBOX = Path("/Users/fanarichardson/Documents/AxiomIQ_Source_Inbox")
COMMITTED_SOURCE_INBOX = (
    Path(__file__).resolve().parents[3]
    / "tests"
    / "fixtures"
    / "course_compiler_demo"
    / "source_inbox_portable"
)


def resolve_source_inbox_root(
    explicit: str | Path | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve explicit argument, then environment, then committed fixtures."""
    environment = os.environ if environ is None else environ
    configured = explicit or environment.get(SOURCE_INBOX_ENV)
    candidate = configured or COMMITTED_SOURCE_INBOX
    root = Path(candidate).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"source inbox root is not a directory: {root}")
    if configured is None and not (root / "fixture_manifest.json").is_file():
        raise FileNotFoundError(f"committed source inbox lacks fixture_manifest.json: {root}")
    return root


def optional_host_source_inbox(
    *, environ: Mapping[str, str] | None = None
) -> Path | None:
    """Return the legacy host inbox only under explicit opt-in and when mounted."""
    environment = os.environ if environ is None else environ
    opted_in = environment.get(HOST_SOURCE_INBOX_OPT_IN_ENV) == "1"
    return HOST_SOURCE_INBOX if opted_in and HOST_SOURCE_INBOX.is_dir() else None
