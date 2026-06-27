"""Smoke test for the non-live Course Compiler Demo MVP."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "tools/course_compiler_demo/expected_final_demo_outputs.json"
INPUT_PATH = REPO_ROOT / "tools/course_compiler_demo/sample_inputs/math_demo_input.txt"
OUTPUT_DIR = REPO_ROOT / "reports/course_compiler_demo/smoke_test_run"
COMPILER_PATH = REPO_ROOT / "tools/course_compiler_demo/run_course_compiler_demo.py"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise AssertionError(f"{path.name} must contain a JSON object")
    return payload


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def fail(message: str) -> None:
    print("Smoke test result: fail")
    print(f"Reason: {message}")
    raise SystemExit(1)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def list_status(paths: list[str]) -> str:
    command = ["git", "status", "--short", "--untracked-files=all", *paths]
    result = run_command(command)
    if result.returncode != 0:
        raise AssertionError(result.stderr.strip() or "git status failed")
    return result.stdout.strip()


def assert_top_level_status(payloads: dict[str, dict[str, Any]], required_status: str) -> None:
    for filename, payload in payloads.items():
        if filename.endswith(".json") and "status" in payload:
            require(
                payload["status"] == required_status,
                f"{filename} status must be {required_status}",
            )


def assert_forbidden_claims(output_dir: Path, forbidden_claims: list[str]) -> None:
    searchable_files = [
        path for path in output_dir.iterdir() if path.suffix in {".json", ".md"}
    ]
    for path in searchable_files:
        content = path.read_text(encoding="utf-8")
        for claim in forbidden_claims:
            require(claim not in content, f"forbidden claim {claim!r} found in {path.name}")


def main() -> int:
    try:
        manifest = load_json(MANIFEST_PATH)
        before_forbidden_status = list_status(["backend/app", "frontend/src"])
        require(before_forbidden_status == "", "backend/app or frontend/src dirty before smoke test")

        if OUTPUT_DIR.exists():
            shutil.rmtree(OUTPUT_DIR)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        result = run_command(
            [
                sys.executable,
                str(COMPILER_PATH.relative_to(REPO_ROOT)),
                "--input",
                str(INPUT_PATH.relative_to(REPO_ROOT)),
                "--subject",
                "MATHEMATICS",
                "--mode",
                "student_practice",
                "--output",
                str(OUTPUT_DIR.relative_to(REPO_ROOT)),
            ]
        )
        if result.returncode != 0:
            details = result.stderr.strip() or result.stdout.strip()
            fail(f"compiler command failed: {details}")

        required_files = manifest["required_output_files"]
        missing = [filename for filename in required_files if not (OUTPUT_DIR / filename).is_file()]
        require(not missing, f"missing required output files: {missing}")

        json_payloads = {
            path.name: load_json(path)
            for path in OUTPUT_DIR.iterdir()
            if path.suffix == ".json"
        }
        assert_top_level_status(json_payloads, manifest["required_top_level_status"])

        extraction = json_payloads["curriculum_extraction_package.json"]
        practice = json_payloads["practice_module_package.json"]
        assessment = json_payloads["practice_assessment_package.json"]
        performance = json_payloads["performance_tracking_package.json"]
        validation = json_payloads["validation_report.json"]
        gaps = json_payloads["content_gaps.json"]

        topic_count = len(extraction.get("topic_candidates", []))
        micro_skill_count = len(extraction.get("micro_skill_candidates", []))
        practice_item_count = len(practice.get("practice_sequence", []))
        assessment_item_count = len(assessment.get("assessment_items", []))
        gap_count = len(gaps.get("content_gaps", []))

        minimum_counts = manifest["minimum_counts"]
        require(topic_count >= minimum_counts["topic_count"], "topic count below expected minimum")
        require(
            micro_skill_count >= minimum_counts["micro_skill_count"],
            "micro-skill count below expected minimum",
        )
        require(
            practice_item_count >= minimum_counts["practice_item_count"],
            "practice item count below expected minimum",
        )
        require(
            assessment_item_count >= minimum_counts["assessment_item_count"],
            "assessment item count below expected minimum",
        )
        require(performance, "performance tracking package must parse as a non-empty object")

        validation_result = validation.get("overall_result")
        require(
            validation_result in manifest["accepted_validation_results"],
            "validation_report.json overall_result is not accepted",
        )

        for report_name, markers in manifest["required_report_text_markers"].items():
            content = (OUTPUT_DIR / report_name).read_text(encoding="utf-8")
            for marker in markers:
                require(marker in content, f"{report_name} missing marker {marker!r}")

        demo_report = (OUTPUT_DIR / "demo_report.md").read_text(encoding="utf-8")
        boundary_text = demo_report.lower()
        for marker in manifest["required_non_live_boundary_markers"]:
            require(
                marker.lower() in boundary_text,
                f"demo_report.md missing non-live boundary marker {marker!r}",
            )

        assert_forbidden_claims(OUTPUT_DIR, manifest["forbidden_generated_files_or_claims"])

        after_forbidden_status = list_status(["backend/app", "frontend/src"])
        require(after_forbidden_status == "", "backend/app or frontend/src dirty after smoke test")

    except AssertionError as exc:
        fail(str(exc))

    print("Smoke test result: pass")
    print(f"Output folder: {OUTPUT_DIR.relative_to(REPO_ROOT)}")
    print(f"Validation result: {validation_result}")
    print(f"Topic count: {topic_count}")
    print(f"Micro-skill count: {micro_skill_count}")
    print(f"Practice item count: {practice_item_count}")
    print(f"Assessment item count: {assessment_item_count}")
    print(f"Gap count: {gap_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
