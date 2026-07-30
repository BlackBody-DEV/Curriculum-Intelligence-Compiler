"""Universal answer-engine registry."""

from .registry import (
    AnswerEngine,
    AnswerEngineDescriptor,
    AnswerEngineRegistry,
    AnswerEngineResult,
    build_default_registry,
    resolve_engine_type,
)
from .chemistry import ChemicalFormulaEngine, ChemicalReactionEngine
from .code_execution import CodeExecutionPythonEngine
from .graphs import CoordinateGraphEngine, StructuredDiagramEngine
from .matrix import MatrixAnswerEngine
from .scientific_response import ScientificStructuredResponseEngine, RubricScoredExplanationEngine
from .symbolic import EquationSystemEngine, SymbolicExpressionEngine

__all__ = [
    "AnswerEngine",
    "AnswerEngineDescriptor",
    "AnswerEngineRegistry",
    "AnswerEngineResult",
    "build_default_registry",
    "resolve_engine_type",
    "ChemicalFormulaEngine", "ChemicalReactionEngine", "CodeExecutionPythonEngine",
    "CoordinateGraphEngine", "StructuredDiagramEngine", "MatrixAnswerEngine",
    "ScientificStructuredResponseEngine", "RubricScoredExplanationEngine",
    "EquationSystemEngine", "SymbolicExpressionEngine",
]
