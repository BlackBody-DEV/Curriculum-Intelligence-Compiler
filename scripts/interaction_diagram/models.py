"""Compiler-side immutable models for declarative interaction specifications."""
from dataclasses import dataclass
from typing import Any, Mapping

@dataclass(frozen=True)
class InteractionSchemaDeclaration:
    interaction_schema_id: str
    interaction_schema_version: str
    interaction_schema_sha256: str

@dataclass(frozen=True)
class CalculatedValue:
    id: str
    formula_id: str
    inputs: Mapping[str, Any]
    unit: str

@dataclass(frozen=True)
class InteractionSpecification:
    schema_id: str
    schema_version: str
    spec_id: str
    renderer_id: str
    linked_explanation_id: str
    linked_procedure_id: str
    payload: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]):
        return cls(value['schema_id'],value['schema_version'],value['spec_id'],value['renderer_id'],value['linked_explanation_id'],value['linked_procedure_id'],dict(value))
