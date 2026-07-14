# compiler_release_package_semantic_validator Report

- package_id: PKG_DELIBERATELY_INVALID_001
- verdict: reject
- errors: 5
- warnings: 0

This report may describe fixture-only rejection evidence.

## Errors

- ARTIFACT_INVENTORY: Required artifact categories are missing. (generation_family_candidate, performance_tracking_target, procedure_candidate, question_candidate, review_record, signal_mapping, validation_report)
- DETERMINISM: Manifest finalization does not reproduce declared checksum. (None)
- IDENTIFIER_UNIQUENESS: Duplicate artifact IDs found. (None)
- INTEGRITY: Artifact checksum mismatch. (None)
- INTEGRITY: Manifest integrity checksum mismatch. (None)
