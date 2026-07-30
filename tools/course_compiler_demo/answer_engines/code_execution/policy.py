"""Fail-closed AST policy for the bounded Python subset."""

from __future__ import annotations

import ast
from dataclasses import dataclass


SAFE_CALLS = frozenset({"abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "len", "list", "max", "min", "print", "range", "reversed", "round", "sorted", "str", "sum", "tuple", "zip"})
FORBIDDEN_NAMES = frozenset({"eval", "exec", "compile", "open", "__import__", "os", "sys", "socket", "subprocess", "pathlib", "ctypes", "multiprocessing", "globals", "locals", "vars", "getattr", "setattr", "delattr", "input", "help", "breakpoint", "memoryview", "type", "object", "super"})
ALLOWED_NODES = (
    ast.Module, ast.Expr, ast.Assign, ast.AnnAssign, ast.Name, ast.Load, ast.Store,
    ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.Set, ast.BinOp, ast.UnaryOp,
    ast.BoolOp, ast.Compare, ast.If, ast.IfExp, ast.For, ast.While, ast.Break,
    ast.Continue, ast.Pass, ast.FunctionDef, ast.arguments, ast.arg, ast.Return,
    ast.Call, ast.Subscript, ast.Slice, ast.ListComp, ast.SetComp, ast.DictComp,
    ast.GeneratorExp, ast.comprehension, ast.Add, ast.Sub, ast.Mult, ast.Div,
    ast.FloorDiv, ast.Mod, ast.Pow, ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
)


class PolicyViolation(ValueError):
    pass


@dataclass(frozen=True)
class AstPolicy:
    max_source_bytes: int = 16_384
    max_nodes: int = 1_000
    max_literal_items: int = 1_000

    def validate(self, source: str) -> ast.Module:
        if not isinstance(source, str) or not source.strip():
            raise PolicyViolation("non-empty Python source is required")
        if len(source.encode("utf-8")) > self.max_source_bytes:
            raise PolicyViolation("source exceeds byte limit")
        try:
            tree = ast.parse(source, mode="exec")
        except (SyntaxError, ValueError) as exc:
            raise PolicyViolation(f"invalid syntax: {exc.msg if isinstance(exc, SyntaxError) else exc}") from None
        nodes = list(ast.walk(tree))
        if len(nodes) > self.max_nodes:
            raise PolicyViolation("program exceeds AST node limit")
        functions = {node.name for node in nodes if isinstance(node, ast.FunctionDef)}
        for node in nodes:
            if not isinstance(node, ALLOWED_NODES):
                raise PolicyViolation(f"syntax {type(node).__name__} is prohibited")
            if isinstance(node, ast.Name) and (node.id.startswith("_") or node.id in FORBIDDEN_NAMES):
                raise PolicyViolation(f"name {node.id!r} is prohibited")
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith("_") or node.decorator_list or node.args.vararg or node.args.kwarg:
                    raise PolicyViolation("function decorators and variadic arguments are prohibited")
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_CALLS | functions:
                    raise PolicyViolation("only allowlisted builtins and declared functions may be called")
            if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)) and len(node.value) > self.max_source_bytes:
                raise PolicyViolation("literal exceeds size limit")
            if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and len(node.elts) > self.max_literal_items:
                raise PolicyViolation("literal exceeds item limit")
            if isinstance(node, ast.Dict) and len(node.keys) > self.max_literal_items:
                raise PolicyViolation("literal exceeds item limit")
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Pow) and isinstance(node.right, ast.Constant):
                if not isinstance(node.right.value, (int, float)) or abs(node.right.value) > 10_000:
                    raise PolicyViolation("power exponent exceeds limit")
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
                constants = [part.value for part in (node.left, node.right) if isinstance(part, ast.Constant)]
                if any(isinstance(value, int) and value > self.max_literal_items for value in constants):
                    raise PolicyViolation("static repetition exceeds item limit")
        return tree
