"""Deterministic, machine-readable graph and diagram grading."""

from __future__ import annotations

import json
import math
from typing import Any, Mapping

from tools.course_compiler_demo.answer_engines.registry import (
    AnswerEngineDescriptor, AnswerEngineRegistry, AnswerEngineResult,
)
from tools.course_compiler_demo.universal_core import AnswerContractV1


def _failure(engine: str, operation: str, reason: str) -> AnswerEngineResult:
    return AnswerEngineResult("INVALID", engine, operation, None, (reason,))


def _number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("coordinates and measurements must be finite numbers")
    result = float(value)
    return 0.0 if result == 0 else result


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise ValueError(f"{name} must be non-empty bounded text")
    return value.strip()


def _keys(item: Mapping[str, Any], allowed: set[str], required: set[str]) -> None:
    if set(item) - allowed or not required <= set(item):
        raise ValueError("structure has missing or unsupported fields")


def _pair(value: Any) -> list[float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("coordinate pairs require exactly two numbers")
    return [_number(value[0]), _number(value[1])]


def _items(value: Any, name: str, *, required: bool = False, maximum: int = 500) -> list[Any]:
    if not isinstance(value, list) or (required and not value) or len(value) > maximum:
        raise ValueError(f"{name} must be a bounded list")
    return value


def _unique(items: list[Mapping[str, Any]], name: str) -> None:
    identities = [item["id"] for item in items]
    if len(identities) != len(set(identities)):
        raise ValueError(f"{name} ids must be unique")


class _Engine:
    engine_type = ""
    engine_id = ""
    engine_version = "1.0"
    supported_answer_contracts: tuple[str, ...] = ()

    def _contract(self, contract: Any, operation: str) -> AnswerEngineResult | None:
        if not isinstance(contract, AnswerContractV1) or contract.engine_type != self.engine_type:
            return _failure(self.engine_type, operation, "answer contract does not match engine")
        return None

    def derive(self, value: Mapping[str, Any], contract: AnswerContractV1) -> AnswerEngineResult:
        if not isinstance(value, Mapping) or "independently_derived_answer" not in value:
            return _failure(self.engine_type, "derive", "independently_derived_answer is required")
        result = self.normalize(value["independently_derived_answer"], contract)
        return AnswerEngineResult(result.status, result.engine_type, "derive", result.value, result.reasons)

    def grade(self, response: Any, expected: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._contract(contract, "grade"):
            return invalid
        actual, target = self.normalize(response, contract), self.normalize(expected, contract)
        if actual.status != "PASS" or target.status != "PASS":
            reasons = actual.reasons + target.reasons
            return _failure(self.engine_type, "grade", "; ".join(reasons) or "invalid answer")
        passed = json.dumps(actual.value, sort_keys=True, separators=(",", ":")) == json.dumps(target.value, sort_keys=True, separators=(",", ":"))
        return AnswerEngineResult("PASS" if passed else "FAIL", self.engine_type, "grade", passed)


class CoordinateGraphEngine(_Engine):
    engine_type = "coordinate_graph"
    engine_id = "coordinate-graph-structured-v1"
    supported_answer_contracts = ("coordinate_graph",)
    _allowed = {"points", "lines", "functions", "domain", "range", "transformations", "vectors", "features"}

    def normalize(self, answer: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._contract(contract, "normalize"):
            return invalid
        try:
            if not isinstance(answer, Mapping) or not answer or set(answer) - self._allowed:
                raise ValueError("graph answer must be a non-empty machine-readable graph object")
            out: dict[str, Any] = {}
            if "points" in answer:
                points = []
                for item in _items(answer["points"], "points"):
                    if not isinstance(item, Mapping): raise ValueError("point must be an object")
                    _keys(item, {"id", "x", "y", "label"}, {"id", "x", "y"})
                    point = {"id": _text(item["id"], "point id"), "x": _number(item["x"]), "y": _number(item["y"])}
                    if "label" in item: point["label"] = _text(item["label"], "label")
                    points.append(point)
                _unique(points, "point")
                out["points"] = sorted(points, key=lambda x: x["id"])
            if "lines" in answer:
                lines = []
                for item in _items(answer["lines"], "lines"):
                    if not isinstance(item, Mapping): raise ValueError("line must be an object")
                    _keys(item, {"id", "slope", "y_intercept", "x_intercept"}, {"id", "slope", "y_intercept"})
                    line = {"id": _text(item["id"], "line id"), "slope": _number(item["slope"]), "y_intercept": _number(item["y_intercept"])}
                    if "x_intercept" in item:
                        line["x_intercept"] = _number(item["x_intercept"])
                        if line["slope"] == 0 or not math.isclose(line["x_intercept"], -line["y_intercept"] / line["slope"], rel_tol=1e-12, abs_tol=1e-12):
                            raise ValueError("x-intercept is inconsistent with line equation")
                    lines.append(line)
                _unique(lines, "line")
                out["lines"] = sorted(lines, key=lambda x: x["id"])
            if "functions" in answer:
                funcs=[]
                for item in _items(answer["functions"], "functions"):
                    if not isinstance(item, Mapping): raise ValueError("function plot must be an object")
                    _keys(item,{"id","samples"},{"id","samples"})
                    samples=sorted((_pair(p) for p in _items(item["samples"], "function samples", required=True)),key=lambda p:(p[0],p[1]))
                    if len(samples) < 2 or len({sample[0] for sample in samples}) != len(samples): raise ValueError("function plot requires at least two unique x samples")
                    funcs.append({"id":_text(item["id"],"function id"),"samples":samples})
                _unique(funcs, "function")
                out["functions"]=sorted(funcs,key=lambda x:x["id"])
            for name in ("domain", "range"):
                if name in answer:
                    out[name] = _pair(answer[name])
                    if out[name][0] > out[name][1]: raise ValueError(f"{name} bounds must be ordered")
            if "vectors" in answer:
                vectors=[]
                for item in _items(answer["vectors"], "vectors"):
                    if not isinstance(item,Mapping): raise ValueError("vector must be an object")
                    _keys(item,{"id","start","end"},{"id","start","end"})
                    vectors.append({"id":_text(item["id"],"vector id"),"start":_pair(item["start"]),"end":_pair(item["end"])})
                _unique(vectors, "vector")
                out["vectors"]=sorted(vectors,key=lambda x:x["id"])
            if "transformations" in answer:
                trans=[]
                schemas = {
                    "translate": ({"type", "dx", "dy"}, ("dx", "dy")),
                    "scale": ({"type", "sx", "sy"}, ("sx", "sy")),
                    "rotate": ({"type", "degrees", "center"}, ("degrees",)),
                    "reflect": ({"type", "axis"}, ()),
                }
                for item in _items(answer["transformations"], "transformations"):
                    if not isinstance(item,Mapping): raise ValueError("transformation must be an object")
                    if "type" not in item: raise ValueError("transformation type is required")
                    kind=_text(item["type"],"transformation type")
                    if kind not in schemas: raise ValueError("unsupported transformation")
                    fields, numeric = schemas[kind]; _keys(item, fields, fields)
                    normalized = {"type": kind}
                    for field in numeric: normalized[field] = _number(item[field])
                    if kind == "rotate": normalized["center"] = _pair(item["center"])
                    if kind == "reflect":
                        axis = _text(item["axis"], "reflection axis")
                        if axis not in {"x", "y", "y=x", "y=-x"}: raise ValueError("unsupported reflection axis")
                        normalized["axis"] = axis
                    trans.append(normalized)
                out["transformations"]=trans
            if "features" in answer:
                allowed_features={"x_intercept","y_intercept","maximum","minimum","increasing","decreasing","constant","continuous","discontinuous","asymptote"}
                features=_items(answer["features"], "features")
                if not features or any(not isinstance(x,str) or x.strip() not in allowed_features for x in features) or len(features)!=len(set(features)): raise ValueError("features must be unique declared selections")
                out["features"]=sorted(x.strip() for x in features)
            if out.get("functions"):
                samples = [sample for function in out["functions"] for sample in function["samples"]]
                if "domain" in out and any(not out["domain"][0] <= sample[0] <= out["domain"][1] for sample in samples):
                    raise ValueError("function samples contradict declared domain")
                if "range" in out and any(not out["range"][0] <= sample[1] <= out["range"][1] for sample in samples):
                    raise ValueError("function samples contradict declared range")
                for function in out["functions"]:
                    deltas = [right[1] - left[1] for left, right in zip(function["samples"], function["samples"][1:])]
                    if "increasing" in out.get("features", []) and not all(delta > 0 for delta in deltas): raise ValueError("samples contradict increasing feature")
                    if "decreasing" in out.get("features", []) and not all(delta < 0 for delta in deltas): raise ValueError("samples contradict decreasing feature")
                    if "constant" in out.get("features", []) and not all(delta == 0 for delta in deltas): raise ValueError("samples contradict constant feature")
            if out.get("lines"):
                slopes = [line["slope"] for line in out["lines"]]
                if "increasing" in out.get("features", []) and not all(value > 0 for value in slopes): raise ValueError("lines contradict increasing feature")
                if "decreasing" in out.get("features", []) and not all(value < 0 for value in slopes): raise ValueError("lines contradict decreasing feature")
                if "constant" in out.get("features", []) and not all(value == 0 for value in slopes): raise ValueError("lines contradict constant feature")
            if not out: raise ValueError("graph contains no supported features")
            return AnswerEngineResult("PASS",self.engine_type,"normalize",out)
        except (TypeError, ValueError) as exc:
            return _failure(self.engine_type,"normalize",str(exc))


class StructuredDiagramEngine(_Engine):
    engine_type = "structured_diagram"
    engine_id = "structured-diagram-v1"
    supported_answer_contracts = ("structured_diagram",)

    def normalize(self, answer: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._contract(contract,"normalize"): return invalid
        try:
            if not isinstance(answer,Mapping) or set(answer)!={"nodes","edges","dimensions","relationships"}: raise ValueError("diagram requires nodes, edges, dimensions, and relationships")
            nodes=[]
            for item in _items(answer["nodes"], "nodes", required=True):
                if not isinstance(item,Mapping): raise ValueError("node must be an object")
                _keys(item,{"id","label"},{"id","label"}); nodes.append({"id":_text(item["id"],"node id"),"label":_text(item["label"],"node label")})
            ids=[x["id"] for x in nodes]
            if len(ids)!=len(set(ids)): raise ValueError("node ids must be unique")
            edges=[]
            for item in _items(answer["edges"], "edges"):
                if not isinstance(item,Mapping): raise ValueError("edge must be an object")
                _keys(item,{"id","source","target","label"},{"id","source","target","label"})
                edge={k:_text(item[k],f"edge {k}") for k in ("id","source","target","label")}
                if edge["source"] not in ids or edge["target"] not in ids: raise ValueError("edge references unknown node")
                edges.append(edge)
            _unique(edges, "edge")
            dimensions=[]
            for item in _items(answer["dimensions"], "dimensions"):
                if not isinstance(item,Mapping): raise ValueError("dimension must be an object")
                _keys(item,{"id","value","unit"},{"id","value","unit"})
                value=_number(item["value"])
                if value <= 0: raise ValueError("dimension value must be positive")
                dimensions.append({"id":_text(item["id"],"dimension id"),"value":value,"unit":_text(item["unit"],"unit")})
            _unique(dimensions, "dimension")
            relationships=[]
            allowed={"parallel","perpendicular","connected","equal","contains","adjacent"}
            all_ids=ids + [edge["id"] for edge in edges] + [dimension["id"] for dimension in dimensions]
            if len(all_ids) != len(set(all_ids)): raise ValueError("diagram ids must be globally unique")
            reference_ids=set(all_ids)
            for item in _items(answer["relationships"], "relationships"):
                if not isinstance(item,Mapping): raise ValueError("relationship must be an object")
                _keys(item,{"type","members"},{"type","members"}); kind=_text(item["type"],"relationship")
                members=item["members"]
                normalized_members=[x.strip() for x in members] if isinstance(members,list) and all(isinstance(x,str) for x in members) else []
                if kind not in allowed or len(normalized_members)<2 or len(normalized_members)!=len(set(normalized_members)) or not all(x in reference_ids for x in normalized_members): raise ValueError("invalid declared relationship")
                relationships.append({"type":kind,"members":sorted(normalized_members)})
            out={"nodes":sorted(nodes,key=lambda x:x["id"]),"edges":sorted(edges,key=lambda x:x["id"]),"dimensions":sorted(dimensions,key=lambda x:x["id"]),"relationships":sorted(relationships,key=lambda x:(x["type"],x["members"]))}
            return AnswerEngineResult("PASS",self.engine_type,"normalize",out)
        except (TypeError,ValueError) as exc: return _failure(self.engine_type,"normalize",str(exc))


def register_graph_engines(registry: AnswerEngineRegistry) -> AnswerEngineRegistry:
    """Register both enabled adapters in a caller-owned universal registry."""
    for engine in (CoordinateGraphEngine(), StructuredDiagramEngine()):
        registry.register(AnswerEngineDescriptor(engine.engine_type, True, "bounded machine-readable capability"), engine)
    return registry
