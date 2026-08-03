# Interactive instructional diagram contract v1.2.0

Schema ID remains `axiomiq_interactive_instructional_diagram_interaction_v1`; the version is `1.2.0`. Version 1.0.0 and 1.1.0 artifacts are immutable and continue through their original validators.

V1.2 adds exactly one renderer (`statics_fbd_3d_v1`), five constraint models, one trusted formula (`statics_hydrostatic_center_of_pressure_v1`), and one display vocabulary (`statics_beam_sign_convention_overlay_v1`). Unknown identifiers fail closed. The declarative-data-only security boundary is unchanged: scripts, event handlers, HTML/remote payloads, data URLs, arbitrary expressions, and unregistered computation are rejected.

Interaction-bearing packages declare the schema version and exact SHA-256 digests for the schema and all four v1.2 registries. `interaction_registry_manifest_v1_2.json` provides the combined registry digest basis.
