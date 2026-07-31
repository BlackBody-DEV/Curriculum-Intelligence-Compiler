"""Deterministic validation for the compiler milestone 093 release checkpoint.

This module is release tooling only.  It reads repository-local compiler
contracts and produces no canonical, database, Beta, or student-visible writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from tools.course_compiler_demo.answer_engines.registry import ENABLED_ENGINE_TYPES
from tools.course_compiler_demo.canonical_projection import projection_mode
from tools.course_compiler_demo.generation_recipes.domains.math_engineering import (
    COURSE_RECIPE_REGISTRY,
)
from tools.course_compiler_demo.generation_recipes.domains.science_cs import RECIPES
from tools.course_compiler_demo.production_wave_032 import build_production_wave
from tools.course_compiler_demo.source_corpus.pipeline import compile_reference_course_corpora
from tools.course_compiler_demo.universal_integration.capability_catalog_wave_044 import (
    compile_cross_catalog_pilots,
    compile_diagnostics,
    discover_course_catalog,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path("docs/course_compiler_demo/releases/compiler_milestone_093_v1.json")
REPORT_PATH = Path("docs/course_compiler_demo/releases/COMPILER_MILESTONE_093_CHECKPOINT.md")
AUTHORIZED_BASELINE = "9443075a28254ae918e263ab84b69f36d2ed4e1d"
AUTHORIZED_TREE = "a4596fa1d33caaa59554da881d81ac547b9d9157"
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_CI_RUNS = (
    {
        "run_id": 30657885246,
        "event": "push",
        "branch": "validation/compiler-continuous-clean-room-092",
        "head_sha": AUTHORIZED_BASELINE,
        "conclusion": "success",
        "repository_checkout_suite": "PASS",
        "gitless_archive_suite": "PASS",
        "temporary_storage_preflight": "PASS",
    },
    {
        "run_id": 30659592823,
        "event": "push",
        "branch": "main",
        "head_sha": AUTHORIZED_BASELINE,
        "conclusion": "success",
        "repository_checkout_suite": "PASS",
        "gitless_archive_suite": "PASS",
        "temporary_storage_preflight": "PASS",
    },
)
EXPECTED_AUDITS = (
    {
        "audit_id": "UNIVERSAL_CURRICULUM_COMPILER_TOPIC_PROCEDURE_GENERATION_REPORT",
        "scope": "Wave 056 generation, diagnostics, Beta export, and protected boundaries",
        "validated_tip": "8b52306824177686d4f672f08b13ee485d2d0967",
        "verdict": "PASS",
    },
    {
        "audit_id": "UNIVERSAL_SOURCE_CORPUS_WAVE_066_COMPLETION_REPORT",
        "scope": "Wave 066 history, six-course proof, semantic preservation, and protected boundaries",
        "validated_tip": "b743fd26bd15007b942e1587cdfb94901e5bd739",
        "verdict": "PASS",
    },
    {
        "audit_id": "CANONICAL_EXECUTION_AND_BETA_PROJECTION_WAVE_048_COMPLETION_REPORT",
        "scope": "non-live projection planning, lineage, rollback, and safety boundaries",
        "validated_tip": "59e3eb5275425cd7e31b17d2ce8afe7d83ca7420",
        "verdict": "PASS",
    },
    {
        "audit_id": "COMPILER_CONTINUOUS_CLEAN_ROOM_CERTIFICATION_REPORT",
        "scope": "CI semantics, Git-less portability, storage controls, and no test weakening",
        "validated_tip": AUTHORIZED_BASELINE,
        "verdict": "PASS",
    },
)


class MilestoneValidationError(ValueError):
    """The milestone evidence does not match the repository state."""


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _recipe_inventory() -> list[dict[str, Any]]:
    math_recipes = [recipe for values in COURSE_RECIPE_REGISTRY.values() for recipe in values]
    rows = []
    for recipe in (*math_recipes, *RECIPES):
        rows.append(
            {
                "recipe_id": recipe.recipe_id,
                "version": recipe.version,
                "binding": dict(recipe.binding.__dict__),
            }
        )
    return sorted(rows, key=lambda row: row["recipe_id"])


def collect_repository_evidence(root: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    """Recompute the milestone's repository-backed counts and hashes."""
    root = Path(root)
    catalog = discover_course_catalog()
    if catalog["missing_new_courses"]:
        raise MilestoneValidationError("course catalog is incomplete")

    engines = sorted(ENABLED_ENGINE_TYPES)
    recipes = _recipe_inventory()

    legacy = build_production_wave()
    legacy_banks = sorted(
        (
            {
                "course_id": report["course_id"],
                "question_count": report["validated"],
                "sha256": report["bank_sha256"],
            }
            for report in legacy["courses"].values()
        ),
        key=lambda row: row["course_id"],
    )

    pilots = compile_cross_catalog_pilots()
    if pilots["status"] != "PASS":
        raise MilestoneValidationError("Wave 056 pilot proof did not pass")
    wave_056_banks = sorted(
        (
            {
                "course_id": course["course_id"],
                "question_count": course["validated"],
                "sha256": canonical_sha256(course["questions"]),
            }
            for course in pilots["courses"]
        ),
        key=lambda row: row["course_id"],
    )
    diagnostics = compile_diagnostics(pilots)
    source_corpus = compile_reference_course_corpora()
    source_summary = source_corpus["summary"]

    legacy_count = sum(row["question_count"] for row in legacy_banks)
    wave_056_count = sum(row["question_count"] for row in wave_056_banks)
    legacy_hash = canonical_sha256(legacy_banks)
    wave_056_hash = canonical_sha256(wave_056_banks)

    return {
        "capabilities": {
            "course_packs": {
                "count": len(catalog["total"]),
                "identifiers_sha256": canonical_sha256(sorted(catalog["total"])),
                "content_sha256": canonical_sha256(catalog["total"]),
            },
            "enabled_answer_capabilities": {
                "count": len(engines),
                "identifiers": engines,
                "identifiers_sha256": canonical_sha256(engines),
            },
            "generation_recipes": {
                "count": len(recipes),
                "inventory_sha256": canonical_sha256(recipes),
            },
            "validated_questions": {
                "legacy_production_wave": legacy_count,
                "wave_056": wave_056_count,
                "total": legacy_count + wave_056_count,
            },
            "diagnostic_assessments": diagnostics["assessment_count"],
        },
        "production_banks": {
            "legacy_production_wave": {
                "course_count": len(legacy_banks),
                "question_count": legacy_count,
                "aggregate_sha256": legacy_hash,
                "banks": legacy_banks,
            },
            "wave_056": {
                "course_count": len(wave_056_banks),
                "question_count": wave_056_count,
                "aggregate_sha256": wave_056_hash,
                "banks": wave_056_banks,
            },
            "combined": {
                "course_count": len(legacy_banks) + len(wave_056_banks),
                "question_count": legacy_count + wave_056_count,
                "aggregate_sha256": canonical_sha256(
                    {"legacy_production_wave": legacy_hash, "wave_056": wave_056_hash}
                ),
            },
        },
        "source_corpus_wave_066": {
            "reference_courses": source_summary["reference_courses"],
            "source_documents": source_summary["source_documents_processed"],
            "source_segments": source_summary["source_segments_processed"],
            "curriculum_synthesis_packages": source_summary["curriculum_synthesis_packages"],
            "generation_manifests": source_summary["generation_manifests"],
            "generation_question_target": source_summary["generation_question_target"],
            "assessment_blueprints": source_summary["assessment_blueprints"],
            "assessment_compiler_blueprints": source_summary["assessment_compiler_blueprints"],
            "deterministic_sha256": source_corpus["deterministic_sha256"],
            "canonical_authority": source_summary["canonical_authority"],
        },
        "canonical_execution_beta_projection_wave_048": {
            "mode": "NON_LIVE_DATABASE_NEUTRAL",
            "status": "VALIDATED_PLANNING_ONLY",
            "safety": projection_mode()["status_labels"],
            "planner_sha256": sha256_file(
                root / "tools/course_compiler_demo/canonical_projection/planner.py"
            ),
            "specification_sha256": sha256_file(
                root / "docs/CANONICAL_EXECUTION_BETA_PROJECTION_SPEC_v1.md"
            ),
            "execution_map_sha256": sha256_file(
                root / "reports/course_compiler_demo/canonical_projection/wave_048_execution_map.json"
            ),
        },
        "portable_validation": {
            "requirements_lock_sha256": sha256_file(root / "requirements.lock"),
            "workflow_path": ".github/workflows/compiler-continuous-clean-room.yml",
            "workflow_sha256": sha256_file(
                root / ".github/workflows/compiler-continuous-clean-room.yml"
            ),
            "suite_command": "python -m pytest -p no:cacheprovider tests/course_compiler_demo",
            "repository_checkout_gate": True,
            "gitless_archive_gate": True,
            "temporary_storage_preflight": True,
        },
    }


def load_manifest(root: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    return json.loads((Path(root) / MANIFEST_PATH).read_text(encoding="utf-8"))


def validate_manifest(manifest: Mapping[str, Any], root: Path = REPOSITORY_ROOT) -> None:
    if manifest.get("schema_version") != "1.0.0":
        raise MilestoneValidationError("unsupported milestone schema version")
    snapshot = manifest.get("compiler_snapshot", {})
    if snapshot.get("commit") != AUTHORIZED_BASELINE or not SHA1.fullmatch(str(snapshot.get("commit", ""))):
        raise MilestoneValidationError("compiler snapshot commit is not the authorized baseline")
    if snapshot.get("tracked_tree_sha1") != AUTHORIZED_TREE or not SHA1.fullmatch(
        str(snapshot.get("tracked_tree_sha1", ""))
    ):
        raise MilestoneValidationError("compiler tracked-tree hash is invalid")

    actual = collect_repository_evidence(root)
    for section in actual:
        if manifest.get(section) != actual[section]:
            raise MilestoneValidationError(f"manifest section drift: {section}")

    declared = manifest["capabilities"]["enabled_answer_capabilities"]["identifiers"]
    if declared != sorted(ENABLED_ENGINE_TYPES):
        raise MilestoneValidationError("unsupported or missing answer capability identifier")

    protected = manifest.get("protected_state", {})
    required_false = {
        "canonical_promotion_authorized",
        "canonical_writes",
        "database_access",
        "database_writes",
        "adaptive_platform_modified",
        "protected_phase_e_modified",
        "student_visible",
        "live_beta_import",
        "performance_tracking_implemented",
    }
    if set(protected) != required_false or any(protected.values()):
        raise MilestoneValidationError("protected-state declarations must be complete and false")

    ci = manifest.get("ci_evidence", {})
    if ci.get("workflow_path") != actual["portable_validation"]["workflow_path"]:
        raise MilestoneValidationError("CI workflow reference drift")
    if ci.get("workflow_sha256") != actual["portable_validation"]["workflow_sha256"]:
        raise MilestoneValidationError("CI workflow hash drift")
    runs = ci.get("successful_runs", [])
    if runs != list(EXPECTED_CI_RUNS):
        raise MilestoneValidationError("successful CI evidence is incomplete")
    if any(not SHA1.fullmatch(str(run["head_sha"])) for run in runs):
        raise MilestoneValidationError("CI head commit is malformed")

    audits = manifest.get("independent_audit_references", [])
    if audits != list(EXPECTED_AUDITS) or any(
        not SHA1.fullmatch(str(audit.get("validated_tip", ""))) for audit in audits
    ):
        raise MilestoneValidationError("independent audit references are incomplete or malformed")

    release = manifest.get("release_candidate", {})
    if release.get("proposed_annotated_tag") != "compiler-milestone-093-v1":
        raise MilestoneValidationError("release tag candidate drift")
    if release.get("tag_created") is not False or release.get("tag_pushed") is not False:
        raise MilestoneValidationError("release tag must remain uncreated")
    if not manifest.get("intentionally_deferred_scope"):
        raise MilestoneValidationError("intentionally deferred scope is missing")
    if not manifest.get("known_non_blocking_maintenance_gaps"):
        raise MilestoneValidationError("known maintenance gaps are missing")


def render_checkpoint_report(manifest: Mapping[str, Any]) -> str:
    capabilities = manifest["capabilities"]
    banks = manifest["production_banks"]
    source = manifest["source_corpus_wave_066"]
    wave_048 = manifest["canonical_execution_beta_projection_wave_048"]
    lines = [
        "# Compiler Milestone 093 Release Checkpoint",
        "",
        "Status: `VALIDATED_TAG_CANDIDATE_NOT_CREATED`",
        "",
        "This report is deterministically rendered from `compiler_milestone_093_v1.json`.",
        "It certifies repository-local compiler evidence only and grants no protected-system authority.",
        "",
        "## Snapshot",
        "",
        f"- Compiler commit: `{manifest['compiler_snapshot']['commit']}`",
        f"- Tracked-tree SHA-1: `{manifest['compiler_snapshot']['tracked_tree_sha1']}`",
        f"- Proposed annotated tag: `{manifest['release_candidate']['proposed_annotated_tag']}`",
        "- Tag created or pushed: `false`",
        "",
        "## Validated capability census",
        "",
        f"- Course packs: `{capabilities['course_packs']['count']}`",
        f"- Enabled answer capabilities: `{capabilities['enabled_answer_capabilities']['count']}`",
        f"- Generation recipes: `{capabilities['generation_recipes']['count']}`",
        f"- Production-validated questions: `{capabilities['validated_questions']['total']}` "
        f"(`{capabilities['validated_questions']['legacy_production_wave']}` + "
        f"`{capabilities['validated_questions']['wave_056']}`)",
        f"- Diagnostic assessments: `{capabilities['diagnostic_assessments']}`",
        "",
        "Enabled identifiers: " + ", ".join(
            f"`{identifier}`" for identifier in capabilities["enabled_answer_capabilities"]["identifiers"]
        ),
        "",
        "## Production-bank integrity",
        "",
        "| Bank set | Courses | Questions | Aggregate SHA-256 |",
        "| --- | ---: | ---: | --- |",
        f"| Legacy production wave | {banks['legacy_production_wave']['course_count']} | "
        f"{banks['legacy_production_wave']['question_count']} | `{banks['legacy_production_wave']['aggregate_sha256']}` |",
        f"| Wave 056 | {banks['wave_056']['course_count']} | {banks['wave_056']['question_count']} | "
        f"`{banks['wave_056']['aggregate_sha256']}` |",
        f"| Combined | {banks['combined']['course_count']} | {banks['combined']['question_count']} | "
        f"`{banks['combined']['aggregate_sha256']}` |",
        "",
        "## Source Corpus Wave 066",
        "",
        f"- Reference courses / sources / segments: `{source['reference_courses']}` / "
        f"`{source['source_documents']}` / `{source['source_segments']}`",
        f"- Generation target: `{source['generation_question_target']}`",
        f"- Required assessment blueprints: `{source['assessment_blueprints']}`",
        f"- Deterministic SHA-256: `{source['deterministic_sha256']}`",
        "- Canonical authority: `false`",
        "",
        "## Wave 048 and continuous validation",
        "",
        f"- Wave 048 status: `{wave_048['status']}`",
        f"- Wave 048 mode: `{wave_048['mode']}`",
        f"- CI workflow: `{manifest['ci_evidence']['workflow_path']}`",
        "- Successful CI runs: " + ", ".join(
            f"`{run['run_id']}`" for run in manifest["ci_evidence"]["successful_runs"]
        ),
        "- Repository checkout and Git-less archive gates: `PASS`",
        "",
        "## Protected-state boundary",
        "",
    ]
    lines.extend(f"- {key}: `false`" for key in sorted(manifest["protected_state"]))
    lines.extend(["", "## Intentionally deferred", ""])
    lines.extend(f"- {item}" for item in manifest["intentionally_deferred_scope"])
    lines.extend(["", "## Known non-blocking maintenance gaps", ""])
    lines.extend(f"- {item}" for item in manifest["known_non_blocking_maintenance_gaps"])
    lines.extend(["", "## Independent audit references", ""])
    lines.extend(
        f"- `{audit['audit_id']}` — `{audit['verdict']}` at `{audit['validated_tip']}`"
        for audit in manifest["independent_audit_references"]
    )
    return "\n".join(lines) + "\n"


def validate_checkpoint(root: Path = REPOSITORY_ROOT) -> None:
    root = Path(root)
    manifest = load_manifest(root)
    validate_manifest(manifest, root)
    report = (root / REPORT_PATH).read_text(encoding="utf-8")
    if report != render_checkpoint_report(manifest):
        raise MilestoneValidationError("milestone manifest and report drift")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "render", "evidence"))
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    args = parser.parse_args()
    if args.command == "evidence":
        print(json.dumps(collect_repository_evidence(args.root), sort_keys=True, indent=2))
    elif args.command == "render":
        manifest = load_manifest(args.root)
        print(render_checkpoint_report(manifest), end="")
    else:
        validate_checkpoint(args.root)
        print("COMPILER_MILESTONE_093_VALIDATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
