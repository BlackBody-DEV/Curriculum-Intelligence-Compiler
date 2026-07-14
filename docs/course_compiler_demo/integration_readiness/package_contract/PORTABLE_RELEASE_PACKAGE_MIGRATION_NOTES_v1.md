# Portable Release Package Migration Notes v1

Earlier compiler outputs include math demo packages, ACEF scaffolds, Alpha reference census reports, a package boundary probe, and a vector-components seed packet. Those artifacts remain useful evidence, but they do not freeze a portable integration contract.

`compiler_release_package_v1` differs by requiring a manifest-first package root, explicit artifact inventory, SHA-256 and byte-size integrity, source/provenance references, non-live safety fields, review-required status, deterministic serialization, and fixture-backed contract tests.

This contract does not authorize writing to adaptive-platform, database contact, runtime routes, learner-loop implementation, canonical promotion, or student-visible publishing. Future protected integration still requires a separate scope-lock lane.
