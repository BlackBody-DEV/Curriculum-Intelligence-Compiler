"""Demo-only canonical matching for extraction candidates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REGISTRY_PATH = Path(__file__).with_name("demo_canonical_registry.json")


def _normalize(value: str) -> str:
    return " ".join(value.lower().replace("-", " ").split())


def load_demo_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _registry_names(registry: dict[str, Any]) -> tuple[set[str], set[str]]:
    topics: set[str] = set()
    skills: set[str] = set()
    for subject in registry.get("subjects", []):
        for course in subject.get("courses", []):
            for topic in course.get("topics", []):
                topics.add(_normalize(topic.get("topic", "")))
                for skill in topic.get("micro_skills", []):
                    skills.add(_normalize(skill.get("name", "")))
    return topics, skills


def match_candidates_to_demo_registry(
    topic_candidates: list[dict[str, Any]],
    micro_skill_candidates: list[dict[str, Any]],
    registry_path: Path = REGISTRY_PATH,
) -> None:
    registry = load_demo_registry(registry_path)
    topic_names, skill_names = _registry_names(registry)

    for topic in topic_candidates:
        name = topic["topic_name"]
        if _normalize(name) in topic_names:
            topic["alignment_status"] = "matched_existing_demo"
            topic["possible_canonical_matches"] = [
                {
                    "match_name": name,
                    "match_scope": "demo_registry",
                    "confidence": "high",
                    "status": "demo_unverified",
                }
            ]
        else:
            topic["alignment_status"] = "candidate_new"
            topic["possible_canonical_matches"] = []

    for skill in micro_skill_candidates:
        name = skill["micro_skill_name"]
        skill["alignment_status"] = (
            "matched_existing_demo" if _normalize(name) in skill_names else "candidate_new"
        )
