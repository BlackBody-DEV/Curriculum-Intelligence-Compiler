"""Rule constants for the portable release-package semantic validator."""

from __future__ import annotations


REQUIRED_MANIFEST_FIELDS = {
    "package_id",
    "package_contract",
    "package_contract_semver",
    "package_version",
    "compiler_name",
    "compiler_version",
    "created_at",
    "content_status",
    "review_status",
    "subject",
    "topic_codes",
    "subtopic_codes",
    "micro_skill_codes",
    "source_references",
    "artifact_inventory",
    "procedure_artifact_ids",
    "question_artifact_ids",
    "generation_family_artifact_ids",
    "signal_mapping_artifact_ids",
    "performance_tracking_artifact_ids",
    "review_artifact_ids",
    "validation_artifact_ids",
    "asset_artifact_ids",
    "known_gaps",
    "promotion_recommendation",
    "safety_boundary",
    "integrity",
    "compatibility_metadata",
}

REQUIRED_DESCRIPTOR_FIELDS = {
    "artifact_id",
    "artifact_type",
    "relative_path",
    "media_type",
    "schema_ref",
    "sha256",
    "byte_size",
    "required",
    "status",
    "source_reference_ids",
    "depends_on_artifact_ids",
}

REQUIRED_SOURCE_FIELDS = {
    "source_id",
    "source_type",
    "title_or_authored_label",
    "rights_status",
    "privacy_status",
    "preservation_mode",
    "original_artifact_ref",
    "content_checksum",
    "provenance_refs",
    "excerpt_policy",
}

REQUIRED_CATEGORIES = {
    "source_metadata",
    "source_interpretation",
    "curriculum_extraction",
    "procedure_candidate",
    "question_candidate",
    "generation_family_candidate",
    "signal_mapping",
    "performance_tracking_target",
    "review_record",
    "validation_report",
}

SUPPORTED_MEDIA_TYPES = {"application/json"}

SUPPORTED_PROMOTION_RECOMMENDATIONS = {
    "hold_for_human_review",
    "eligible_for_protected_integration_review",
    "reject",
}

SAFE_BOUNDARY = {
    "non_live": True,
    "non_canonical": True,
    "human_review_required": True,
    "student_visible": False,
    "database_contact_required": False,
    "adaptive_platform_contact_required": False,
    "runtime_route_required": False,
    "learner_state_mutation_required": False,
    "canonical_promotion_performed": False,
}

FORBIDDEN_TEXT_MARKERS = {
    "/Users/fanarichardson/adaptive-platform",
    "adaptive-platform staging destination",
    "DATABASE_URL",
    "database credential",
    "runtime endpoint activation instruction",
    "student-visible publication instruction",
    "canonical promotion instruction",
    "canonical_approved",
    "live_ready",
    "production_ready",
    "database_imported",
    "runtime_enabled",
}

APPROVED_SIGNAL_CATEGORIES = {
    "axis_confusion",
    "component_addition_error",
    "component_swap_error",
    "degree_radian_or_angle_reference_error",
    "direction_error",
    "rounding_or_precision_error",
    "sign_error",
    "sign_or_placement_error",
    "simple_average_used",
    "trig_function_error",
    "unclassified",
}

RULE_ORDER = [
    "CONTRACT_VERSION",
    "JSON_PARSE",
    "STRUCTURAL_SCHEMA",
    "ARTIFACT_INVENTORY",
    "PATH_CONTAINMENT",
    "IDENTIFIER_UNIQUENESS",
    "REFERENCE_INTEGRITY",
    "PROVENANCE",
    "PROCEDURE_QUESTION_LINKAGE",
    "GENERATION_FAMILY_LINKAGE",
    "SIGNAL_POLICY",
    "REVIEW_STATE",
    "RIGHTS_SAFETY",
    "SAFETY_BOUNDARY",
    "INTEGRITY",
    "DETERMINISM",
    "KNOWN_GAPS",
]
