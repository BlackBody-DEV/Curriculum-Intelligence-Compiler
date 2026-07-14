# Compiler Integration-Readiness 7-Day Board

## Sprint

- Task: COMPILER-INTEGRATION-READINESS-BASELINE-INVENTORY-001
- Date: 2026-07-13
- Repository: Curriculum-Intelligence-Compiler
- Boundary: compiler repository only; adaptive-platform read-only
- Sprint target: deterministic, validated, portable compiler packages plus an offline consumption plan
- Integration status: paused until COMPILER-STAGING-PROTECTED-SCOPE-LOCK-001 or equivalent scope-lock lane

## Locked Content Set

The selected Statics integration-readiness set remains the 14-procedure release set:

1. vector_components_2d
2. resultant_2d_addition
3. resultant_magnitude
4. resultant_direction_2d
5. equilibrant_force
6. solve_particle_equil_2d
7. moment_of_force_scalar_2d
8. couple_moment
9. principle_of_moments_varignon
10. resultant_line_of_action
11. beam_reactions
12. simple_distributed_load_resultant
13. centroid_first_moments
14. composite_centroid

## Day 1 Baseline Finding

No legally and operationally safe real Statics source was found in the compiler repository. Existing supported inputs are demo/sample text or generated seed/report material. Lane A is therefore blocked until a rights-cleared real Statics source is supplied or explicitly approved outside adaptive-platform.

## Board

| Task ID | Lane | Owner | Dependency | Deliverable | Acceptance Test | Duration | Parallel | Owned Paths | Forbidden Overlap | Status |
|---|---|---|---|---|---|---:|---|---|---|---|
| COMPILER-INTEGRATION-READINESS-BASELINE-INVENTORY-001 | Baseline | Codex | none | baseline reports, board, ownership map | JSON validates, tests pass, compiler push succeeds | 3h | no | docs/course_compiler_demo/integration_readiness/COMPILER_INTEGRATION_READINESS_* | adaptive-platform/** | complete |
| COMPILER-REAL-STATICS-SOURCE-PIPELINE-001 | A | Real-source pipeline agent | baseline complete and real source supplied | preserved source, extraction, candidates, review package | deterministic run with provenance and non-live validation | 6h | yes after blocker resolved | tools/course_compiler_demo/intake/; tools/course_compiler_demo/extract/; tools/course_compiler_demo/sample_inputs/real_statics/; reports/course_compiler_demo/integration_readiness/real_source/; tests/course_compiler_demo/test_real_source_pipeline* | adaptive-platform/**; release_package/**; reference_consumer/** | blocked_real_source_missing |
| COMPILER-PORTABLE-RELEASE-PACKAGE-CONTRACT-001 | B | Package contract agent | baseline complete | versioned package and manifest contract, five golden fixtures | fixture schemas validate; invalid fixtures reject by expected metadata | 6h | yes | tools/course_compiler_demo/release_package/contracts/; tools/course_compiler_demo/release_package/manifest/; docs/course_compiler_demo/integration_readiness/package_contract/; tests/course_compiler_demo/test_release_package_contract* | tools/course_compiler_demo/intake/**; tools/course_compiler_demo/extract/**; adaptive-platform/** | ready |
| COMPILER-SEMANTIC-RELEASE-PACKAGE-VALIDATION-001 | C | Semantic validation agent | Lane B contract published or versioned draft interface | semantic validator and fixture result reports | all fixture verdicts match expected accept/warn/reject matrix | 6h | after Lane B | tools/course_compiler_demo/release_package/validate/; tests/course_compiler_demo/test_release_package_validation*; reports/course_compiler_demo/integration_readiness/validation/ | Lane B contract files except read-only; adaptive-platform/** | waiting_on_lane_b |
| COMPILER-OFFLINE-REFERENCE-CONSUMER-001 | D | Offline consumer agent | Lane B contract published or versioned draft interface | offline consumer and dry-run import plan | validates manifest, checksums, refs; rejects unsafe packages | 6h | after Lane B | tools/course_compiler_demo/reference_consumer/; tests/course_compiler_demo/test_reference_consumer*; reports/course_compiler_demo/integration_readiness/reference_consumer/ | adaptive-platform/**; release_package/contracts/** except read-only | waiting_on_lane_b |
| COMPILER-STATICS-CONTENT-READINESS-14-001 | E | Content readiness agent | baseline complete | 14-procedure manifest, coverage matrix, gap report | every selected code has status and missing components recorded | 6h | yes | reports/course_compiler_demo/integration_readiness/content_set/; docs/course_compiler_demo/integration_readiness/content_set/; tests/course_compiler_demo/test_integration_content_set* | adaptive-platform/**; Lane A core builders | ready |
| COMPILER-INTEGRATION-COMPATIBILITY-SCOPE-LOCK-001 | F | Compatibility agent | baseline complete | compatibility matrix and protected scope-lock request | read-only evidence only; request authorizes nothing | 6h | yes | docs/course_compiler_demo/integration_readiness/compatibility/; docs/course_compiler_demo/integration_readiness/scope_lock/; reports/course_compiler_demo/integration_readiness/compatibility/ | adaptive-platform writes; runtime route work | ready |
| COMPILER-INTEGRATION-REPRODUCTION-HARNESS-001 | G | Reproduction harness agent | baseline complete | harness skeleton, boundary evidence schema, smoke test skeleton | pytest passes; evidence reports all adaptive writes false | 6h | yes | tools/course_compiler_demo/integration_readiness/; tests/course_compiler_demo/test_integration_readiness_reproduction*; reports/course_compiler_demo/integration_readiness/reproduction/; docs/course_compiler_demo/integration_readiness/release_qa/ | adaptive-platform/**; Lane B/C/D implementation files | ready |

## Parallel Launch Order

Start immediately after this baseline commit:

- Lane B: portable package contract
- Lane E: content readiness
- Lane F: compatibility and scope lock
- Lane G: reproduction harness skeleton

Lane A must wait for a rights-cleared real Statics source.

Lane C and Lane D must wait for Lane B unless they use a clearly versioned draft interface owned by Lane B without shared-file modification.

