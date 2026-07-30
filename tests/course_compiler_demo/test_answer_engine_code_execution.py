import json

import pytest

from tools.course_compiler_demo.answer_engines.code_execution import CodeExecutionPythonEngine, ExecutionPolicy
from tools.course_compiler_demo.universal_core import AnswerContractV1


def contract(cases=None):
    return AnswerContractV1("contract:bounded-python", "code_execution_python", {"cases": cases or [{"entrypoint": "solve", "args": [2], "expected": 4}]})


VALID = [
    "x = 1", "x = -2", "x = 1 + 2 * 3", "x = 7 // 2", "x = 7 % 2",
    "x = True and False", "x = 2 if True else 3", "x = [1, 2, 3]", "x = (1, 2)", "x = {'a': 1}",
    "x = {1, 2}", "x = [n*n for n in range(4)]", "x = {n for n in range(3)}", "x = {n:n*n for n in range(3)}", "x = sum(n for n in range(4))",
    "if 1 < 2:\n x = 3", "for n in range(3):\n x = n", "n = 0\nwhile n < 3:\n n = n + 1", "for n in range(3):\n if n == 1: break", "for n in range(3):\n if n == 1: continue",
    "def f(x):\n return x + 1", "def f(x=1):\n return x", "def f(a, b):\n return max(a, b)", "def f(xs):\n return len(xs)", "def f(s):\n return str(s)",
    "x = abs(-1)", "x = all([True, True])", "x = any([False, True])", "x = bool(1)", "x = dict()",
    "x = list(range(3))", "x = tuple(range(2))", "x = sorted([2, 1])", "x = list(reversed([1, 2]))", "x = round(1.25, 1)",
    "x = min(1, 2)", "x = max(1, 2)", "x = int('2')", "x = float('2.5')", "x = list(enumerate([3]))",
    "x = list(zip([1], [2]))", "print('ok')", "def f(n):\n if n <= 1: return 1\n return n * f(n-1)", "x = 'abc'[1]", "x = [1,2,3][1:]",
    "x = 2 ** 8", "x = not False", "x = 2 in [1,2]", "pass", "def solve(x):\n return x * x",
]


MALICIOUS = [
    "import os", "from os import path", "open('/tmp/x','w')", "eval('1')", "exec('x=1')",
    "compile('1','','eval')", "__import__('os')", "import sys", "import socket", "import subprocess",
    "import pathlib", "import ctypes", "import multiprocessing", "globals()", "locals()",
    "vars()", "getattr('', 'upper')", "setattr(object(), 'x', 1)", "delattr(object(), 'x')", "input()",
    "help()", "breakpoint()", "type(1)", "object()", "memoryview(b'x')",
    "(1).__class__", "[].append(1)", "lambda: 1", "class X: pass", "try:\n x=1\nexcept: pass",
    "with open('x') as f: pass", "raise ValueError()", "assert True", "yield 1", "async def f(): pass",
    "await f()", "x := 1", "global x", "nonlocal x", "del x",
    "def _hidden(): pass", "_x = 1", "def f(*args): pass", "def f(**kwargs): pass", "@print\ndef f(): pass",
    "x = 2 ** 10001", "x = b'a' * 20000", "match 1:\n case 1: pass", "async for x in y: pass", "x = (lambda: 1)()",
]


@pytest.mark.parametrize("source", VALID)
def test_fifty_valid_programs_are_accepted(source):
    assert CodeExecutionPythonEngine().normalize(source, contract()).status == "PASS"


@pytest.mark.parametrize("source", MALICIOUS)
def test_fifty_prohibited_programs_fail_closed(source):
    assert CodeExecutionPythonEngine().normalize(source, contract()).status == "INVALID"


def test_unit_test_grading_is_deterministic_and_protocol_compatible():
    engine = CodeExecutionPythonEngine()
    spec = contract([{"entrypoint": "solve", "args": [2], "expected": 4}, {"entrypoint": "solve", "args": [3], "expected": 9}])
    first = engine.grade("def solve(x):\n return x*x", None, spec)
    second = engine.grade("def solve(x):\n return x*x", None, spec)
    assert first.status == "PASS" and first.value == second.value
    assert json.dumps(first.to_dict(), sort_keys=True) == json.dumps(second.to_dict(), sort_keys=True)
    assert first.engine_type == "code_execution_python"


def test_trace_output_and_expression_programs():
    engine = CodeExecutionPythonEngine()
    spec = contract([{"expected_stdout": "0\n1\n2\n"}])
    assert engine.grade("for n in range(3):\n print(n)", None, spec).status == "PASS"


def test_timeout_and_output_limits_are_enforced():
    engine = CodeExecutionPythonEngine(ExecutionPolicy(timeout_seconds=.2, output_bytes=64))
    assert engine.execute("while True:\n pass", {"expected_stdout": ""})["status"] == "LIMIT"
    assert engine.execute("for n in range(100):\n print('abcdefgh')", {"expected_stdout": ""})["status"] != "PASS"


def test_memory_limit_is_enforced():
    engine = CodeExecutionPythonEngine(ExecutionPolicy(timeout_seconds=2, memory_bytes=96 * 1024 * 1024))
    outcome = engine.execute("x = [0] * 50000000", {"expected_stdout": ""})
    assert outcome["status"] == "INVALID" and "limit" in outcome["reason"]


def test_no_host_file_mutation(tmp_path):
    marker = tmp_path / "marker"
    marker.write_text("unchanged")
    engine = CodeExecutionPythonEngine()
    assert engine.normalize(f"open({str(marker)!r}, 'w')", contract()).status == "INVALID"
    assert marker.read_text() == "unchanged"


def test_network_process_reflection_and_imports_rejected_before_execution():
    engine = CodeExecutionPythonEngine()
    attacks = ["socket.socket()", "subprocess.run(['id'])", "().__class__", "__import__('os').system('id')", "import threading"]
    assert all(engine.normalize(source, contract()).status == "INVALID" for source in attacks)


def test_independent_derivation_and_contract_mismatch():
    engine = CodeExecutionPythonEngine()
    result = engine.derive({"independently_derived_answer": "x=1"}, contract())
    assert result.status == "PASS" and result.operation == "derive"
    wrong = AnswerContractV1("wrong", "numeric_scalar", {})
    assert engine.normalize("x=1", wrong).status == "INVALID"


@pytest.mark.parametrize("case", [
    {}, {"expected": None}, {"args": [1], "expected_stdout": ""},
    {"entrypoint": "solve", "args": {"not": "a list"}, "expected": 1},
    {"entrypoint": "_hidden", "expected": 1},
    {"expected_stdout": 1},
    {"entrypoint": "solve", "args": [{1, 2}], "expected": 1},
    {"entrypoint": "solve", "args": [[[[[[[[[[[[[1]]]]]]]]]]]]], "expected": 1},
])
def test_malformed_cases_fail_closed_without_host_exceptions(case):
    result = CodeExecutionPythonEngine().grade("def solve(x=None):\n return x", None, contract([case]))
    assert result.status == "INVALID"


@pytest.mark.parametrize(("source", "expected"), [
    ("def solve():\n return True", 1),
    ("def solve():\n return [True]", [1]),
    ("def solve():\n return {'x': True}", {"x": 1}),
])
def test_json_comparison_is_recursively_type_strict(source, expected):
    result = CodeExecutionPythonEngine().grade(source, None, contract([{"entrypoint": "solve", "expected": expected}]))
    assert result.status == "FAIL"
