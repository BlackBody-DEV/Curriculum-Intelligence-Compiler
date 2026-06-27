"""Minimal package validation helpers for demo artifacts."""

from __future__ import annotations

from typing import Any


def validate_demo_package(package: dict[str, Any], required_fields: list[str]) -> None:
    missing = [field for field in required_fields if field not in package]
    if missing:
        raise ValueError(f"Package missing required fields: {missing}")
    if package.get("status") != "demo_unverified":
        raise ValueError("Package must use status demo_unverified.")
