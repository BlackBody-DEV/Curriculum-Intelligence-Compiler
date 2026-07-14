# Dry-Run Integration Plan v1

Accepted packages receive a non-operational dry-run plan containing:

- `plan_id`
- `package_id`
- `plan_status`
- `package_contract`
- `package_version`
- `source_validation_summary`
- `artifact_processing_order`
- `artifact_groups`
- `review_gates`
- `known_gaps`
- `compatibility_warnings`
- `required_future_destination_capabilities`
- `prohibited_operations`
- `rollback_expectations`
- `boundary_statement`

Artifact groups are conceptual only: source and provenance, curriculum identity, procedure candidates, question candidates, generation family candidates, signal mappings, performance tracking targets, review records, validation evidence, assets, and known gaps.

The plan records generic future destination capabilities such as candidate-record intake, identifier mapping, review-state preservation, non-live staging isolation, transaction or rollback boundary, and artifact-reference validation.

Every plan prohibits adaptive-platform writes, database writes, migrations, runtime-route calls, learner-state modification, canonical promotion, and student-visible publication.

Rejected packages do not receive an actionable plan. Their plan artifact, when present, contains only `plan_status: not_generated_package_rejected`.
