# vector_components_2d Release Package v1

This package is compiler-side, non-live, and review-pending.
It has not been imported into adaptive-platform.
It has not been promoted to canonical content.
It is not student-visible.

## Package Identity
- package_id: `STATICS_VECTOR_COMPONENTS_2D_INTERNAL_V1`
- package_version: `compiler_release_package_v1`
- package_status: `compiler_non_live_review_pending`
- emitter_version: `release_package_emitter_v1`

## Source Summary
- subject_code: `STATICS`
- topic_code: `force_vectors`
- subtopic_code: `two_dimensional_vector_components`
- selected_micro_skill_code: `vector_components_2d`

## Procedures Included
- `PROC_SEED_VECTOR_COMPONENTS_2D_001`: Resolve a two-dimensional vector into horizontal and vertical components by using the vector magnitude, the angle measured from the positive x axis, and the standard component relationships Fx = F cos(theta) and Fy = F sin(theta). Preserve the sign of each component according to the quadrant or stated direction convention.

## Questions Included
- `Q_SEED_VECTOR_COMPONENTS_2D_001`: A 10 N force acts at an angle of 30 degrees above the positive x axis. Determine the x and y components of the force.

## Generation Families Included
- `GF_SEED_VECTOR_COMPONENTS_2D_001`: component_resolution_numeric_pair

## Practice Module Summary
- package_id: `PM_VECTOR_COMPONENTS_2D_001`

## Assessment Summary
- package_id: `PA_VECTOR_COMPONENTS_2D_001`

## Performance-Tracking Summary
- package_id: `PERF_VECTOR_COMPONENTS_2D_001`

## Content Gaps
- none

## Validation Result
- validation result: pass
- errors: 0
- warnings: 0

## Rights and Provenance Summary
- rights_summary: `{'source_basis': 'original_axiomiq_seed_wording', 'third_party_copying': 'not_used', 'rights_review_required': True}`
- source_provenance: `{'source_payload_package_id': 'DAY2_VECTOR_COMPONENTS_2D_SEED_PACKET_001', 'evidence_refs': [{'ref_id': 'release_day1_procedure_set_lock', 'path': 'docs/course_compiler_demo/internal_release/RELEASE_DAY1_STATICS_PROCEDURE_SET_LOCK.md'}, {'ref_id': 'release_day1_one_micro_skill_target', 'path': 'docs/course_compiler_demo/internal_release/RELEASE_DAY1_ONE_MICRO_SKILL_PROOF_TARGET.md'}, {'ref_id': 'compiler_package_boundary_probe', 'path': 'reports/course_compiler_demo/release_day1_probe/COMPILER_PACKAGE_BOUNDARY_PROBE_001.md'}], 'privacy_status': {'contains_student_data': False, 'contains_personal_data': False, 'privacy_review_required': False}}`

## Non-Live Boundary
- adaptive-platform write: false
- DB read/write: false
- canonical promotion: false
- student-visible publishing: false
- deployment: false

## Known Limitations
- This is a seed packet, not an executable package emitter output.
- Question and generation family seeds require human review before any runtime use.
- Failure signals are proposed for the Day 2 proof and are not promoted into canonical Alpha.
- No Alpha staging implementation, DB write, or student-visible publishing is authorized by this packet.

## Recommended Review Step
Human review and controlled protected-integration audit are required before any Alpha import.
