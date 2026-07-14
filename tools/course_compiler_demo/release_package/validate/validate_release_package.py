"""CLI for semantic validation of portable compiler release packages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.course_compiler_demo.release_package.validate.models import VALIDATOR_NAME
from tools.course_compiler_demo.release_package.validate.package_validator import (
    COMPILER_ROOT,
    FROZEN_FIXTURE_ROOT,
    validate_package,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a portable compiler release package.")
    parser.add_argument("--package", required=True, help="Package root containing manifest.json")
    parser.add_argument("--output", help="Compiler-owned output directory for validation reports")
    parser.add_argument("--no-write", action="store_true", help="Print JSON result and write no files")
    return parser.parse_args()


def safe_output_dir(output: str | None, package_root: Path) -> Path | None:
    if output is None:
        return None
    raw = Path(output)
    if any(part == ".." for part in raw.parts):
        raise ValueError("Output path must not contain parent traversal.")
    resolved = raw.resolve()
    compiler_root = COMPILER_ROOT.resolve()
    try:
        resolved.relative_to(compiler_root)
    except ValueError as exc:
        raise ValueError("Output path must stay inside the compiler repository.") from exc
    if "adaptive-platform" in resolved.as_posix():
        raise ValueError("Output path must not resolve under adaptive-platform.")
    package_resolved = package_root.resolve()
    try:
        resolved.relative_to(package_resolved)
        raise ValueError("Output path must not overlap the package being validated.")
    except ValueError as exc:
        if "must not overlap" in str(exc):
            raise
    try:
        resolved.relative_to(FROZEN_FIXTURE_ROOT.resolve())
        raise ValueError("Output path must not overlap frozen fixture paths.")
    except ValueError as exc:
        if "must not overlap" in str(exc):
            raise
    return resolved


def write_reports(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "validation_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    lines = [
        f"# {VALIDATOR_NAME} Report",
        "",
        f"- package_id: {result.get('package_id')}",
        f"- verdict: {result.get('overall_verdict')}",
        f"- errors: {len(result.get('errors', []))}",
        f"- warnings: {len(result.get('warnings', []))}",
        "",
    ]
    if result.get("overall_verdict") == "reject":
        lines.append("This report may describe fixture-only rejection evidence.")
        lines.append("")
    if result.get("errors"):
        lines.extend(["## Errors", ""])
        for issue in result["errors"]:
            lines.append(f"- {issue['rule_id']}: {issue['message']} ({issue.get('evidence')})")
        lines.append("")
    if result.get("warnings"):
        lines.extend(["## Warnings", ""])
        for issue in result["warnings"]:
            lines.append(f"- {issue['rule_id']}: {issue['message']} ({issue.get('evidence')})")
        lines.append("")
    (output_dir / "validation_report.md").write_text("\n".join(lines))


def main() -> int:
    args = parse_args()
    package_root = Path(args.package)
    if args.no_write:
        result = validate_package(package_root)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["overall_verdict"] in {"accept", "accept_with_warnings"} else 1

    try:
        output_dir = safe_output_dir(args.output, package_root)
    except ValueError as exc:
        result = {
            "validator_name": VALIDATOR_NAME,
            "overall_verdict": "validator_error",
            "errors": [
                {
                    "rule_id": "OUTPUT_PATH",
                    "severity": "error",
                    "message": str(exc),
                    "artifact_id": "package",
                    "field": "output",
                    "path": "output",
                    "evidence": args.output,
                    "recommended_action": "Choose a compiler-owned output path outside packages and fixtures.",
                }
            ],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2

    result = validate_package(package_root)
    if output_dir is None:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["overall_verdict"] in {"accept", "accept_with_warnings"} else 1

    write_reports(result, output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["overall_verdict"] in {"accept", "accept_with_warnings"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
