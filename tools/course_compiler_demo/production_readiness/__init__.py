"""Fail-closed contracts for a separately authorized student activation."""

from .readiness import (
    ADAPTIVE_MAIN_BASELINE,
    COMPILER_BASELINE,
    ProductionReadinessError,
    build_import_package,
    classify_replay,
    classify_import_error,
    deployment_gate,
    reopen_rehearsal,
    run_synthetic_student_flow,
    validate_import_package,
)

__all__ = [
    "ADAPTIVE_MAIN_BASELINE",
    "COMPILER_BASELINE",
    "ProductionReadinessError",
    "build_import_package",
    "classify_replay",
    "classify_import_error",
    "deployment_gate",
    "reopen_rehearsal",
    "run_synthetic_student_flow",
    "validate_import_package",
]
