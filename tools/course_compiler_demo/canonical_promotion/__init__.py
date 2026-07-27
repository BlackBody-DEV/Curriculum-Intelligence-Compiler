"""Canonical promotion preparation helpers.

This package prepares noncanonical compiler outputs for human canonical-review
workflows. It never assigns canonical IDs, writes canonical records, touches a
database, or marks content student-visible.
"""

from .preparation_mode import (
    EXECUTION_PROFILE,
    MODE_IDENTIFIER,
    CanonicalPromotionPreparationError,
    DocumentCompilerInputAdapter,
    PhaseEProductionInputAdapter,
    prepare_promotion_root,
    reopen_preparation_run,
    run_preparation_pilot,
)

__all__ = [
    "EXECUTION_PROFILE",
    "MODE_IDENTIFIER",
    "CanonicalPromotionPreparationError",
    "DocumentCompilerInputAdapter",
    "PhaseEProductionInputAdapter",
    "prepare_promotion_root",
    "reopen_preparation_run",
    "run_preparation_pilot",
]
