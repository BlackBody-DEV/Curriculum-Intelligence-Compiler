# Generation requirement compiler

The source-driven compiler transforms synthesized curriculum declarations into proposed `GenerationRequirementsPackageV1` and `GenerationManifestV1` records. It does not generate questions. Every requirement preserves its course, unit, topic, micro-skill, procedure, generation family, recipe requirement, answer engine, difficulty allocation, question target, question-type allocation, assessment roles, failure signals, asset policy, and duplicate constraints.

Compilation requires the caller's resolved source-evidence claim identities. Any referenced identity outside that set fails closed. Input requirements are sorted by identity so equivalent inputs serialize identically; allocation values must be finite, nonnegative, and sum to one, and duplicate-policy data must be deterministic JSON.

Dependencies are explicitly classified as existing-supported, existing-unsupported, new procedure/family/recipe/answer-engine required, or asset/diagram/OCR dependent. A ready requirement must explicitly declare existing support, resolved evidence, and no blockers. Unsupported and new dependencies cannot be marked ready; contradictory supported/unsupported classifications are rejected. Conflict-blocked requirements retain both their evidence and blocker identities.

Manifests include only fully ready requirements, remain `PROPOSED` and human-review-required, and carry no canonical authority. The compiler performs no database or adaptive-platform contact, no canonical writes, no student-visible activation, no performance tracking, and no question generation.
