# Coordinate-Graph and Structured-Diagram Engines

Lane 044F provides `coordinate_graph` and `structured_diagram` adapters for bounded, machine-readable answers. Neither engine accepts pixels, OCR, sketches, image URLs, freeform prose, or arbitrary diagram interpretation.

`coordinate_graph` supports finite labeled points; slope/intercept lines; sampled functions with unique x-values; ordered domains and ranges; translations, axis scaling, rotations about declared centers, and reflection across four declared axes; vector arrows; and a closed set of graph-feature selections. IDs are unique within each element kind, unordered collections normalize by ID, finite numerics canonicalize to floats, and a supplied x-intercept must agree with the slope-intercept equation. Samples must lie within declared domains and ranges; increasing, decreasing, or constant selections must agree with sampled functions and line slopes. Transformation order is preserved because composition is not generally commutative.

`structured_diagram` requires labeled unique nodes plus explicit edge, dimension, and relationship lists. Node, edge, and dimension IDs are globally unique. Edges must resolve to nodes. Relationships use only `parallel`, `perpendicular`, `connected`, `equal`, `contains`, or `adjacent`, contain at least two distinct normalized members, and resolve to declared node, edge, or dimension IDs. Dimensions require positive finite values and bounded unit labels.

Both engines implement validation, deterministic normalization, independent derivation, exact structured grading, stable serialization through the universal result type, and caller-owned registry registration/support decisions. Invalid and unsupported structures return reasons and never fall back to numeric or multiple-choice grading. Collection and text bounds limit structural resource use.

## Independent audit scope

The lane audit covers identifier uniqueness, cross-reference closure, line/intercept consistency, interval ordering, sampled-function ambiguity, transformation schemas and ordering, relationship membership, finite numeric handling, deterministic reordering, contract mismatch, and explicit rejection of image/freeform inputs. The proof suite contains 75 valid coordinate graphs, 25 valid structured diagrams, and 25 malformed or ambiguous answers.
