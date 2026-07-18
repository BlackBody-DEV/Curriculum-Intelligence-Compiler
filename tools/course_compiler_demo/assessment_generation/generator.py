"""Deterministic assessment generator."""

from __future__ import annotations

import random
from typing import Any

from .blueprint import validate_blueprint
from .answer_calculators import calculate_answer
from .fingerprints import exact_fingerprint, structural_fingerprint
from .models import ASSESSMENT_CONTRACT_VERSION, QUESTION_CONTRACT_VERSION, NON_LIVE_BOUNDARY
from .prompt_builders import build_prompt
from .solution_builders import build_solution
from .validators import review_record, validate_family_scope, validate_question


def _difficulty_slots(blueprint: dict[str, Any]) -> list[str]:
    dist = blueprint["difficulty_distribution"]
    slots: list[str] = []
    for difficulty in ["foundational", "standard", "advanced"]:
        slots.extend([difficulty] * int(dist.get(difficulty, 0)))
    return slots


def _rng(seed: int, slot_index: int, attempt: int) -> random.Random:
    return random.Random(f"{seed}:{slot_index}:{attempt}")


def _physics_params(difficulty: str, rng: random.Random) -> dict[str, Any]:
    target_by_diff = {
        "foundational": ["acceleration"],
        "standard": ["acceleration", "net_force", "mass"],
        "advanced": ["acceleration", "net_force", "mass"],
    }
    target = rng.choice(target_by_diff[difficulty])
    mass = rng.choice([2, 3, 4, 5, 6, 8, 10, 12])
    accel = rng.choice([1.5, 2, 2.5, 3, 4, 5])
    if difficulty == "advanced" and rng.choice([True, False]):
        accel = -accel
    force = mass * accel
    return {
        "target_variable": target,
        "mass_kg": mass,
        "acceleration_mps2": accel,
        "net_force_n": force,
    }


def _statics_params(difficulty: str, rng: random.Random) -> dict[str, Any]:
    magnitude = rng.choice([40, 50, 60, 75, 80, 90, 100, 120])
    angle = rng.choice([15, 25, 30, 35, 45, 53.130102, 60])
    patterns = {
        "foundational": [(1, 1, "Quadrant I")],
        "standard": [(1, 1, "Quadrant I"), (-1, 1, "Quadrant II"), (1, -1, "Quadrant IV")],
        "advanced": [(1, 1, "Quadrant I"), (-1, 1, "Quadrant II"), (-1, -1, "Quadrant III"), (1, -1, "Quadrant IV")],
    }
    sx, sy, label = rng.choice(patterns[difficulty])
    return {"magnitude": magnitude, "angle_degrees": angle, "x_sign": sx, "y_sign": sy, "quadrant_label": label}


PARAM_BUILDERS = {
    "newtons_second_law_numeric_1d": _physics_params,
    "vector_components_2d_numeric_pair": _statics_params,
}

MAX_ATTEMPTS_PER_SLOT = 200


def _params_for_family(family: dict[str, Any], difficulty: str, rng: random.Random) -> dict[str, Any]:
    builder = PARAM_BUILDERS[family["family_type"]]
    return builder(difficulty, rng)


def generate_assessment(
    *,
    family: dict[str, Any],
    blueprint: dict[str, Any],
    historical_fingerprints: set[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    validate_blueprint(blueprint)
    validate_family_scope(family, blueprint)
    seed = int(blueprint["random_seed"])
    slots = _difficulty_slots(blueprint)
    historical = historical_fingerprints or set()
    exact_seen: set[str] = set()
    structural_seen: set[str] = set()
    questions: list[dict[str, Any]] = []
    rejected = {
        "rejected_exact_duplicates": 0,
        "rejected_structural_duplicates": 0,
        "rejected_scope": 0,
        "rejected_parameter_constraints": 0,
        "rejected_answer_validation": 0,
    }
    scenario_rng = random.Random(f"{seed}:scenario")
    scenarios = list(family["scenario_templates"])

    for slot_index, difficulty in enumerate(slots, start=1):
        made = None
        for attempt in range(1, MAX_ATTEMPTS_PER_SLOT + 1):
            rng = _rng(seed, slot_index, attempt)
            params = _params_for_family(family, difficulty, rng)
            scenario = scenarios[(scenario_rng.randrange(len(scenarios)) + attempt + slot_index) % len(scenarios)]
            answer = calculate_answer(family["answer_calculator_id"], params)
            question = {
                "contract_version": QUESTION_CONTRACT_VERSION,
                "question_id": f"{blueprint['assessment_id']}_Q{slot_index:03d}",
                "assessment_id": blueprint["assessment_id"],
                "slot_id": f"SLOT_{slot_index:03d}",
                "generation_family_id": family["generation_family_id"],
                "generation_family_version": family["family_version"],
                "subject_code": family["subject_code"],
                "topic_code": family["topic_code"],
                "subtopic_code": family["subtopic_code"],
                "micro_skill_code": family["target_micro_skill_code"],
                "procedure_code": family["approved_procedure_code"],
                "prerequisite_skills_used": family["approved_prerequisite_skills"],
                "difficulty": difficulty,
                "question_type": family["question_types"][0],
                "question_origin": family["question_origin"],
                "parameter_set": params,
                "scenario_template_id": scenario["scenario_template_id"],
                "prompt": build_prompt(family["prompt_builder_id"], params, scenario),
                "answer_input_schema": family["answer_adapter_type"],
                "accepted_units": family["accepted_units"],
                "grading_type": family["grading_type"],
                "tolerance": family["tolerance"],
                "expected_answer": answer,
                "solution_steps": build_solution(family["solution_builder_id"], params, answer),
                "known_failure_modes": family["known_failure_modes"],
                "scope_validation": {"status": "not_run"},
                "answer_validation": {"status": "not_run"},
                "generation_seed": f"{seed}:{slot_index}:{attempt}",
                "generation_attempt": attempt,
                "review_status": "pending",
                "locked": False,
                "validation_status": "not_run",
            }
            question["exact_fingerprint"] = exact_fingerprint(question)
            question["structural_fingerprint"] = structural_fingerprint(question, family)
            if question["exact_fingerprint"] in exact_seen or question["exact_fingerprint"] in historical:
                rejected["rejected_exact_duplicates"] += 1
                continue
            if question["structural_fingerprint"] in structural_seen or question["structural_fingerprint"] in historical:
                rejected["rejected_structural_duplicates"] += 1
                continue
            errors = validate_question(question, family, blueprint)
            if errors:
                rejected["rejected_answer_validation"] += 1
                continue
            question["scope_validation"] = {"status": "pass"}
            question["answer_validation"] = {"status": "pass"}
            question["validation_status"] = "pass"
            exact_seen.add(question["exact_fingerprint"])
            structural_seen.add(question["structural_fingerprint"])
            made = question
            break
        if made is not None:
            questions.append(made)

    duplicate_report = {
        "requested_count": int(blueprint["question_count"]),
        "generated_count": len(questions),
        **rejected,
        "parameter_space_exhausted": len(questions) < int(blueprint["question_count"]),
        "exact_fingerprints": sorted(exact_seen),
        "structural_fingerprints": sorted(structural_seen),
    }
    assessment = {
        "contract_version": ASSESSMENT_CONTRACT_VERSION,
        "assessment_id": blueprint["assessment_id"],
        "title": blueprint["title"],
        "assessment_type": blueprint["assessment_type"],
        "subject_code": blueprint["subject_code"],
        "topic_codes": blueprint["selected_topic_codes"],
        "micro_skill_codes": blueprint["selected_micro_skill_codes"],
        "generation_family_ids": [family["generation_family_id"]],
        "review_status": "review_pending",
        "validation_status": "pass" if len(questions) == int(blueprint["question_count"]) else "partial",
        "non_live_boundary": dict(NON_LIVE_BOUNDARY),
        "questions": questions,
    }
    decisions = {
        "contract_version": "assessment_review_decisions_v1",
        "assessment_id": blueprint["assessment_id"],
        "review_records": [
            {
                **review_record(question_id=q["question_id"], decision="pending"),
            }
            for q in questions
        ],
    }
    return assessment, duplicate_report, decisions


def regenerate_question(
    *,
    assessment: dict[str, Any],
    family: dict[str, Any],
    blueprint: dict[str, Any],
    slot_id: str,
    child_seed: int,
) -> dict[str, Any]:
    existing = next(q for q in assessment["questions"] if q["slot_id"] == slot_id)
    if existing.get("locked"):
        raise ValueError("locked question cannot be regenerated")
    clone = {
        **blueprint,
        "question_count": 1,
        "random_seed": child_seed,
        "difficulty_distribution": {existing["difficulty"]: 1},
        "question_type_distribution": {existing["question_type"]: 1},
        "generation_family_allocation": {
            family["generation_family_id"]: {
                "question_count": 1,
                "approved_procedure_codes": [family["approved_procedure_code"]],
            }
        },
    }
    generated, _, _ = generate_assessment(family=family, blueprint=clone)
    replacement = generated["questions"][0]
    replacement["slot_id"] = slot_id
    replacement["question_id"] = existing["question_id"] + "_R001"
    return replacement
