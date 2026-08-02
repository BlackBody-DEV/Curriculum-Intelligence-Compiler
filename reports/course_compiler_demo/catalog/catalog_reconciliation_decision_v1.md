# Catalog reconciliation decision v1

## Authoritative decisions

1. The implemented execution denominator is 33 courses.
2. The validated inventory is 1,275 unique locked production questions: 600 legacy plus 675 Wave 056.
3. The remaining allocation is 8,625 questions.
4. The v1 600 figure omitted Wave 056; it was not caused by fixtures, diagnostic double-counting, duplicates, superseded revisions, out-of-catalog questions, or overlapping indexes.
5. Thermodynamics is `DECLARED_BUT_NOT_IMPLEMENTED`; resolving it requires Architect authority.
6. Both parallel lanes are blocked from immediate launch until the Architect explicitly accepts the 33-course denominator or authorizes later Thermodynamics implementation.

## Disputed mappings

| Intended entity | Repository representation | Classification | Denominator effect if added standalone |
|---|---|---|---|
| Thermodynamics | Absent | DECLARED_BUT_NOT_IMPLEMENTED | 33 → 34 |
| Measurement and Units | MECHANICS / Measurement and vectors | IMPLEMENTED_AS_UNIT_OR_TOPIC | 33 → 34 |
| Vectors | MECHANICS / Measurement and vectors; STATICS / Vector Operations | IMPLEMENTED_AS_UNIT_OR_TOPIC | 33 → 34 |
| Waves and Oscillations | WAVES_AND_OPTICS | IMPLEMENTED_UNDER_ALTERNATE_IDENTITY | 33 → 34 |
| Optics | WAVES_AND_OPTICS | IMPLEMENTED_UNDER_ALTERNATE_IDENTITY | 33 → 34 |

## First checkpoints

- TRACK MATH-110: Algebra I and Calculus I move from 100 to 200 validated questions each; checkpoint increment 100 each.
- TRACK PHYSICS-111: Statics and Electricity and Magnetism move from 100 to 200 validated questions each; checkpoint increment 100 each.

No question generation, assessment compilation, canonical preparation, export construction, database access, or adaptive-platform access was performed by this reconciliation.
