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
    ProductionQuestionBankInputAdapter,
    ProductionQuestionCandidateInputAdapter,
    BetaExportReferenceInputAdapter,
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
    "ProductionQuestionBankInputAdapter",
    "ProductionQuestionCandidateInputAdapter",
    "BetaExportReferenceInputAdapter",
    "prepare_promotion_root",
    "reopen_preparation_run",
    "run_preparation_pilot",
]

from .reconciliation import RUN_ID as RECONCILIATION_RUN_ID, reopen_universal_reconciliation_pilot, run_universal_reconciliation_pilot
__all__ += ["RECONCILIATION_RUN_ID", "run_universal_reconciliation_pilot", "reopen_universal_reconciliation_pilot"]
