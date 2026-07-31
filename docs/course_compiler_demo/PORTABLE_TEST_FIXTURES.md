# Portable compiler test fixtures

The default compiler test suite uses only repository-owned, newly authored test
fixtures. These fixtures are noncanonical, are never student-visible, and are
ineligible for database writes, canonical promotion, or Alpha import.

## Source Inbox fixture

`tests/fixtures/course_compiler_demo/source_inbox_portable` exercises the same
intake surfaces as the former host-only baseline: syllabus and course-definition
text, JSONL question-bank input, a text-native PDF, normalized instructional
source, curriculum extraction, and duplicate detection. Its manifest records
the rights status, privacy status, stable SHA-256 digest, segments, and evidence
for every file.

Resolution order is explicit path, `AXIOMIQ_SOURCE_INBOX_ROOT`, then the committed
fixture. The historical host corpus is only checked by the separately marked
`host_environment_integration` test when that corpus is mounted.

## Phase E replay fixture

`tests/fixtures/course_compiler_demo/phase_e_portable_replay` contains 15
public-schema synthetic approved artifacts: five Force Systems multiple-choice,
five Force Systems numeric, and five Vector Operations numeric-pair artifacts.
The production family adapters read and convert these artifacts; the fixture
does not inject prebuilt finalized rows or replace adapter conversion logic.

| Original behavior under test | Portable fixture | Assertions preserved | Assertions added | Assertions removed / reason |
| --- | --- | --- | --- | --- |
| Source intake through compile, review, generation, regeneration, and export | Newly authored Physics and Statics normalized text | Complete state, 10 questions, validation, locking, answer separation, reopen | Manifest hashes, segment/evidence identities, rights/privacy, no path persistence | None |
| Source formats and duplicate detection | Text, syllabus, course definition, JSONL, PDF, duplicate pair | Format discovery, PDF extraction, duplicate equality | Exact inventory and rights-safe provenance | None |
| Approved Phase E filtering | 15 synthetic `approved/*.json` records | Production discovery and `AUTHOR_COMPLETE` filtering | Manifest digests, regular-file and no-symlink checks | None |
| Force multiple choice | 5 synthetic records | Count, type, answer contract, adapter identity, golden agreement | Scenario diversity | None; fixtures faithfully preserve the bounded generator's current A-first contract |
| Force numeric | 5 synthetic records | Numeric conversion, benchmark authority, generation | Signed and multiple-vector sums, including zero | None |
| Vector numeric pair | 5 synthetic records | Pair order, conversion, benchmark authority | Nonzero angles, both axis families, quadrants and signs | None |
| Signed procedure | Procedure ID, steps, digest | Procedure identity and replay packets | Nonempty steps, reproducible digest, mutation rejection | None |
| Blind boundary | Production generation and independent derivation packets | Benchmark answers remain sealed | Fixture-only metadata excluded from runtime packets | None |
| Golden replay and reopen | Portable adapters and temporary production root | Export, lock, lineage, copied-root reopen | Recursive host/protected-path rejection | None |

Every Phase E fixture artifact carries the `PORTABLE_SYNTHETIC_PHASE_E_TEST_FIXTURE`
type and explicit false flags for student visibility, Alpha import, canonical
promotion, database writes, and protected content. Protected-workspace parity is
available only with `PHASE_E_PROTECTED_INTEGRATION=1` and is separately marked
`protected_fixture_integration`. Host Source Inbox parity requires
`AXIOMIQ_HOST_SOURCE_INBOX_INTEGRATION=1`; that opted-in test traverses the same
acceptance workflow as the portable default.

The `portable_baseline` marker identifies default repository-portable coverage.
No default test requires `/Users`, a sibling checkout, a protected workspace, a
Git worktree, or network access.

## Canonical-promotion preparation fixtures

`tests/fixtures/course_compiler_demo/canonical_promotion_portable` contains four
newly authored, snapshot-only public-contract authority references. Its manifest
pins their exact inventory and SHA-256 digests and labels them noncanonical,
nonprivate, nonprotected, ineligible for Alpha import, and unauthorized for
canonical or database writes. Canonical-promotion tests copy these files through
the production snapshot routine and retain the original source/snapshot identity
and integrity assertions.

The six production-bank dependencies are generated deterministically in pytest
temporary storage by the repository's production bank builders. No external bank
file is copied or committed. The factory reconstructs six locked banks with 100
validated candidates apiece, validates every `ProductionQuestionBankV1` checksum,
and proves candidate/derivation/validation linkage and provenance. Hash mutation
continues to fail closed.

Canonical-promotion tests also use five existing synthetic Phase E records whose
public generation-family metadata covers the original return, regenerate,
curriculum-escalation, and rejection scenarios. All original eligibility,
rights, asset, duplicate, review-action, restart/reopen, and no-write assertions
remain required; none of these tests is converted to an optional skip.
