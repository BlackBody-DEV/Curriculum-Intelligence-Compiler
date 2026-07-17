# Compiler Release Package Emitter v1

`tools/course_compiler_demo/package/release_package_emitter.py` emits deterministic, compiler-side, non-live release packages from approved compiler seed packets or normalized compiler candidate payloads.

The emitter is reusable across subjects. It derives subject, topic, micro-skill, procedure, question, generation-family, provenance, and rights data from the input payload; the proof command uses `vector_components_2d`, but the implementation does not hard-code Statics identifiers.

## CLI

```bash
python3 tools/course_compiler_demo/emit_release_package.py \
  --input reports/course_compiler_demo/internal_release/vector_components_2d_seed_packet/vector_components_2d_seed_packet.json \
  --package-id STATICS_VECTOR_COMPONENTS_2D_INTERNAL_V1 \
  --output reports/course_compiler_demo/internal_release/release_package_emitter_proof
```

## Output

The CLI writes exactly four files in the requested output directory:

- release package JSON
- release manifest JSON
- human-readable Markdown report
- validation JSON

## Non-Live Boundary

This package is compiler-side, non-live, and review-pending.
It has not been imported into adaptive-platform.
It has not been promoted to canonical content.
It is not student-visible.

The emitter performs no database access, no network access, no adaptive-platform writes, no deployment, no canonical promotion, and no student-visible publishing.

## Validation

The emitter fails closed for missing required components, duplicate IDs, broken question/procedure links, broken generation-family links, inconsistent subject or micro-skill targeting, missing provenance, missing rights status, unsafe live/canonical claims, malformed input, and output directories inside `/Users/fanarichardson/adaptive-platform`.

The manifest records package and file checksums. The manifest itself records `manifest_sha256_excluding_self`, because a file cannot contain a final cryptographic hash of its own complete bytes without self-reference.

The emitter guarantees deterministic semantic package content for identical normalized inputs and explicit package metadata. Timestamp fields such as `created_at` and validation timestamps may vary between runs, so tests compare the timestamp-normalized semantic digest rather than byte-for-byte equality of the full emitted JSON files.
