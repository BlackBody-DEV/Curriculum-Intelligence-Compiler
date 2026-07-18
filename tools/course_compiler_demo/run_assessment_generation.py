#!/usr/bin/env python3
"""Run deterministic non-live assessment generation from a fixed family contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from assessment_generation.blueprint import load_blueprint
from assessment_generation.family_loader import load_family
from assessment_generation.generator import generate_assessment
from assessment_generation.storage import load_historical_fingerprints, write_assessment_run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--family", required=True, type=Path)
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--history-root", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    family = load_family(args.family)
    blueprint = load_blueprint(args.blueprint)
    historical = load_historical_fingerprints(args.history_root)
    assessment, duplicate_report, review_decisions = generate_assessment(
        family=family,
        blueprint=blueprint,
        historical_fingerprints=historical,
    )
    if duplicate_report["generated_count"] != duplicate_report["requested_count"]:
        print("ASSESSMENT_GENERATION_INCOMPLETE")
        print(f"requested_count={duplicate_report['requested_count']}")
        print(f"generated_count={duplicate_report['generated_count']}")
        return 2
    write_assessment_run(
        output_dir=args.output,
        blueprint=blueprint,
        family=family,
        assessment=assessment,
        duplicate_report=duplicate_report,
        review_decisions=review_decisions,
    )
    print("ASSESSMENT_GENERATION_VALID")
    print(f"assessment_id={assessment['assessment_id']}")
    print(f"generated_count={duplicate_report['generated_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
