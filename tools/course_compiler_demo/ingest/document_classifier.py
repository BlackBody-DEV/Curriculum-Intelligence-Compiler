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


def _score_terms(text: str, terms: list[str]) -> tuple[int, list[str]]:
    matched = [term for term in terms if re.search(rf"\b{re.escape(term)}\b", text)]
    return len(matched), matched


def detect_math_course_level(raw_text: str) -> dict[str, Any]:
    text = raw_text.lower()
    rules = [
        (
            "DIFFERENTIAL_EQUATIONS",
            [
                "differential equation",
                "differential equations",
                "separable equation",
                "separable equations",
                "linear first order",
                "first order equation",
                "initial value problem",
                "initial value problems",
                "slope field",
                "slope fields",
                "second order equation",
                "second order equations",
                "systems of differential equations",
            ],
        ),
        (
            "CALCULUS_I",
            [
                "limit",
                "limits",
                "derivative",
                "derivatives",
                "power rule",
                "chain rule",
                "critical point",
                "critical points",
                "increasing",
                "decreasing",
                "applications of derivatives",
            ],
        ),
        ("CALCULUS_II", ["integral", "integrals", "series"]),
        ("LINEAR_ALGEBRA", ["matrix", "matrices", "row-reduce", "row reduce"]),
        ("ALGEBRA_I", ["linear equation", "linear equations", "slope", "graphing lines"]),
    ]
    scored = []
    for level, terms in rules:
        score, matched = _score_terms(text, terms)
        if score:
            scored.append({"course_level": level, "score": score, "matched_terms": matched})
    if not scored:
        return {
            "detected_course_level": "UNKNOWN_MATH_LEVEL",
            "course_level_confidence": "low",
            "classification_evidence": [],
            "competing_classifications": [],
            "tie_breaking": "fail_closed_no_math_course_evidence",
            "fail_closed": True,
        }

    priority = {
        "DIFFERENTIAL_EQUATIONS": 0,
        "CALCULUS_I": 1,
        "CALCULUS_II": 2,
        "LINEAR_ALGEBRA": 3,
        "ALGEBRA_I": 4,
    }
    scored.sort(key=lambda item: (-item["score"], priority[item["course_level"]]))
    winner = scored[0]
    confidence = "high" if winner["score"] >= 3 else "medium"
    return {
        "detected_course_level": winner["course_level"],
        "course_level_confidence": confidence,
        "classification_evidence": [
            {
                "course_level": item["course_level"],
                "matched_terms": item["matched_terms"],
                "score": item["score"],
            }
            for item in scored
        ],
        "competing_classifications": [
            {"course_level": item["course_level"], "score": item["score"]}
            for item in scored[1:]
        ],
        "tie_breaking": "highest_evidence_score_then_advanced_math_before_algebra",
        "fail_closed": False,
    }
