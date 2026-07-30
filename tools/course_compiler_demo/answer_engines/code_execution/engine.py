"""Bounded, deterministic Python execution and grading adapter."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import json
import math
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
from typing import Any, Mapping

from tools.course_compiler_demo.answer_engines.registry import AnswerEngineResult
from tools.course_compiler_demo.universal_core import AnswerContractV1
from .policy import AstPolicy, PolicyViolation


@dataclass(frozen=True)
class ExecutionPolicy:
    timeout_seconds: float = 1.0
    memory_bytes: int = 128 * 1024 * 1024
    output_bytes: int = 16 * 1024
    process_limit: int = 1
    file_bytes: int = 0


def _limit_process(policy: ExecutionPolicy) -> None:
    # Some kernels expose but do not implement every POSIX resource. Apply all
    # supported limits; the AST boundary and parent limits remain mandatory.
    for key, value in (
        (resource.RLIMIT_CPU, 1), (resource.RLIMIT_AS, policy.memory_bytes),
        (resource.RLIMIT_DATA, policy.memory_bytes),
        (resource.RLIMIT_FSIZE, policy.file_bytes),
        (resource.RLIMIT_NPROC, policy.process_limit), (resource.RLIMIT_NOFILE, 8),
    ):
        try:
            resource.setrlimit(key, (value, value))
        except (OSError, ValueError):
            pass


class CodeExecutionPythonEngine:
    engine_type = "code_execution_python"
    engine_id = "bounded-python"
    engine_version = "1.0"

    def __init__(self, policy: ExecutionPolicy | None = None, ast_policy: AstPolicy | None = None):
        self.policy = policy or ExecutionPolicy()
        self.ast_policy = ast_policy or AstPolicy()

    def _failure(self, operation: str, reason: str, status: str = "INVALID") -> AnswerEngineResult:
        return AnswerEngineResult(status, self.engine_type, operation, None, (reason,))

    def _contract(self, contract: AnswerContractV1, operation: str) -> AnswerEngineResult | None:
        if not isinstance(contract, AnswerContractV1) or contract.engine_type != self.engine_type:
            return self._failure(operation, "answer contract does not match engine")
        return None

    @staticmethod
    def _source(answer: Any) -> str:
        return answer.get("source") if isinstance(answer, Mapping) else answer

    def normalize(self, answer: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._contract(contract, "normalize"):
            return invalid
        source = self._source(answer)
        try:
            tree = self.ast_policy.validate(source)
        except PolicyViolation as exc:
            return self._failure("normalize", str(exc))
        normalized = ast.unparse(tree).strip() + "\n"
        return AnswerEngineResult("PASS", self.engine_type, "normalize", {"source": normalized})

    def derive(self, derivation_input: Mapping[str, Any], contract: AnswerContractV1) -> AnswerEngineResult:
        if not isinstance(derivation_input, Mapping) or "independently_derived_answer" not in derivation_input:
            return self._failure("derive", "independently_derived_answer is required")
        result = self.normalize(derivation_input["independently_derived_answer"], contract)
        return AnswerEngineResult(result.status, result.engine_type, "derive", result.value, result.reasons)

    @staticmethod
    def _validate_json(value: Any, *, depth: int = 0, budget: list[int] | None = None) -> None:
        budget = budget if budget is not None else [0]
        budget[0] += 1
        if depth > 12 or budget[0] > 10_000:
            raise ValueError("JSON value exceeds structural limit")
        if value is None or isinstance(value, (str, bool, int)):
            return
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError("JSON numbers must be finite")
            return
        if isinstance(value, list):
            for item in value:
                CodeExecutionPythonEngine._validate_json(item, depth=depth + 1, budget=budget)
            return
        if isinstance(value, dict) and all(isinstance(key, str) for key in value):
            for item in value.values():
                CodeExecutionPythonEngine._validate_json(item, depth=depth + 1, budget=budget)
            return
        raise ValueError("values must use strict JSON-compatible types")

    @staticmethod
    def _strict_equal(actual: Any, expected: Any) -> bool:
        # JSON serialization preserves distinctions Python equality erases
        # (notably true versus 1) and provides deterministic deep comparison.
        try:
            left = json.dumps(actual, sort_keys=True, separators=(",", ":"), allow_nan=False)
            right = json.dumps(expected, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError):
            return False
        return left == right

    def _validate_case(self, case: Any) -> None:
        if not isinstance(case, Mapping) or set(case) - {"entrypoint", "args", "expected", "expected_stdout"}:
            raise ValueError("test case has unsupported fields")
        if "expected" not in case and "expected_stdout" not in case:
            raise ValueError("test case requires expected or expected_stdout oracle")
        entrypoint = case.get("entrypoint")
        if "expected" in case and (not isinstance(entrypoint, str) or not entrypoint.isidentifier() or entrypoint.startswith("_")):
            raise ValueError("return-value tests require a public entrypoint")
        if "args" in case and (entrypoint is None or not isinstance(case["args"], list)):
            raise ValueError("args require an entrypoint and must be a list")
        if entrypoint is not None and (not isinstance(entrypoint, str) or not entrypoint.isidentifier() or entrypoint.startswith("_")):
            raise ValueError("entrypoint must be a public identifier")
        if "expected_stdout" in case and not isinstance(case["expected_stdout"], str):
            raise ValueError("expected_stdout must be a string")
        self._validate_json(case.get("args", []))
        if "expected" in case:
            self._validate_json(case["expected"])

    def execute(self, source: str, case: Mapping[str, Any]) -> dict[str, Any]:
        try:
            self.ast_policy.validate(source)
            self._validate_case(case)
            payload = json.dumps({"source": source, "entrypoint": case.get("entrypoint"), "args": case.get("args", []), "output_limit": self.policy.output_bytes}, sort_keys=True, separators=(",", ":"), allow_nan=False)
            if len(payload.encode("utf-8")) > 64 * 1024:
                raise ValueError("execution payload exceeds byte limit")
        except (PolicyViolation, TypeError, ValueError) as exc:
            return {"status": "INVALID", "reason": str(exc)}
        worker = str(Path(__file__).with_name("worker.py"))
        with tempfile.TemporaryDirectory(prefix="axiomiq-python-") as directory:
            try:
                completed = subprocess.run(
                    [sys.executable, "-I", "-S", worker], input=payload, text=True,
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, cwd=directory,
                    env={"PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1"},
                    timeout=self.policy.timeout_seconds, check=False,
                    preexec_fn=lambda: _limit_process(self.policy),
                )
            except subprocess.TimeoutExpired:
                return {"status": "LIMIT", "reason": "execution timeout"}
            if len(completed.stdout.encode("utf-8")) > self.policy.output_bytes + 1024:
                return {"status": "LIMIT", "reason": "output limit exceeded"}
            try:
                return json.loads(completed.stdout)
            except (json.JSONDecodeError, UnicodeError):
                return {"status": "LIMIT" if completed.returncode < 0 else "RUNTIME_ERROR", "reason": "worker terminated without a valid report"}

    def grade(self, response: Any, expected: Any, contract: AnswerContractV1) -> AnswerEngineResult:
        if invalid := self._contract(contract, "grade"):
            return invalid
        normalized = self.normalize(response, contract)
        if normalized.status != "PASS":
            return self._failure("grade", normalized.reasons[0])
        cases = contract.grading_contract.get("cases")
        if not isinstance(cases, list) or not cases or len(cases) > 100:
            return self._failure("grade", "one to 100 deterministic test cases are required")
        reports = []
        for index, case in enumerate(cases):
            try:
                self._validate_case(case)
            except ValueError as exc:
                return self._failure("grade", str(exc))
            outcome = self.execute(normalized.value["source"], case)
            passed = outcome.get("status") == "PASS"
            if "expected" in case:
                passed = passed and self._strict_equal(outcome.get("return_value"), case["expected"])
            if "expected_stdout" in case:
                passed = passed and outcome.get("stdout") == case["expected_stdout"]
            reports.append({"case": index, "passed": passed, "status": outcome.get("status", "RUNTIME_ERROR")})
        passed = all(item["passed"] for item in reports)
        value = {"passed": passed, "passed_count": sum(item["passed"] for item in reports), "total_count": len(reports), "cases": reports}
        return AnswerEngineResult("PASS" if passed else "FAIL", self.engine_type, "grade", value)
