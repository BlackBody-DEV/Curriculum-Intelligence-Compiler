# Source assessment blueprints

The source assessment-blueprint compiler accepts evidence-backed declarations for course outcomes, assessment objectives, topic and micro-skill coverage, difficulty and question-type distributions, time budgets, source assessment examples, generation families, grading engines, and course-pack assessment policies. It emits a deterministic package containing exactly one `PRACTICE`, `DIAGNOSTIC`, `FORMATIVE`, and `SUMMATIVE` blueprint.

Every identity is resolved against an owning course. Compilation blocks unknown or cross-course units, topics, micro-skills, prerequisites, evidence claims, outcomes, objectives, generation families, grading engines, examples, and policies. It also blocks incomplete required coverage, unresolved conflicts or coverage gaps, invalid distributions, impossible time budgets, duplicate identities, malformed reuse/variant/scoring/rubric policies, and packages that do not contain exactly the four supported blueprint types.

Source blueprints and packages remain `PROPOSED`, reviewable, and noncanonical. Projection into `AssessmentBlueprintV1` preserves that boundary. The compiler does not generate questions, track performance, write canonical records or databases, modify the adaptive platform, or publish student-visible content.
