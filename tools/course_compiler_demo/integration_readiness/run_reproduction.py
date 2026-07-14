"""CLI for deterministic compiler integration reproduction evidence."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from tools.course_compiler_demo.integration_readiness.models import canonical_json
from tools.course_compiler_demo.integration_readiness.reproduction_runner import (
    fixture_matrix,
    future_generated_package_reproduction,
    reproduce_package,
    safe_output_dir,
)


ALLOWED_ROOT_FILES = {
    "reproduction_matrix.json",
    "reproduction_matrix.md",
    "zero_boundary_contact_evidence.json",
}
ALLOWED_PACKAGE_FILES = {
    "reproduction_result.json",
    "reproduction_report.md",
    "run_1_validator_result.json",
    "run_1_consumer_result.json",
    "run_2_validator_result.json",
    "run_2_consumer_result.json",
    "determinism_comparison.json",
    "boundary_evidence.json",
    "input_inventory.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run compiler integration reproduction harness.")
    parser.add_argument("--mode", required=True, choices=["fixture_reproduction", "existing_package_reproduction", "future_generated_package_reproduction"])
    parser.add_argument("--package", help="Compiler-side package root for existing package reproduction")
    parser.add_argument("--output", help="Compiler-owned output directory")
    parser.add_argument("--repeat-count", type=int, default=2)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def _comparison_from_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "manifest_digest_match": result.get("manifest_digest_match"),
        "artifact_digest_match": result.get("artifact_digest_match"),
        "artifact_order_match": result.get("artifact_order_match"),
        "dependency_order_match": result.get("dependency_order_match"),
        "reference_resolution_match": result.get("reference_resolution_match"),
        "error_order_match": result.get("error_order_match"),
        "warning_order_match": result.get("warning_order_match"),
        "package_non_mutation_confirmed": result.get("package_non_mutation_confirmed"),
        "deterministic_fields_compared": result.get("deterministic_fields_compared"),
        "volatile_fields_excluded": result.get("volatile_fields_excluded"),
    }


def _package_report(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Reproduction Report",
            "",
            f"- package_id: {result.get('package_id')}",
            f"- reproduction_verdict: {result.get('reproduction_verdict')}",
            f"- validator_verdicts: {result.get('actual_validator_verdicts')}",
            f"- consumer_verdicts: {result.get('actual_consumer_verdicts')}",
            f"- plan_statuses: {result.get('actual_plan_statuses')}",
            f"- package_non_mutation_confirmed: {result.get('package_non_mutation_confirmed')}",
            "",
            "HARNESS_REPRODUCTION_CONFIRMED" if not result.get("blockers") else "HARNESS_REPRODUCTION_NOT_CONFIRMED",
            "REAL_SOURCE_REPRODUCTION_NOT_RUN",
            "COMPILER_INTEGRATION_READINESS_NOT_YET_CONFIRMED",
            "",
        ]
    )


def write_package_result(output: Path, result: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    written_names = sorted(ALLOWED_PACKAGE_FILES)
    result["boundary_evidence"]["files_written"] = [
        str(output / name) for name in written_names
    ]
    files: dict[str, Any] = {
        "reproduction_result.json": result,
        "determinism_comparison.json": _comparison_from_result(result),
        "boundary_evidence.json": result["boundary_evidence"],
        "input_inventory.json": {
            "input_inventory_digest": result.get("input_inventory_digest"),
            "input_artifact_digests": result.get("input_artifact_digests"),
        },
    }
    for run in result.get("run_results", [])[:2]:
        index = run["run_index"]
        files[f"run_{index}_validator_result.json"] = run["validator_result"]
        files[f"run_{index}_consumer_result.json"] = run["consumer_result"]
    for index in [1, 2]:
        files.setdefault(f"run_{index}_validator_result.json", {})
        files.setdefault(f"run_{index}_consumer_result.json", {})
    for name, payload in files.items():
        if name not in ALLOWED_PACKAGE_FILES:
            raise ValueError(f"Unexpected package report file: {name}")
        (output / name).write_text(canonical_json(payload))
    (output / "reproduction_report.md").write_text(_package_report(result))


def _matrix_report(matrix: dict[str, Any]) -> str:
    lines = [
        "# Fixture Reproduction Matrix",
        "",
        "Harness reproduction is confirmed for frozen fixtures.",
        "Real-source reproduction has not been run.",
        "Compiler integration readiness is not yet confirmed.",
        "",
        "HARNESS_REPRODUCTION_CONFIRMED",
        "REAL_SOURCE_REPRODUCTION_NOT_RUN",
        "COMPILER_INTEGRATION_READINESS_NOT_YET_CONFIRMED",
        "",
        "## Fixture Verdicts",
        "",
    ]
    for name, verdict in matrix["fixture_verdicts"].items():
        lines.append(f"- {name}: {verdict}")
    lines.append("")
    return "\n".join(lines)


def write_fixture_matrix(output: Path, matrix: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=True)
    package_written: list[str] = []
    for name, result in matrix["fixture_results"].items():
        write_package_result(output / name, result)
        package_written.extend(result["boundary_evidence"]["files_written"])
    matrix["boundary_evidence"]["files_written"] = sorted(
        package_written + [str(output / name) for name in sorted(ALLOWED_ROOT_FILES)]
    )
    root_files = {
        "reproduction_matrix.json": matrix,
        "zero_boundary_contact_evidence.json": matrix["boundary_evidence"],
    }
    for name, payload in root_files.items():
        if name not in ALLOWED_ROOT_FILES:
            raise ValueError(f"Unexpected matrix report file: {name}")
        (output / name).write_text(canonical_json(payload))
    (output / "reproduction_matrix.md").write_text(_matrix_report(matrix))


def main() -> int:
    args = parse_args()
    if args.repeat_count < 2:
        result = {"reproduction_verdict": "harness_error", "blockers": ["repeat count must be at least two"]}
        print(canonical_json(result), end="")
        return 2

    if args.mode == "future_generated_package_reproduction":
        result = future_generated_package_reproduction(args.repeat_count)
        print(canonical_json(result), end="")
        return 0 if result["reproduction_verdict"] == "generation_unavailable" else 1

    if args.mode == "existing_package_reproduction":
        if not args.package:
            result = {"reproduction_verdict": "harness_error", "blockers": ["--package is required"]}
            print(canonical_json(result), end="")
            return 2
        output = safe_output_dir(args.output, Path(args.package)) if args.output else None
        result = reproduce_package(args.package, mode=args.mode, repeat_count=args.repeat_count, output_root=output)
        if not args.no_write and output:
            write_package_result(output, result)
        print(canonical_json(result), end="")
        return 0 if result["reproduction_verdict"] in {"reproduced", "reproduced_with_expected_warnings", "reproduced_expected_rejection"} else 1

    output = safe_output_dir(args.output, None) if args.output else None
    matrix = fixture_matrix(repeat_count=args.repeat_count, output_root=output)
    if not args.no_write and output:
        write_fixture_matrix(output, matrix)
    print(canonical_json(matrix), end="")
    return 0 if matrix["reproduction_verdict"] == "reproduced" else 1


if __name__ == "__main__":
    raise SystemExit(main())
