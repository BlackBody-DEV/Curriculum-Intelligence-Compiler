"""Bounded matrix and linear-system answer engine."""

from .engine import MatrixAnswerEngine, register_matrix_engine

__all__ = ("MatrixAnswerEngine", "register_matrix_engine")
