# Operator Dashboard MVP

## Status

The operator dashboard is a local-only compiler control surface for non-live course
compilation and assessment studio review.

It is not a lane runner, not an Alpha integration tool, not a deployment surface,
and not a student-visible application.

## Start

```bash
python3 tools/course_compiler_demo/run_dashboard.py --host 127.0.0.1 --port 8765
```

The server binds only to `127.0.0.1`. Non-loopback hosts, invalid ports, path
traversal identifiers, oversized uploads, unsupported uploads, empty uploads,
and NUL-containing uploads are rejected.

## Local Storage

Dashboard runs are written under:

```text
reports/course_compiler_demo/dashboard_runs/
```

Each run has a `run_manifest.json` plus scoped subdirectories:

```text
source/
compiler/
review/
assessments/
release_package/
```

The manifest records local run state, source receipt metadata, artifact keys,
review status, assessment IDs, and non-live boundary flags.

## Supported Workflow

1. Create a run.
2. Upload a `.txt` or `.md` source, up to 5 MiB.
3. Confirm local-use rights and non-private status.
4. Select an allowlisted profile.
5. Compile the source with direct Python imports.
6. Review local curriculum candidates.
7. Create an assessment blueprint from a committed generation family.
8. Generate deterministic assessment questions.
9. Review, lock, reject, or regenerate individual questions.
10. Export student and instructor assessment files.

Student exports exclude answer keys and solution steps. Instructor exports
include answer and solution material explicitly.

## Supported Profiles

The dashboard exposes fixed local profile choices:

```text
PHYSICS_INTRO_MECHANICS_PROFILE_V1
STATICS_VECTOR_COMPONENTS_RELEASE_PROFILE_V1
```

The Statics profile is a dashboard-local release-package view of the committed
`vector_components_2d` package. It does not add a new subject profile file and
does not modify compiler profiles.

## API Surface

The API is intentionally narrow:

```text
GET  /api/health
GET  /api/profiles
GET  /api/generation-families
GET  /api/runs
POST /api/runs
GET  /api/runs/{run_id}
POST /api/runs/{run_id}/source
POST /api/runs/{run_id}/rights
POST /api/runs/{run_id}/profile
POST /api/runs/{run_id}/compile
GET  /api/runs/{run_id}/results
POST /api/runs/{run_id}/curriculum-review
POST /api/runs/{run_id}/assessments
GET  /api/runs/{run_id}/assessments/{assessment_id}
POST /api/runs/{run_id}/assessments/{assessment_id}/generate
POST /api/runs/{run_id}/assessments/{assessment_id}/review
POST /api/runs/{run_id}/assessments/{assessment_id}/regenerate
GET  /api/runs/{run_id}/assessments/{assessment_id}/exports/{export_type}
GET  /api/runs/{run_id}/artifacts/{artifact_key}
```

There are no generic filesystem, Git, shell, database, Alpha, backend,
frontend, migration, deployment, canonical-promotion, or student-publication
endpoints.

## Non-Live Boundary

The dashboard:

- performs no database reads or writes;
- performs no adaptive-platform writes;
- performs no backend or frontend runtime integration;
- creates no migrations;
- performs no canonical promotion;
- performs no deployment;
- does not create student-visible content;
- does not import content into Alpha;
- does not run arbitrary shell commands;
- does not add dependencies.

## Acceptance Proof

Acceptance proof runs should include both:

```text
Physics: apply_newtons_second_law_1d
Statics: vector_components_2d
```

The proof should demonstrate source upload, rights confirmation, profile
selection, compiler execution, local curriculum review, deterministic assessment
generation, persisted review decisions, locked-question preservation during
regeneration, and separated student/instructor exports.

Raw or normalized source files should not be committed as dashboard artifacts.
Source receipts may record filename, title, format, and SHA-256 hash.
