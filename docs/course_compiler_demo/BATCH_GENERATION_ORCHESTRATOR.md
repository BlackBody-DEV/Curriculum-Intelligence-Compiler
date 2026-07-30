# Batch-generation orchestrator

The version-one batch orchestrator expands a generation manifest deterministically, runs offline provider stages through bounded worker pools, and persists an atomic checkpoint after each completed job. Generation, independent derivation, and validation use separate typed job queues. Provider exceptions are converted into isolated failed-job review outcomes instead of aborting the batch. Failed validation can produce bounded replacement attempts with recorded lineage; exhausted jobs are isolated in the review count.

Output roots must be absolute, outside every Git repository or worktree, and cannot be symbolic links. Checkpoint and manifest writes verify resolved containment and reject symbolic-link escapes. Reopening the same plan resumes unfinished jobs and is idempotent; a different plan cannot consume an existing checkpoint.

`DeterministicFixtureProvider` is an offline proof provider. Tests interrupt and restart a 500-job `.git`-less external run, verifying 500 derivation jobs, 500 validation jobs/outcomes, unique final identities, measured concurrency within the configured bound, and the same manifest hash from an independent fresh run. The runtime performs no network, database, canonical, student, Beta, or adaptive-platform operations.
