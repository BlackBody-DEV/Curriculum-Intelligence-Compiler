"""Deterministic artifact classification for offline planning."""

from __future__ import annotations

from typing import Any


CLASSIFICATIONS = {
    "procedure_candidate": ("future_integration_candidate", "Procedure candidate may be mapped by a future non-live importer."),
    "question_candidate": ("future_integration_candidate", "Question candidate may be mapped by a future non-live importer."),
    "generation_family_candidate": ("future_integration_candidate", "Generation family candidate may be mapped by a future non-live importer."),
    "signal_mapping": ("future_integration_candidate", "Signal mapping may inform future non-live feedback mapping."),
    "performance_tracking_target": ("future_integration_candidate", "Performance target may inform future non-live telemetry design."),
    "review_record": ("review_record", "Review metadata is evidence, not an importable learner artifact."),
    "validation_report": ("validation_evidence", "Validation report is audit evidence."),
    "source_metadata": ("source_or_provenance_record", "Source metadata records provenance only."),
    "source_interpretation": ("source_or_provenance_record", "Source interpretation records provenance context."),
    "asset_reference": ("asset_reference", "Asset reference is optional external media metadata."),
    "known_gap_report": ("known_gap_record", "Known gap report preserves nonblocking review context."),
    "curriculum_extraction": ("non_importable_metadata", "Curriculum extraction is package metadata for review."),
}


def classify_artifact(descriptor: dict[str, Any]) -> tuple[str, str]:
    artifact_type = descriptor.get("artifact_type")
    return CLASSIFICATIONS.get(
        artifact_type,
        ("non_importable_metadata", f"Unsupported optional artifact type retained as metadata: {artifact_type}"),
    )
