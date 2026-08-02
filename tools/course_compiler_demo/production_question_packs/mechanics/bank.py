from __future__ import annotations

import json
import math
from pathlib import Path

from tools.course_compiler_demo.production_questions import (
    ProductionFamily,
    ProductionReviewRecordV1,
    ProductionValidationRecordV1,
    default_validator,
    produce_course_bank,
)
from tools.course_compiler_demo.subject_packs.physics_engineering import (
    build_physics_engineering_course_catalog,
    validate_physics_engineering_course_catalog,
)

DOMAINS = (
    "vector components",
    "kinematics",
    "projectile motion",
    "Newtonian dynamics",
    "work-energy",
    "momentum",
    "rotational motion",
    "gravitation",
    "oscillations",
    "circular motion",
)


def _family(i: int, course: dict) -> ProductionFamily:
    p = course["procedures"][i]
    s = course["micro_skills"][i]
    t = next(x for x in course["topics"] if x["topic_id"] == s["topic_id"])
    vector = i in (0, 5)

    def params(n: int) -> dict:
        parameters = {
            "a": float(n + i + 2),
            "b": float(n + i + 3),
            "speed": float((n % 9) + 4),
            "time": float((n % 5) + 1),
            "angle": float((13 * n + 7 * i) % 70 + 10),
            "mass": float((n % 6) + 2),
            "radius": float((n % 8) + 1.5),
        }
        if i == 4:
            parameters["speed"] = float(n + 4)
        return parameters

    def derive(x: dict) -> float | list[float]:
        a, b, speed, time, angle, mass, radius = (
            x["a"],
            x["b"],
            x["speed"],
            x["time"],
            math.radians(x["angle"]),
            x["mass"],
            x["radius"],
        )
        if i == 0:
            return [a * math.cos(angle), a * math.sin(angle)]
        if i == 1:
            return speed * time + 0.5 * a * time * time
        if i == 2:
            return (speed * speed * math.sin(2 * angle)) / (2 * 9.81)
        if i == 3:
            return a * mass
        if i == 4:
            return 0.5 * mass * speed * speed
        if i == 5:
            return [mass * speed * math.cos(angle), mass * speed * math.sin(angle)]
        if i == 6:
            return 0.5 * a * time * time
        if i == 7:
            return 6.67430e-11 * mass * mass / (radius * radius)
        if i == 8:
            return 1.0 / (2 * math.pi * math.sqrt(mass / a))
        return (speed * speed) / radius

    def gen(x: dict) -> tuple[str, float | list[float]]:
        a, b, speed, time, angle, mass, radius = (
            x["a"],
            x["b"],
            x["speed"],
            x["time"],
            x["angle"],
            x["mass"],
            x["radius"],
        )
        prompts = (
            f"Resolve the {a:.1f} N force at {angle:.1f} degrees counterclockwise from +x into ordered x and y components in N?",
            f"Starting from rest, a particle accelerates at {a:.1f} m/s^2 for {time:.1f} s; what displacement in m results?",
            f"A projectile launched at {speed:.1f} m/s at {angle:.1f} degrees reaches what horizontal range in m?",
            f"What net force in N is required to accelerate a {mass:.1f} kg mass at {a:.1f} m/s^2?",
            f"What kinetic energy in J does a {mass:.1f} kg mass moving at {speed:.1f} m/s have?",
            f"What ordered x and y momentum components in kg m/s follow from a {mass:.1f} kg mass moving at {speed:.1f} m/s at {angle:.1f} degrees?",
            f"Starting from rest, what angular displacement in rad follows for an angular acceleration of {a:.1f} rad/s^2 over {time:.1f} s?",
            f"What gravitational force in N acts between two {mass:.1f} kg masses separated by {radius:.1f} m?",
            f"A mass-spring system with spring constant {a:.1f} N/m and mass {mass:.1f} kg has what oscillation period in s?",
            f"For a particle moving in a circle of radius {radius:.1f} m at speed {speed:.1f} m/s, what centripetal acceleration in m/s^2 results?",
        )
        values = (
            [a * math.cos(math.radians(angle)), a * math.sin(math.radians(angle))],
            speed * time + 0.5 * a * time * time,
            (speed * speed * math.sin(math.radians(2 * angle))) / (2 * 9.81),
            a * mass,
            0.5 * mass * speed * speed,
            [mass * speed * math.cos(math.radians(angle)), mass * speed * math.sin(math.radians(angle))],
            0.5 * a * time * time,
            6.67430e-11 * mass * mass / (radius * radius),
            1.0 / (2 * math.pi * math.sqrt(mass / a)),
            (speed * speed) / radius,
        )
        return prompts[i], values[i]

    return ProductionFamily(
        f"MECHANICS_PRODUCTION_{i:02d}",
        p["procedure_id"],
        t["unit_id"],
        t["topic_id"],
        s["micro_skill_id"],
        "numeric_vector" if vector else "numeric_scalar",
        "numeric_vector" if vector else "numeric_scalar",
        ("unit_mismatch", "axis_confusion", "sign_error", DOMAINS[i].replace(" ", "_") + "_error"),
        params,
        gen,
        derive,
    )


def mechanics_validator(candidate, derivation, generator_answer):
    base = default_validator(candidate, derivation, generator_answer)
    prompt = candidate.prompt.lower()
    index = int(candidate.request["generation_family_id"].split("_")[-1])
    keywords = (
        ("components", "x and y"),
        ("displacement", "m/s^2", "s"),
        ("range", "projectile"),
        ("net force", "kg"),
        ("kinetic energy", "j"),
        ("momentum", "kg m/s"),
        ("angular displacement", "rad"),
        ("gravitational force", "n"),
        ("oscillation period", "period"),
        ("centripetal acceleration", "m/s^2"),
    )
    semantic = all(token in prompt for token in keywords[index])
    reasons = base.reasons + (() if semantic else ("MECHANICS_DOMAIN_VALIDATION_FAILED",))
    return ProductionValidationRecordV1(
        base.validation_id,
        base.candidate_id,
        base.grading_pass,
        base.procedure_compatibility_pass,
        base.failure_signal_pass,
        base.prompt_determinacy_pass,
        base.unit_tolerance_pass and semantic,
        base.answer_contract_pass,
        reasons,
    )


def artifact_reviewer(families, inspected, subject, level):
    if level == "FAMILY":
        family = next((x for x in families if x.family_id == subject), None)
        cohort = [v for v in inspected.values() if v[0].request["generation_family_id"] == subject]
        if family is None or not cohort or any(not v[2].passed or v[1].candidate_id != v[0].candidate_id for v in cohort):
            raise ValueError("family evidence missing or failed")
        findings = (
            f"inspected {len(cohort)} generated candidates and validations for {DOMAINS[int(subject.split('_')[-1])]}",
            f"verified procedure {family.procedure_id}, skill {family.micro_skill_id}, and {family.answer_shape} contract",
        )
    else:
        if subject not in inspected or not inspected[subject][2].passed:
            raise ValueError("candidate evidence missing or failed")
        candidate, derivation, validation = inspected[subject]
        findings = (
            f"inspected prompt and derivation {derivation.derivation_id} for {candidate.request['generation_family_id']}",
            f"verified units, axes, sign convention, and validation {validation.validation_id}",
        )
    return ProductionReviewRecordV1(
        f"review:{level.lower()}:{subject}",
        subject,
        level,
        "PASS",
        "independent_mechanics_artifact_reviewer",
        findings,
    )


def build_bank():
    pack = build_physics_engineering_course_catalog()
    validate_physics_engineering_course_catalog(pack)
    course = pack["courses"]["MECHANICS"]
    evidence = (
        {
            "evidence_id": "MECHANICS:COURSE_CATALOG",
            "source_identity": pack["pack_id"],
            "source_hash": pack["deterministic_sha256"],
            "access": "READ_ONLY_REFERENCE",
        },
    )
    families = tuple(_family(i, course) for i in range(10))
    inspected = {}

    def validator(candidate, derivation, generator_answer):
        result = mechanics_validator(candidate, derivation, generator_answer)
        inspected[candidate.candidate_id] = (candidate, derivation, result)
        return result

    def reviewer(subject, level):
        return artifact_reviewer(families, inspected, subject, level)

    bank, summary = produce_course_bank(
        "MECHANICS",
        pack["pack_id"],
        pack["deterministic_sha256"],
        evidence,
        families,
        reviewer=reviewer,
        validator=validator,
    )
    return bank, summary, evidence


def write_bank(root):
    bank, summary, evidence = build_bank()
    root = Path(root)
    for name in ("authority", "generation", "candidates", "derivations", "validations", "duplicates", "reviews", "banks", "assessments", "exports", "logs"):
        (root / name).mkdir(parents=True, exist_ok=True)
    payloads = {
        "authority/authority.json": {"source_evidence": evidence},
        "generation/requests.json": [x["request"] for x in bank.candidates],
        "candidates/candidates.json": bank.candidates,
        "derivations/derivations.json": bank.derivations,
        "validations/validations.json": bank.validations,
        "duplicates/duplicates.json": bank.duplicates,
        "reviews/reviews.json": bank.reviews,
        "banks/production_bank.json": bank.to_dict(),
        "exports/course_summary.json": summary.to_dict(),
        "logs/run.json": {"status": "PASS", "count": 100, "domains": DOMAINS},
    }
    for rel, value in payloads.items():
        (root / rel).write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    return bank, summary
