# Physics, Engineering Mechanics, and Fluids Course Catalog

This noncanonical, human-review-required catalog adds nine courses: Mechanics, Waves and Optics, Modern Physics, Dynamics, Mechanics of Materials, Strength of Materials, Fluid Mechanics, Hydraulics, and Fluid Dynamics. Each has 8 units, 25 topics, 50 micro-skills, 15 procedures, 15 generation families, 49 explicit prerequisite relationships, two assessment blueprints, and a target production count of 300.

`build_physics_engineering_course_catalog()` returns the expanded 11-course catalog. The original `build_physics_engineering_reference_pack()` API still returns only Statics and Electricity & Magnetism. Their course payloads and the four read-only Statics authority references are copied unchanged into the expanded catalog and validated against a freshly built legacy reference pack.

## Generation and grading conventions

Every new generation family names its micro-skill, procedure, bounded parameter domains, three-level difficulty allocation, numeric answer contract and engine, failure signals, assessment role, and zero-exact-duplicate constraint. Procedures require SI declaration, dimensional verification, an explicit right-handed Cartesian basis, positive-x counterclockwise angles, and a declared sign check. Scalar answers declare their positive sense; vector answers use ordered x/y/z components.

Course policies record SI units and the M/L/T/I/Theta base dimensions. Moments follow the right-hand rule, pressure is gauge unless explicitly absolute, and flux is positive along the outward normal. These declarations are grading metadata; they do not silently convert an undeclared unit or infer an axis convention.

## Authority and limits

All nine additions set `noncanonical=true` and `human_review_required=true`; the containing pack has no canonical authority. Assets are optional and limited to coordinate diagrams, free-body diagrams, and property tables. No student-performance data is permitted. The packs define deterministic curriculum and generation contracts, not validated production questions, canonical promotion, or student-visible activation.

Validation proves exact legacy preservation, hierarchy and prerequisite resolution, complete generation-family fields, two assessment blueprints, deterministic serialization, 300 unique planned jobs per course, and fail-closed rejection of malformed units, dimensions, vectors, signs, identities, allocations, scopes, engines, and duplicate policies.
