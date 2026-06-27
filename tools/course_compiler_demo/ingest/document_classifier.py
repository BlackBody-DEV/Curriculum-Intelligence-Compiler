"""Rule-based document classification for the Course Compiler Demo."""

from __future__ import annotations

import re
from typing import Any


ALLOWED_SUBJECTS = {
    "MATHEMATICS",
    "PHYSICS",
    "ELECTRICITY_AND_MAGNETISM",
    "AEROSPACE",
    "UNKNOWN",
}


def classify_document(raw_text: str) -> dict[str, Any]:
    text = raw_text.lower()
    evidence: list[str] = []

    rules = [
        ("syllabus", ["syllabus", "course schedule"], "Detected syllabus or course schedule language."),
        ("practice_test", ["practice test"], "Detected Practice Test language."),
        ("midterm_review", ["midterm review"], "Detected Midterm Review language."),
        ("final_review", ["final review"], "Detected Final Review language."),
        ("quiz_review", ["quiz review"], "Detected Quiz Review language."),
        ("study_guide", ["study guide"], "Detected Study Guide language."),
        ("homework", ["homework"], "Detected Homework language."),
        ("textbook_excerpt", ["chapter", "section"], "Detected chapter or section language."),
    ]
    for source_type, terms, message in rules:
        if any(term in text for term in terms):
            evidence.append(message)
            return {
                "detected_source_type": source_type,
                "source_type_confidence": "high",
                "classification_evidence": evidence,
            }

    numbered_problem_count = len(re.findall(r"(?m)^\s*\d+[.)]\s+", raw_text))
    if numbered_problem_count >= 2 and "course schedule" not in text:
        evidence.append(f"Detected {numbered_problem_count} numbered problems.")
        return {
            "detected_source_type": "problem_set",
            "source_type_confidence": "medium",
            "classification_evidence": evidence,
        }

    return {
        "detected_source_type": "unknown",
        "source_type_confidence": "low",
        "classification_evidence": evidence,
    }


def detect_subject(raw_text: str, subject_override: str | None = None) -> dict[str, str]:
    if subject_override:
        normalized = subject_override.strip().upper()
        if normalized not in ALLOWED_SUBJECTS:
            raise ValueError(f"Unsupported subject: {subject_override}")
        return {"detected_subject": normalized, "subject_confidence": "high"}

    text = raw_text.lower()
    if any(term in text for term in ["linear equation", "slope", "algebra", "graphing lines"]):
        return {"detected_subject": "MATHEMATICS", "subject_confidence": "medium"}
    if any(term in text for term in ["force", "kinematics", "newton", "vectors"]):
        return {"detected_subject": "PHYSICS", "subject_confidence": "medium"}
    if any(term in text for term in ["electric field", "magnetic field", "circuit", "voltage"]):
        return {"detected_subject": "ELECTRICITY_AND_MAGNETISM", "subject_confidence": "medium"}
    if any(term in text for term in ["aerospace", "airfoil", "orbital", "propulsion"]):
        return {"detected_subject": "AEROSPACE", "subject_confidence": "medium"}
    return {"detected_subject": "UNKNOWN", "subject_confidence": "low"}


def detect_math_course_level(raw_text: str) -> dict[str, str]:
    text = raw_text.lower()
    if any(term in text for term in ["linear equation", "linear equations", "slope", "graphing lines"]):
        return {"detected_course_level": "ALGEBRA_I", "course_level_confidence": "high"}
    if any(term in text for term in ["limit", "derivative", "chain rule"]):
        return {"detected_course_level": "CALCULUS_I", "course_level_confidence": "medium"}
    if any(term in text for term in ["integral", "series"]):
        return {"detected_course_level": "CALCULUS_II", "course_level_confidence": "medium"}
    if any(term in text for term in ["matrix", "matrices", "row-reduce", "row reduce"]):
        return {"detected_course_level": "LINEAR_ALGEBRA", "course_level_confidence": "medium"}
    if any(term in text for term in ["differential equation", "separable"]):
        return {"detected_course_level": "DIFFERENTIAL_EQUATIONS", "course_level_confidence": "medium"}
    return {"detected_course_level": "UNKNOWN_MATH_LEVEL", "course_level_confidence": "low"}
