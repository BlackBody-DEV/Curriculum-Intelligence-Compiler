"""Controller layer for the local operator dashboard."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from tools.course_compiler_demo.assessment_generation.blueprint import validate_blueprint
from tools.course_compiler_demo.assessment_generation.family_loader import load_family
from tools.course_compiler_demo.assessment_generation.generator import generate_assessment, regenerate_question
from tools.course_compiler_demo.assessment_generation.storage import load_historical_fingerprints, write_assessment_run
from tools.course_compiler_demo.assessment_generation.validators import review_record
from tools.course_compiler_demo.ingest.document_classifier import classify_document, detect_subject
from tools.course_compiler_demo.ingest.input_loader import SUPPORTED_INPUT_FORMATS
from tools.course_compiler_demo.profiles.subject_profile_loader import build_profile_run, load_profile

from .run_storage import DEFAULT_DASHBOARD_ROOT, DashboardStorage, DashboardStorageError, load_json, pretty_json, sha256_bytes, utc_now
from .security import DashboardSecurityError, ensure_beneath, validate_identifier, validate_upload


REPO_ROOT = Path(__file__).resolve().parents[3]
PROFILE_DIR = REPO_ROOT / "tools/course_compiler_demo/profiles"
FAMILY_DIR = REPO_ROOT / "tools/course_compiler_demo/assessment_generation/families"
PHYSICS_PROFILE_PATH = PROFILE_DIR / "physics_intro_mechanics_v1.json"
STATICS_RELEASE_PACKAGE = REPO_ROOT / "reports/course_compiler_demo/internal_release/release_package_emitter_proof/vector_components_2d_release_package_v1.json"
SOURCE_INBOX_ROOT = Path("/Users/fanarichardson/Documents/AxiomIQ_Source_Inbox")


class DashboardControllerError(ValueError):
    """Raised when a controller action cannot proceed."""


class DashboardController:
    def __init__(self, storage: DashboardStorage | None = None) -> None:
        self.storage = storage or DashboardStorage(DEFAULT_DASHBOARD_ROOT)
        self._source_text_cache: dict[str, str] = {}

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "noncanonical": True, "student_visible": False}

    def list_profiles(self) -> list[dict[str, Any]]:
        physics = load_profile(PHYSICS_PROFILE_PATH)
        return [
            {
                "profile_id": physics["profile_id"],
                "subject_code": physics["subject_code"],
                "course_levels": physics["supported_course_levels"],
                "description": "Registered Physics profile",
                "enabled": True,
            },
            {
                "profile_id": "STATICS_VECTOR_COMPONENTS_RELEASE_PROFILE_V1",
                "subject_code": "STATICS",
                "course_levels": ["ENGINEERING_MECHANICS_STATICS"],
                "description": "Fixed dashboard profile backed by committed vector-components release package",
                "enabled": True,
            },
        ]

    def list_generation_families(self) -> list[dict[str, Any]]:
        families = []
        for path in sorted(FAMILY_DIR.glob("*.json")):
            family = load_family(path)
            families.append(
                {
                    "generation_family_id": family["generation_family_id"],
                    "subject_code": family["subject_code"],
                    "topic_code": family["topic_code"],
                    "target_micro_skill_code": family["target_micro_skill_code"],
                    "question_types": family["question_types"],
                    "enabled": family["enabled"],
                }
            )
        return families

    def create_run(self, payload: dict[str, Any] | None = None, *, run_id: str | None = None) -> dict[str, Any]:
        payload = payload or {}
        return self.storage.create_run(source_title=str(payload.get("source_title", "")), run_id=run_id)

    def get_run(self, run_id: str) -> dict[str, Any]:
        return self.storage.load_manifest(validate_identifier(run_id, "run ID"))

    def list_runs(self) -> list[dict[str, Any]]:
        return self.storage.list_runs()

    def upload_source(self, run_id: str, *, filename: str, content: bytes, metadata: dict[str, Any]) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        display, source_format = validate_upload(filename, content)
        source_text = content.decode("utf-8")
        source_hash = sha256_bytes(content)
        classification = classify_document(source_text)
        subject = detect_subject(source_text)
        receipt = {
            "source_title": str(metadata.get("source_title") or manifest.get("source_title") or display),
            "source_display_filename": display,
            "source_sha256": source_hash,
            "source_format": source_format,
            "document_type": metadata.get("document_type", classification["detected_source_type"]),
            "author_or_institution": metadata.get("author_or_institution", ""),
            "rights_status": metadata.get("rights_status", "rights_review_required"),
            "privacy_status": metadata.get("privacy_status", "privacy_review_required"),
            "optional_source_reference": metadata.get("optional_source_reference", ""),
            "rights_confirmed": False,
            "detected_subject": subject["detected_subject"],
            "subject_confidence": subject["subject_confidence"],
            "classification": classification,
            "raw_or_normalized_source_retained": bool(metadata.get("retain_normalized_source", False)),
        }
        manifest.update(
            {
                "status": "source_uploaded",
                "source_title": receipt["source_title"],
                "source_display_filename": display,
                "source_sha256": source_hash,
                "source_format": source_format,
                "rights_status": receipt["rights_status"],
                "privacy_status": receipt["privacy_status"],
                "raw_or_normalized_source_retained": receipt["raw_or_normalized_source_retained"],
                "detected_subject": receipt["detected_subject"],
                "last_error": None,
            }
        )
        self.storage.write_json_artifact(manifest, "source_receipt", "source/source_receipt.json", receipt)
        if receipt["raw_or_normalized_source_retained"]:
            self.storage.write_text_artifact(manifest, "normalized_source", "source/normalized_source.txt", source_text)
        else:
            transient = self.storage.run_dir(run_id) / "source/normalized_source.txt"
            if transient.exists():
                transient.unlink()
            self._source_text_cache[run_id] = source_text
        return self.get_run(run_id)

    def confirm_rights(self, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        if manifest["status"] not in {"source_uploaded", "rights_confirmed", "profile_selected"}:
            raise DashboardControllerError("source must be uploaded before rights confirmation")
        manifest["rights_status"] = str(payload.get("rights_status", manifest.get("rights_status") or "confirmed_local_use"))
        manifest["privacy_status"] = str(payload.get("privacy_status", manifest.get("privacy_status") or "non_private"))
        manifest["status"] = "rights_confirmed"
        receipt = load_json(self.storage.artifact_path(manifest, "source_receipt"))
        receipt.update({"rights_confirmed": True, "rights_status": manifest["rights_status"], "privacy_status": manifest["privacy_status"]})
        self.storage.write_json_artifact(manifest, "source_receipt", "source/source_receipt.json", receipt)
        self.storage.save_manifest(manifest)
        return self.get_run(run_id)

    def select_profile(self, run_id: str, profile_id: str) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        if manifest["status"] not in {"rights_confirmed", "profile_selected", "compiler_failed"}:
            raise DashboardControllerError("rights must be confirmed before profile selection")
        profile_id = validate_identifier(profile_id, "profile ID")
        registered = {item["profile_id"] for item in self.list_profiles()}
        if profile_id not in registered:
            raise DashboardControllerError("profile is not registered")
        manifest["selected_profile_id"] = profile_id
        manifest["status"] = "profile_selected"
        self.storage.save_manifest(manifest)
        return self.get_run(run_id)

    def compile_run(self, run_id: str, *, selected_micro_skill: str | None = None) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        if manifest["status"] != "profile_selected":
            raise DashboardControllerError("profile must be selected before compilation")
        manifest["status"] = "compiling"
        manifest["compiler_status"] = "running"
        self.storage.save_manifest(manifest)
        try:
            if manifest["selected_profile_id"] == "PHYSICS_INTRO_MECHANICS_PROFILE_V1":
                self._compile_physics(manifest, selected_micro_skill or "apply_newtons_second_law_1d")
            elif manifest["selected_profile_id"] == "STATICS_VECTOR_COMPONENTS_RELEASE_PROFILE_V1":
                self._compile_statics(manifest)
            else:
                raise DashboardControllerError("unsupported profile")
            manifest = self.get_run(run_id)
            manifest["status"] = "curriculum_review_pending"
            manifest["compiler_status"] = "pass"
            manifest["last_error"] = None
        except Exception as exc:
            manifest["status"] = "compiler_failed"
            manifest["compiler_status"] = "fail"
            manifest["last_error"] = str(exc)
        self.storage.save_manifest(manifest)
        return self.get_run(run_id)

    def _source_text_for_run(self, manifest: dict[str, Any]) -> tuple[str, Path]:
        normalized_key = manifest.get("artifact_index", {}).get("normalized_source")
        if normalized_key:
            path = self.storage.artifact_path(manifest, "normalized_source")
            return path.read_text(encoding="utf-8"), Path(manifest.get("source_display_filename") or "dashboard_uploaded_source.txt")
        cached = self._source_text_cache.get(manifest["run_id"])
        if cached is not None:
            return cached, Path(manifest.get("source_display_filename") or "dashboard_uploaded_source.txt")
        raise DashboardControllerError("source text is unavailable; upload again or retain normalized source for resumable compilation")

    def _compile_physics(self, manifest: dict[str, Any], selected_micro_skill: str) -> None:
        source_text, source_path = self._source_text_for_run(manifest)
        profile = load_profile(PHYSICS_PROFILE_PATH)
        result = build_profile_run(profile=profile, source_text=source_text, source_path=source_path, selected_micro_skill=selected_micro_skill)
        compiler_dir = self.storage.run_dir(manifest["run_id"]) / "compiler"
        compiler_dir.mkdir(parents=True, exist_ok=True)
        for name, payload in result.outputs.items():
            rel = f"compiler/{name}"
            key = Path(name).stem[:80]
            if name.endswith(".json"):
                self.storage.write_json_artifact(manifest, key, rel, self._scrub_local_paths(payload))
            else:
                self.storage.write_text_artifact(manifest, key, rel, str(self._scrub_local_paths(payload)))
        manifest["detected_subject"] = "PHYSICS"
        manifest["detected_course_level"] = "INTRO_PHYSICS_MECHANICS"

    def _compile_statics(self, manifest: dict[str, Any]) -> None:
        package = load_json(STATICS_RELEASE_PACKAGE)
        manifest["detected_subject"] = "STATICS"
        manifest["detected_course_level"] = "ENGINEERING_MECHANICS_STATICS"
        self.storage.write_json_artifact(manifest, "source_document", "compiler/source_document.json", {
            "source_title": manifest["source_title"],
            "source_sha256": manifest["source_sha256"],
            "subject_code": "STATICS",
            "course_profile": "ENGINEERING_MECHANICS_STATICS",
            "rights_status": manifest["rights_status"],
            "privacy_status": manifest["privacy_status"],
        })
        self.storage.write_json_artifact(manifest, "source_interpretation", "compiler/source_interpretation.json", {
            "detected_subject": "STATICS",
            "detected_course_level": "ENGINEERING_MECHANICS_STATICS",
            "subject_confidence": "high",
            "course_level_confidence": "high",
            "interpretation_basis": "fixed approved vector-components release package",
        })
        self.storage.write_json_artifact(manifest, "source_feature_flags", "compiler/source_feature_flags.json", {
            "contains_formula": True,
            "contains_practice_items": True,
            "profile_id": "STATICS_VECTOR_COMPONENTS_RELEASE_PROFILE_V1",
        })
        self.storage.write_json_artifact(manifest, "topic_candidates", "compiler/topic_candidates.json", {"topic_candidates": [{
            "candidate_id": "TOPIC_STATICS_FORCE_VECTORS",
            "topic_code": "force_vectors",
            "topic_name": "Force Vectors",
            "confidence": "high",
            "status": "compiler_dashboard_review_pending",
        }]})
        self.storage.write_json_artifact(manifest, "micro_skill_candidates", "compiler/micro_skill_candidates.json", {"micro_skill_candidates": [{
            "candidate_id": "MS_STATICS_VECTOR_COMPONENTS_2D",
            "micro_skill_code": "vector_components_2d",
            "micro_skill_name": "Resolve a two-dimensional force into signed rectangular components",
            "topic_code": "force_vectors",
            "confidence": "high",
            "status": "compiler_dashboard_review_pending",
        }]})
        self.storage.write_json_artifact(manifest, "dependency_candidates", "compiler/dependency_candidates.json", {"dependency_candidates": []})
        self.storage.write_json_artifact(manifest, "content_gaps", "compiler/content_gaps.json", {"content_gaps": package.get("content_gaps", [])})
        self.storage.write_json_artifact(manifest, "curriculum_extraction_package", "compiler/curriculum_extraction_package.json", package)

    def results(self, run_id: str) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        topics = self._artifact_or_empty(manifest, "topic_candidates", "topic_candidates")
        skills = self._artifact_or_empty(manifest, "micro_skill_candidates", "micro_skill_candidates")
        gaps = self._artifact_or_empty(manifest, "content_gaps", "content_gaps")
        package = self._artifact_or_empty(manifest, "curriculum_extraction_package", None)
        return {
            "run": self._public_manifest(manifest),
            "topics": topics,
            "micro_skills": skills,
            "content_gaps": gaps,
            "procedure_candidates": package.get("procedure_candidates", []) if isinstance(package, dict) else [],
            "question_candidates": package.get("question_candidates", []) if isinstance(package, dict) else [],
            "generation_families": package.get("generation_family_candidates", []) if isinstance(package, dict) else [],
            "validation_status": manifest.get("compiler_status"),
        }

    def curriculum_review(self, run_id: str, decisions: list[dict[str, Any]]) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        allowed = {"pending", "accepted", "rejected", "needs_revision"}
        records = []
        for decision in decisions:
            state = decision.get("decision", "pending")
            if state not in allowed:
                raise DashboardControllerError("unsupported curriculum review decision")
            records.append({
                "candidate_id": validate_identifier(str(decision["candidate_id"]), "candidate ID"),
                "candidate_type": str(decision.get("candidate_type", "unknown")),
                "decision": state,
                "review_note": str(decision.get("review_note", "")),
                "timestamp": utc_now(),
                "noncanonical": True,
                "eligible_for_alpha_import": False,
            })
        payload = {"review_status": "accepted_for_local_use", "decisions": records, "noncanonical": True}
        self.storage.write_json_artifact(manifest, "curriculum_review_decisions", "review/curriculum_review_decisions.json", payload)
        manifest = self.get_run(run_id)
        manifest["curriculum_review_status"] = "accepted_for_local_use"
        manifest["status"] = "assessment_ready"
        self.storage.save_manifest(manifest)
        return payload

    def create_assessment(self, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        family = self._family_for_id(str(payload["generation_family_id"]))
        assessment_id = validate_identifier(str(payload.get("assessment_id") or f"ASSESS_{family['target_micro_skill_code'].upper()}"), "assessment ID")
        count = int(payload.get("question_count", 10))
        difficulty = payload.get("difficulty_distribution") or {"foundational": 3, "standard": 4, "advanced": 3}
        question_types = payload.get("question_type_distribution") or {family["question_types"][0]: count}
        blueprint = {
            "assessment_id": assessment_id,
            "contract_version": "assessment_generation_contract_v1",
            "title": str(payload.get("title", f"{family['target_micro_skill_code']} Assessment")),
            "assessment_type": payload.get("assessment_type", "practice_set"),
            "subject_code": family["subject_code"],
            "course_profile": manifest.get("selected_profile_id") or "dashboard_profile",
            "selected_topic_codes": [family["topic_code"]],
            "selected_micro_skill_codes": [family["target_micro_skill_code"]],
            "question_count": count,
            "difficulty_distribution": difficulty,
            "question_type_distribution": question_types,
            "generation_family_allocation": {
                family["generation_family_id"]: {
                    "question_count": count,
                    "approved_procedure_codes": [family["approved_procedure_code"]],
                }
            },
            "prerequisite_policy": {"allowed_prerequisite_skills": family["approved_prerequisite_skills"]},
            "scaffolding_policy": {"include_scaffolding": False},
            "solution_policy": {"include_solutions_in_instructor_export": True},
            "answer_key_policy": {"student_export_includes_answers": False},
            "uniqueness_policy": {"reject_exact_duplicates": True, "reject_structural_duplicates": True},
            "scope_policy": {"forbidden_downstream_micro_skills": []},
            "rights_boundary": {
                "eligible_for_alpha_import": False,
                "canonical_approved": False,
                "student_visible": False,
                "human_review_required": True,
            },
            "random_seed": int(payload.get("random_seed", 2026071801)),
            "status": "generation_ready",
        }
        validate_blueprint(blueprint)
        rel = f"assessments/{assessment_id}/assessment_blueprint.json"
        self.storage.write_json_artifact(manifest, f"assessment_{assessment_id}_blueprint", rel, blueprint)
        manifest = self.get_run(run_id)
        if assessment_id not in manifest["assessment_ids"]:
            manifest["assessment_ids"].append(assessment_id)
        manifest["status"] = "assessment_ready"
        self.storage.save_manifest(manifest)
        return blueprint

    def generate_assessment(self, run_id: str, assessment_id: str, *, history_run_ids: list[str] | None = None) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        assessment_id = validate_identifier(assessment_id, "assessment ID")
        blueprint = load_json(self.storage.artifact_path(manifest, f"assessment_{assessment_id}_blueprint"))
        family_id = next(iter(blueprint["generation_family_allocation"]))
        family = self._family_for_id(family_id)
        historical = set()
        for prior in history_run_ids or []:
            historical |= load_historical_fingerprints(self.storage.run_dir(validate_identifier(prior, "history run ID")))
        assessment, duplicate_report, decisions = generate_assessment(family=family, blueprint=blueprint, historical_fingerprints=historical)
        output_dir = self.storage.run_dir(run_id) / "assessments" / assessment_id
        write_assessment_run(
            output_dir=output_dir,
            blueprint=blueprint,
            family=family,
            assessment=assessment,
            duplicate_report=duplicate_report,
            review_decisions=decisions,
        )
        for name in ["generation_manifest", "generated_assessment", "duplicate_report", "validation_report", "review_decisions"]:
            manifest.setdefault("artifact_index", {})[f"assessment_{assessment_id}_{name}"] = f"assessments/{assessment_id}/{name}.json"
        for export in ["student_assessment.json", "instructor_assessment.json", "student_assessment.md", "instructor_assessment.md"]:
            key = f"assessment_{assessment_id}_export_{export.replace('.', '_')}"
            manifest["artifact_index"][key] = f"assessments/{assessment_id}/exports/{export}"
        manifest["status"] = "assessment_review_pending"
        self.storage.save_manifest(manifest)
        return self.get_assessment(run_id, assessment_id)

    def get_assessment(self, run_id: str, assessment_id: str) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        assessment_id = validate_identifier(assessment_id, "assessment ID")
        return {
            "blueprint": load_json(self.storage.artifact_path(manifest, f"assessment_{assessment_id}_blueprint")),
            "assessment": load_json(self.storage.artifact_path(manifest, f"assessment_{assessment_id}_generated_assessment")),
            "duplicate_report": load_json(self.storage.artifact_path(manifest, f"assessment_{assessment_id}_duplicate_report")),
            "validation_report": load_json(self.storage.artifact_path(manifest, f"assessment_{assessment_id}_validation_report")),
            "review_decisions": load_json(self.storage.artifact_path(manifest, f"assessment_{assessment_id}_review_decisions")),
        }

    def review_assessment(self, run_id: str, assessment_id: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        assessment_id = validate_identifier(assessment_id, "assessment ID")
        current = load_json(self.storage.artifact_path(manifest, f"assessment_{assessment_id}_review_decisions"))
        assessment = load_json(self.storage.artifact_path(manifest, f"assessment_{assessment_id}_generated_assessment"))
        by_qid = {item["question_id"]: item for item in current["review_records"]}
        for item in records:
            qid = validate_identifier(str(item["question_id"]), "question ID")
            if qid not in by_qid:
                raise DashboardControllerError("unknown question ID")
            locked = bool(item.get("locked", by_qid[qid].get("locked", False)))
            by_qid[qid] = review_record(
                question_id=qid,
                decision=str(item.get("decision", "pending")),
                locked=locked,
                reviewed_at=utc_now(),
                reviewer_note=str(item.get("reviewer_note", "")),
                math_content_edited=bool(item.get("math_content_edited", False)),
                replacement_question_id=item.get("replacement_question_id"),
            )
            for question in assessment.get("questions", []):
                if question.get("question_id") == qid:
                    question["locked"] = locked
        current["review_records"] = list(by_qid.values())
        self.storage.write_json_artifact(manifest, f"assessment_{assessment_id}_review_decisions", f"assessments/{assessment_id}/review_decisions.json", current)
        self.storage.write_json_artifact(manifest, f"assessment_{assessment_id}_generated_assessment", f"assessments/{assessment_id}/generated_assessment.json", assessment)
        return current

    def regenerate(self, run_id: str, assessment_id: str, slot_id: str, child_seed: int) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        assessment_id = validate_identifier(assessment_id, "assessment ID")
        assessment = load_json(self.storage.artifact_path(manifest, f"assessment_{assessment_id}_generated_assessment"))
        blueprint = load_json(self.storage.artifact_path(manifest, f"assessment_{assessment_id}_blueprint"))
        family = self._family_for_id(next(iter(blueprint["generation_family_allocation"])))
        decisions = load_json(self.storage.artifact_path(manifest, f"assessment_{assessment_id}_review_decisions"))
        locked_ids = {item["question_id"] for item in decisions["review_records"] if item.get("locked")}
        for question in assessment["questions"]:
            if question["question_id"] in locked_ids:
                question["locked"] = True
        replacement = regenerate_question(assessment=assessment, family=family, blueprint=blueprint, slot_id=slot_id, child_seed=child_seed)
        old = next(q for q in assessment["questions"] if q["slot_id"] == slot_id)
        before_locked = {q["question_id"]: copy.deepcopy(q) for q in assessment["questions"] if q["question_id"] in locked_ids}
        assessment["questions"] = [replacement if q["slot_id"] == slot_id else q for q in assessment["questions"]]
        for qid, frozen in before_locked.items():
            assert next(q for q in assessment["questions"] if q["question_id"] == qid) == frozen
        self.storage.write_json_artifact(manifest, f"assessment_{assessment_id}_generated_assessment", f"assessments/{assessment_id}/generated_assessment.json", assessment)
        review = self.review_assessment(run_id, assessment_id, [{
            "question_id": old["question_id"],
            "decision": "regenerate",
            "replacement_question_id": replacement["question_id"],
        }])
        review["review_records"].append(review_record(question_id=replacement["question_id"], decision="pending"))
        self.storage.write_json_artifact(manifest, f"assessment_{assessment_id}_review_decisions", f"assessments/{assessment_id}/review_decisions.json", review)
        return {"replacement_question_id": replacement["question_id"], "locked_question_ids": sorted(locked_ids)}

    def export_path(self, run_id: str, assessment_id: str, export_type: str) -> Path:
        allowed = {
            "student_json": "student_assessment.json",
            "student_markdown": "student_assessment.md",
            "instructor_json": "instructor_assessment.json",
            "instructor_markdown": "instructor_assessment.md",
        }
        if export_type not in allowed:
            raise DashboardControllerError("unsupported export type")
        manifest = self.get_run(run_id)
        return self.storage.artifact_path(manifest, f"assessment_{validate_identifier(assessment_id, 'assessment ID')}_export_{allowed[export_type].replace('.', '_')}")

    def artifact(self, run_id: str, artifact_key: str) -> Any:
        manifest = self.get_run(run_id)
        path = self.storage.artifact_path(manifest, artifact_key)
        if path.suffix == ".json":
            return load_json(path)
        return path.read_text(encoding="utf-8")

    def release_gate(self, run_id: str, assessment_id: str) -> dict[str, Any]:
        data = self.get_assessment(run_id, assessment_id)
        records = data["review_decisions"]["review_records"]
        invalidated = any(item.get("validation_invalidated") for item in records)
        complete = all(item["decision"] in {"accepted", "rejected", "needs_revision", "regenerate"} for item in records)
        ready = data["validation_report"]["validation_status"] == "pass" and complete and not invalidated
        return {"release_ready": ready, "review_complete": complete, "validation_invalidated": invalidated, "noncanonical": True}

    def write_run_summary(self, run_id: str, assessment_id: str, *, source_identity: str, profile: str, regeneration: dict[str, Any]) -> None:
        manifest = self.get_run(run_id)
        data = self.get_assessment(run_id, assessment_id)
        results = self.results(run_id)
        text = "\n".join(
            [
                f"# Dashboard Acceptance Run: {run_id}",
                "",
                f"Source identity: {source_identity}",
                f"Rights status: {manifest.get('rights_status')}",
                f"Profile: {profile}",
                f"Compiler outcome: {manifest.get('compiler_status')}",
                f"Topics: {', '.join(t.get('topic_code', '') for t in results['topics'])}",
                f"Micro-skills: {', '.join(s.get('micro_skill_code', '') for s in results['micro_skills'])}",
                f"Assessment family: {data['assessment']['generation_family_ids'][0]}",
                f"Question count: {len(data['assessment']['questions'])}",
                "Review outcomes: local review decisions persisted",
                f"Regeneration outcome: {regeneration.get('replacement_question_id')}",
                f"Locked-question preservation: {bool(regeneration.get('locked_question_ids'))}",
                f"Validation outcome: {data['validation_report']['validation_status']}",
                "Export outcome: student and instructor exports generated",
                "Non-live boundary: noncanonical, student_visible false, eligible_for_alpha_import false",
                "Known limitations: local compiler proof only; no deployment, DB contact, Alpha write, or student publication.",
            ]
        ) + "\n"
        self.storage.write_text_artifact(manifest, "run_summary", "run_summary.md", text)

    def _artifact_or_empty(self, manifest: dict[str, Any], key: str, payload_key: str | None) -> Any:
        try:
            data = load_json(self.storage.artifact_path(manifest, key))
        except Exception:
            return [] if payload_key else {}
        return data.get(payload_key, data) if payload_key else data

    def _family_for_id(self, family_id: str) -> dict[str, Any]:
        family_id = validate_identifier(family_id, "generation family ID")
        for path in FAMILY_DIR.glob("*.json"):
            family = load_family(path)
            if family["generation_family_id"] == family_id:
                return family
        raise DashboardControllerError("unknown generation family")

    def _public_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in manifest.items() if key != "artifact_index"} | {"artifact_keys": sorted(manifest.get("artifact_index", {}))}

    def _scrub_local_paths(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._scrub_local_paths(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._scrub_local_paths(item) for item in value]
        if isinstance(value, str):
            try:
                path = Path(value)
                if path.is_absolute() and path.resolve().is_relative_to(SOURCE_INBOX_ROOT):
                    return f"external_source_inbox:{path.name}"
            except Exception:
                pass
        return value
