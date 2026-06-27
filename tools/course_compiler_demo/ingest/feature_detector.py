"""Feature detection for source documents."""

from __future__ import annotations

import re
from typing import Any


FEATURE_NAMES = [
    "has_timeline",
    "has_topics",
    "has_subtopics",
    "has_questions",
    "has_answers",
    "has_worked_solutions",
    "has_formulas",
    "has_diagrams",
    "has_learning_objectives",
    "has_rubric",
    "has_exam_dates",
    "has_homework_due_dates",
    "has_practice_potential",
    "has_assessment_potential",
    "has_corpus_value",
]


def _flag(value: bool, confidence: str = "medium", evidence: list[str] | None = None) -> dict[str, Any]:
    return {
        "value": value,
        "confidence": confidence,
        "evidence": evidence or [],
    }


def detect_features(raw_text: str, source_type: str) -> dict[str, dict[str, Any]]:
    text = raw_text.lower()
    flags = {name: _flag(False) for name in FEATURE_NAMES}

    if "topics:" in text:
        flags["has_topics"] = _flag(True, "high", ["Detected Topics section."])
    if re.search(r"(?m)^\s+[-*]\s+", raw_text) or "subtopics:" in text:
        flags["has_subtopics"] = _flag(True, "medium", ["Detected indented list or Subtopics section."])
    if "problems:" in text or re.search(r"(?m)^\s*\d+[.)]\s+", raw_text):
        flags["has_questions"] = _flag(True, "high", ["Detected Problems section or numbered problems."])
    if "answer" in text or "answers:" in text:
        flags["has_answers"] = _flag(True, "high", ["Detected answer language."])
    if "solution" in text or "worked solution" in text:
        flags["has_worked_solutions"] = _flag(True, "high", ["Detected solution language."])
    if re.search(r"\b\d*[a-z]\s*[+\-*/=]\s*[-\d]", raw_text, re.IGNORECASE) or re.search(
        r"\by\s*=", raw_text, re.IGNORECASE
    ):
        flags["has_formulas"] = _flag(True, "high", ["Detected equation-like text."])
    if re.search(r"\b(diagram|figure|graph|chart)\b", text):
        flags["has_diagrams"] = _flag(True, "medium", ["Detected diagram or figure language."])
    if any(term in text for term in ["learning objective", "objectives:", "students will"]):
        flags["has_learning_objectives"] = _flag(True, "medium", ["Detected learning objective language."])
    if "rubric" in text:
        flags["has_rubric"] = _flag(True, "high", ["Detected rubric language."])
    if "timeline" in text or "schedule" in text:
        flags["has_timeline"] = _flag(True, "medium", ["Detected timeline or schedule language."])
    if "exam" in text or re.search(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", raw_text):
        flags["has_exam_dates"] = _flag(True, "medium", ["Detected exam or date-like language."])
    if "due" in text:
        flags["has_homework_due_dates"] = _flag(True, "medium", ["Detected due-date language."])

    practice_types = {"homework", "practice_test", "quiz_review", "study_guide", "problem_set"}
    assessment_types = {"practice_test", "quiz_review", "midterm_review", "final_review"}
    if source_type in practice_types or flags["has_questions"]["value"]:
        flags["has_practice_potential"] = _flag(True, "high", ["Source can support practice generation."])
    if source_type in assessment_types:
        flags["has_assessment_potential"] = _flag(True, "high", ["Source type can support assessment preparation."])
    if flags["has_topics"]["value"] or flags["has_questions"]["value"]:
        flags["has_corpus_value"] = _flag(True, "high", ["Detected reusable topics or questions."])

    return flags
