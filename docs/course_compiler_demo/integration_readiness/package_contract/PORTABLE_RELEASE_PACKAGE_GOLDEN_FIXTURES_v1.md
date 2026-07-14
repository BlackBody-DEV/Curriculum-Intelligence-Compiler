# Portable Release Package Golden Fixtures v1

The fixture set is compiler-side and fixture-only. It uses AxiomIQ-authored synthetic metadata and contains no protected textbook passages or proprietary source excerpts.

- `minimal_valid`: smallest structurally valid package with all required artifact categories.
- `normal_multi_artifact`: multiple procedures, questions, generation families, signal mappings, provenance links, and one worked-example asset reference.
- `known_nonblocking_gaps`: structurally valid package with explicit nonblocking gaps and `hold_for_human_review`.
- `deliberately_invalid`: fixture-only reject case with duplicate artifact IDs and an incorrect checksum.
- `safety_boundary_violation`: fixture-only unsafe reject case containing inert forbidden safety claims and an inert adaptive-platform path string.

Invalid fixtures are labeled with `expected_verdict: reject`; the safety fixture also has `unsafe_fixture: true`.
