"""CLI for emitting a deterministic compiler-side release package."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.course_compiler_demo.package.release_package_emitter import (
    ReleasePackageEmitterError,
    emit_release_package,
    load_json,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit a non-live compiler release package.")
    parser.add_argument("--input", required=True, help="Input seed or normalized compiler package JSON.")
    parser.add_argument("--package-id", required=True, help="Explicit release package ID.")
    parser.add_argument("--output", required=True, help="Output directory for the four generated files.")
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        return 2

    try:
        payload = load_json(input_path)
        result = emit_release_package(
            source_payload=payload,
            output_dir=Path(args.output),
            package_id=args.package_id,
        )
    except ReleasePackageEmitterError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("DOCS_COMPILER_RELEASE_PACKAGE_EMITTED")
    print(f"validation_status: {result.validation_status}")
    print(f"semantic_digest: {result.semantic_digest}")
    print(f"release_package: {result.package_path}")
    print(f"manifest: {result.manifest_path}")
    print(f"report: {result.report_path}")
    print(f"validation: {result.validation_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
