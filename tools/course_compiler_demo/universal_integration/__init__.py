"""Integrated, noncanonical universal compiler discovery and proof surface."""
from .system import (
    COURSE_ORDER, IntegratedJob, build_course_registry, build_service_registry,
    build_universal_package, plan_course_jobs, secure_batch_orchestrator, strict_beta_dry_run_validate,
)
from .proofs import run_assessment_export_proof, run_scale_proof
__all__ = [
    "COURSE_ORDER","IntegratedJob","build_course_registry","build_service_registry",
    "build_universal_package","plan_course_jobs","secure_batch_orchestrator","strict_beta_dry_run_validate",
    "run_assessment_export_proof","run_scale_proof",
]
