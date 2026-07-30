"""Shared dashboard test helpers."""

from __future__ import annotations


def pytest_configure(config):
    config.addinivalue_line("markers", "portable_baseline: repository-portable default baseline coverage")
    config.addinivalue_line("markers", "protected_fixture_integration: opt-in protected Phase E integration coverage")
    config.addinivalue_line("markers", "host_environment_integration: opt-in private host environment parity coverage")
