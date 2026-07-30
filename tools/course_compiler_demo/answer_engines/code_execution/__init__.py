"""Bounded Python answer engine.

The package is intentionally self-contained so synthesis can register the adapter
without weakening the shared registry while parallel lanes are in flight.
"""

from .engine import CodeExecutionPythonEngine, ExecutionPolicy

__all__ = ["CodeExecutionPythonEngine", "ExecutionPolicy"]
