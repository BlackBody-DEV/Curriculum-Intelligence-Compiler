"""Semantic validation for frozen portable compiler release packages."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from tools.course_compiler_demo.release_package.manifest.integrity import (
    CONTRACT_SEMVER,
    PACKAGE_CONTRACT,
    canonical_json_bytes,
    finalize_manifest,
    manifest_sha256,
    sha256_file,
)
from tools.course_compiler_demo.release_package.validate.models import (
    VALIDATOR_NAME,
    VALIDATOR_VERSION,
    ValidationContext,
    now_iso,
)
from tools.course_compiler_demo.release_package.validate.semantic_rules import (
    APPROVED_SIGNAL_CATEGORIES,
    FORBIDDEN_TEXT_MARKERS,
    REQUIRED_CATEGORIES,
    REQUIRED_DESCRIPTOR_FIELDS,
    REQUIRED_MANIFEST_FIELDS,
    REQUIRED_SOURCE_FIELDS,
    RULE_ORDER,
    SAFE_BOUNDARY,
    SUPPORTED_MEDIA_TYPES,
    SUPPORTED_PROMOTION_RECOMMENDATIONS,
)


COMPILER_ROOT = Path(__file__).resolve().parents[4]
FROZEN_FIXTURE_ROOT = COMPILER_ROOT / "tools/course_compiler_demo/release_package/golden_packages"


class PackageValidator:
    def __init__(self, compiler_root: Path | None = None) -> None:
        self.compiler_root = compiler_root or COMPILER_ROOT

    def validate(self, package_root: Path | str) -> dict[str, Any]:
        package = Path(package_root)
        ctx = ValidationContext(package_path=str(package))
        manifest_path = package / "manifest.json"
        manifest: dict[str, Any] | None = None
        artifact_payloads: dict[str, Any] = {}

        if not manifest_path.exists():
            ctx.add_error(
                "JSON_PARSE",
                "Package manifest is missing.",
                field="manifest.json",
                recommended_action="Add a manifest.json file at the package root.",
            )
            return self._result(ctx)

        try:
            manifest = json.loads(manifest_path.read_text())
        except Exception as exc:
            ctx.add_error(
                "JSON_PARSE",
                "Package manifest is malformed JSON.",
                field="manifest.json",
                evidence=str(exc),
                recommended_action="Fix manifest JSON syntax.",
            )
            return self._result(ctx)

        ctx.package_id = manifest.get("package_id")
        ctx.package_contract = manifest.get("package_contract")
        ctx.package_version = manifest.get("package_version")

        self._contract_version(ctx, manifest)
        self._structural(ctx, manifest)
        self._artifact_inventory(ctx, package, manifest, artifact_payloads)
        self._paths(ctx, package, manifest)
        self._identifiers(ctx, manifest, artifact_payloads)
        self._references(ctx, manifest)
        self._provenance(ctx, manifest)
        self._linkage(ctx, manifest, artifact_payloads)
        self._signals(ctx, manifest, artifact_payloads)
        self._review_state(ctx, manifest, artifact_payloads)
        self._rights_safety(ctx, manifest, artifact_payloads)
        self._safety_boundary(ctx, manifest, artifact_payloads)
        self._integrity(ctx, manifest)
        self._determinism(ctx, manifest)
        self._known_gaps(ctx, manifest)
        return self._result(ctx)

    def _contract_version(self, ctx: ValidationContext, manifest: dict[str, Any]) -> None:
        ok = True
        if manifest.get("package_contract") != PACKAGE_CONTRACT:
            ok = False
            ctx.add_error("CONTRACT_VERSION", "Unsupported package contract.", field="package_contract", evidence=str(manifest.get("package_contract")))
        if manifest.get("package_contract_semver") != CONTRACT_SEMVER:
            ok = False
            ctx.add_error("CONTRACT_VERSION", "Unsupported package contract version.", field="package_contract_semver", evidence=str(manifest.get("package_contract_semver")))
        if not manifest.get("compiler_version"):
            ok = False
            ctx.add_error("CONTRACT_VERSION", "Compiler version is required.", field="compiler_version")
        ctx.set_rule("CONTRACT_VERSION", "pass" if ok else "fail", "Contract/version fields checked.")

    def _structural(self, ctx: ValidationContext, manifest: dict[str, Any]) -> None:
        ok = True
        missing = sorted(REQUIRED_MANIFEST_FIELDS - manifest.keys())
        if missing:
            ok = False
            ctx.add_error("STRUCTURAL_SCHEMA", "Manifest is missing required fields.", field="manifest", evidence=", ".join(missing))
        for item in manifest.get("artifact_inventory", []):
            missing_desc = sorted(REQUIRED_DESCRIPTOR_FIELDS - item.keys())
            if missing_desc:
                ok = False
                ctx.add_error("STRUCTURAL_SCHEMA", "Artifact descriptor is missing required fields.", scope=item.get("artifact_id", "artifact"), field="artifact_inventory", evidence=", ".join(missing_desc))
        if manifest.get("promotion_recommendation") not in SUPPORTED_PROMOTION_RECOMMENDATIONS:
            ok = False
            ctx.add_error("STRUCTURAL_SCHEMA", "Unsupported promotion recommendation.", field="promotion_recommendation")
        ctx.set_rule("STRUCTURAL_SCHEMA", "pass" if ok else "fail", "Structural fields checked.")

    def _artifact_inventory(
        self,
        ctx: ValidationContext,
        package: Path,
        manifest: dict[str, Any],
        artifact_payloads: dict[str, Any],
    ) -> None:
        ok = True
        inventory = manifest.get("artifact_inventory", [])
        declared_paths = {item.get("relative_path") for item in inventory}
        actual_paths = {
            path.relative_to(package).as_posix()
            for path in package.rglob("*")
            if path.is_file() and path.name not in {"manifest.json", "README.md"}
        }
        missing_files = sorted(path for path in declared_paths if path and not (package / path).is_file())
        extra_files = sorted(actual_paths - declared_paths)
        if missing_files:
            ok = False
            ctx.add_error("ARTIFACT_INVENTORY", "Declared artifact file is missing.", field="artifact_inventory", evidence=", ".join(missing_files))
        if extra_files:
            ok = False
            ctx.add_error("ARTIFACT_INVENTORY", "Package contains undeclared artifact files.", field="artifact_inventory", evidence=", ".join(extra_files))

        categories = {item.get("artifact_type") for item in inventory}
        missing_categories = sorted(REQUIRED_CATEGORIES - categories)
        if missing_categories:
            ok = False
            ctx.add_error("ARTIFACT_INVENTORY", "Required artifact categories are missing.", field="artifact_inventory", evidence=", ".join(missing_categories))

        for item in inventory:
            artifact_id = item.get("artifact_id", "artifact")
            if item.get("media_type") not in SUPPORTED_MEDIA_TYPES:
                ok = False
                ctx.add_error("ARTIFACT_INVENTORY", "Unsupported artifact media type.", scope=artifact_id, field="media_type", evidence=str(item.get("media_type")))
            if not item.get("schema_ref"):
                ok = False
                ctx.add_error("ARTIFACT_INVENTORY", "Artifact schema reference is required.", scope=artifact_id, field="schema_ref")
            path = package / str(item.get("relative_path", ""))
            if path.is_file() and item.get("media_type") == "application/json":
                try:
                    artifact_payloads[artifact_id] = json.loads(path.read_text())
                except Exception as exc:
                    ok = False
                    ctx.add_error("ARTIFACT_INVENTORY", "Artifact JSON is malformed.", scope=artifact_id, field=item.get("relative_path"), evidence=str(exc))
            ctx.artifact_results.append(
                {
                    "artifact_id": artifact_id,
                    "artifact_type": item.get("artifact_type"),
                    "relative_path": item.get("relative_path"),
                    "declared": True,
                    "exists": path.is_file(),
                }
            )
        ctx.set_rule("ARTIFACT_INVENTORY", "pass" if ok else "fail", "Artifact inventory checked.")

    def _paths(self, ctx: ValidationContext, package: Path, manifest: dict[str, Any]) -> None:
        ok = True
        root = package.resolve()
        for item in manifest.get("artifact_inventory", []):
            artifact_id = item.get("artifact_id", "artifact")
            rel = str(item.get("relative_path", ""))
            path = Path(rel)
            if path.is_absolute():
                ok = False
                ctx.add_error("PATH_CONTAINMENT", "Artifact path must be relative.", scope=artifact_id, field="relative_path", evidence=rel)
                continue
            if "\\" in rel or ".." in path.parts:
                ok = False
                ctx.add_error("PATH_CONTAINMENT", "Artifact path must not contain parent traversal or backslashes.", scope=artifact_id, field="relative_path", evidence=rel)
                continue
            resolved = (package / rel).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                ok = False
                ctx.add_error("PATH_CONTAINMENT", "Artifact path escapes package root.", scope=artifact_id, field="relative_path", evidence=rel)
            if (package / rel).is_symlink():
                target = os.path.realpath(package / rel)
                if not str(target).startswith(str(root)):
                    ok = False
                    ctx.add_error("PATH_CONTAINMENT", "Artifact symlink escapes package root.", scope=artifact_id, field="relative_path", evidence=rel)
        ctx.set_rule("PATH_CONTAINMENT", "pass" if ok else "fail", "Path containment checked.")

    def _identifiers(self, ctx: ValidationContext, manifest: dict[str, Any], artifact_payloads: dict[str, Any]) -> None:
        ok = True
        artifact_ids = [item.get("artifact_id") for item in manifest.get("artifact_inventory", [])]
        if len(artifact_ids) != len(set(artifact_ids)):
            ok = False
            ctx.add_error("IDENTIFIER_UNIQUENESS", "Duplicate artifact IDs found.", field="artifact_inventory")
        source_ids = [source.get("source_id") for source in manifest.get("source_references", [])]
        if len(source_ids) != len(set(source_ids)):
            ok = False
            ctx.add_error("IDENTIFIER_UNIQUENESS", "Duplicate source IDs found.", field="source_references")

        id_fields = {
            "procedure_candidate": "candidate_id",
            "question_candidate": "candidate_id",
            "generation_family_candidate": "family_id",
            "signal_mapping": "mapping_id",
            "performance_tracking_target": "target_id",
            "review_record": "review_id",
            "validation_report": "validation_id",
        }
        for artifact_type, field in id_fields.items():
            values = []
            for item in manifest.get("artifact_inventory", []):
                if item.get("artifact_type") == artifact_type:
                    payload = artifact_payloads.get(item.get("artifact_id"), {})
                    value = payload.get(field)
                    if value:
                        values.append(value)
            if len(values) != len(set(values)):
                ok = False
                ctx.add_error("IDENTIFIER_UNIQUENESS", f"Duplicate {artifact_type} IDs found.", field=field)
        ctx.set_rule("IDENTIFIER_UNIQUENESS", "pass" if ok else "fail", "Identifier uniqueness checked.")

    def _references(self, ctx: ValidationContext, manifest: dict[str, Any]) -> None:
        ok = True
        artifact_ids = {item.get("artifact_id") for item in manifest.get("artifact_inventory", [])}
        source_ids = {source.get("source_id") for source in manifest.get("source_references", [])}
        for item in manifest.get("artifact_inventory", []):
            artifact_id = item.get("artifact_id", "artifact")
            for dep in item.get("depends_on_artifact_ids", []):
                if dep not in artifact_ids:
                    ok = False
                    ctx.add_error("REFERENCE_INTEGRITY", "Artifact dependency does not resolve.", scope=artifact_id, field="depends_on_artifact_ids", evidence=str(dep))
            for source_id in item.get("source_reference_ids", []):
                if source_id not in source_ids:
                    ok = False
                    ctx.add_error("REFERENCE_INTEGRITY", "Source reference does not resolve.", scope=artifact_id, field="source_reference_ids", evidence=str(source_id))
        for list_name in [
            "procedure_artifact_ids",
            "question_artifact_ids",
            "generation_family_artifact_ids",
            "signal_mapping_artifact_ids",
            "performance_tracking_artifact_ids",
            "review_artifact_ids",
            "validation_artifact_ids",
            "asset_artifact_ids",
        ]:
            for artifact_id in manifest.get(list_name, []):
                if artifact_id not in artifact_ids:
                    ok = False
                    ctx.add_error("REFERENCE_INTEGRITY", "Manifest artifact ID list contains unresolved ID.", field=list_name, evidence=str(artifact_id))
        if self._has_cycle(manifest):
            ok = False
            ctx.add_error("REFERENCE_INTEGRITY", "Artifact dependency cycle detected.", field="depends_on_artifact_ids")
        ctx.set_rule("REFERENCE_INTEGRITY", "pass" if ok else "fail", "Reference integrity checked.")

    def _has_cycle(self, manifest: dict[str, Any]) -> bool:
        graph = {
            item.get("artifact_id"): set(item.get("depends_on_artifact_ids", []))
            for item in manifest.get("artifact_inventory", [])
        }
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            for dep in graph.get(node, set()):
                if dep in graph and visit(dep):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        return any(visit(node) for node in graph)

    def _provenance(self, ctx: ValidationContext, manifest: dict[str, Any]) -> None:
        ok = True
        for source in manifest.get("source_references", []):
            missing = sorted(REQUIRED_SOURCE_FIELDS - source.keys())
            if missing:
                ok = False
                ctx.add_error("PROVENANCE", "Source reference is missing required provenance fields.", scope=source.get("source_id", "source"), field="source_references", evidence=", ".join(missing))
            if not source.get("provenance_refs"):
                ok = False
                ctx.add_error("PROVENANCE", "Source reference needs at least one provenance reference.", scope=source.get("source_id", "source"), field="provenance_refs")
            if "protected passage" in json.dumps(source).lower():
                ok = False
                ctx.add_error("PROVENANCE", "Source metadata appears to expose protected source content.", scope=source.get("source_id", "source"))
        for item in manifest.get("artifact_inventory", []):
            if item.get("artifact_type") in {"procedure_candidate", "question_candidate", "generation_family_candidate"} and not item.get("source_reference_ids"):
                ok = False
                ctx.add_error("PROVENANCE", "Instructional artifact requires at least one source reference.", scope=item.get("artifact_id", "artifact"), field="source_reference_ids")
        ctx.set_rule("PROVENANCE", "pass" if ok else "fail", "Source provenance checked.")

    def _linkage(self, ctx: ValidationContext, manifest: dict[str, Any], artifact_payloads: dict[str, Any]) -> None:
        pq_ok = True
        gf_ok = True
        procedure_ids = set(manifest.get("procedure_artifact_ids", []))
        question_ids = set(manifest.get("question_artifact_ids", []))
        micro_skills = set(manifest.get("micro_skill_codes", []))
        for item in manifest.get("artifact_inventory", []):
            artifact_id = item.get("artifact_id")
            payload = artifact_payloads.get(artifact_id, {})
            if item.get("artifact_type") == "question_candidate":
                deps = set(item.get("depends_on_artifact_ids", []))
                if not (deps & procedure_ids) and not payload.get("micro_skill") and not micro_skills:
                    pq_ok = False
                    ctx.add_error("PROCEDURE_QUESTION_LINKAGE", "Question candidate is orphaned from procedure and micro-skill context.", scope=artifact_id)
                if not payload.get("answer_type"):
                    pq_ok = False
                    ctx.add_error("PROCEDURE_QUESTION_LINKAGE", "Question candidate must declare answer_type.", scope=artifact_id, field="answer_type")
                if not payload.get("candidate_type"):
                    pq_ok = False
                    ctx.add_error("PROCEDURE_QUESTION_LINKAGE", "Question candidate must declare origin/candidate_type.", scope=artifact_id, field="candidate_type")
            if item.get("artifact_type") == "generation_family_candidate":
                deps = set(item.get("depends_on_artifact_ids", []))
                if not (deps & (procedure_ids | question_ids)) and not payload.get("variable_parameters"):
                    gf_ok = False
                    ctx.add_error("GENERATION_FAMILY_LINKAGE", "Generation family is orphaned from procedures/questions and has no parameter definition.", scope=artifact_id)
                params = payload.get("variable_parameters", [])
                if len(params) != len(set(params)):
                    gf_ok = False
                    ctx.add_error("GENERATION_FAMILY_LINKAGE", "Generation family parameter names must be unique.", scope=artifact_id, field="variable_parameters")
                if payload.get("student_visible") is True or payload.get("live_deployable") is True:
                    gf_ok = False
                    ctx.add_error("GENERATION_FAMILY_LINKAGE", "Generation family must remain non-live.", scope=artifact_id)
        ctx.set_rule("PROCEDURE_QUESTION_LINKAGE", "pass" if pq_ok else "fail", "Procedure/question linkage checked.")
        ctx.set_rule("GENERATION_FAMILY_LINKAGE", "pass" if gf_ok else "fail", "Generation-family linkage checked.")

    def _signals(self, ctx: ValidationContext, manifest: dict[str, Any], artifact_payloads: dict[str, Any]) -> None:
        ok = True
        targets = set(manifest.get("micro_skill_codes", [])) | set(manifest.get("procedure_artifact_ids", [])) | set(manifest.get("question_artifact_ids", []))
        for item in manifest.get("artifact_inventory", []):
            if item.get("artifact_type") != "signal_mapping":
                continue
            payload = artifact_payloads.get(item.get("artifact_id"), {})
            for signal in payload.get("signals", []):
                if signal not in APPROVED_SIGNAL_CATEGORIES:
                    ok = False
                    ctx.add_error("SIGNAL_POLICY", "Unknown signal category.", scope=item.get("artifact_id", "artifact"), field="signals", evidence=str(signal))
            target = payload.get("target")
            if target and target not in targets:
                ok = False
                ctx.add_error("SIGNAL_POLICY", "Signal mapping target is undeclared.", scope=item.get("artifact_id", "artifact"), field="target", evidence=str(target))
            if payload.get("runtime_execution") is True:
                ok = False
                ctx.add_error("SIGNAL_POLICY", "Signal mapping may not claim runtime execution.", scope=item.get("artifact_id", "artifact"))
        ctx.set_rule("SIGNAL_POLICY", "pass" if ok else "fail", "Signal policy checked.")

    def _review_state(self, ctx: ValidationContext, manifest: dict[str, Any], artifact_payloads: dict[str, Any]) -> None:
        ok = True
        if manifest.get("content_status") != "non_live_candidate":
            ok = False
            ctx.add_error("REVIEW_STATE", "content_status must be non_live_candidate.", field="content_status", evidence=str(manifest.get("content_status")))
        if manifest.get("review_status") != "human_review_required":
            ok = False
            ctx.add_error("REVIEW_STATE", "review_status must be human_review_required.", field="review_status")
        for item in manifest.get("artifact_inventory", []):
            if item.get("status") != "human_review_required":
                ok = False
                ctx.add_error("REVIEW_STATE", "Artifact status must be human_review_required.", scope=item.get("artifact_id", "artifact"), field="status")
            payload = artifact_payloads.get(item.get("artifact_id"), {})
            if payload.get("review_status") and payload.get("review_status") != "review_pending":
                ok = False
                ctx.add_error("REVIEW_STATE", "Artifact review_status must remain review_pending.", scope=item.get("artifact_id", "artifact"), field="review_status")
        ctx.set_rule("REVIEW_STATE", "pass" if ok else "fail", "Review state checked.")

    def _rights_safety(self, ctx: ValidationContext, manifest: dict[str, Any], artifact_payloads: dict[str, Any]) -> None:
        ok = True
        for source in manifest.get("source_references", []):
            if source.get("rights_status") not in {"axiomiq_authored", "synthetic_fixture", "rights_review_required"}:
                ok = False
                ctx.add_error("RIGHTS_SAFETY", "Unsupported or unsafe rights status.", scope=source.get("source_id", "source"), field="rights_status")
            if source.get("privacy_status") not in {"no_personal_data", "privacy_review_required"}:
                ok = False
                ctx.add_error("RIGHTS_SAFETY", "Unsupported privacy status.", scope=source.get("source_id", "source"), field="privacy_status")
        text = json.dumps({"manifest": manifest, "artifacts": artifact_payloads}, sort_keys=True)
        if "copyrighted textbook" in text.lower() or "answer key" in text.lower():
            ok = False
            ctx.add_error("RIGHTS_SAFETY", "Package appears to include protected source payload markers.")
        ctx.set_rule("RIGHTS_SAFETY", "pass" if ok else "fail", "Rights and privacy safety checked.")

    def _safety_boundary(self, ctx: ValidationContext, manifest: dict[str, Any], artifact_payloads: dict[str, Any]) -> None:
        ok = True
        safety = manifest.get("safety_boundary", {})
        for key, expected in SAFE_BOUNDARY.items():
            if safety.get(key) is not expected:
                ok = False
                ctx.add_error("SAFETY_BOUNDARY", "Safety boundary value is unsafe.", field=f"safety_boundary.{key}", evidence=f"{safety.get(key)!r}")
        text = json.dumps({"manifest": manifest, "artifacts": artifact_payloads}, sort_keys=True)
        for marker in sorted(FORBIDDEN_TEXT_MARKERS):
            if marker in text:
                ok = False
                ctx.add_error("SAFETY_BOUNDARY", "Forbidden safety marker found.", field="package_text", evidence=marker)
        if '"student_visible": true' in text.lower():
            ok = False
            ctx.add_error("SAFETY_BOUNDARY", "Student-visible true claim found.", field="package_text")
        ctx.set_rule("SAFETY_BOUNDARY", "pass" if ok else "fail", "Safety boundary checked.")

    def _integrity(self, ctx: ValidationContext, manifest: dict[str, Any]) -> None:
        ok = True
        package = Path(ctx.package_path)
        for item in manifest.get("artifact_inventory", []):
            path = package / str(item.get("relative_path", ""))
            if not path.is_file():
                continue
            if item.get("sha256") != sha256_file(path):
                ok = False
                ctx.add_error("INTEGRITY", "Artifact checksum mismatch.", scope=item.get("artifact_id", "artifact"), field="sha256")
            if item.get("byte_size") != len(path.read_bytes()):
                ok = False
                ctx.add_error("INTEGRITY", "Artifact byte size mismatch.", scope=item.get("artifact_id", "artifact"), field="byte_size")
        if manifest.get("integrity", {}).get("package_manifest_sha256") != manifest_sha256(manifest):
            ok = False
            ctx.add_error("INTEGRITY", "Manifest integrity checksum mismatch.", field="integrity.package_manifest_sha256")
        ctx.set_rule("INTEGRITY", "pass" if ok else "fail", "Checksums and byte sizes checked.")

    def _determinism(self, ctx: ValidationContext, manifest: dict[str, Any]) -> None:
        ok = True
        first = canonical_json_bytes(manifest)
        second = canonical_json_bytes(manifest)
        if first != second:
            ok = False
            ctx.add_error("DETERMINISM", "Manifest canonical serialization is not deterministic.")
        if finalize_manifest(manifest).get("integrity", {}).get("package_manifest_sha256") != manifest.get("integrity", {}).get("package_manifest_sha256"):
            ok = False
            ctx.add_error("DETERMINISM", "Manifest finalization does not reproduce declared checksum.", field="integrity.package_manifest_sha256")
        ids = [item.get("artifact_id") for item in manifest.get("artifact_inventory", [])]
        if ids != sorted(ids):
            ok = False
            ctx.add_error("DETERMINISM", "Artifact ordering must be deterministic by artifact_id.", field="artifact_inventory")
        ctx.set_rule("DETERMINISM", "pass" if ok else "fail", "Determinism checked.")

    def _known_gaps(self, ctx: ValidationContext, manifest: dict[str, Any]) -> None:
        ok = True
        gaps = manifest.get("known_gaps", [])
        for gap in gaps:
            severity = gap.get("severity")
            gap_class = gap.get("gap_class", "nonblocking_declared" if severity == "nonblocking" else "blocking_content")
            if gap_class != "nonblocking_declared":
                ok = False
                ctx.add_error("KNOWN_GAPS", "Blocking gap declared.", field="known_gaps", evidence=str(gap.get("gap_id")))
            elif severity != "nonblocking":
                ok = False
                ctx.add_error("KNOWN_GAPS", "Nonblocking gap must use severity nonblocking.", field="known_gaps", evidence=str(gap.get("gap_id")))
            else:
                ctx.add_warning("KNOWN_GAPS", "Declared nonblocking gap.", field="known_gaps", evidence=str(gap.get("gap_id")))
        if gaps and manifest.get("promotion_recommendation") != "hold_for_human_review":
            ok = False
            ctx.add_error("KNOWN_GAPS", "Packages with known gaps must hold for human review.", field="promotion_recommendation")
        ctx.set_rule("KNOWN_GAPS", "pass" if ok else "fail", "Known gaps classified.")

    def _result(self, ctx: ValidationContext) -> dict[str, Any]:
        errors = sorted(ctx.errors)
        warnings = sorted(ctx.warnings)
        completed_at = now_iso()
        if errors:
            verdict = "reject"
        elif warnings:
            verdict = "accept_with_warnings"
        else:
            verdict = "accept"

        rule_map = {result.rule_id: result for result in ctx.rule_results}
        rule_results = [
            rule_map.get(rule_id, None).to_dict()
            if rule_id in rule_map
            else {"rule_id": rule_id, "status": "not_run", "message": "Rule did not run."}
            for rule_id in RULE_ORDER
        ]
        status_by_rule = {item["rule_id"]: item["status"] for item in rule_results}
        return {
            "validator_name": VALIDATOR_NAME,
            "validator_version": VALIDATOR_VERSION,
            "package_path": ctx.package_path,
            "package_id": ctx.package_id,
            "package_contract": ctx.package_contract,
            "package_version": ctx.package_version,
            "validation_started_at": ctx.validation_started_at,
            "validation_completed_at": completed_at,
            "overall_verdict": verdict,
            "schema_status": status_by_rule.get("STRUCTURAL_SCHEMA", "not_run"),
            "manifest_status": status_by_rule.get("CONTRACT_VERSION", "not_run"),
            "artifact_inventory_status": status_by_rule.get("ARTIFACT_INVENTORY", "not_run"),
            "identifier_status": status_by_rule.get("IDENTIFIER_UNIQUENESS", "not_run"),
            "reference_integrity_status": status_by_rule.get("REFERENCE_INTEGRITY", "not_run"),
            "provenance_status": status_by_rule.get("PROVENANCE", "not_run"),
            "procedure_question_linkage_status": status_by_rule.get("PROCEDURE_QUESTION_LINKAGE", "not_run"),
            "generation_family_linkage_status": status_by_rule.get("GENERATION_FAMILY_LINKAGE", "not_run"),
            "signal_policy_status": status_by_rule.get("SIGNAL_POLICY", "not_run"),
            "review_state_status": status_by_rule.get("REVIEW_STATE", "not_run"),
            "rights_status": status_by_rule.get("RIGHTS_SAFETY", "not_run"),
            "safety_boundary_status": status_by_rule.get("SAFETY_BOUNDARY", "not_run"),
            "integrity_status": status_by_rule.get("INTEGRITY", "not_run"),
            "determinism_status": status_by_rule.get("DETERMINISM", "not_run"),
            "known_gap_status": status_by_rule.get("KNOWN_GAPS", "not_run"),
            "errors": [issue.to_dict() for issue in errors],
            "warnings": [issue.to_dict() for issue in warnings],
            "rule_results": rule_results,
            "artifact_results": sorted(ctx.artifact_results, key=lambda item: item.get("artifact_id") or ""),
            "boundary_evidence": {
                "adaptive_platform_accessed": False,
                "adaptive_platform_modified": False,
                "database_contacted": False,
                "network_contacted": False,
                "runtime_route_created": False,
                "learner_loop_implemented": False,
                "canonical_promotion_performed": False,
                "student_visible_output_created": False,
            },
        }


def validate_package(package_root: Path | str) -> dict[str, Any]:
    return PackageValidator().validate(package_root)
