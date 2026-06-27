"""Rule-based math extraction for the Course Compiler Demo."""

from __future__ import annotations

import re
from typing import Any

from .evidence_builder import find_evidence_for_terms


TOPIC_DICTIONARY = {
    "Linear Equations": ["linear equations", "solve for x", "two-step equation"],
    "Systems of Equations": ["systems of equations", "system of equations"],
    "Graphing Lines": ["graphing lines", "slope", "y-intercept", "line through"],
    "Functions": ["functions", "function", "evaluate f"],
    "Polynomials": ["polynomials", "polynomial"],
    "Factoring": ["factoring", "factor"],
    "Quadratics": ["quadratics", "quadratic"],
    "Trigonometry": ["trigonometry", "sine", "cosine", "tangent"],
    "Limits": ["limits", "limit"],
    "Derivatives": ["derivatives", "derivative", "power rule", "chain rule"],
    "Integrals": ["integrals", "integral"],
    "Series": ["series"],
    "Vectors": ["vectors", "vector"],
    "Matrices": ["matrices", "matrix", "row-reduce", "row reduce"],
    "Linear Transformations": ["linear transformations", "linear transformation"],
    "Differential Equations": ["differential equations", "differential equation"],
}


MICRO_SKILL_DICTIONARY = {
    "Isolate the Variable": {
        "terms": ["solve for x", "linear equations"],
        "topic": "Linear Equations",
        "difficulty": "introductory",
    },
    "Combine Like Terms": {
        "terms": ["combining like terms", "combine like terms"],
        "topic": "Linear Equations",
        "difficulty": "introductory",
    },
    "Solve a Two-Step Equation": {
        "terms": ["3x + 5 = 20", "2x - 7 = 11", "two-step equation"],
        "topic": "Linear Equations",
        "difficulty": "introductory",
    },
    "Compute Slope": {
        "terms": ["slope", "line through"],
        "topic": "Graphing Lines",
        "difficulty": "introductory",
    },
    "Identify Y-Intercept": {
        "terms": ["y-intercept", "y ="],
        "topic": "Graphing Lines",
        "difficulty": "introductory",
    },
    "Graph a Line from an Equation": {
        "terms": ["graphing lines", "y ="],
        "topic": "Graphing Lines",
        "difficulty": "introductory",
    },
    "Evaluate a Function": {
        "terms": ["evaluate a function", "evaluate f"],
        "topic": "Functions",
        "difficulty": "introductory",
    },
    "Factor a Quadratic": {
        "terms": ["factor a quadratic", "factoring"],
        "topic": "Quadratics",
        "difficulty": "intermediate",
    },
    "Evaluate a Limit": {
        "terms": ["evaluate a limit", "limits"],
        "topic": "Limits",
        "difficulty": "intermediate",
    },
    "Apply the Power Rule": {
        "terms": ["power rule"],
        "topic": "Derivatives",
        "difficulty": "intermediate",
    },
    "Apply the Chain Rule": {
        "terms": ["chain rule"],
        "topic": "Derivatives",
        "difficulty": "intermediate",
    },
    "Evaluate a Definite Integral": {
        "terms": ["definite integral"],
        "topic": "Integrals",
        "difficulty": "intermediate",
    },
    "Row-Reduce a Matrix": {
        "terms": ["row-reduce", "row reduce", "matrix"],
        "topic": "Matrices",
        "difficulty": "intermediate",
    },
    "Solve a Separable Differential Equation": {
        "terms": ["separable differential equation"],
        "topic": "Differential Equations",
        "difficulty": "advanced",
    },
}


def _slug(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", value.upper()).strip("_")


def _matches(raw_text: str, terms: list[str]) -> bool:
    lowered = raw_text.lower()
    return any(term.lower() in lowered for term in terms)


def extract_math_candidates(
    raw_text: str,
    *,
    source_id: str,
    subject: str,
    course_level: str,
) -> dict[str, Any]:
    topic_candidates: list[dict[str, Any]] = []
    micro_skill_candidates: list[dict[str, Any]] = []
    evidence_records: list[dict[str, Any]] = []

    topic_id_by_name: dict[str, str] = {}
    for topic_name, terms in TOPIC_DICTIONARY.items():
        if not _matches(raw_text, terms):
            continue
        topic_id = f"TOPIC_{len(topic_candidates) + 1:03d}"
        evidence = find_evidence_for_terms(
            raw_text, source_id, terms, "topic_candidate", f"EV_TOPIC_{len(topic_candidates) + 1:03d}"
        )
        evidence_records.extend(evidence)
        topic_id_by_name[topic_name] = topic_id
        topic_candidates.append(
            {
                "candidate_id": topic_id,
                "topic_name": topic_name,
                "subject_candidate": subject,
                "course_level_candidate": course_level,
                "description": f"Candidate topic detected from demo source language for {topic_name}.",
                "source_position": {
                    "line_start": evidence[0]["line_start"] if evidence else None,
                    "line_end": evidence[-1]["line_end"] if evidence else None,
                },
                "confidence": "high" if evidence else "medium",
                "evidence_refs": [record["evidence_id"] for record in evidence],
                "possible_canonical_matches": [],
                "alignment_status": "uncertain_mapping",
                "status": "demo_unverified",
            }
        )

    for skill_name, config in MICRO_SKILL_DICTIONARY.items():
        if not _matches(raw_text, config["terms"]):
            continue
        parent_topic_name = config["topic"]
        if parent_topic_name not in topic_id_by_name:
            continue
        skill_id = f"MSKILL_{len(micro_skill_candidates) + 1:03d}"
        evidence = find_evidence_for_terms(
            raw_text,
            source_id,
            config["terms"],
            "micro_skill_candidate",
            f"EV_SKILL_{len(micro_skill_candidates) + 1:03d}",
        )
        evidence_records.extend(evidence)
        micro_skill_candidates.append(
            {
                "candidate_id": skill_id,
                "micro_skill_name": skill_name,
                "micro_skill_description": f"Candidate micro-skill detected for {parent_topic_name}.",
                "parent_topic_candidate_id": topic_id_by_name[parent_topic_name],
                "parent_subtopic_candidate_id": None,
                "subject_candidate": subject,
                "course_level_candidate": course_level,
                "difficulty_estimate": config["difficulty"],
                "prerequisite_micro_skill_candidates": [],
                "evidence_refs": [record["evidence_id"] for record in evidence],
                "confidence": "high" if evidence else "medium",
                "alignment_status": "uncertain_mapping",
                "status": "demo_unverified",
            }
        )

    return {
        "topic_candidates": topic_candidates,
        "micro_skill_candidates": micro_skill_candidates,
        "source_evidence": evidence_records,
    }
