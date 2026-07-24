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
and unsafe uploads are rejected. Text uploads containing NUL bytes are rejected.

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
2. Upload a `.txt`, `.md`, or text-native `.pdf` source, up to 50 MiB.
3. Confirm local-use rights and non-private status.
4. Select an allowlisted profile.
5. Compile the source with direct Python imports.
6. Review local curriculum candidates.
7. Generate a dashboard-local practice package for accepted compatible skills.
8. Create an assessment blueprint from a committed or dashboard-local generation family only when
   that family is compatible with the accepted curriculum.
9. Generate deterministic assessment questions.
10. Review, lock, reject, or regenerate individual questions.
11. Export student and instructor assessment files.

Student exports exclude answer keys and solution steps. Instructor exports
include answer and solution material explicitly.

## PDF Intake

PDF support is limited to local text-native extraction.

Supported:

```text
.pdf files with extractable text
page enumeration
page-ordered text extraction
local provenance hashing
```

Not supported:

```text
OCR
scanned or image-only PDF interpretation
encrypted or password-protected PDFs
external PDF-processing APIs
network services
```

PDF uploads fail closed when the file is corrupt, empty, zero-page, encrypted,
textless, image-only, over the 50 MiB upload limit, over the 1,500-page or extracted
text limits, or otherwise cannot be parsed safely. The operator-facing failure
is a bounded PDF error code rather than source text, tracebacks, or local paths.

For accepted PDFs, the source receipt records the original PDF SHA-256, extracted
text SHA-256, page count, pages containing text, blank-page count, extracted
character count, processing duration, applied resource limits, `pypdf` version,
rights/privacy status, OCR status, external service status, and retention
decisions.

Raw PDFs are temporary and are not retained in dashboard run storage. Extracted
text is retained only when the operator chooses local normalized-source
retention. If retention is disabled, extracted text is kept only in memory long
enough to pass through the existing compiler path and is removed after
compilation.

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
GET  /api/runs/{run_id}/generation-families
POST /api/runs/{run_id}/source
POST /api/runs/{run_id}/rights
POST /api/runs/{run_id}/profile
POST /api/runs/{run_id}/compile
GET  /api/runs/{run_id}/results
POST /api/runs/{run_id}/curriculum-review
POST /api/runs/{run_id}/practice
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

## Assessment Compatibility Guard

Assessment-family choices are filtered by the current run's detected subject,
course level, accepted topics, and accepted micro-skills. The server enforces the
same rule when creating a blueprint; a direct request for an incompatible family
fails with:

```text
incompatible_assessment_generation_family
```

A `MATHEMATICS / CALCULUS_I` run does not expose the Physics Newton's-law
generation family. When no compatible family exists, the dashboard displays:

```text
No compatible assessment generation family is available for the accepted curriculum. Assessment generation remains a content gap.
```

The run remains compiled and reviewable. The dashboard does not silently
substitute unrelated assessment families and does not claim assessment generation
passed when no source-compatible family exists.

## Dashboard-Local Calculus Practice and Assessment

For `MATHEMATICS / CALCULUS_I` runs, the dashboard can create demo-only
procedure candidates and source-aligned generated learning artifacts after
curriculum review accepts all five compatible micro-skills:

```text
evaluate_a_limit
apply_the_power_rule
apply_the_chain_rule
find_critical_points
analyze_increasing_and_decreasing_intervals
```

The compatible generation family is:

```text
GF_MATH_CALCULUS_I_FOUNDATIONS_V1
```

The default practice package is `Calculus I Foundations Practice`, with ten
items, two per accepted Calculus micro-skill when all five are accepted. The
default assessment also generates exactly ten questions, two per accepted
Calculus micro-skill. These artifacts are AxiomIQ-authored demo outputs with
`status=demo_unverified`, `noncanonical=true`, `canonical_approved=false`,
`eligible_for_alpha_import=false`, `student_visible=false`, and
`human_review_required=true`.

The Calculus family is not exposed for Physics or Statics runs and a direct
incompatible request fails closed with `incompatible_assessment_generation_family`.
Student exports omit answers, answer keys, solutions, and generation parameters
that disclose answers. Instructor exports are produced through explicit export
actions and may contain answer-bearing material for local review.

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
- uses the pinned local `pypdf==6.14.2` dependency for text-native PDF intake;
- does not install OCR, crypto extras, image-conversion, or external-service dependencies.

## Acceptance Proof

Acceptance proof runs should include both:

```text
Physics: apply_newtons_second_law_1d
Statics: vector_components_2d
```

The proof should demonstrate source upload, rights/privacy confirmation,
document-first interpretation, optional profile alignment, compiler execution,
local curriculum review, deterministic assessment generation, persisted review
decisions, locked-question preservation during regeneration, separated
student/instructor exports, run history, and reopening after restart.

Raw or normalized source files should not be committed as dashboard artifacts.
Source receipts may record filename, title, format, and SHA-256 hash.

## Run-State Persistence

File selection alone never marks a source uploaded. A successful Upload Source
request persists the same visible run with:

```text
status: source_ready
source_display_filename
source_format
source_sha256
source_title
rights_status
privacy_status
updated_at
```

The Source view shows the persisted filename, run ID, retention decision, and
whether the run is ready to compile. Compile remains disabled until the manifest
has `source_ready` plus filename, hash, rights, and privacy. A selected profile
is optional alignment metadata and is not a compile prerequisite.

When Compile is accepted, the manifest is saved before compiler execution as:

```text
status: compiling
compiler_status: running
last_error: null
```

Successful compilation persists:

```text
status: compiled
compiler_status: complete
detected_subject
detected_course_level
artifact_index
curriculum_summary
profile_alignment_status
release_status: review_required
```

Failed compilation persists:

```text
status: failed
compiler_status: failed
last_error
```

A visible success state must not coexist with `compiler_status: not_run`.

## Compile Flow

After a successful compile, the Source view shows a human-readable compilation
summary. The operator should see:

```text
Compilation complete
run ID
source title
source filename
document type
detected subject
detected course level
selected profile or none
profile alignment status
practice potential
assessment potential
topic count and topic names
micro-skill count and micro-skill names
content-gap summary
review status
raw PDF retained: No
extracted text retained: Yes/No
run saved to dashboard history: Yes
```

The dashboard then presents the required path:

```text
Review Curriculum
Save Review Decisions
Configure Assessment
Generate Questions
```

Assessment configuration is disabled until compilation succeeds and curriculum
review decisions are saved. Question generation is disabled until a valid
assessment blueprint has been created. If compilation produces no usable topics
or micro-skills, the run is marked failed and the operator sees a recovery
message rather than a blank success state.
