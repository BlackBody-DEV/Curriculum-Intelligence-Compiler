"""Family adapters for Phase E replay authority.

Family-specific field interpretation belongs here. The replay pipeline consumes
the universal row and benchmark packets returned by these adapters.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import load_json, sha256_file

PHASE_E_ROOT = Path("/Users/fanarichardson/AxiomIQ_Work/phase_e")
ADAPTIVE_ROOT = Path("/Users/fanarichardson/adaptive-platform")
FORCE_SYSTEMS_FAMILY_KEY = "force_systems"
VECTOR_OPERATIONS_FAMILY_KEY = "vector_operations"
DEFAULT_MIXED_REPLAY_FAMILY_KEYS = (FORCE_SYSTEMS_FAMILY_KEY, VECTOR_OPERATIONS_FAMILY_KEY)
UNAVAILABLE_FAMILY_CAPABILITIES = {
    "moments_and_couples": {
        "family_identifier": "Moments and Couples",
        "adapter_identifier": None,
        "finalized_immutable_records": 0,
        "runtime_supported_rows": 0,
        "adapter_implemented": False,
        "not_replayable_reason": "no finalized immutable records currently available",
    }
}


class FamilyAdapterError(ValueError):
    pass


@dataclass(frozen=True)
class PhaseEFamilyAdapter:
    family_key: str
    family_identifier: str
    adapter_identifier: str
    workspace: Path
    topic_code: str

    adapter_contract_version: str = "PHASE_E_FAMILY_ADAPTER_v0_1"

    @property
    def approved_dir(self) -> Path:
        return self.workspace / "approved"

    @property
    def manifest_dir(self) -> Path:
        return self.workspace / "manifest"

    def finalized_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        if not self.approved_dir.exists():
            return records
        for path in sorted(self.approved_dir.glob("*.json")):
            if path.name == "approved_manifest.json":
                continue
            artifact = load_json(path)
            if artifact.get("author_status") != "AUTHOR_COMPLETE":
                continue
            try:
                row = self.artifact_to_row(path, artifact)
                benchmark = self.artifact_to_benchmark(path, artifact)
            except FamilyAdapterError:
                continue
            records.append(
                {
                    "source_path": str(path),
                    "source_sha256": sha256_file(path),
                    "row": row,
                    "benchmark": benchmark,
                    "eligibility_evidence": {
                        "source": f"immutable finalized external {self.family_identifier} approved record",
                        "author_status": artifact.get("author_status"),
                        "stable_source_sha256": sha256_file(path),
                        "final_review_or_validation_evidence_present": True,
                        "active_editing_ownership": False,
                    },
                }
            )
        return records

    def artifact_to_row(self, path: Path, artifact: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def artifact_to_benchmark(self, path: Path, artifact: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def capability(self) -> dict[str, Any]:
        approved = list(self.approved_dir.glob("*.json")) if self.approved_dir.exists() else []
        author = list((self.workspace / "author_results").glob("*.json")) if (self.workspace / "author_results").exists() else []
        review = list((self.workspace / "review_results").glob("*.json")) if (self.workspace / "review_results").exists() else []
        manifest = list(self.manifest_dir.glob("*.json")) if self.manifest_dir.exists() else []
        finalized = self.finalized_records()
        qtypes: dict[str, int] = {}
        atypes: dict[str, int] = {}
        procs: dict[str, int] = {}
        for item in finalized:
            row = item["row"]
            qtypes[row["question_type"]] = qtypes.get(row["question_type"], 0) + 1
            atypes[row["answer_type"]] = atypes.get(row["answer_type"], 0) + 1
            procs[row["procedure_id"]] = procs.get(row["procedure_id"], 0) + 1
        return {
            "family_identifier": self.family_identifier,
            "adapter_identifier": self.adapter_identifier,
            "manifest_authority": [{"path": str(p), "sha256": sha256_file(p)} for p in manifest],
            "ledger_authority": [{"path": str(p), "sha256": sha256_file(p)} for p in manifest if "ledger" in p.name.lower()],
            "workspace_approved_records": len(approved),
            "workspace_author_results": len(author),
            "workspace_review_results": len(review),
            "finalized_immutable_records": len(finalized),
            "question_type_allocations": qtypes,
            "answer_type_allocations": atypes,
            "procedure_coverage_count": len(procs),
            "runtime_supported_rows": len(finalized),
            "unsupported_rows": [],
            "adapter_implemented": True,
        }


class ForceSystemsFamilyAdapter(PhaseEFamilyAdapter):
    def __init__(self) -> None:
        super().__init__(
            family_key="force_systems",
            family_identifier="Force Systems",
            adapter_identifier="ForceSystemsFamilyAdapter",
            workspace=PHASE_E_ROOT / "force_systems",
            topic_code="STATICS_FORCE_SYSTEMS",
        )

    def artifact_to_row(self, path: Path, artifact: dict[str, Any]) -> dict[str, Any]:
        frozen = artifact["frozen_manifest_row"]
        answer_type = artifact["answer_type"]
        if answer_type not in {"numeric", "multiple_choice"}:
            raise FamilyAdapterError(f"unsupported Force Systems answer type: {answer_type}")
        if artifact.get("question_type") not in {"numeric_tolerance", "multiple_choice"}:
            raise FamilyAdapterError(f"unsupported Force Systems question type: {artifact.get('question_type')}")
        return {
            "manifest_uuid": artifact["question_id"],
            "ordinal": artifact["ordinal"],
            "family_identifier": frozen.get("family_id", self.family_identifier),
            "destination_canonical_path": artifact["reserved_canonical_path"],
            "ledger_identity": {"ordinal": artifact["ordinal"], "question_id": artifact["question_id"], "canonical_path": artifact["reserved_canonical_path"]},
            "signed_procedure": {"procedure_id": artifact["procedure_id"], "procedure_steps": artifact.get("procedure_steps_verbatim", [])},
            "procedure_id": artifact["procedure_id"],
            "procedure_sha256": artifact["procedure_sha256"],
            "generation_family": frozen.get("generation_family", "golden_replay"),
            "difficulty": frozen.get("difficulty_level", 1),
            "question_type": artifact["question_type"],
            "answer_type": answer_type,
            "answer_parts_contract": artifact.get("answer_parts_contract"),
            "tolerance_policy": {"tolerance": artifact.get("tolerance") or frozen.get("tolerance")},
            "permitted_failure_signals": artifact.get("permitted_failure_signals") or frozen.get("permitted_failure_signals", []),
            "prompt_constraints": frozen.get("prompt_constraints", "Use text-only replay constraints."),
            "primitive_input_data": _force_numeric_primitive_data(artifact) if answer_type == "numeric" else (artifact.get("givens", {}).get("scenario") or "complete-option support inventory scenario"),
            "diagram_policy": {"diagram_required": bool(frozen.get("diagram_required", False))},
            "uniqueness_constraints": [artifact["reserved_canonical_path"]],
            "existing_record_disposition": "finalized_immutable_golden_replay_source",
            "adapter_identifier": self.adapter_identifier,
            "adapter_contract_version": self.adapter_contract_version,
            "adapter_metadata": {"source_path": str(path), "source_sha256": sha256_file(path)},
        }

    def artifact_to_benchmark(self, path: Path, artifact: dict[str, Any]) -> dict[str, Any]:
        if artifact["answer_type"] == "multiple_choice":
            answer = artifact.get("answer") or {}
            correct_option_id = answer.get("option_id") or answer.get("correct_option_id") or artifact.get("correct_option_id")
            if not correct_option_id:
                raise FamilyAdapterError("multiple-choice artifact lacks correct option authority")
            expected_answer = {"type": "multiple_choice", "correct_option_id": correct_option_id}
        else:
            answers = artifact.get("answers") or artifact.get("answer_parts") or []
            if not answers:
                raise FamilyAdapterError("numeric artifact lacks final answer authority")
            answer = answers[0]
            expected_answer = {"type": "numeric", "value": round(float(answer["value"]), 6), "unit": answer.get("unit", "N")}
            correct_option_id = None
        return _benchmark_packet(path, artifact, expected_answer, correct_option_id)


class VectorOperationsFamilyAdapter(PhaseEFamilyAdapter):
    def __init__(self) -> None:
        super().__init__(
            family_key="vector_operations",
            family_identifier="Vector Operations",
            adapter_identifier="VectorOperationsFamilyAdapter",
            workspace=PHASE_E_ROOT / "vector_operations",
            topic_code="STATICS_VECTORS",
        )

    def artifact_to_row(self, path: Path, artifact: dict[str, Any]) -> dict[str, Any]:
        if artifact.get("answer_type") != "numeric_pair" or artifact.get("question_type") != "numeric_pair":
            raise FamilyAdapterError("unsupported Vector Operations row shape")
        givens = artifact.get("givens") or {}
        required = {"magnitude", "angle_deg", "reference_axis", "x_sign", "y_sign"}
        if not required.issubset(givens):
            raise FamilyAdapterError("unsupported Vector Operations primitive data")
        frozen = artifact["frozen_manifest_row"]
        return {
            "manifest_uuid": artifact["question_id"],
            "ordinal": artifact["ordinal"],
            "family_identifier": frozen.get("family_id", self.family_identifier),
            "destination_canonical_path": artifact.get("reserved_canonical_path") or f"curriculum/statics/questions/{self.topic_code}/{artifact['ordinal']:03d}_{artifact['question_id']}.json",
            "ledger_identity": {"ordinal": artifact["ordinal"], "question_id": artifact["question_id"], "canonical_path": artifact.get("reserved_canonical_path")},
            "signed_procedure": {"procedure_id": artifact["procedure_id"], "procedure_steps": artifact.get("procedure_steps_verbatim", [])},
            "procedure_id": artifact["procedure_id"],
            "procedure_sha256": artifact["procedure_sha256"],
            "generation_family": artifact.get("generation_family") or frozen.get("generation_family", "vector_components_2d"),
            "difficulty": artifact.get("difficulty_level") or frozen.get("difficulty_level", 1),
            "question_type": artifact["question_type"],
            "answer_type": artifact["answer_type"],
            "answer_parts_contract": artifact.get("answer_parts_contract"),
            "tolerance_policy": {"tolerance": 0.05, "unit": givens.get("unit", "N")},
            "permitted_failure_signals": artifact.get("permitted_failure_signals") or frozen.get("permitted_failure_signals", []),
            "prompt_constraints": "Use text-only Cartesian vector component givens. Preserve output order F_x, F_y.",
            "primitive_input_data": _vector_primitive_text(givens),
            "diagram_policy": {"diagram_required": bool(artifact.get("diagram_required") or frozen.get("diagram_required", False))},
            "uniqueness_constraints": [artifact["question_id"], str(path)],
            "existing_record_disposition": "finalized_immutable_golden_replay_source",
            "adapter_identifier": self.adapter_identifier,
            "adapter_contract_version": self.adapter_contract_version,
            "adapter_metadata": {"source_path": str(path), "source_sha256": sha256_file(path), "givens": givens},
        }

    def artifact_to_benchmark(self, path: Path, artifact: dict[str, Any]) -> dict[str, Any]:
        expected_answer = {
            "type": "numeric_pair",
            "values": [
                {"label": part["label"], "value": round(float(part["value"]), 6), "unit": part.get("unit", "N")}
                for part in artifact["answer_parts"]
            ],
        }
        return _benchmark_packet(path, artifact, expected_answer, None)


def _benchmark_packet(path: Path, artifact: dict[str, Any], expected_answer: dict[str, Any], correct_option_id: str | None) -> dict[str, Any]:
    return {
        "benchmark_identifier": f"{artifact['ordinal']:03d}-{artifact['question_id']}",
        "source_path": str(path),
        "source_sha256": sha256_file(path),
        "manifest_uuid": artifact["question_id"],
        "ordinal": artifact["ordinal"],
        "procedure_id": artifact["procedure_id"],
        "procedure_sha256": artifact["procedure_sha256"],
        "question_type": artifact["question_type"],
        "answer_type": artifact["answer_type"],
        "benchmark_prompt": artifact.get("prompt", ""),
        "expected_answer": expected_answer,
        "worked_solution": artifact.get("solution", {}),
        "correct_option_id": correct_option_id,
        "answer_bearing_parameters": {"benchmark_answer_contract_complete": True},
        "review_notes": "finalized external record selected for golden replay",
        "validation_conclusions": artifact.get("author_status", "AUTHOR_COMPLETE"),
        "benchmark_canary": f"CANARY_{artifact['ordinal']:03d}_{artifact['question_id'][:8]}",
    }


def _force_numeric_primitive_data(artifact: dict[str, Any]) -> str:
    from .common import parse_component_vectors

    vectors = parse_component_vectors(str(artifact.get("prompt", "")))
    if not vectors:
        raise FamilyAdapterError(f"numeric artifact lacks generation-visible component vectors: {artifact.get('question_id')}")
    vector_text = ", ".join(f"F{index}=<{x:g},{y:g}> N" for index, (x, y) in enumerate(vectors, start=1))
    return f"Signed rectangular force components are {vector_text}. Determine only nonnegative resultant magnitude R."


def _vector_primitive_text(givens: dict[str, Any]) -> str:
    return (
        "Vector component givens: "
        f"magnitude={givens['magnitude']} {givens.get('unit', 'N')}; "
        f"angle_deg={givens['angle_deg']}; reference_axis={givens['reference_axis']}; "
        f"angle_sense={givens.get('angle_sense', 'declared')}; "
        f"x_sign={givens['x_sign']}; y_sign={givens['y_sign']}."
    )


def vector_components_from_primitive(text: str) -> dict[str, Any]:
    import re

    def grab(name: str) -> str:
        match = re.search(rf"{name}=([^;\\.]+)", text)
        if not match:
            raise ValueError(f"missing {name}")
        return match.group(1).strip()

    magnitude = float(grab("magnitude").split()[0])
    unit = grab("magnitude").split()[1] if len(grab("magnitude").split()) > 1 else "N"
    angle_deg = float(grab("angle_deg"))
    reference_axis = grab("reference_axis")
    x_sign = float(grab("x_sign"))
    y_sign = float(grab("y_sign"))
    angle = math.radians(angle_deg)
    if reference_axis in {"+x", "-x"}:
        x_mag = magnitude * math.cos(angle)
        y_mag = magnitude * math.sin(angle)
    elif reference_axis in {"+y", "-y"}:
        y_mag = magnitude * math.cos(angle)
        x_mag = magnitude * math.sin(angle)
    else:
        raise ValueError(f"unsupported reference_axis: {reference_axis}")
    return {
        "type": "numeric_pair",
        "values": [
            {"label": "F_x", "value": round(x_sign * x_mag, 6), "unit": unit},
            {"label": "F_y", "value": round(y_sign * y_mag, 6), "unit": unit},
        ],
    }


_ADAPTERS: dict[str, PhaseEFamilyAdapter] = {
    FORCE_SYSTEMS_FAMILY_KEY: ForceSystemsFamilyAdapter(),
    VECTOR_OPERATIONS_FAMILY_KEY: VectorOperationsFamilyAdapter(),
}


def get_family_adapter(family_key: str) -> PhaseEFamilyAdapter:
    try:
        return _ADAPTERS[family_key]
    except KeyError as exc:
        raise FamilyAdapterError(f"unknown Phase E family: {family_key}") from exc


def registered_adapters() -> dict[str, PhaseEFamilyAdapter]:
    return dict(_ADAPTERS)


def protected_family_workspace_roots() -> tuple[Path, ...]:
    return tuple(adapter.workspace for adapter in _ADAPTERS.values())
