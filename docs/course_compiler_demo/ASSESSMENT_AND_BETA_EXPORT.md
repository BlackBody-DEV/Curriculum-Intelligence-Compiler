# Assessment Compiler and AxiomIQ Beta Export

This lane compiles deterministic assessments from validated question references and builds versioned, read-only transfer packages for AxiomIQ Beta. It never imports, activates, or writes to Beta, the adaptive platform, canonical storage, or a database.

## Assessment compilation

`compile_assessment` validates the versioned foundation blueprint, filters by course and unit scope, prevents reuse unless explicitly allowed, and satisfies exact topic, difficulty, and question-type allocations. It also requires declared micro-skill and prerequisite coverage and enforces the time budget. The same blueprint, normalized bank, seed, and variant index produce byte-identical JSON. Missing coverage raises `AssessmentCompilationError`; partial assessments are never returned.

Variant identity is derived from blueprint identity, seed, and variant index. Scoring rules and rubrics remain authoritative blueprint metadata. Selected references receive an assessment identity and role without changing the source bank.

## Beta export boundary

`build_beta_export` uses `BetaExportPackageV1` and `ValidatedQuestionReferenceV1`. References carry curriculum and proposed-canonical mapping state, question and revision identity, procedure and answer contracts, difficulty, grading, failure signals, assessment metadata, evidence, provenance, assets, and version data.

`dry_run_import_validate` performs structural and identity checks only and returns `would_write: false`. `stable_export_hash` hashes canonical compact JSON. Universal-contract recursive validation rejects student IDs, attempts, scores, mastery, progress, adaptive decisions, and performance history. Exports never assert canonical authority.

## Scale proof

Lane tests compile a 25-question practice assessment, a 40-question summative assessment, and three deterministic variants from synthetic validated references. They also validate a single export containing 300 references. All providers and evidence are synthetic; no adaptive-platform or Beta write occurs.
