# Generation requirement compiler

The compiler transforms synthesized curriculum declarations into proposed `GenerationRequirementsPackageV1` and `GenerationManifestV1` records. Every requirement preserves course, unit, topic, micro-skill, procedure, generation family, recipe requirement, answer engine, difficulty allocation, question target, question-type allocation, assessment roles, failure signals, asset policy, and duplicate constraints.

Dependencies are explicitly classified as existing-supported, existing-unsupported, new procedure/family/recipe/answer-engine required, or asset/diagram/OCR dependent. Unsupported and new dependencies cannot be marked ready. Missing, conflicting, or incomplete evidence fails closed. Manifests include only fully ready requirements, remain proposed and reviewable, and never generate questions or grant canonical, database, adaptive-platform, or student-visible authority.
