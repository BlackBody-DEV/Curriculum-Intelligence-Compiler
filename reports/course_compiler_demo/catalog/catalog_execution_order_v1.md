# Catalog execution order v1

Baseline: `e155fd453684a03bc876674dd1658447d9e30e15`. Compiler repository only.

1. Architect resolves `THERMODYNAMICS_MISSING_FROM_AUTHORITATIVE_CATALOG` and confirms whether concept-only mappings satisfy Measurement and Units, Vectors, Waves and Oscillations, and Optics.
2. Integration owner freezes shared contracts and registries listed in `catalog_track_ownership_v1.json` as read-only for both production tracks.
3. Start TRACK MATH-109 and TRACK PHYSICS-110 from the same accepted baseline in separate worktrees and branches.
4. Each track works only in course-owned production-question folders, checkpointing every locked 100-question bank and stopping each course at 300 validated questions.
5. Build course-local diagnostic, practice, summative, and variant packages only after the validated bank reaches its requirement.
6. Integration owner performs deferred shared registry/schema/index updates after both tracks deliver collision-free course-local outputs.
7. Canonical preparation and Beta export remain separate, later, explicitly authorized operations.

## Initial ordering

- TRACK MATH-109: finish Algebra I and Calculus I (200 remaining each), then Pre-Algebra, Geometry, Algebra II, Trigonometry, Precalculus, Calculus II, Calculus III, Linear Algebra, Differential Equations, Numerical Methods, Engineering Analysis, Applied Mathematics.
- TRACK PHYSICS-110: finish Statics and Electricity and Magnetism (200 remaining each), then Mechanics, Waves and Optics, Modern Physics, Dynamics, Mechanics of Materials, Strength of Materials, Fluid Mechanics, Hydraulics, Fluid Dynamics. Thermodynamics cannot enter the lane until architect resolution.

## Collision gate

No lane may edit subject-pack catalogs, answer-engine registries, generation-recipe registries, universal-integration aggregates, schemas, or aggregate documentation. Any required change there stops the lane and returns to the integration owner.
