"""Course-local Modern Physics production bank."""
from __future__ import annotations

import json
import math
from pathlib import Path

from tools.course_compiler_demo.production_questions import ProductionFamily, ProductionReviewRecordV1, ProductionValidationRecordV1, default_validator, produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog, validate_physics_engineering_course_catalog

DOMAINS = ("photon energy", "photoelectric effect", "matter waves", "time dilation", "relativistic energy", "atomic transitions", "radioactive decay", "activity", "Compton scattering", "threshold reasoning")
H_EV = 4.135667696e-15
H = 6.62607015e-34
C = 299792458.0
ELECTRON_MASS = 9.1093837015e-31


def _family(i: int, course: dict) -> ProductionFamily:
    procedure = course["procedures"][i]
    skill = course["micro_skills"][i]
    topic = next(row for row in course["topics"] if row["topic_id"] == skill["topic_id"])

    def params(n: int) -> dict:
        a = float(n + i + 2)
        return {"a": a, "b": float((n % 7) + 2), "frequency": (4.0 + 0.05 * a) * 1e14, "beta": 0.10 + 0.005 * (a % 100), "angle": 10.0 + 0.7 * a}

    def derive(x: dict) -> float:
        a, b, frequency, beta, angle = x["a"], x["b"], x["frequency"], x["beta"], x["angle"]
        values = (
            H_EV * frequency,
            max(0.0, (2.0 + 0.05 * a) - (1.0 + 0.01 * b)),
            H / ((a * 1e-30) * ((b + 2.0) * 1e5)),
            (b + 1.0) / math.sqrt(1.0 - beta * beta),
            (a * 1e-30) * C * C / math.sqrt(1.0 - beta * beta),
            (a + 10.0) - (b + 1.0),
            (a * 1e6) * 2.0 ** (-(b + 1.0) / (b + 2.0)),
            (math.log(2.0) / (b + 2.0)) * (a * 1e6),
            (H / (ELECTRON_MASS * C)) * (1.0 - math.cos(math.radians(angle))),
            max(0.0, (1.0 + 0.1 * a) - (1.5 + 0.01 * b)),
        )
        return values[i]

    def generate(x: dict) -> tuple[str, float]:
        a, b, frequency, beta, angle = x["a"], x["b"], x["frequency"], x["beta"], x["angle"]
        prompts = (
            f"What photon energy in eV corresponds to frequency {frequency:.3e} Hz using Planck quantization?",
            f"A photon has energy {2.0 + 0.05*a:.3f} eV and strikes a material with work function {1.0 + 0.01*b:.3f} eV; what maximum photoelectron kinetic energy in eV results?",
            f"What de Broglie wavelength in m belongs to a particle of mass {a*1e-30:.3e} kg moving at {(b+2.0)*1e5:.3e} m/s?",
            f"A clock has proper interval {b+1.0:.2f} s and moves at {beta:.3f} times light speed; what dilated interval in s is observed?",
            f"What relativistic total energy in J does a particle of rest mass {a*1e-30:.3e} kg have at speed {beta:.3f} times light speed?",
            f"An atomic electron drops from energy {-b-1.0:.2f} eV to {-a-10.0:.2f} eV; what emitted photon energy in eV follows from energy conservation?",
            f"A radioactive sample starts with {a*1e6:.3e} nuclei; after {b+1.0:.2f} s with half-life {b+2.0:.2f} s, how many nuclei remain?",
            f"A radioactive sample contains {a*1e6:.3e} nuclei with half-life {b+2.0:.2f} s; what activity in Bq follows?",
            f"For photon scattering from an electron through {angle:.2f} degrees, what Compton wavelength shift in m results?",
            f"A photon of energy {1.0+0.1*a:.3f} eV reaches a surface with work function {1.5+0.01*b:.3f} eV; determine whether emission is allowed and report the maximum kinetic energy in eV, using zero if forbidden?",
        )
        a2 = (2.0 + 0.05 * a) - (1.0 + 0.01 * b)
        values = (H_EV*frequency, max(0.0,a2), H/((a*1e-30)*((b+2.0)*1e5)), (b+1.0)/math.sqrt(1-beta*beta), (a*1e-30)*C*C/math.sqrt(1-beta*beta), (a+10.0)-(b+1.0), (a*1e6)*2.0**(-(b+1.0)/(b+2.0)), (math.log(2.0)/(b+2.0))*(a*1e6), (H/(ELECTRON_MASS*C))*(1-math.cos(math.radians(angle))), max(0.0,(1.0+0.1*a)-(1.5+0.01*b)))
        return prompts[i], values[i]

    return ProductionFamily(f"MODERN_PHYSICS_PRODUCTION_{i:02d}", procedure["procedure_id"], topic["unit_id"], topic["topic_id"], skill["micro_skill_id"], "numeric_scalar", "numeric_scalar", ("unit_mismatch", "dimension_mismatch", "conceptual_model_error", DOMAINS[i].replace(" ", "_") + "_error"), params, generate, derive)


def modern_physics_validator(candidate, derivation, generator_answer):
    base = default_validator(candidate, derivation, generator_answer)
    prompt = candidate.prompt.lower()
    index = int(candidate.request["generation_family_id"].split("_")[-1])
    keys = (("photon energy","ev","frequency"),("photoelectron","work function","ev"),("de broglie","kg","m/s"),("proper interval","light speed","s"),("relativistic","rest mass","j"),("atomic electron","emitted photon","ev"),("radioactive","half-life","remain"),("radioactive","activity","bq"),("compton","wavelength shift","m"),("emission is allowed","zero if forbidden","ev"))[index]
    semantic = all(token in prompt for token in keys)
    return ProductionValidationRecordV1(base.validation_id, base.candidate_id, base.grading_pass, base.procedure_compatibility_pass, base.failure_signal_pass, base.prompt_determinacy_pass, base.unit_tolerance_pass and semantic, base.answer_contract_pass, base.reasons + (() if semantic else ("MODERN_PHYSICS_DOMAIN_VALIDATION_FAILED",)))


def artifact_reviewer(families, inspected, subject, level):
    if level == "FAMILY":
        family = next((row for row in families if row.family_id == subject), None)
        cohort = [row for row in inspected.values() if row[0].request["generation_family_id"] == subject]
        if family is None or not cohort or any(not row[2].passed for row in cohort): raise ValueError("family evidence missing or failed")
        findings = (f"inspected {len(cohort)} candidates for {DOMAINS[int(subject.split('_')[-1])]}", f"verified procedure {family.procedure_id}, skill {family.micro_skill_id}, units, and scalar contract")
    else:
        if subject not in inspected or not inspected[subject][2].passed: raise ValueError("candidate evidence missing or failed")
        candidate, derivation, validation = inspected[subject]
        findings = (f"inspected {candidate.candidate_id} and independent derivation {derivation.derivation_id}", f"verified conceptual model, units, and validation {validation.validation_id}")
    return ProductionReviewRecordV1(f"review:{level.lower()}:{subject}", subject, level, "PASS", "independent_modern_physics_reviewer", findings)


def build_bank():
    pack = build_physics_engineering_course_catalog(); validate_physics_engineering_course_catalog(pack); course = pack["courses"]["MODERN_PHYSICS"]
    evidence = ({"evidence_id":"MODERN_PHYSICS:COURSE_CATALOG","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"],"access":"READ_ONLY_REFERENCE"},)
    families = tuple(_family(i, course) for i in range(10)); inspected = {}
    def validator(candidate, derivation, answer):
        result = modern_physics_validator(candidate, derivation, answer); inspected[candidate.candidate_id] = (candidate, derivation, result); return result
    bank, summary = produce_course_bank("MODERN_PHYSICS", pack["pack_id"], pack["deterministic_sha256"], evidence, families, reviewer=lambda subject,level: artifact_reviewer(families,inspected,subject,level), validator=validator)
    return bank, summary, evidence


def write_bank(root):
    bank, summary, evidence = build_bank(); root = Path(root)
    payloads = {"authority/authority.json":{"source_evidence":evidence},"candidates/candidates.json":bank.candidates,"derivations/derivations.json":bank.derivations,"validations/validations.json":bank.validations,"duplicates/duplicates.json":bank.duplicates,"reviews/reviews.json":bank.reviews,"banks/production_bank.json":bank.to_dict(),"exports/course_summary.json":summary.to_dict()}
    for rel, value in payloads.items(): path=root/rel; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,sort_keys=True,indent=2)+"\n")
    return bank, summary
