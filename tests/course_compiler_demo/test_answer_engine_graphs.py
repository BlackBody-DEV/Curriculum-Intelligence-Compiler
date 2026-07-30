import json

import pytest

from tools.course_compiler_demo.answer_engines.graphs import CoordinateGraphEngine, StructuredDiagramEngine, register_graph_engines
from tools.course_compiler_demo.answer_engines.registry import AnswerEngineRegistry
from tools.course_compiler_demo.universal_core import AnswerContractV1


def contract(engine):
    return AnswerContractV1(f"contract:{engine}", engine, {})


GRAPH_CASES = (
    [{"points": [{"id": f"P{i}", "x": i, "y": -i}]} for i in range(25)]
    + [{"lines": [{"id": f"L{i}", "slope": i + 1, "y_intercept": -(i + 1), "x_intercept": 1}]} for i in range(25)]
    + [{"functions": [{"id": f"f{i}", "samples": [[0, i], [1, i + 1]]}], "domain": [0, 1], "range": [i, i + 1], "features": ["increasing"]} for i in range(25)]
)


def diagram(index):
    return {
        "nodes": [{"id": f"A{index}", "label": "start"}, {"id": f"B{index}", "label": "end"}],
        "edges": [{"id": f"E{index}", "source": f"A{index}", "target": f"B{index}", "label": "segment"}],
        "dimensions": [{"id": f"D{index}", "value": index + 1, "unit": "cm"}],
        "relationships": [{"type": "connected", "members": [f"A{index}", f"B{index}"]}],
    }


DIAGRAM_CASES = [diagram(i) for i in range(25)]


MALFORMED = [
    None, {}, {"image": "graph.png"}, {"points": "bad"}, {"points": [{"id": "P", "x": True, "y": 0}]},
    {"points": [{"id": "P", "x": 0, "y": float("inf")}]}, {"points": [{"id": "P", "x": 0, "y": 0}, {"id": "P", "x": 1, "y": 1}]},
    {"lines": [{"id": "L", "slope": 2, "y_intercept": 1, "x_intercept": 4}]},
    {"functions": [{"id": "f", "samples": [[0, 0]]}]}, {"functions": [{"id": "f", "samples": [[0, 0], [0, 1]]}]},
    {"domain": [2, 1]}, {"range": [0]}, {"features": ["looks_steep"]}, {"features": ["maximum", "maximum"]},
    {"transformations": [{"type": "skew", "parameters": [1, 2]}]}, {"transformations": [{}]},
    {"transformations": [{"type": "reflect", "axis": "z"}]}, {"transformations": [{"type": "rotate", "degrees": 90, "center": [0]}]},
    {"vectors": [{"id": "v", "start": [0, 0], "end": [1]}]},
    {"nodes": [], "edges": [], "dimensions": [], "relationships": []},
    {"nodes": [{"id": "A", "label": "a"}, {"id": "A", "label": "b"}], "edges": [], "dimensions": [], "relationships": []},
    {"nodes": [{"id": "A", "label": "a"}], "edges": [{"id": "E", "source": "A", "target": "Z", "label": "bad"}], "dimensions": [], "relationships": []},
    {"nodes": [{"id": "A", "label": "a"}], "edges": [], "dimensions": [{"id": "D", "value": "wide", "unit": "cm"}], "relationships": []},
    {"nodes": [{"id": "A", "label": "a"}, {"id": "B", "label": "b"}], "edges": [], "dimensions": [], "relationships": [{"type": "near", "members": ["A", "B"]}]},
    {"nodes": [{"id": "A", "label": "a"}, {"id": "B", "label": "b"}], "edges": [], "dimensions": [], "relationships": [{"type": "parallel", "members": ["A", "Z"]}]},
]


@pytest.mark.parametrize("answer", GRAPH_CASES)
def test_seventy_five_machine_readable_graph_cases(answer):
    result = CoordinateGraphEngine().normalize(answer, contract("coordinate_graph"))
    assert result.status == "PASS" and result.engine_type == "coordinate_graph"


@pytest.mark.parametrize("answer", DIAGRAM_CASES)
def test_twenty_five_structured_diagram_cases(answer):
    result = StructuredDiagramEngine().normalize(answer, contract("structured_diagram"))
    assert result.status == "PASS" and result.engine_type == "structured_diagram"


@pytest.mark.parametrize("answer", MALFORMED)
def test_twenty_five_malformed_or_ambiguous_cases_fail_closed(answer):
    engine = StructuredDiagramEngine() if isinstance(answer, dict) and "nodes" in answer else CoordinateGraphEngine()
    assert engine.normalize(answer, contract(engine.engine_type)).status == "INVALID"


def test_graph_normalization_is_deterministic_and_numeric_canonical():
    engine = CoordinateGraphEngine(); spec = contract(engine.engine_type)
    first = {"points": [{"id": "B", "x": -0.0, "y": 2}, {"id": "A", "x": 1, "y": 1.0}]}
    second = {"points": [{"id": "A", "x": 1.0, "y": 1}, {"id": "B", "x": 0, "y": 2.0}]}
    a, b = engine.normalize(first, spec), engine.normalize(second, spec)
    assert a.value == b.value
    assert json.dumps(a.to_dict(), sort_keys=True, separators=(",", ":")) == json.dumps(b.to_dict(), sort_keys=True, separators=(",", ":"))
    assert engine.grade(first, second, spec).status == "PASS"


def test_lines_intercepts_transformations_vectors_and_feature_selections_grade():
    answer = {"lines": [{"id": "L", "slope": 2, "y_intercept": -4, "x_intercept": 2}], "vectors": [{"id": "v", "start": [0, 0], "end": [2, 3]}], "transformations": [{"type": "translate", "dx": 2, "dy": 3}, {"type": "rotate", "degrees": 90, "center": [0, 0]}, {"type": "reflect", "axis": "y=x"}], "features": ["x_intercept", "increasing"]}
    engine = CoordinateGraphEngine(); spec = contract(engine.engine_type)
    assert engine.grade(answer, answer, spec).status == "PASS"


def test_diagram_order_is_canonical_but_labels_and_relationships_must_match():
    expected = diagram(1)
    reordered = {key: list(reversed(value)) for key, value in expected.items()}
    engine = StructuredDiagramEngine(); spec = contract(engine.engine_type)
    assert engine.grade(reordered, expected, spec).status == "PASS"
    changed = diagram(1); changed["nodes"][0]["label"] = "different"
    assert engine.grade(changed, expected, spec).status == "FAIL"


def test_independent_derivation_registry_support_and_no_fallback():
    registry = register_graph_engines(AnswerEngineRegistry())
    for engine_type, answer in (("coordinate_graph", GRAPH_CASES[0]), ("structured_diagram", DIAGRAM_CASES[0])):
        spec = contract(engine_type)
        assert registry.support_decision(spec).status == "SUPPORTED"
        derived = registry.derive({"independently_derived_answer": answer}, spec)
        assert derived.status == "PASS" and derived.operation == "derive" and derived.engine_type == engine_type
    unsupported = contract("unrelated_engine")
    assert registry.normalize({}, unsupported).status == "UNSUPPORTED"


def test_contract_mismatch_and_freeform_or_image_answers_are_rejected():
    engine = CoordinateGraphEngine()
    assert engine.normalize(GRAPH_CASES[0], contract("structured_diagram")).status == "INVALID"
    assert engine.normalize("a hand-drawn parabola", contract(engine.engine_type)).status == "INVALID"
    assert engine.normalize({"image": "data:image/png;base64,..."}, contract(engine.engine_type)).status == "INVALID"


def test_diagram_ids_and_trimmed_relationship_members_are_globally_unambiguous():
    engine = StructuredDiagramEngine(); spec = contract(engine.engine_type)
    duplicate = {"nodes": [{"id": "X", "label": "node"}, {"id": "Y", "label": "node"}], "edges": [], "dimensions": [{"id": "X", "value": 1, "unit": "m"}], "relationships": []}
    trimmed = {"nodes": [{"id": "X", "label": "node"}, {"id": "Y", "label": "node"}], "edges": [], "dimensions": [], "relationships": [{"type": "connected", "members": ["X", "X "]}]}
    assert engine.normalize(duplicate, spec).status == "INVALID"
    assert engine.normalize(trimmed, spec).status == "INVALID"


@pytest.mark.parametrize("answer", [
    {"functions": [{"id": "f", "samples": [[0, 100], [1, 200]]}], "domain": [10, 20]},
    {"functions": [{"id": "f", "samples": [[0, 100], [1, 200]]}], "range": [-1, 1]},
    {"functions": [{"id": "f", "samples": [[0, 0], [1, 1]]}], "features": ["decreasing"]},
    {"lines": [{"id": "L", "slope": -1, "y_intercept": 0}], "features": ["increasing"]},
])
def test_cross_field_graph_contradictions_fail_closed(answer):
    engine = CoordinateGraphEngine()
    assert engine.normalize(answer, contract(engine.engine_type)).status == "INVALID"
