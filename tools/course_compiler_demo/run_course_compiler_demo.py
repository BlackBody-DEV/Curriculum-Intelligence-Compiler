"""Minimal CLI placeholder for the non-live Course Compiler Demo."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AxiomIQ Course Compiler Demo placeholder CLI."
    )
    parser.add_argument(
        "--version",
        action="version",
        version="course-compiler-demo 0.0.0-demo",
    )
    return parser


def main() -> int:
    build_parser().parse_args()
    print(
        "Course Compiler Demo skeleton only. "
        "No pipeline execution or output generation is implemented yet."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
