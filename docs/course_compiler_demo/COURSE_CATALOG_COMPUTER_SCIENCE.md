# Remaining Computer-Science Course Catalog

This expanded, noncanonical catalog adds Data Structures, Algorithms, and Computational Thinking while preserving the existing Programming Fundamentals course payload and its integrity hash. The original `build_programming_fundamentals_pack()` API remains unchanged; `build_computer_science_course_catalog()` provides the four-course catalog.

Each new course contains 8 units, 25 topics, 50 micro-skills, 15 procedures, 15 generation families, 49 prerequisites, two assessment blueprints, and target production count 300. Every course and the containing catalog are human-review-required and explicitly lack canonical authority.

## Answer allocations and safety

Families rotate across bounded `code_execution`, `multiple_choice`, `numeric_vector` trace grading, and `rubric_scored_explanation`. Each declares a micro-skill, procedure, bounded input/variant domain, difficulty distribution, engine-specific answer contract, failure signals, practice/summative role, and a zero-exact-duplicate fingerprint rule.

Code families are restricted to Python `solve`, 1,000 ms, 64 MB, no network, no filesystem, and no imports. This catalog declares those limits but does not execute code. Numeric traces are ordered vectors of at most 20 exact values. Rubric responses require structured fields and reject unrestricted freeform prose. No family silently falls back when its engine is unavailable.

Optional assets are limited to trace tables, data-structure diagrams, and flowcharts with rights evidence; student-performance data is forbidden. The packs define proposed curriculum and deterministic generation capacity only—not validated production questions, canonical promotion, or student-visible activation.

Validation proves the common gates, exact Programming Fundamentals preservation, hierarchy and procedure coverage, all four engine allocations, bounded-code policy, prerequisite and assessment resolution, deterministic 300-job plans, explicit disabled-engine blockers, and fail-closed malformed-catalog behavior.
