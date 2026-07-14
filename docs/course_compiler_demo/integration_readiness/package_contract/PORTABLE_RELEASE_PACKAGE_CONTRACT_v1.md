# Portable Release Package Contract v1

## Purpose

`compiler_release_package_v1` freezes the compiler-side portable package shape for future protected integration review. It is implementation-independent, non-live, non-canonical, human-review-required, and does not authorize adaptive-platform changes.

## Version

- contract identifier: compiler_release_package_v1
- semantic version: 1.0.0

## Required Manifest Semantics

Valid packages must declare `content_status: non_live_candidate` and `review_status: human_review_required`. Valid packages must not claim canonical approval, production readiness, live readiness, database import, runtime enablement, or student visibility.

## Validation Implementation Note

This lane does not add dependencies. The schema files are frozen JSON contract documents, and the current automated tests use repository-local structural checks plus deterministic checksum/path/safety checks. Full formal JSON Schema validation is reserved for the semantic validation lane if the repository later approves a schema-validation dependency or implements a local schema subset.

## Required Artifacts

The contract supports source metadata, source interpretation, curriculum extraction, procedure candidates, question candidates, generation-family candidates, signal mappings, performance targets, review records, validation reports, asset references, and known-gap reports. Optional categories may be empty only when the manifest explicitly declares that state.

## Relationship to Earlier Specs

The procedure, question, and generation-family import specifications define non-live candidate records and review gates. This package contract wraps those candidate families into a portable directory and manifest model. The Day 1 package boundary probe and vector seed packet were shape and seed evidence; they were not executable package contracts and are superseded only for package layout purposes.
