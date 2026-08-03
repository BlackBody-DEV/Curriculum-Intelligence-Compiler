# Interactive instructional diagram contract v1.1.0

Schema ID: `axiomiq_interactive_instructional_diagram_interaction_v1`

Version 1.1.0 is an additive trusted-registry expansion of the audited 1.0.0 contract. The 1.0.0 schema, validator, adapter, fixture, and fallback remain available and valid without conversion.

The security envelope is unchanged: specifications are closed, declarative JSON data. Scripts, HTML event surfaces, remote code or assets, arbitrary expressions, and unknown renderer or formula identifiers fail closed. Mathematics is selected only by a versioned `formula_id` whose typed implementation is compiler-owned and whose registry entry declares inputs, output, dimensional/unit rules, bounds, invariants, deterministic reference cases, negative cases, and a trusted Beta implementation identifier.

Compiler packages carrying interaction specifications must declare `interaction_schema_id`, `interaction_schema_version`, and `interaction_schema_sha256`. They also integrity-bind the trusted registries with `interaction_formula_registry_sha256` and `interaction_renderer_registry_sha256`. Every digest is SHA-256 of the exact canonical artifact bytes.

Canonical artifacts:

- `schemas/axiomiq_interactive_instructional_diagram_interaction_v1.schema.json`
- `schemas/axiomiq_interactive_instructional_diagram_interaction_v1_1.schema.json`
- `schemas/interaction_renderer_registry_v1_1.json`
- `schemas/interaction_formula_registry_v1_1.json`
- `scripts/interaction_diagram/validate_interaction_spec_v1_1.py`
- `scripts/interaction_diagram/formulas_v1_1.py`
- `scripts/interaction_diagram/package_contract.py`
