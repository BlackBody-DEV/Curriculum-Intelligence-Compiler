"""Zero-boundary-contact evidence for reproduction runs."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from tools.course_compiler_demo.integration_readiness.models import COMPILER_ROOT


BOUNDARY_FALSES = {
    "adaptive_platform_accessed": False,
    "adaptive_platform_modified": False,
    "adaptive_platform_git_activity": False,
    "adaptive_platform_files_staged": False,
    "adaptive_platform_commit_prepared": False,
    "adaptive_platform_commit_created": False,
    "adaptive_platform_push_performed": False,
    "adaptive_platform_staging_directory_written": False,
    "database_contacted": False,
    "network_endpoint_contacted": False,
    "runtime_route_created_or_called": False,
    "learner_loop_work_performed": False,
    "grading_work_performed": False,
    "persistence_work_performed": False,
    "retrieval_work_performed": False,
    "canonical_promotion_performed": False,
    "student_visible_output_created": False,
    "source_package_modified": False,
}


def boundary_evidence(
    *,
    allowed_output_root: Path | None,
    commands_executed: list[str],
    files_read: list[str],
    files_written: list[str],
    environment_names: list[str] | None = None,
) -> dict[str, Any]:
    modules = sorted(
        name for name in sys.modules if name.startswith("tools.course_compiler_demo")
    )
    return {
        **BOUNDARY_FALSES,
        "compiler_repository_root": str(COMPILER_ROOT),
        "allowed_output_root": str(allowed_output_root) if allowed_output_root else None,
        "commands_executed": sorted(commands_executed),
        "files_read": sorted(set(files_read)),
        "files_written": sorted(set(files_written)),
        "environment_variable_names_consulted": sorted(environment_names or []),
        "external_modules_imported": modules,
    }
