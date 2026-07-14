# compiler_release_package_semantic_validator Report

- package_id: PKG_SAFETY_BOUNDARY_VIOLATION_001
- verdict: reject
- errors: 7
- warnings: 0

This report may describe fixture-only rejection evidence.

## Errors

- ARTIFACT_INVENTORY: Required artifact categories are missing. (generation_family_candidate, performance_tracking_target, procedure_candidate, question_candidate, review_record, signal_mapping, validation_report)
- REVIEW_STATE: content_status must be non_live_candidate. (canonical_approved)
- SAFETY_BOUNDARY: Forbidden safety marker found. (/Users/fanarichardson/adaptive-platform)
- SAFETY_BOUNDARY: Forbidden safety marker found. (canonical_approved)
- SAFETY_BOUNDARY: Safety boundary value is unsafe. (True)
- SAFETY_BOUNDARY: Safety boundary value is unsafe. (True)
- SAFETY_BOUNDARY: Student-visible true claim found. (None)
