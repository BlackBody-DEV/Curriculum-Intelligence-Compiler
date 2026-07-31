"""Shared dashboard test helpers."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


_CANONICAL_PORTABLE_TESTS = {
    "test_canonical_promotion_evidence_gates.py",
    "test_canonical_promotion_preparation.py",
    "test_canonical_promotion_portable_fixtures.py",
    "test_canonical_promotion_universal_reconciliation.py",
    "test_dashboard_canonical_promotion.py",
}


def pytest_configure(config):
    config.addinivalue_line("markers", "portable_baseline: repository-portable default baseline coverage")
    config.addinivalue_line("markers", "protected_fixture_integration: opt-in protected Phase E integration coverage")
    config.addinivalue_line("markers", "host_environment_integration: opt-in private host environment parity coverage")


@pytest.fixture(autouse=True)
def portable_canonical_promotion_dependencies(request, monkeypatch):
    """Route canonical-promotion tests through repository-owned public contracts."""
    if Path(str(request.node.fspath)).name not in _CANONICAL_PORTABLE_TESTS:
        yield
        return
    from tools.course_compiler_demo.canonical_promotion import preparation_mode
    from tools.course_compiler_demo.phase_e_production import family_adapters
    from tools.course_compiler_demo.testing.canonical_promotion_portable import (
        PORTABLE_AUTHORITY_ROOT,
        validate_portable_canonical_fixture,
    )
    from tools.course_compiler_demo.testing.phase_e_portable import portable_adapters

    validate_portable_canonical_fixture()
    portable_phase_e_root = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "course_compiler_demo"
        / "phase_e_portable_replay"
    )
    if os.environ.get("PHASE_E_PROTECTED_INTEGRATION") != "1":
        monkeypatch.setattr(family_adapters, "_ADAPTERS", portable_adapters(portable_phase_e_root))
    monkeypatch.setattr(preparation_mode, "REFERENCE_ROOT", PORTABLE_AUTHORITY_ROOT)
    yield


@pytest.fixture(scope="session")
def portable_production_root(tmp_path_factory):
    from tools.course_compiler_demo.testing.canonical_promotion_portable import build_portable_production_banks

    return build_portable_production_banks(tmp_path_factory.mktemp("portable-production-banks"))
