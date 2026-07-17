# Physics Intro Mechanics Profile v1

`PHYSICS_INTRO_MECHANICS_PROFILE_V1` is a compiler-side, non-live subject ingestion profile for proving that the release-package pipeline can handle a first new subject outside Statics.

The profile maps an AxiomIQ-owned synthetic Physics source through:

- Vectors
- Net Force
- Newton's Second Law

The selected release micro-skill is `apply_newtons_second_law_1d`. The dependency chain is:

`resolve_force_components_2d -> compute_net_force_1d -> apply_newtons_second_law_1d`

All generated candidates remain `human_review_required`, noncanonical, not student-visible, not eligible for Alpha import, and compiler-side only. The profile does not authorize database contact, adaptive-platform writes, deployment, or canonical promotion.
