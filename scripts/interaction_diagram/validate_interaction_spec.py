"""Gates 1-8 validators for interactive instructional diagram interaction specs.

Gates 9-16 are renderer-side and out of scope for this module.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

import jsonschema

from .formulas import FormulaError, evaluate_formula

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = (
    REPO_ROOT
    / "schemas"
    / "axiomiq_interactive_instructional_diagram_interaction_v1.schema.json"
)

GATE_NAMES = (
    "schema",
    "procedure_link",
    "diagram_to_text_consistency",
    "mathematical_state",
    "deterministic_replay",
    "variable_bound",
    "reset_state",
    "step_transition",
)

FORBIDDEN_EXACT_KEYS = {
    "script",
    "javascript",
    "__proto__",
    "constructor",
    "eval",
    "expression",
    "expr",
    "code",
    "handler",
    "callback",
    "onclick",
    "ondblclick",
    "onmousedown",
    "onmouseup",
    "onmouseover",
    "onmouseout",
    "onkeydown",
    "onkeyup",
    "onload",
    "onerror",
}

FORBIDDEN_STRING_PATTERNS = (
    re.compile(r"(?i)<\s*script\b"),
    re.compile(r"(?i)\bjavascript\s*:"),
    re.compile(r"(?i)\bdata\s*:"),
    re.compile(r"(?i)\bhttps?\s*:"),
    re.compile(r"(?i)\beval\s*\("),
    re.compile(r"(?i)\bnew\s+Function\b"),
    re.compile(r"(?i)\bon[a-z]+\s*="),
    re.compile(r"(?i)\bimport\s*\("),
    re.compile(r"[\r\n].*;\s*"),  # multi-statement script-like payloads
)

SUPPORTED_RENDERERS = {
    "statics_vector_plane_v1",
    "statics_force_vector_v1",
    "statics_fbd_v1",
    "statics_composite_area_v1",
}

DIAGRAM_FINGERPRINT_FIELDS = (
    "diagram_type",
    "renderer_id",
    "visible_labels",
    "units",
    "static_fallback_specification",
)

INTERACTION_FINGERPRINT_FIELDS = (
    "student_adjustable_variables",
    "available_toggles",
    "dependent_calculated_values",
    "geometric_constraints",
    "mathematical_constraints",
    "procedural_step_states",
    "expected_state_transitions",
    "keyboard_interaction_model",
    "initial_state",
    "reset_state",
)


@dataclass
class GateResult:
    gate: str
    passed: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    passed: bool
    gate_results: list[GateResult]
    security_rejections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "security_rejections": list(self.security_rejections),
            "gates": [
                {
                    "gate": item.gate,
                    "passed": item.passed,
                    "errors": list(item.errors),
                }
                for item in self.gate_results
            ],
        }


def _canonical_dumps(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def fingerprint_payload(value: Any) -> str:
    return hashlib.sha256(_canonical_dumps(value).encode("utf-8")).hexdigest()


def compute_diagram_fingerprint(spec: Mapping[str, Any]) -> str:
    payload = {key: spec[key] for key in DIAGRAM_FINGERPRINT_FIELDS}
    return fingerprint_payload(payload)


def compute_interaction_fingerprint(spec: Mapping[str, Any]) -> str:
    payload = {key: spec[key] for key in INTERACTION_FINGERPRINT_FIELDS}
    return fingerprint_payload(payload)


def _walk(node: Any, path: str = "$") -> list[tuple[str, Any]]:
    found: list[tuple[str, Any]] = [(path, node)]
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(_walk(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found.extend(_walk(value, f"{path}[{index}]"))
    return found


def collect_security_rejections(spec: Any) -> list[str]:
    rejections: list[str] = []
    if not isinstance(spec, dict):
        return ["spec must be a JSON object"]

    renderer = spec.get("renderer_id")
    if renderer not in SUPPORTED_RENDERERS:
        rejections.append(f"unsupported renderer_id: {renderer!r}")

    for path, node in _walk(spec):
        if isinstance(node, dict):
            for key in node:
                lowered = str(key).lower()
                if lowered in FORBIDDEN_EXACT_KEYS:
                    rejections.append(
                        f"forbidden key at {path}.{key}: executable or event surface rejected"
                    )
                    continue
                # Reject unknown short on* event handler keys (onclick already exact-matched).
                if (
                    lowered.startswith("on")
                    and len(lowered) <= 32
                    and lowered[2:].isalpha()
                    and lowered
                    not in {
                        "online",
                        "only",
                        "onset",
                        "onto",
                    }
                ):
                    rejections.append(
                        f"forbidden event-handler key at {path}.{key}"
                    )
        if isinstance(node, str):
            for pattern in FORBIDDEN_STRING_PATTERNS:
                if pattern.search(node):
                    rejections.append(
                        f"forbidden executable/remote payload at {path}: {node[:80]!r}"
                    )
                    break
            if node.strip().startswith(("http://", "https://", "//", "javascript:", "data:")):
                rejections.append(f"remote or executable asset rejected at {path}")

    for calc in spec.get("dependent_calculated_values", []) if isinstance(spec, dict) else []:
        if not isinstance(calc, dict):
            continue
        formula_id = calc.get("formula_id")
        if not isinstance(formula_id, str) or formula_id not in {
            "cartesian_fx_from_magnitude_angle_deg",
            "cartesian_fy_from_magnitude_angle_deg",
            "sum_selected",
            "resultant_magnitude_from_rx_ry",
            "resultant_direction_deg_from_rx_ry",
        }:
            rejections.append(
                f"unvalidated or unsupported formula_id rejected: {formula_id!r}"
            )
        # Reject smuggling free-form math through operand strings.
        for value in (calc.get("inputs") or {}).values():
            if isinstance(value, str) and any(ch in value for ch in "()*/+-%"):
                rejections.append(
                    f"unvalidated expression-like input rejected: {value!r}"
                )

    # Deduplicate while preserving order.
    seen: set[str] = set()
    unique: list[str] = []
    for item in rejections:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def gate_schema(spec: Mapping[str, Any]) -> GateResult:
    errors: list[str] = []
    try:
        jsonschema.validate(instance=spec, schema=_load_schema())
    except jsonschema.ValidationError as exc:
        errors.append(exc.message)
    except Exception as exc:  # pragma: no cover - fail closed
        errors.append(f"schema validation failed closed: {exc}")

    if isinstance(spec, dict):
        expected_diagram = compute_diagram_fingerprint(spec)
        expected_interaction = compute_interaction_fingerprint(spec)
        if spec.get("diagram_fingerprint") != expected_diagram:
            errors.append("diagram_fingerprint does not match canonical diagram payload")
        if spec.get("interaction_fingerprint") != expected_interaction:
            errors.append(
                "interaction_fingerprint does not match canonical interaction payload"
            )
    return GateResult("schema", not errors, errors)


def gate_procedure_link(
    spec: Mapping[str, Any],
    procedure_registry: Mapping[str, Mapping[str, Any]] | None,
) -> GateResult:
    errors: list[str] = []
    if not procedure_registry:
        errors.append("procedure registry is required for procedure-link gate")
        return GateResult("procedure_link", False, errors)

    procedure_id = spec.get("linked_procedure_id")
    signature = spec.get("linked_procedure_signature") or {}
    record = procedure_registry.get(str(procedure_id))
    if record is None:
        errors.append(f"linked_procedure_id not found in registry: {procedure_id!r}")
        return GateResult("procedure_link", False, errors)

    status = record.get("status") or (record.get("phase_d_sign_off") or {}).get("status")
    if status != "signed_off":
        errors.append(f"linked procedure is not signed_off: {procedure_id!r}")

    phase = record.get("phase_d_sign_off") or record.get("signature") or {}
    for key in ("status", "reviewer", "date"):
        if signature.get(key) != phase.get(key) and key in signature:
            # Allow notes-only drift; status/reviewer/date must match authority.
            if key == "status" or signature.get(key) != phase.get(key):
                if signature.get(key) != phase.get(key):
                    errors.append(
                        f"linked_procedure_signature.{key} does not match authority signature"
                    )
    if signature.get("status") != "signed_off":
        errors.append("linked_procedure_signature.status must be signed_off")

    step_count = 0
    procedure_steps = record.get("procedure")
    if isinstance(procedure_steps, list):
        step_count = len(procedure_steps)
    declared_steps = spec.get("procedural_step_states") or []
    if step_count and len(declared_steps) != step_count:
        errors.append(
            "procedural_step_states count must match linked procedure step count"
        )
    else:
        for index, step in enumerate(declared_steps, start=1):
            if step.get("procedure_step_index") != index:
                errors.append(
                    f"procedural_step_states[{index - 1}].procedure_step_index must be {index}"
                )
    return GateResult("procedure_link", not errors, errors)


def gate_diagram_to_text_consistency(spec: Mapping[str, Any]) -> GateResult:
    errors: list[str] = []
    variable_ids = {item["id"] for item in spec.get("student_adjustable_variables", [])}
    calc_ids = {item["id"] for item in spec.get("dependent_calculated_values", [])}
    toggle_ids = {item["id"] for item in spec.get("available_toggles", [])}
    known = variable_ids | calc_ids | toggle_ids

    objective = str(spec.get("instructional_objective", "")).lower()
    accessibility = str(spec.get("accessibility_description", "")).lower()
    if "script" in objective or "script" in accessibility:
        errors.append("diagram text must not reference executable scripts")

    for label in spec.get("visible_labels", []):
        binds_to = label.get("binds_to")
        root = str(binds_to).split(".", 1)[0]
        if root not in known and binds_to not in known:
            errors.append(f"visible label binds to unknown value: {binds_to!r}")
        toggle = label.get("visible_when_toggle")
        if toggle is not None and toggle not in toggle_ids:
            errors.append(f"visible label references unknown toggle: {toggle!r}")

    # Vector explanation must mention components and resultant in accessibility text.
    if spec.get("diagram_type") in {"vector_plane", "force_vector"}:
        needed = ("component", "resultant", "magnitude", "direction")
        for token in needed:
            if token not in accessibility:
                errors.append(
                    f"accessibility_description missing required concept: {token}"
                )
    return GateResult("diagram_to_text_consistency", not errors, errors)


def _merge_values(
    variables: Mapping[str, float], calculated: Mapping[str, float]
) -> dict[str, float]:
    merged = dict(variables)
    merged.update(calculated)
    return merged


def evaluate_calculated(
    spec: Mapping[str, Any], variables: Mapping[str, float]
) -> dict[str, float]:
    values = {str(key): float(value) for key, value in variables.items()}
    # Dependents may rely on earlier dependents; evaluate in declared order.
    for calc in spec.get("dependent_calculated_values", []):
        result = evaluate_formula(calc["formula_id"], values, calc.get("inputs") or {})
        values[calc["id"]] = float(result)
    return {
        calc["id"]: values[calc["id"]]
        for calc in spec.get("dependent_calculated_values", [])
    }


def gate_mathematical_state(spec: Mapping[str, Any]) -> GateResult:
    errors: list[str] = []
    try:
        baseline = evaluate_calculated(spec, spec["initial_state"]["variables"])
    except (FormulaError, KeyError, TypeError, ValueError) as exc:
        return GateResult("mathematical_state", False, [f"initial-state math failed: {exc}"])

    for case in spec.get("deterministic_validation_cases", []):
        try:
            got = evaluate_calculated(spec, case["input_variables"])
        except (FormulaError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"case {case.get('case_id')}: {exc}")
            continue
        for key, expected in (case.get("expected_calculated") or {}).items():
            tolerance = float((case.get("tolerance") or {}).get(key, 0.0))
            actual = got.get(key)
            if actual is None:
                errors.append(f"case {case['case_id']}: missing calculated value {key}")
                continue
            if abs(actual - float(expected)) > tolerance:
                errors.append(
                    f"case {case['case_id']}: {key} expected {expected} ± {tolerance}, got {actual}"
                )

    # Constraints that declare dependent_matches_formula against initial state.
    for constraint in spec.get("mathematical_constraints", []):
        if constraint.get("constraint_type") != "dependent_matches_formula":
            continue
        dependent = constraint.get("operands", {}).get("dependent")
        if dependent not in baseline:
            errors.append(f"constraint {constraint.get('id')}: unknown dependent")
    return GateResult("mathematical_state", not errors, errors)


def gate_deterministic_replay(spec: Mapping[str, Any]) -> GateResult:
    errors: list[str] = []
    first: list[dict[str, float]] = []
    second: list[dict[str, float]] = []
    for case in spec.get("deterministic_validation_cases", []):
        try:
            first.append(evaluate_calculated(spec, case["input_variables"]))
            second.append(evaluate_calculated(spec, case["input_variables"]))
        except (FormulaError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"replay failed for {case.get('case_id')}: {exc}")
            continue
    if _canonical_dumps(first) != _canonical_dumps(second):
        errors.append("deterministic replay diverged across identical inputs")
    return GateResult("deterministic_replay", not errors, errors)


def _within_increment(value: float, minimum: float, increment: float) -> bool:
    if increment <= 0:
        return False
    steps = round((value - minimum) / increment)
    reconstituted = minimum + steps * increment
    return math.isclose(reconstituted, value, rel_tol=0.0, abs_tol=1e-9)


def gate_variable_bound(spec: Mapping[str, Any]) -> GateResult:
    errors: list[str] = []
    variables = {
        item["id"]: item for item in spec.get("student_adjustable_variables", [])
    }
    states = [spec["initial_state"], spec["reset_state"]]
    states.extend(
        {
            "variables": case["input_variables"],
            "toggles": case.get("toggle_overrides") or {},
            "active_step_id": spec["initial_state"]["active_step_id"],
        }
        for case in spec.get("deterministic_validation_cases", [])
    )

    for state in states:
        for var_id, meta in variables.items():
            if var_id not in state["variables"]:
                errors.append(f"state missing adjustable variable {var_id}")
                continue
            value = float(state["variables"][var_id])
            minimum = float(meta["minimum"])
            maximum = float(meta["maximum"])
            increment = float(meta["increment"])
            if value < minimum or value > maximum:
                errors.append(
                    f"{var_id}={value} outside declared bounds [{minimum}, {maximum}]"
                )
            if not _within_increment(value, minimum, increment):
                errors.append(
                    f"{var_id}={value} is not aligned to increment {increment} from {minimum}"
                )
            if minimum > maximum:
                errors.append(f"{var_id} has minimum greater than maximum")
    return GateResult("variable_bound", not errors, errors)


def gate_reset_state(spec: Mapping[str, Any]) -> GateResult:
    errors: list[str] = []
    initial = spec["initial_state"]
    reset = spec["reset_state"]
    if initial["variables"] != reset["variables"]:
        errors.append("reset_state.variables must equal initial_state.variables")
    if initial["toggles"] != reset["toggles"]:
        errors.append("reset_state.toggles must equal initial_state.toggles")
    if reset["active_step_id"] != initial["active_step_id"]:
        # Reset may return to the first instructional step even if later navigation occurred.
        first_step = spec["procedural_step_states"][0]["step_id"]
        if reset["active_step_id"] != first_step:
            errors.append("reset_state.active_step_id must equal the first procedural step")
    return GateResult("reset_state", not errors, errors)


def gate_step_transition(spec: Mapping[str, Any]) -> GateResult:
    errors: list[str] = []
    step_ids = [step["step_id"] for step in spec.get("procedural_step_states", [])]
    step_set = set(step_ids)
    if len(step_ids) != len(step_set):
        errors.append("procedural_step_states contains duplicate step_id values")

    transitions = spec.get("expected_state_transitions", [])
    if not any(item.get("trigger") == "auto_enter_on_load" for item in transitions):
        errors.append("expected_state_transitions must include auto_enter_on_load")
    if not any(item.get("trigger") == "student_reset" for item in transitions):
        errors.append("expected_state_transitions must include student_reset")

    adjacency: dict[str, set[str]] = {step_id: set() for step_id in step_ids}
    for item in transitions:
        source = item.get("from_step_id")
        target = item.get("to_step_id")
        if source not in step_set or target not in step_set:
            errors.append(
                f"transition {item.get('id')} references unknown step ({source!r} -> {target!r})"
            )
            continue
        if item.get("trigger") == "student_next_step":
            adjacency[source].add(target)

    # Forward next-step chain must cover every consecutive pair.
    for left, right in zip(step_ids, step_ids[1:]):
        if right not in adjacency.get(left, set()):
            errors.append(
                f"missing student_next_step transition from {left} to {right}"
            )
    return GateResult("step_transition", not errors, errors)


def validate_interaction_spec(
    spec: Mapping[str, Any] | Any,
    *,
    procedure_registry: Mapping[str, Mapping[str, Any]] | None = None,
) -> ValidationReport:
    security_rejections = collect_security_rejections(spec)
    gate_results: list[GateResult] = []

    if security_rejections:
        # Fail closed before semantic gates consume untrusted content.
        for gate in GATE_NAMES:
            gate_results.append(
                GateResult(
                    gate,
                    False,
                    ["blocked by security rejection"] if gate == "schema" else [],
                )
            )
        gate_results[0].errors.extend(security_rejections)
        return ValidationReport(False, gate_results, security_rejections)

    assert isinstance(spec, dict)
    gate_results.append(gate_schema(spec))
    gate_results.append(gate_procedure_link(spec, procedure_registry))
    gate_results.append(gate_diagram_to_text_consistency(spec))
    gate_results.append(gate_mathematical_state(spec))
    gate_results.append(gate_deterministic_replay(spec))
    gate_results.append(gate_variable_bound(spec))
    gate_results.append(gate_reset_state(spec))
    gate_results.append(gate_step_transition(spec))

    passed = all(item.passed for item in gate_results)
    return ValidationReport(passed, gate_results, [])


def load_procedure_registry_from_paths(paths: Sequence[Path]) -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for path in paths:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        procedure_id = data.get("procedure_id")
        if not isinstance(procedure_id, str):
            raise ValueError(f"procedure file missing procedure_id: {path}")
        registry[procedure_id] = data
    return registry
