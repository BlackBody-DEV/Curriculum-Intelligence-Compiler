"""CLI for compiler-side subject-profile ingestion proof runs."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.course_compiler_demo.profiles.subject_profile_loader import (
    ProfileValidationError,
    SubjectProfileRunError,
    build_profile_run,
    load_profile,
    safe_output_dir,
    write_profile_run,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a compiler-side subject ingestion profile.")
    parser.add_argument("--profile", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--selected-micro-skill", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    try:
        profile_path = Path(args.profile)
        input_path = Path(args.input)
        output_dir = safe_output_dir(args.output)
        if not input_path.is_file():
            raise SubjectProfileRunError(f"input not found: {input_path}")
        profile = load_profile(profile_path)
        text = input_path.read_text(encoding="utf-8")
        result = build_profile_run(
            profile=profile,
            source_text=text,
            source_path=input_path,
            selected_micro_skill=args.selected_micro_skill,
        )
        if output_dir.exists():
            shutil.rmtree(output_dir)
        write_profile_run(result, output_dir)
    except (ProfileValidationError, SubjectProfileRunError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("SUBJECT_PROFILE_INGESTION_COMPLETE")
    print(f"profile_id: {profile['profile_id']}")
    print(f"selected_micro_skill_code: {args.selected_micro_skill}")
    print(f"semantic_seed_digest: {result.semantic_digest}")
    print(f"output: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
