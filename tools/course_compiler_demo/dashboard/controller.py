"""Controller layer for the local operator dashboard."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

from tools.course_compiler_demo.assessment_generation.blueprint import validate_blueprint
from tools.course_compiler_demo.assessment_generation.exporters import write_exports
from tools.course_compiler_demo.assessment_generation.family_loader import load_family
from tools.course_compiler_demo.assessment_generation.generator import generate_assessment, regenerate_question
from tools.course_compiler_demo.assessment_generation.storage import load_historical_fingerprints, write_assessment_run
from tools.course_compiler_demo.assessment_generation.validators import review_record
from tools.course_compiler_demo.ingest.document_classifier import classify_document, detect_math_course_level, detect_subject
from tools.course_compiler_demo.ingest.input_loader import SUPPORTED_INPUT_FORMATS
from tools.course_compiler_demo.profiles.subject_profile_loader import build_profile_run, load_profile

from .calculus_generation import (
    CALCULUS_FAMILY_ID,
    CALCULUS_REQUIRED_SKILLS,
    calculus_family,
    generate_calculus_assessment,
    practice_package,
    procedure_candidates,
    regenerate_calculus_question,
    write_calculus_assessment,
)
from .limits import pdf_limit_snapshot
from .pdf_intake import DashboardPdfIntakeError, extract_text_native_pdf
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
            families.append(self._public_family(family))
        families.append(self._public_family(calculus_family()))
        return families

    def compatible_generation_families(self, run_id: str) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        topics, skills, _gaps = self._curriculum_results(manifest)
        compatible = [
            self._public_family(family)
            for family in self._all_families()
            if self._family_is_compatible_with_run(family, manifest, topics, skills)
        ]
        return {
            "generation_families": compatible,
            "content_gap": None
            if compatible
            else "No compatible assessment generation family is available for the accepted curriculum. Assessment generation remains a content gap.",
            "detected_subject": manifest.get("detected_subject"),
            "detected_course_level": manifest.get("detected_course_level"),
        }

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
        retain_source = bool(metadata.get("retain_normalized_source", False))
        pdf_provenance: dict[str, Any] = {}
        rights_status = metadata.get("rights_status", "rights_review_required")
        privacy_status = metadata.get("privacy_status", "privacy_review_required")
        profile_id = self._profile_from_metadata(metadata, manifest)
        if source_format == "pdf":
            try:
                pdf_result = extract_text_native_pdf(display, content, retain_extracted_text=retain_source)
            except DashboardPdfIntakeError as exc:
                manifest["status"] = "source_ready" if manifest.get("source_display_filename") else "created"
                manifest["last_error"] = str(exc)
                self.storage.save_manifest(manifest)
                raise
            source_text = pdf_result.text
            source_hash = pdf_result.provenance["original_pdf_sha256"]
            pdf_provenance = pdf_result.provenance
            pdf_provenance["rights_status"] = rights_status
            pdf_provenance["privacy_status"] = privacy_status
        else:
            source_text = content.decode("utf-8")
            source_hash = sha256_bytes(content)
        classification = self._dashboard_classification(source_text, source_format=source_format)
        subject = self._detect_dashboard_subject(source_text, profile_id=profile_id)
        receipt = {
            "source_title": str(metadata.get("source_title") or manifest.get("source_title") or display),
            "source_display_filename": display,
            "source_sha256": source_hash,
            "source_format": source_format,
            "document_type": metadata.get("document_type", classification["detected_source_type"]),
            "author_or_institution": metadata.get("author_or_institution", ""),
            "rights_status": rights_status,
            "privacy_status": privacy_status,
            "optional_source_reference": metadata.get("optional_source_reference", ""),
            "rights_confirmed": False,
            "detected_subject": subject["detected_subject"],
            "subject_confidence": subject["subject_confidence"],
            "classification": classification,
            "raw_or_normalized_source_retained": retain_source,
            "ocr_used": False,
            "external_service_used": False,
        }
        if pdf_provenance:
            receipt["pdf_provenance"] = pdf_provenance
            receipt["source_sha256"] = pdf_provenance["original_pdf_sha256"]
            receipt["extracted_text_sha256"] = pdf_provenance["extracted_text_sha256"]
            receipt["raw_pdf_retained"] = False
            receipt["extracted_text_retained"] = pdf_provenance["extracted_text_retained"]
        manifest.update(
            {
                "status": "source_ready",
                "source_title": receipt["source_title"],
                "source_display_filename": display,
                "source_sha256": source_hash,
                "source_format": source_format,
                "source_file_size_bytes": len(content),
                "rights_status": receipt["rights_status"],
                "privacy_status": receipt["privacy_status"],
                "raw_or_normalized_source_retained": receipt["raw_or_normalized_source_retained"],
                "selected_profile_id": profile_id,
                "profile_alignment_status": "auto_detect_pending" if not profile_id else "manual_profile_pending",
                "profile_alignment_warning": None,
                "detected_subject": receipt["detected_subject"],
                "pdf_validation": pdf_provenance if pdf_provenance else None,
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
        if manifest["status"] not in {"source_ready", "source_uploaded", "rights_confirmed", "profile_selected", "failed"}:
            raise DashboardControllerError("source must be uploaded before rights confirmation")
        manifest["rights_status"] = str(payload.get("rights_status", manifest.get("rights_status") or "confirmed_local_use"))
        manifest["privacy_status"] = str(payload.get("privacy_status", manifest.get("privacy_status") or "non_private"))
        manifest["status"] = "source_ready"
        pdf_validation = manifest.get("pdf_validation")
        if isinstance(pdf_validation, dict):
            pdf_validation["rights_status"] = manifest["rights_status"]
            pdf_validation["privacy_status"] = manifest["privacy_status"]
            manifest["pdf_validation"] = pdf_validation
        receipt = load_json(self.storage.artifact_path(manifest, "source_receipt"))
        receipt.update({"rights_confirmed": True, "rights_status": manifest["rights_status"], "privacy_status": manifest["privacy_status"]})
        pdf_provenance = receipt.get("pdf_provenance")
        if isinstance(pdf_provenance, dict):
            pdf_provenance["rights_status"] = manifest["rights_status"]
            pdf_provenance["privacy_status"] = manifest["privacy_status"]
            receipt["pdf_provenance"] = pdf_provenance
        self.storage.write_json_artifact(manifest, "source_receipt", "source/source_receipt.json", receipt)
        self.storage.save_manifest(manifest)
        return self.get_run(run_id)

    def select_profile(self, run_id: str, profile_id: str) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        if manifest["status"] not in {"source_ready", "source_uploaded", "rights_confirmed", "profile_selected", "compiled", "failed", "compiler_failed"}:
            raise DashboardControllerError("source must be uploaded before profile selection")
        profile_id = validate_identifier(profile_id, "profile ID")
        registered = {item["profile_id"] for item in self.list_profiles()}
        if profile_id not in registered:
            raise DashboardControllerError("profile is not registered")
        manifest["selected_profile_id"] = profile_id
        manifest["profile_alignment_status"] = "manual_profile_pending"
        manifest["profile_alignment_warning"] = None
        manifest["status"] = "source_ready"
        self.storage.save_manifest(manifest)
        return self.get_run(run_id)

    def compile_run(self, run_id: str, *, selected_micro_skill: str | None = None) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        if not self._ready_to_compile(manifest):
            raise DashboardControllerError("source upload, rights, privacy, and persisted source-ready state are required before compilation")
        manifest["status"] = "compiling"
        manifest["compiler_status"] = "running"
        manifest["last_error"] = None
        self.storage.save_manifest(manifest)
        try:
            profile_id = manifest.get("selected_profile_id")
            if profile_id == "PHYSICS_INTRO_MECHANICS_PROFILE_V1" and self._profile_is_compatible(manifest, "PHYSICS"):
                self._compile_physics(manifest, selected_micro_skill or "apply_newtons_second_law_1d")
            elif profile_id == "STATICS_VECTOR_COMPONENTS_RELEASE_PROFILE_V1" and self._profile_is_compatible(manifest, "STATICS"):
                self._compile_statics(manifest)
            elif profile_id and profile_id in {item["profile_id"] for item in self.list_profiles()}:
                self._compile_document_first(manifest, profile_alignment_status="conflict_warning")
            else:
                self._compile_document_first(manifest, profile_alignment_status="candidate_new")
            manifest = self.get_run(run_id)
            self._require_curriculum_results(manifest)
            topics, skills, _gaps = self._curriculum_results(manifest)
            manifest["status"] = "compiled"
            manifest["compiler_status"] = "complete"
            manifest["curriculum_summary"] = {
                "topic_count": len(topics),
                "micro_skill_count": len(skills),
                "review_required": True,
            }
            manifest["topic_count"] = len(topics)
            manifest["micro_skill_count"] = len(skills)
            manifest["release_status"] = "review_required"
            manifest["review_required"] = True
            manifest["last_error"] = None
        except Exception as exc:
            manifest["status"] = "failed"
            manifest["compiler_status"] = "failed"
            manifest["last_error"] = str(exc)
        finally:
            if manifest.get("source_format") == "pdf" and not manifest.get("raw_or_normalized_source_retained"):
                self._source_text_cache.pop(run_id, None)
        self.storage.save_manifest(manifest)
        return self.get_run(run_id)

    def _profile_from_metadata(self, metadata: dict[str, Any], manifest: dict[str, Any]) -> str:
        profile_id = str(metadata.get("profile_id") or metadata.get("selected_profile_id") or manifest.get("selected_profile_id") or "")
        if not profile_id:
            return ""
        profile_id = validate_identifier(profile_id, "profile ID")
        registered = {item["profile_id"] for item in self.list_profiles()}
        if profile_id not in registered:
            raise DashboardControllerError("profile is not registered")
        return profile_id

    def _ready_to_compile(self, manifest: dict[str, Any]) -> bool:
        rights_status = str(manifest.get("rights_status") or "")
        privacy_status = str(manifest.get("privacy_status") or "")
        return (
            manifest.get("status") == "source_ready"
            and bool(manifest.get("source_display_filename"))
            and bool(manifest.get("source_sha256"))
            and bool(manifest.get("source_format"))
            and rights_status in {"approved_local_use", "owned_by_axiomiq"}
            and privacy_status == "non_private"
        )

    def _profile_is_compatible(self, manifest: dict[str, Any], expected_subject: str) -> bool:
        detected = str(manifest.get("detected_subject") or "").upper()
        return detected in {"", "UNKNOWN", expected_subject}

    def _detect_dashboard_subject(self, source_text: str, *, profile_id: str = "") -> dict[str, str]:
        if profile_id == "PHYSICS_INTRO_MECHANICS_PROFILE_V1" and re.search(r"\b(physics|newton|force|acceleration|mechanics)\b", source_text, re.I):
            return {"detected_subject": "PHYSICS", "subject_confidence": "profile_hint_high"}
        if profile_id == "STATICS_VECTOR_COMPONENTS_RELEASE_PROFILE_V1" and re.search(r"\b(statics|force|vector|component|equilibrium)\b", source_text, re.I):
            return {"detected_subject": "STATICS", "subject_confidence": "profile_hint_high"}
        math_level = detect_math_course_level(source_text)
        if math_level["detected_course_level"] != "UNKNOWN_MATH_LEVEL":
            return {"detected_subject": "MATHEMATICS", "subject_confidence": math_level["course_level_confidence"]}
        return detect_subject(source_text)

    def _dashboard_classification(self, source_text: str, *, source_format: str) -> dict[str, Any]:
        classification = classify_document(source_text)
        if classification["detected_source_type"] != "unknown":
            return classification
        if source_format == "pdf" and re.search(r"limit|derivative|calculus|problem|exercise|review", source_text, re.I):
            return {
                "detected_source_type": "instructional_pdf",
                "source_type_confidence": "medium",
                "classification_evidence": ["Dashboard-local fallback detected instructional PDF language."],
            }
        return classification

    def _dashboard_course_level(self, source_text: str, subject: str) -> tuple[str, str]:
        if subject == "MATHEMATICS":
            math_level = detect_math_course_level(source_text)
            return math_level["detected_course_level"], math_level["course_level_confidence"]
        if subject == "PHYSICS":
            return "INTRO_PHYSICS_MECHANICS", "medium"
        if subject == "STATICS":
            return "ENGINEERING_MECHANICS_STATICS", "medium"
        return "UNKNOWN_COURSE_LEVEL", "low"

    def _compile_document_first(self, manifest: dict[str, Any], *, profile_alignment_status: str) -> None:
        source_text, source_path = self._source_text_for_run(manifest)
        classification = self._dashboard_classification(source_text, source_format=str(manifest.get("source_format") or ""))
        subject = self._detect_dashboard_subject(source_text, profile_id=str(manifest.get("selected_profile_id") or ""))
        course_level, course_confidence = self._dashboard_course_level(source_text, subject["detected_subject"])
        topics, skills, evidence = self._dashboard_extract_candidates(
            source_text,
            subject=subject["detected_subject"],
            course_level=course_level,
        )
        gaps = self._dashboard_content_gaps(topics, skills, subject["detected_subject"], course_level)
        source_id = f"SOURCE_{manifest['run_id']}"
        profile_id = manifest.get("selected_profile_id") or ""
        alignment_warning = None
        if profile_alignment_status == "conflict_warning":
            alignment_warning = (
                f"Selected profile {profile_id} does not match detected subject "
                f"{subject['detected_subject']}; extraction continued without profile blocking."
            )
        elif profile_alignment_status == "candidate_new":
            alignment_warning = "No compatible existing profile was required for extraction; candidates require review."

        self.storage.write_json_artifact(manifest, "source_document", "compiler/source_document.json", {
            "source_id": source_id,
            "source_title": manifest.get("source_title") or source_path.name,
            "source_filename": manifest.get("source_display_filename"),
            "source_type": classification["detected_source_type"],
            "source_scale": "local_dashboard_upload",
            "source_sha256": manifest.get("source_sha256"),
            "rights_status": manifest.get("rights_status"),
            "privacy_status": manifest.get("privacy_status"),
            "status": "demo_unverified",
            "noncanonical": True,
            "student_visible": False,
        })
        self.storage.write_json_artifact(manifest, "source_interpretation", "compiler/source_interpretation.json", {
            "detected_document_type": classification["detected_source_type"],
            "document_type_confidence": classification["source_type_confidence"],
            "detected_subject": subject["detected_subject"],
            "subject_confidence": subject["subject_confidence"],
            "detected_course_level": course_level,
            "course_level_confidence": course_confidence,
            "profile_alignment_status": profile_alignment_status,
            "profile_alignment_warning": alignment_warning,
            "extraction_rationale": "Dashboard-local rule-based document-first interpretation.",
            "status": "demo_unverified",
            "noncanonical": True,
            "student_visible": False,
        })
        self.storage.write_json_artifact(manifest, "source_feature_flags", "compiler/source_feature_flags.json", {
            "contains_formula": bool(re.search(r"[=∫]|derivative|limit|critical point|force|vector", source_text, re.I)),
            "contains_practice_items": bool(re.search(r"problem|exercise|example|find|evaluate|apply|analy", source_text, re.I)),
            "profile_required_for_extraction": False,
            "selected_profile_id": profile_id or None,
            "status": "demo_unverified",
        })
        self.storage.write_json_artifact(manifest, "topic_candidates", "compiler/topic_candidates.json", {
            "status": "demo_unverified",
            "topic_candidates": topics,
        })
        self.storage.write_json_artifact(manifest, "micro_skill_candidates", "compiler/micro_skill_candidates.json", {
            "status": "demo_unverified",
            "micro_skill_candidates": skills,
        })
        self.storage.write_json_artifact(manifest, "practice_targets", "compiler/practice_targets.json", {
            "status": "demo_unverified",
            "practice_target_candidates": self._dashboard_practice_targets(topics, skills),
        })
        procedures = procedure_candidates() if subject["detected_subject"] == "MATHEMATICS" and course_level == "CALCULUS_I" else []
        self.storage.write_json_artifact(manifest, "procedure_candidates", "compiler/procedure_candidates.json", {
            "status": "demo_unverified",
            "procedure_candidates": procedures,
        })
        assessment_targets = self._dashboard_assessment_targets(topics, skills)
        compatible_family_ids = [
            family["generation_family_id"]
            for family in self._all_families()
            if self._family_is_compatible_with_run(family, manifest, topics, skills)
        ]
        for target in assessment_targets:
            target["compatible_generation_family_ids"] = compatible_family_ids
            target["assessment_potential"] = "available" if compatible_family_ids else "content_gap"
            if not compatible_family_ids:
                target["content_gap"] = "No compatible assessment generation family is available for the accepted curriculum. Assessment generation remains a content gap."
        self.storage.write_json_artifact(manifest, "assessment_targets", "compiler/assessment_targets.json", {
            "status": "demo_unverified",
            "assessment_target_candidates": assessment_targets,
        })
        self.storage.write_json_artifact(manifest, "content_gaps", "compiler/content_gaps.json", {
            "status": "demo_unverified",
            "content_gaps": gaps,
        })
        self.storage.write_json_artifact(manifest, "curriculum_extraction_package", "compiler/curriculum_extraction_package.json", {
            "package_id": f"DASHBOARD_EXTRACT_{manifest['run_id']}",
            "status": "demo_unverified",
            "detected_document_type": classification["detected_source_type"],
            "detected_subject": subject["detected_subject"],
            "detected_course_level": course_level,
            "topic_candidates": topics,
            "micro_skill_candidates": skills,
            "procedure_candidates": procedures,
            "practice_target_candidates": self._dashboard_practice_targets(topics, skills),
            "assessment_target_candidates": self._dashboard_assessment_targets(topics, skills),
            "content_gaps": gaps,
            "source_evidence": evidence,
            "profile_alignment_status": profile_alignment_status,
            "profile_alignment_warning": alignment_warning,
            "review_required": True,
            "noncanonical": True,
            "student_visible": False,
        })
        manifest["detected_subject"] = subject["detected_subject"]
        manifest["detected_course_level"] = course_level
        manifest["document_type"] = classification["detected_source_type"]
        manifest["document_type_confidence"] = classification["source_type_confidence"]
        manifest["subject_confidence"] = subject["subject_confidence"]
        manifest["course_level_confidence"] = course_confidence
        manifest["profile_alignment_status"] = profile_alignment_status
        manifest["profile_alignment_warning"] = alignment_warning
        manifest["practice_potential"] = "available" if skills else "review_required"
        manifest["assessment_potential"] = "available" if compatible_family_ids else "content_gap"
        manifest["assessment_content_gap"] = None if compatible_family_ids else "No compatible assessment generation family is available for the accepted curriculum. Assessment generation remains a content gap."
        manifest["review_required"] = True
        manifest["all_outputs_demo_unverified"] = True
        manifest["student_visible"] = False
        self.storage.save_manifest(manifest)

    def _dashboard_extract_candidates(
        self,
        source_text: str,
        *,
        subject: str,
        course_level: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        rules = self._dashboard_candidate_rules(subject)
        topics: list[dict[str, Any]] = []
        skills: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        topic_id_by_name: dict[str, str] = {}
        for topic_name, terms in rules["topics"]:
            if not self._text_matches(source_text, terms):
                continue
            topic_id = f"TOPIC_{len(topics) + 1:03d}"
            topic_id_by_name[topic_name] = topic_id
            evidence_id = f"EV_TOPIC_{len(evidence) + 1:03d}"
            evidence.append(self._evidence_record(evidence_id, source_text, terms, topic_name))
            topics.append({
                "candidate_id": topic_id,
                "topic_code": self._candidate_code(topic_name),
                "topic_name": topic_name,
                "subject_candidate": subject,
                "course_level_candidate": course_level,
                "confidence": "high",
                "evidence_refs": [evidence_id],
                "alignment_status": "uncertain_mapping",
                "status": "demo_unverified",
                "noncanonical": True,
                "student_visible": False,
            })
        for skill_name, topic_name, terms in rules["skills"]:
            if topic_name not in topic_id_by_name or not self._text_matches(source_text, terms):
                continue
            skill_id = f"MSKILL_{len(skills) + 1:03d}"
            evidence_id = f"EV_SKILL_{len(evidence) + 1:03d}"
            evidence.append(self._evidence_record(evidence_id, source_text, terms, skill_name))
            skills.append({
                "candidate_id": skill_id,
                "micro_skill_code": self._candidate_code(skill_name),
                "micro_skill_name": skill_name,
                "micro_skill_description": f"Candidate micro-skill detected for {topic_name}.",
                "parent_topic_candidate_id": topic_id_by_name[topic_name],
                "subject_candidate": subject,
                "course_level_candidate": course_level,
                "confidence": "high",
                "evidence_refs": [evidence_id],
                "alignment_status": "uncertain_mapping",
                "status": "demo_unverified",
                "noncanonical": True,
                "student_visible": False,
            })
        if not topics:
            topics.append({
                "candidate_id": "TOPIC_001",
                "topic_code": "review_required_topic",
                "topic_name": "Review Required Topic",
                "subject_candidate": subject,
                "course_level_candidate": course_level,
                "confidence": "low",
                "evidence_refs": [],
                "alignment_status": "review_required",
                "status": "demo_unverified",
                "noncanonical": True,
                "student_visible": False,
            })
        if not skills:
            skills.append({
                "candidate_id": "MSKILL_001",
                "micro_skill_code": "review_required_micro_skill",
                "micro_skill_name": "Review Required Micro-skill",
                "micro_skill_description": "Generic candidate retained so unknown sources do not fail initial extraction.",
                "parent_topic_candidate_id": topics[0]["candidate_id"],
                "subject_candidate": subject,
                "course_level_candidate": course_level,
                "confidence": "low",
                "evidence_refs": [],
                "alignment_status": "review_required",
                "status": "demo_unverified",
                "noncanonical": True,
                "student_visible": False,
            })
        return topics, skills, evidence

    def _dashboard_candidate_rules(self, subject: str) -> dict[str, list[Any]]:
        if subject == "MATHEMATICS":
            return {
                "topics": [
                    ("Limits", ["limit", "limits"]),
                    ("Derivatives", ["derivative", "derivatives", "power rule", "chain rule"]),
                    ("Applications of Derivatives", ["critical point", "critical points", "increasing", "decreasing", "optimization"]),
                ],
                "skills": [
                    ("Evaluate a Limit", "Limits", ["evaluate a limit", "limit", "limits"]),
                    ("Apply the Power Rule", "Derivatives", ["power rule"]),
                    ("Apply the Chain Rule", "Derivatives", ["chain rule"]),
                    ("Find Critical Points", "Applications of Derivatives", ["critical point", "critical points"]),
                    ("Analyze Increasing and Decreasing Intervals", "Applications of Derivatives", ["increasing", "decreasing"]),
                ],
            }
        if subject == "PHYSICS":
            return {
                "topics": [("Forces and Motion", ["force", "newton", "acceleration"])],
                "skills": [("Apply Newton's Second Law", "Forces and Motion", ["newton", "f net", "acceleration"])],
            }
        return {
            "topics": [("Source-Aligned Concepts", ["subject", "topic", "concept", "example", "problem"])],
            "skills": [("Review Source-Aligned Skill", "Source-Aligned Concepts", ["practice", "problem", "find", "apply", "evaluate"])],
        }

    def _text_matches(self, source_text: str, terms: list[str]) -> bool:
        lowered = source_text.lower()
        return any(term.lower() in lowered for term in terms)

    def _candidate_code(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")

    def _evidence_record(self, evidence_id: str, source_text: str, terms: list[str], label: str) -> dict[str, Any]:
        lowered = source_text.lower()
        for term in terms:
            index = lowered.find(term.lower())
            if index >= 0:
                start = max(0, index - 80)
                end = min(len(source_text), index + len(term) + 80)
                return {
                    "evidence_id": evidence_id,
                    "evidence_type": "dashboard_rule_match",
                    "matched_label": label,
                    "matched_term": term,
                    "short_excerpt": source_text[start:end].replace("\n", " ").strip(),
                    "confidence": "high",
                    "status": "demo_unverified",
                }
        return {
            "evidence_id": evidence_id,
            "evidence_type": "dashboard_rule_match",
            "matched_label": label,
            "matched_term": terms[0] if terms else "",
            "short_excerpt": "",
            "confidence": "medium",
            "status": "demo_unverified",
        }

    def _dashboard_practice_targets(self, topics: list[dict[str, Any]], skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{
            "candidate_id": "PRACTICE_TARGET_001",
            "target_type": "demo_practice_module",
            "target_topic_candidate_ids": [topic["candidate_id"] for topic in topics],
            "target_micro_skill_candidate_ids": [skill["candidate_id"] for skill in skills],
            "practice_potential": "available" if skills else "review_required",
            "status": "demo_unverified",
            "student_visible": False,
        }]

    def _dashboard_assessment_targets(self, topics: list[dict[str, Any]], skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{
            "candidate_id": "ASSESSMENT_TARGET_001",
            "assessment_type": "demo_readiness_check",
            "covered_topic_candidate_ids": [topic["candidate_id"] for topic in topics],
            "covered_micro_skill_candidate_ids": [skill["candidate_id"] for skill in skills],
            "assessment_potential": "available" if skills else "review_required",
            "status": "demo_unverified",
            "student_visible": False,
        }]

    def _dashboard_content_gaps(
        self,
        topics: list[dict[str, Any]],
        skills: list[dict[str, Any]],
        subject: str,
        course_level: str,
    ) -> list[dict[str, Any]]:
        gaps = [{
            "gap_id": "GAP_REVIEW_REQUIRED",
            "severity": "review_required",
            "description": "Candidates are dashboard-local, demo-unverified, and require human curriculum review before use.",
            "status": "demo_unverified",
        }]
        if subject == "UNKNOWN" or course_level.startswith("UNKNOWN"):
            gaps.append({
                "gap_id": "GAP_UNKNOWN_CLASSIFICATION",
                "severity": "warning",
                "description": "Subject or course level could not be confidently classified; generic candidates were retained for review.",
                "status": "demo_unverified",
            })
        if not topics or not skills:
            gaps.append({
                "gap_id": "GAP_LOW_CANDIDATE_SIGNAL",
                "severity": "warning",
                "description": "Few source-aligned candidates were detected; operator review is required.",
                "status": "demo_unverified",
            })
        return gaps

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
        self.storage.save_manifest(manifest)

    def _compile_statics(self, manifest: dict[str, Any]) -> None:
        package = load_json(STATICS_RELEASE_PACKAGE)
        manifest["detected_subject"] = "STATICS"
        manifest["detected_course_level"] = "ENGINEERING_MECHANICS_STATICS"
        self.storage.save_manifest(manifest)
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
        topics, skills, gaps = self._curriculum_results(manifest)
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

    def compile_summary(self, run_id: str) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        topics, skills, gaps = self._curriculum_results(manifest)
        try:
            receipt = load_json(self.storage.artifact_path(manifest, "source_receipt"))
        except Exception:
            receipt = {}
        package = self._artifact_or_empty(manifest, "curriculum_extraction_package", None)
        topic_items = [
            {
                "candidate_id": topic.get("candidate_id", ""),
                "code": topic.get("topic_code", ""),
                "name": topic.get("topic_name") or topic.get("topic_code", ""),
                "status": topic.get("status", ""),
            }
            for topic in topics
        ]
        micro_skill_items = [
            {
                "candidate_id": skill.get("candidate_id", ""),
                "code": skill.get("micro_skill_code", ""),
                "name": skill.get("micro_skill_name") or skill.get("micro_skill_code", ""),
                "status": skill.get("status", ""),
            }
            for skill in skills
        ]
        content_gap_items = [
            {
                "gap_id": gap.get("gap_id", ""),
                "severity": gap.get("severity", ""),
                "description": gap.get("description", ""),
            }
            for gap in gaps
        ]
        normalized_source_exists = "normalized_source" in manifest.get("artifact_index", {})
        pdf_validation = manifest.get("pdf_validation") or {}
        curriculum_ready = manifest.get("compiler_status") == "complete" and bool(topic_items) and bool(micro_skill_items)
        return {
            "status": "compilation_complete" if curriculum_ready else "compilation_blocked",
            "operator_message": "Compilation complete" if curriculum_ready else "Compilation did not produce usable curriculum results",
            "run_id": manifest["run_id"],
            "source_title": manifest.get("source_title", ""),
            "source_display_filename": manifest.get("source_display_filename", ""),
            "document_type": manifest.get("document_type") or package.get("detected_document_type", "") if isinstance(package, dict) else receipt.get("document_type", ""),
            "detected_subject": manifest.get("detected_subject", ""),
            "detected_course_level": manifest.get("detected_course_level", ""),
            "selected_profile_id": manifest.get("selected_profile_id", ""),
            "profile_alignment_status": manifest.get("profile_alignment_status", "review_required"),
            "profile_alignment_warning": manifest.get("profile_alignment_warning"),
            "practice_potential": manifest.get("practice_potential", "review_required"),
            "assessment_potential": manifest.get("assessment_potential", "review_required"),
            "topic_count": len(topic_items),
            "topics": topic_items,
            "micro_skill_count": len(micro_skill_items),
            "micro_skills": micro_skill_items,
            "content_gap_count": len(content_gap_items),
            "content_gaps": content_gap_items,
            "review_status": manifest.get("curriculum_review_status", "pending"),
            "release_status": manifest.get("release_status", "not_ready"),
            "retention": {
                "raw_pdf_retained": bool(pdf_validation.get("raw_pdf_retained", False)),
                "extracted_text_retained": bool(pdf_validation.get("extracted_text_retained", normalized_source_exists)),
                "normalized_source_retained": normalized_source_exists,
            },
            "pdf_validation": {
                "file_size_bytes": pdf_validation.get("file_size_bytes"),
                "page_count": pdf_validation.get("page_count"),
                "processed_page_count": pdf_validation.get("processed_page_count"),
                "pages_containing_text": pdf_validation.get("pages_containing_text"),
                "source_sha256": pdf_validation.get("original_pdf_sha256"),
                "extracted_text_sha256": pdf_validation.get("extracted_text_sha256"),
                "processing_duration_seconds": pdf_validation.get("processing_duration_seconds"),
                "applied_resource_limits": pdf_validation.get("applied_resource_limits", pdf_limit_snapshot()),
            },
            "compatible_generation_families": self.compatible_generation_families(run_id)["generation_families"],
            "assessment_content_gap": manifest.get("assessment_content_gap"),
            "persistence": {
                "run_saved_to_dashboard_history": self.storage.run_dir(manifest["run_id"]).exists(),
                "manifest_saved": (self.storage.run_dir(manifest["run_id"]) / "run_manifest.json").exists(),
                "source_metadata_saved": "source_receipt" in manifest.get("artifact_index", {}),
                "compiler_outputs_saved": all(
                    key in manifest.get("artifact_index", {})
                    for key in ["topic_candidates", "micro_skill_candidates", "content_gaps"]
                ),
            },
            "next_steps": [
                "Review Curriculum",
                "Save Review Decisions",
                "Configure Assessment",
                "Generate Questions",
            ],
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

    def generate_practice(self, run_id: str) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        accepted = self._accepted_micro_skill_codes(manifest)
        compatible = [skill for skill in CALCULUS_REQUIRED_SKILLS if skill in accepted]
        if not compatible:
            raise DashboardControllerError("no compatible accepted Calculus micro-skills for practice")
        package = practice_package(run_id, compatible)
        self.storage.write_json_artifact(manifest, "practice_package", "practice/calculus_i_foundations_practice.json", package)
        manifest = self.get_run(run_id)
        manifest["practice_package_id"] = package["practice_package_id"]
        manifest["practice_item_count"] = package["practice_item_count"]
        self.storage.save_manifest(manifest)
        return package

    def create_assessment(self, run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        if not self._assessment_configuration_ready(manifest):
            raise DashboardControllerError("save curriculum review decisions before configuring an assessment")
        family = self._family_for_id(str(payload["generation_family_id"]))
        topics, skills, _gaps = self._curriculum_results(manifest)
        if not self._family_is_compatible_with_run(family, manifest, topics, skills):
            manifest["last_error"] = "incompatible_assessment_generation_family"
            self.storage.save_manifest(manifest)
            raise DashboardControllerError("incompatible_assessment_generation_family")
        assessment_id = validate_identifier(str(payload.get("assessment_id") or f"ASSESS_{family['target_micro_skill_code'].upper()}"), "assessment ID")
        count = int(payload.get("question_count", 10))
        difficulty = payload.get("difficulty_distribution") or (
            {"foundational": 4, "standard": 3, "advanced": 3}
            if family["generation_family_id"] == CALCULUS_FAMILY_ID
            else {"foundational": 3, "standard": 4, "advanced": 3}
        )
        question_types = payload.get("question_type_distribution") or {family["question_types"][0]: count}
        selected_skills = (
            [skill for skill in CALCULUS_REQUIRED_SKILLS if skill in self._accepted_micro_skill_codes(manifest)]
            if family["generation_family_id"] == CALCULUS_FAMILY_ID
            else [family["target_micro_skill_code"]]
        )
        selected_topics = (
            sorted({PROCEDURES["topic_code"] for PROCEDURES in procedure_candidates() if PROCEDURES["micro_skill_code"] in selected_skills})
            if family["generation_family_id"] == CALCULUS_FAMILY_ID
            else [family["topic_code"]]
        )
        approved_procedures = (
            [item["procedure_id"] for item in procedure_candidates() if item["micro_skill_code"] in selected_skills]
            if family["generation_family_id"] == CALCULUS_FAMILY_ID
            else [family["approved_procedure_code"]]
        )
        blueprint = {
            "assessment_id": assessment_id,
            "contract_version": "assessment_generation_contract_v1",
            "title": str(payload.get("title", f"{family['target_micro_skill_code']} Assessment")),
            "assessment_type": payload.get("assessment_type", "practice_set"),
            "subject_code": family["subject_code"],
            "course_profile": manifest.get("selected_profile_id") or "dashboard_profile",
            "selected_topic_codes": selected_topics,
            "selected_micro_skill_codes": selected_skills,
            "question_count": count,
            "difficulty_distribution": difficulty,
            "question_type_distribution": question_types,
            "generation_family_allocation": {
                family["generation_family_id"]: {
                    "question_count": count,
                    "approved_procedure_codes": approved_procedures,
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
        if family_id == CALCULUS_FAMILY_ID:
            assessment, duplicate_report, decisions = generate_calculus_assessment(blueprint, self._accepted_micro_skill_codes(manifest))
            output_dir = self.storage.run_dir(run_id) / "assessments" / assessment_id
            write_calculus_assessment(output_dir, blueprint, assessment, duplicate_report, decisions)
            for name in ["generation_manifest", "generated_assessment", "duplicate_report", "validation_report", "review_decisions"]:
                manifest.setdefault("artifact_index", {})[f"assessment_{assessment_id}_{name}"] = f"assessments/{assessment_id}/{name}.json"
            for export in ["student_assessment.json", "instructor_assessment.json", "student_assessment.md", "instructor_assessment.md"]:
                key = f"assessment_{assessment_id}_export_{export.replace('.', '_')}"
                manifest["artifact_index"][key] = f"assessments/{assessment_id}/exports/{export}"
            manifest["status"] = "assessment_review_pending"
            self.storage.save_manifest(manifest)
            return self.get_assessment(run_id, assessment_id)
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
        self._invalidate_assessment_exports(run_id, assessment_id)
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
        if family["generation_family_id"] == CALCULUS_FAMILY_ID:
            replacement = regenerate_calculus_question(assessment, blueprint, slot_id, child_seed)
        else:
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
        self._invalidate_assessment_exports(run_id, assessment_id)
        return {"replacement_question_id": replacement["question_id"], "locked_question_ids": sorted(locked_ids)}

    def export_path(self, run_id: str, assessment_id: str, export_type: str) -> Path:
        if export_type not in self._export_filenames():
            raise DashboardControllerError("unsupported export type")
        manifest = self._refresh_assessment_exports(run_id, assessment_id)
        filename = self._export_filenames()[export_type]
        return self.storage.artifact_path(manifest, self._export_artifact_key(validate_identifier(assessment_id, "assessment ID"), filename))

    def _export_filenames(self) -> dict[str, str]:
        return {
            "student_json": "student_assessment.json",
            "student_markdown": "student_assessment.md",
            "instructor_json": "instructor_assessment.json",
            "instructor_markdown": "instructor_assessment.md",
        }

    def _export_artifact_key(self, assessment_id: str, filename: str) -> str:
        return f"assessment_{assessment_id}_export_{filename.replace('.', '_')}"

    def _invalidate_assessment_exports(self, run_id: str, assessment_id: str) -> None:
        manifest = self.get_run(run_id)
        assessment_id = validate_identifier(assessment_id, "assessment ID")
        changed = False
        for filename in self._export_filenames().values():
            key = self._export_artifact_key(assessment_id, filename)
            if key in manifest.get("artifact_index", {}):
                manifest["artifact_index"].pop(key, None)
                changed = True
        if changed:
            self.storage.save_manifest(manifest)

    def _refresh_assessment_exports(self, run_id: str, assessment_id: str) -> dict[str, Any]:
        manifest = self.get_run(run_id)
        assessment_id = validate_identifier(assessment_id, "assessment ID")
        assessment = load_json(self.storage.artifact_path(manifest, f"assessment_{assessment_id}_generated_assessment"))
        output_dir = self.storage.run_dir(run_id) / "assessments" / assessment_id
        write_exports(assessment, output_dir)
        manifest = self.get_run(run_id)
        for filename in self._export_filenames().values():
            key = self._export_artifact_key(assessment_id, filename)
            manifest.setdefault("artifact_index", {})[key] = f"assessments/{assessment_id}/exports/{filename}"
        self.storage.save_manifest(manifest)
        return self.get_run(run_id)

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

    def _curriculum_results(self, manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        topics = self._artifact_or_empty(manifest, "topic_candidates", "topic_candidates")
        skills = self._artifact_or_empty(manifest, "micro_skill_candidates", "micro_skill_candidates")
        gaps = self._artifact_or_empty(manifest, "content_gaps", "content_gaps")
        return (
            topics if isinstance(topics, list) else [],
            skills if isinstance(skills, list) else [],
            gaps if isinstance(gaps, list) else [],
        )

    def _require_curriculum_results(self, manifest: dict[str, Any]) -> None:
        topics, skills, _gaps = self._curriculum_results(manifest)
        if not topics or not skills:
            raise DashboardControllerError("compilation produced no usable curriculum results")

    def _family_for_id(self, family_id: str) -> dict[str, Any]:
        family_id = validate_identifier(family_id, "generation family ID")
        for family in self._all_families():
            if family["generation_family_id"] == family_id:
                return family
        raise DashboardControllerError("unknown generation family")

    def _all_families(self) -> list[dict[str, Any]]:
        return [load_family(path) for path in sorted(FAMILY_DIR.glob("*.json"))] + [calculus_family()]

    def _assessment_configuration_ready(self, manifest: dict[str, Any]) -> bool:
        return (
            manifest.get("status") in {"assessment_ready", "assessment_review_pending"}
            and manifest.get("curriculum_review_status") == "accepted_for_local_use"
        )

    def _public_family(self, family: dict[str, Any]) -> dict[str, Any]:
        return {
            "generation_family_id": family["generation_family_id"],
            "subject_code": family["subject_code"],
            "topic_code": family["topic_code"],
            "target_micro_skill_code": family["target_micro_skill_code"],
            "question_types": family["question_types"],
            "enabled": family["enabled"],
        }

    def _family_is_compatible_with_run(
        self,
        family: dict[str, Any],
        manifest: dict[str, Any],
        topics: list[dict[str, Any]],
        skills: list[dict[str, Any]],
    ) -> bool:
        if not family.get("enabled", False):
            return False
        if family.get("generation_family_id") == CALCULUS_FAMILY_ID:
            accepted = set(self._accepted_micro_skill_codes(manifest))
            return (
                str(manifest.get("detected_subject") or "").upper() == "MATHEMATICS"
                and manifest.get("detected_course_level") == "CALCULUS_I"
                and set(CALCULUS_REQUIRED_SKILLS) <= accepted
            )
        if str(family.get("subject_code", "")).upper() != str(manifest.get("detected_subject") or "").upper():
            return False
        profile_id = str(manifest.get("selected_profile_id") or "")
        if profile_id == "PHYSICS_INTRO_MECHANICS_PROFILE_V1" and family.get("subject_code") == "PHYSICS":
            return True
        if profile_id == "STATICS_VECTOR_COMPONENTS_RELEASE_PROFILE_V1" and family.get("subject_code") == "STATICS":
            return True
        topic_codes = {str(item.get("topic_code", "")) for item in topics}
        skill_codes = {str(item.get("micro_skill_code", "")) for item in skills}
        if family.get("topic_code") in topic_codes:
            return True
        if family.get("target_micro_skill_code") in skill_codes:
            return True
        target = str(family.get("target_micro_skill_code", ""))
        if any(target.startswith(code + "_") or code.startswith(target + "_") for code in skill_codes if code):
            return True
        package = self._artifact_or_empty(manifest, "curriculum_extraction_package", None)
        if isinstance(package, dict):
            family_ids = {
                str(item.get("family_id") or item.get("generation_family_id") or "")
                for item in package.get("generation_family_candidates", [])
            }
            if family.get("generation_family_id") in family_ids:
                return True
        return False

    def _accepted_micro_skill_codes(self, manifest: dict[str, Any]) -> list[str]:
        try:
            review = load_json(self.storage.artifact_path(manifest, "curriculum_review_decisions"))
        except Exception:
            return []
        accepted_ids = {item.get("candidate_id") for item in review.get("decisions", []) if item.get("decision") == "accepted"}
        _topics, skills, _gaps = self._curriculum_results(manifest)
        return [skill.get("micro_skill_code", "") for skill in skills if skill.get("candidate_id") in accepted_ids or skill.get("micro_skill_code") in accepted_ids]

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
