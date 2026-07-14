# Offline Consumer Result Contract v1

Each consumer run returns a stable JSON object with:

- `consumer_name`
- `consumer_version`
- `package_path`
- `package_id`
- `package_contract`
- `package_version`
- `validator_name`
- `validator_version`
- `validator_verdict`
- `consumer_verdict`
- `consumption_started_at`
- `consumption_completed_at`
- `manifest_loaded`
- `artifact_count`
- `artifact_type_counts`
- `declared_artifacts`
- `resolved_references`
- `unresolved_references`
- `dependency_order`
- `importable_artifacts`
- `review_only_artifacts`
- `non_importable_artifacts`
- `compatibility_warnings`
- `known_gaps`
- `dry_run_plan_status`
- `boundary_evidence`
- `errors`
- `warnings`

Allowed consumer verdicts are `accepted_for_offline_planning`, `accepted_for_offline_planning_with_warnings`, `rejected_without_plan`, and `consumer_error`.

Artifact classifications are limited to future planning categories:

- `future_integration_candidate`
- `review_record`
- `validation_evidence`
- `source_or_provenance_record`
- `asset_reference`
- `known_gap_record`
- `non_importable_metadata`
- `rejected_artifact`

The contract never classifies artifacts as canonical, live, student-visible, database-ready, or runtime-enabled.
