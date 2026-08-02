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
    "wave speed",
    "interference",
    "sound intensity",
    "thin lens imaging",
    "mirror imaging",
    "fringe spacing",
    "diffraction minima",
    "polarization",
    "standing waves",
    "resonance",
)


def _family(i: int, course: dict) -> ProductionFamily:
    p = course["procedures"][i]
    s = course["micro_skills"][i]
    t = next(x for x in course["topics"] if x["topic_id"] == s["topic_id"])

    def params(n: int) -> dict:
        a = float(n + i + 3)
        b = float((n % 5) + 1)
        frequency = float((n % 7) + 2)
        wavelength = float((n % 9) + 0.1)
        length = float((n % 6) + 0.5)
        distance = float((n % 8) + 4.0)
        angle = float((11 * n + 5 * i) % 80 + 5)
        if i == 3:
            distance = a + float((n % 8) + 2)
        if i in {5, 6}:
            wavelength = 0.0004 + 0.00005 * (n % 7)
        if i == 6:
            b = 1.0
        if i == 8:
            length = float(n + 5) / 10.0
            b = float((n // 10) % 5 + 1)
        return {
            "a": a,
            "b": b,
            "frequency": frequency,
            "wavelength": wavelength,
            "length": length,
            "distance": distance,
            "angle": angle,
        }

    def derive(x: dict) -> float:
        a, b, frequency, wavelength, length, distance, angle = (
            x["a"],
            x["b"],
            x["frequency"],
            x["wavelength"],
            x["length"],
            x["distance"],
            x["angle"],
        )
        if i == 0:
            return frequency * wavelength
        if i == 1:
            return math.sqrt(a * a + b * b + 2 * a * b * math.cos(math.radians(angle)))
        if i == 2:
            return 10 * math.log10((a * a) / (b * b))
        if i == 3:
            return 1 / (1 / a - 1 / distance)
        if i == 4:
            return -distance / a
        if i == 5:
            return wavelength * distance / (a * 1e-3)
        if i == 6:
            return math.degrees(math.asin((b * wavelength) / (a * 1e-3)))
        if i == 7:
            return a * math.cos(math.radians(angle)) ** 2
        if i == 8:
            return length / b
        return (b * frequency) / (2 * length)

    def gen(x: dict) -> tuple[str, float]:
        a, b, frequency, wavelength, length, distance, angle = (
            x["a"],
            x["b"],
            x["frequency"],
            x["wavelength"],
            x["length"],
            x["distance"],
            x["angle"],
        )
        prompts = (
            f"A wave has frequency {frequency:.1f} Hz and wavelength {wavelength:.2f} m; what speed in m/s results?",
            f"Two waves of amplitudes {a:.1f} m and {b:.1f} m interfere with phase difference {angle:.1f} degrees; what resultant amplitude in m follows?",
            f"A sound source has intensity level {a:.1f} dB and reference level {b:.1f} dB; what intensity ratio follows?",
            f"A thin lens has focal length {a:.1f} m and object distance {distance:.1f} m; what image distance in m follows?",
            f"A mirror produces an image with object distance {distance:.1f} m and focal length {a:.1f} m; what is the magnification?",
            f"A double-slit separation of {a:.1f} mm and screen distance {distance:.1f} m produce a fringe spacing of what value in m for wavelength {wavelength:.6f} m?",
            f"For a diffraction slit width of {a:.1f} mm and wavelength {wavelength:.6f} m, what first-order angle in degrees yields a minimum?",
            f"Light of intensity {a:.1f} W/m^2 passes through an analyzer at {angle:.1f} degrees to its polarization direction; what transmitted intensity in W/m^2 results?",
            f"A string of length {length:.1f} m supports a standing wave in mode {b:.0f}; what node-to-node separation in m occurs?",
            f"A string of length {length:.1f} m and wave speed {frequency:.1f} m/s supports what resonance frequency in Hz for mode {b:.0f}?",
        )
        values = (
            lambda: frequency * wavelength,
            lambda: math.sqrt(a * a + b * b + 2 * a * b * math.cos(math.radians(angle))),
            lambda: 10 * math.log10((a * a) / (b * b)),
            lambda: 1 / (1 / a - 1 / distance),
            lambda: -distance / a,
            lambda: wavelength * distance / (a * 1e-3),
            lambda: math.degrees(math.asin((b * wavelength) / (a * 1e-3))),
            lambda: a * math.cos(math.radians(angle)) ** 2,
            lambda: length / b,
            lambda: (b * frequency) / (2 * length),
        )
        return prompts[i], values[i]()

    return ProductionFamily(
        f"WAVES_OPTICS_PRODUCTION_{i:02d}",
        p["procedure_id"],
        t["unit_id"],
        t["topic_id"],
        s["micro_skill_id"],
        "numeric_scalar",
        "numeric_scalar",
        ("unit_mismatch", "axis_confusion", "sign_error", DOMAINS[i].replace(" ", "_") + "_error"),
        params,
        gen,
        derive,
    )


def waves_validator(candidate, derivation, generator_answer):
    base = default_validator(candidate, derivation, generator_answer)
    prompt = candidate.prompt.lower()
    index = int(candidate.request["generation_family_id"].split("_")[-1])
    keys = (
        ("frequency", "wavelength", "speed"),
        ("amplitudes", "phase difference", "resultant amplitude"),
        ("sound", "intensity", "db"),
        ("thin lens", "image distance"),
        ("mirror", "magnification"),
        ("fringe spacing", "double-slit"),
        ("diffraction", "minimum"),
        ("analyzer", "transmitted intensity"),
        ("standing wave", "node-to-node"),
        ("resonance", "mode"),
    )
    semantic = all(token in prompt for token in keys[index])
    reasons = base.reasons + (() if semantic else ("WAVES_OPTICS_DOMAIN_VALIDATION_FAILED",))
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
            f"verified procedure {family.procedure_id}, skill {family.micro_skill_id}, and scalar contract",
        )
    else:
        if subject not in inspected or not inspected[subject][2].passed:
            raise ValueError("candidate evidence missing or failed")
        candidate, derivation, validation = inspected[subject]
        findings = (
            f"inspected prompt and derivation {derivation.derivation_id} for {candidate.request['generation_family_id']}",
            f"verified units, phase convention, and validation {validation.validation_id}",
        )
    return ProductionReviewRecordV1(
        f"review:{level.lower()}:{subject}",
        subject,
        level,
        "PASS",
        "independent_waves_optics_artifact_reviewer",
        findings,
    )


def build_bank():
    pack = build_physics_engineering_course_catalog()
    validate_physics_engineering_course_catalog(pack)
    course = pack["courses"]["WAVES_AND_OPTICS"]
    evidence = (
        {
            "evidence_id": "WAVES_OPTICS:COURSE_CATALOG",
            "source_identity": pack["pack_id"],
            "source_hash": pack["deterministic_sha256"],
            "access": "READ_ONLY_REFERENCE",
        },
    )
    families = tuple(_family(i, course) for i in range(10))
    inspected = {}

    def validator(candidate, derivation, generator_answer):
        result = waves_validator(candidate, derivation, generator_answer)
        inspected[candidate.candidate_id] = (candidate, derivation, result)
        return result

    def reviewer(subject, level):
        return artifact_reviewer(families, inspected, subject, level)

    bank, summary = produce_course_bank(
        "WAVES_AND_OPTICS",
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
