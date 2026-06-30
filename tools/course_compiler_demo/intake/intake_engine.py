"""CLI for the non-live Curriculum Intake Engine v0.1."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from acef_mapper import write_acef_scaffolds
from artifact_router import (
    archive_original,
    ensure_folder_model,
    supported_input_files,
    unsupported_input_files,
    verify_required_outputs,
)
from intake_registry import (
    build_intake_record,
    load_json,
    make_intake_id,
    timestamp_utc,
    write_json,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SUPPORTED_SUFFIXES = {".txt", ".md"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Non-live Curriculum Intake Engine for Course Compiler Demo sources."
    )
    parser.add_argument("--incoming", default="incoming", help="Folder containing local intake files.")
    parser.add_argument(
        "--original-artifacts",
        default="original_artifacts",
        help="Folder for preserved original artifacts.",
    )
    parser.add_argument(
        "--output-root",
        default="compiler_output",
        help="Root folder for intake run outputs.",
    )
    parser.add_argument("--subject", default="MATHEMATICS", help="Subject override for compiler run.")
    parser.add_argument("--mode", default="student_practice", help="Compiler processing mode.")
    return parser


def _repo_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _relative(path: Path) -> Path:
    try:
        return path.relative_to(REPO_ROOT)
    except ValueError:
        return path


def _run_compiler(*, input_path: Path, output_dir: Path, subject: str, mode: str) -> None:
    command = [
        sys.executable,
        "tools/course_compiler_demo/run_course_compiler_demo.py",
        "--input",
        _relative(input_path).as_posix(),
        "--subject",
        subject,
        "--mode",
        mode,
        "--output",
        _relative(output_dir).as_posix(),
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"Compiler pipeline failed for {input_path.name}: {details}")


def process_file(
    *,
    source_path: Path,
    sequence: int,
    folders: dict[str, Path],
    subject: str,
    mode: str,
) -> dict[str, str]:
    created_at = timestamp_utc()
    intake_id = make_intake_id(created_at=created_at, sequence=sequence)
    run_dir = folders["intake_runs"] / intake_id
    run_dir.mkdir(parents=True, exist_ok=False)

    _run_compiler(input_path=source_path, output_dir=run_dir, subject=subject, mode=mode)
    missing = verify_required_outputs(run_dir)
    if missing:
        raise RuntimeError(f"Compiler run {intake_id} missing required outputs: {missing}")

    original_artifact_path = archive_original(
        source_path=source_path,
        original_artifacts_dir=folders["original_artifacts"],
        intake_id=intake_id,
    )

    source_interpretation = load_json(run_dir / "source_interpretation.json")
    intake_record = build_intake_record(
        intake_id=intake_id,
        original_filename=source_path.name,
        original_artifact_path=_relative(original_artifact_path),
        input_path=_relative(source_path),
        compiler_output_path=_relative(run_dir),
        detected_file_type=source_path.suffix.lower().lstrip("."),
        detected_subject=source_interpretation.get("detected_subject", "UNKNOWN"),
        detected_document_type=source_interpretation.get("detected_source_type", "unknown"),
        processing_mode=mode,
        created_at=created_at,
    )
    write_json(run_dir / "intake_record.json", intake_record)

    write_acef_scaffolds(run_dir=run_dir, staging_dirs=folders, intake_id=intake_id)
    return {
        "intake_id": intake_id,
        "original_artifact_path": _relative(original_artifact_path).as_posix(),
        "compiler_output_path": _relative(run_dir).as_posix(),
    }


def main() -> int:
    args = build_parser().parse_args()
    incoming_dir = _repo_path(args.incoming)
    folders = ensure_folder_model(
        incoming_dir=incoming_dir,
        original_artifacts_dir=_repo_path(args.original_artifacts),
        output_root=_repo_path(args.output_root),
    )

    supported_files = supported_input_files(incoming_dir, SUPPORTED_SUFFIXES)
    unsupported_files = unsupported_input_files(incoming_dir, SUPPORTED_SUFFIXES)

    processed: list[dict[str, str]] = []
    for sequence, source_path in enumerate(supported_files, start=1):
        processed.append(
            process_file(
                source_path=source_path,
                sequence=sequence,
                folders=folders,
                subject=args.subject,
                mode=args.mode,
            )
        )

    print("Curriculum Intake Engine result")
    print(f"processed files: {len(processed)}")
    for item in processed:
        print(
            f"- {item['intake_id']}: {item['compiler_output_path']} "
            f"(original: {item['original_artifact_path']})"
        )
    if unsupported_files:
        print("unsupported files left in incoming:")
        for path in unsupported_files:
            print(f"- {_relative(path).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
