# Vector Components 2D Seed Packet

## Purpose

This seed packet defines the minimum non-live content seed for the Day 2 `vector_components_2d` one-micro-skill proof target.

## Release Context

The Day 2 proof must show an internal vertical slice from a compiler package or simulated package into controlled Alpha import/staging, review, practice module opening, answer submission, grading, failure signal display, readiness/progress persistence, and performance retrieval.

## Non-Live Boundary

- selected_micro_skill_code: vector_components_2d
- status: human_review_required
- review_status: review_pending
- canonical_promotion_status: not_authorized
- copying_allowed_now: false
- student_visible: false
- live_deployable: false

This packet is non-live seed material only.

## Micro-Skill

`vector_components_2d` covers resolving a two-dimensional vector into x and y components using a magnitude, an angle reference, trigonometric component formulas, and signed component conventions.

## Procedure Seed

Resolve a two-dimensional vector into horizontal and vertical components by using the vector magnitude, the angle measured from the positive x axis, and the standard component relationships:

- Fx = F cos(theta)
- Fy = F sin(theta)

The learner should identify the magnitude and angle reference, compute the x and y components, apply signs according to the vector direction, and report both components with units and appropriate rounding.

## Question Seed

Practice item:

- prompt: A 10 N force acts at an angle of 30 degrees above the positive x axis. Determine the x and y components of the force.
- vector magnitude: 10
- angle from +x axis: 30 degrees
- expected x component: 8.66 N
- expected y component: 5.00 N
- tolerance: 0.05
- correct answer pair: Fx = 8.66, Fy = 5.00

## Generation Family Seed

The generation family should vary:

- magnitude
- angle
- quadrant
- units
- sign convention
- answer tolerance

Each generated item must preserve a clear angle reference and a reviewable signed component answer.

## Answer Logic

Use:

- Fx = F cos(theta)
- Fy = F sin(theta)

For the seed item:

- Fx = 10 cos(30 degrees) = 8.660254...
- Fy = 10 sin(30 degrees) = 5.000000...

Rounded answer: Fx = 8.66 N, Fy = 5.00 N.

## Grading Expectation

The answer type is `numeric_pair`. The runtime proof should expect the pair order `Fx, Fy` and pass only when both values are within tolerance after normalization. Units are part of the instructional context, but this seed does not require unit parsing in the Day 2 proof.

## Failure Signal Mapping

- component_swap_error: learner reports the x and y components in the wrong positions.
- sign_error: learner computes component magnitudes correctly but assigns an incorrect sign.
- trig_function_error: learner uses the wrong trigonometric function for the stated angle reference.
- degree_radian_or_angle_reference_error: learner uses the wrong angle mode or treats the angle as measured from the wrong axis.
- rounding_or_precision_error: learner uses the right method but rounds outside tolerance.

## Evidence and Rights

Evidence references:

- docs/course_compiler_demo/internal_release/RELEASE_DAY1_STATICS_PROCEDURE_SET_LOCK.md
- docs/course_compiler_demo/internal_release/RELEASE_DAY1_ONE_MICRO_SKILL_PROOF_TARGET.md
- reports/course_compiler_demo/release_day1_probe/COMPILER_PACKAGE_BOUNDARY_PROBE_001.md

Rights status: original AxiomIQ seed wording, no third-party copying used.

Privacy status: no student data and no personal data.

## Human Review Status

The packet is `human_review_required` and `review_pending`. The content is not canonical, not active, not student-visible, and not live-deployable.

## Known Limitations

- This packet is not an executable package emitter output.
- The question seed and generation family seed require human review.
- Failure-signal mappings are proposed for a Day 2 proof and are not canonical Alpha signals.
- The packet does not prove package import, review, runtime binding, persistence, or retrieval by itself.

## Day 2 Proof Use

This seed packet should be used as the content seed for the Day 2 `vector_components_2d` proof package or simulated package. The proof must show an internal authenticated user opening the practice module, submitting an answer, receiving grading and a failure signal, and producing persistent retrievable performance data.

## Not Authorized

- this packet does not authorize Alpha staging implementation
- this packet does not authorize writing into adaptive-platform
- this packet does not authorize DB contact
- this packet does not authorize canonical promotion
- this packet does not authorize student-visible publishing
- this packet does not authorize backend or frontend runtime changes
- this packet does not authorize migrations, OCR, parser work, or new dependencies
