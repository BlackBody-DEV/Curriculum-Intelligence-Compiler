"""Dashboard-local Calculus I demo procedures, practice, and assessment generation."""

from __future__ import annotations

import random
from collections import Counter
from typing import Any

from tools.course_compiler_demo.assessment_generation.exporters import write_exports
from tools.course_compiler_demo.assessment_generation.fingerprints import exact_fingerprint, structural_fingerprint
from tools.course_compiler_demo.assessment_generation.models import (
    ASSESSMENT_CONTRACT_VERSION,
    NON_LIVE_BOUNDARY,
    QUESTION_CONTRACT_VERSION,
    sha256_payload,
)
from tools.course_compiler_demo.assessment_generation.validators import review_record, validation_report


CALCULUS_FAMILY_ID = "GF_MATH_CALCULUS_I_FOUNDATIONS_V1"
CALCULUS_FAMILY_DISPLAY_NAME = "Calculus I Foundations - Accepted Curriculum Mix"
CALCULUS_REQUIRED_SKILLS = [
    "evaluate_a_limit",
    "apply_the_power_rule",
    "apply_the_chain_rule",
    "find_critical_points",
    "analyze_increasing_and_decreasing_intervals",
]


PROCEDURES = {
    "evaluate_a_limit": {
        "procedure_id": "PROC_DEMO_CALC_EVALUATE_LIMIT_V1",
        "topic_code": "limits",
        "topic": "Limits",
        "concept_statement": "Evaluate limits by simplifying the expression, then substituting when the resulting expression is defined.",
        "formula_or_rule": "If f is continuous at a, then lim x->a f(x) = f(a). Removable factors may be canceled before substitution.",
        "steps": ["Identify the approach value.", "Simplify removable factors if needed.", "Substitute the approach value.", "Report the exact value."],
        "worked_example": {"prompt": "Evaluate lim x->2 (x^2 - 4)/(x - 2).", "answer": "4", "check": "(x^2 - 4)/(x - 2) = x + 2, so at x=2 the value is 4."},
        "common_errors": ["Substituting before removing a zero denominator.", "Canceling terms instead of factors."],
    },
    "apply_the_power_rule": {
        "procedure_id": "PROC_DEMO_CALC_POWER_RULE_V1",
        "topic_code": "derivatives",
        "topic": "Derivatives",
        "concept_statement": "Differentiate each power term by multiplying by the exponent and reducing the exponent by one.",
        "formula_or_rule": "d/dx [a x^n] = a n x^(n-1) for positive integer n.",
        "steps": ["Apply the power rule to each term.", "Keep constant multiples.", "Drop constant terms.", "Combine like derivative terms."],
        "worked_example": {"prompt": "Differentiate f(x)=3x^4-2x+5.", "answer": "12x^3-2", "check": "3*4x^3 - 2 + 0 = 12x^3 - 2."},
        "common_errors": ["Leaving the exponent unchanged.", "Differentiating constants as one."],
    },
    "apply_the_chain_rule": {
        "procedure_id": "PROC_DEMO_CALC_CHAIN_RULE_V1",
        "topic_code": "derivatives",
        "topic": "Derivatives",
        "concept_statement": "Differentiate the outside function and multiply by the derivative of the inside function.",
        "formula_or_rule": "d/dx [(g(x))^n] = n(g(x))^(n-1)g'(x).",
        "steps": ["Identify the inside function g(x).", "Differentiate the outside power.", "Multiply by g'(x).", "Simplify constants."],
        "worked_example": {"prompt": "Differentiate f(x)=(2x+3)^4.", "answer": "8(2x+3)^3", "check": "4(2x+3)^3 * 2 = 8(2x+3)^3."},
        "common_errors": ["Forgetting the inside derivative.", "Multiplying by the exponent twice."],
    },
    "find_critical_points": {
        "procedure_id": "PROC_DEMO_CALC_FIND_CRITICAL_POINTS_V1",
        "topic_code": "applications_of_derivatives",
        "topic": "Applications of Derivatives",
        "concept_statement": "Critical points occur where the derivative is zero or undefined and the original function is defined.",
        "formula_or_rule": "For differentiable polynomials, solve f'(x)=0.",
        "steps": ["Differentiate the function.", "Set the derivative equal to zero.", "Solve exactly.", "Report x-values in the domain."],
        "worked_example": {"prompt": "Find critical points of f(x)=x^2-6x+4.", "answer": "x=3", "check": "f'(x)=2x-6, so 2x-6=0 gives x=3."},
        "common_errors": ["Solving f(x)=0 instead of f'(x)=0.", "Reporting y-values only."],
    },
    "analyze_increasing_and_decreasing_intervals": {
        "procedure_id": "PROC_DEMO_CALC_INCREASING_DECREASING_V1",
        "topic_code": "applications_of_derivatives",
        "topic": "Applications of Derivatives",
        "concept_statement": "Use the sign of f'(x) on intervals split by critical numbers to classify increasing and decreasing behavior.",
        "formula_or_rule": "f increases where f'(x)>0 and decreases where f'(x)<0.",
        "steps": ["Find derivative sign-change points.", "Create intervals around them.", "Test the derivative sign on each interval.", "Label increasing and decreasing intervals."],
        "worked_example": {"prompt": "Analyze f'(x)=(x-1)(x-3).", "answer": "Increasing on (-infinity,1) and (3,infinity); decreasing on (1,3).", "check": "The derivative is positive outside the roots and negative between them."},
        "common_errors": ["Testing f(x) instead of f'(x).", "Reversing the sign intervals."],
    },
}


def calculus_family() -> dict[str, Any]:
    return {
        "generation_family_id": CALCULUS_FAMILY_ID,
        "display_name": CALCULUS_FAMILY_DISPLAY_NAME,
        "contract_version": "assessment_generation_family_v1",
        "family_version": "1.0.0",
        "family_type": "dashboard_calculus_i_foundations_mix",
        "subject_code": "MATHEMATICS",
        "course_level": "CALCULUS_I",
        "topic_code": "calculus_i_foundations",
        "subtopic_code": "source_aligned_foundations",
        "supported_micro_skills": list(CALCULUS_REQUIRED_SKILLS),
        "target_micro_skill_code": "calculus_i_foundations_mix",
        "approved_procedure_code": "PROC_DEMO_CALC_FOUNDATIONS_MIX_V1",
        "approved_prerequisite_skills": [],
        "question_types": ["calculus_exact_response"],
        "answer_adapter_type": "exact_symbolic_or_interval",
        "accepted_units": ["none"],
        "grading_type": "exact_demo",
        "tolerance": {"absolute": 0},
        "reasoning_sequence": ["identify_skill", "apply_procedure", "verify_exact_answer"],
        "structural_signature_fields": ["micro_skill_code", "template", "parameters"],
        "known_failure_modes": ["algebra_error", "rule_selection_error", "sign_interval_error"],
        "rights_boundary": dict(NON_LIVE_BOUNDARY),
        "question_origin": "axiomiq_original_generated_demo",
        "human_review_required": True,
        "enabled": True,
    }


def procedure_candidates() -> list[dict[str, Any]]:
    candidates = []
    for skill_code in CALCULUS_REQUIRED_SKILLS:
        item = PROCEDURES[skill_code]
        candidates.append({
            **item,
            "subject": "MATHEMATICS",
            "course_level": "CALCULUS_I",
            "micro_skill_code": skill_code,
            "status": "demo_unverified",
            "noncanonical": True,
            "canonical_approved": False,
            "eligible_for_alpha_import": False,
            "student_visible": False,
            "human_review_required": True,
        })
    return candidates


def _format_poly(terms: list[tuple[int, int]]) -> str:
    pieces = []
    for coeff, exp in terms:
        if coeff == 0:
            continue
        sign = "-" if coeff < 0 else "+"
        mag = abs(coeff)
        if exp == 0:
            body = str(mag)
        elif exp == 1:
            body = "x" if mag == 1 else f"{mag}x"
        else:
            body = f"x^{exp}" if mag == 1 else f"{mag}x^{exp}"
        pieces.append((sign, body))
    if not pieces:
        return "0"
    first_sign, first_body = pieces[0]
    text = f"-{first_body}" if first_sign == "-" else first_body
    for sign, body in pieces[1:]:
        text += f" {sign} {body}"
    return text


def _question_for(skill: str, slot_index: int, difficulty: str, seed: int) -> dict[str, Any]:
    rng = random.Random(f"{seed}:{slot_index}:{skill}")
    proc = PROCEDURES[skill]
    if skill == "evaluate_a_limit":
        a = rng.choice([1, 2, 3, 4, -1, -2])
        b = rng.choice([2, 3, 5, -2])
        c = rng.choice([1, 2, -1])
        if difficulty == "advanced":
            prompt = f"Evaluate lim x->{a} ((x - {a})({b}x + {c}))/(x - {a})."
            answer = str(b * a + c)
            params = {"template": "removable_linear_factor", "a": a, "b": b, "c": c}
            solution = [f"Cancel the common factor x - {a}.", f"Substitute x={a} into {b}x + {c}.", f"The limit is {answer}."]
        else:
            prompt = f"Evaluate lim x->{a} ({b}x + {c})."
            answer = str(b * a + c)
            params = {"template": "linear_direct_substitution", "a": a, "b": b, "c": c}
            solution = [f"The expression is continuous at x={a}.", f"Substitute x={a}: {b}({a}) + {c} = {answer}."]
    elif skill == "apply_the_power_rule":
        coeff = rng.choice([2, 3, 4, -2, -3])
        exp = rng.choice([2, 3, 4, 5])
        const = rng.choice([0, 1, -4, 5])
        prompt = f"Differentiate f(x) = {_format_poly([(coeff, exp), (const, 0)])}."
        answer = _format_poly([(coeff * exp, exp - 1)])
        params = {"template": "monomial_power_rule", "coeff": coeff, "exp": exp, "const": const}
        solution = [f"Apply d/dx [a x^n] = an x^(n-1).", f"{coeff}*{exp}x^{exp - 1} gives {answer}.", "The constant derivative is 0."]
    elif skill == "apply_the_chain_rule":
        a = rng.choice([2, 3, 4])
        b = rng.choice([1, -1, 2, 5])
        n = rng.choice([2, 3, 4, 5])
        prompt = f"Differentiate f(x) = ({a}x + {b})^{n}."
        answer = f"{n * a}({a}x + {b})^{n - 1}"
        params = {"template": "linear_inside_power", "a": a, "b": b, "n": n}
        solution = [f"Let g(x)={a}x + {b}, so g'(x)={a}.", f"Use n(g(x))^(n-1)g'(x).", f"The derivative is {answer}."]
    elif skill == "find_critical_points":
        r = rng.choice([-3, -2, -1, 1, 2, 3, 4])
        c = rng.choice([-5, 0, 4])
        prompt = f"Find the critical point of f(x) = x^2 {'-' if 2*r > 0 else '+'} {abs(2*r)}x {'+' if c >= 0 else '-'} {abs(c)}."
        answer = f"x = {r}"
        params = {"template": "quadratic_single_critical_point", "root": r, "c": c}
        solution = [f"Differentiate: f'(x)=2x - {2*r}.", f"Set f'(x)=0: 2x - {2*r}=0.", f"The critical point occurs at {answer}."]
    else:
        r1 = rng.choice([-3, -2, -1, 0, 1])
        r2 = rng.choice([2, 3, 4, 5])
        prompt = f"For a function with f'(x) = (x - {r1})(x - {r2}), identify where f is increasing and decreasing."
        answer = f"increasing: (-infinity, {r1}) and ({r2}, infinity); decreasing: ({r1}, {r2})"
        params = {"template": "two_root_derivative_sign_chart", "r1": r1, "r2": r2}
        solution = [f"The derivative roots are x={r1} and x={r2}.", "The product is positive outside the roots and negative between them.", answer]
    return {
        "skill": skill,
        "procedure": proc,
        "prompt": prompt,
        "answer": answer,
        "params": params,
        "solution": solution,
    }


def _make_question(assessment_id: str, slot_index: int, skill: str, difficulty: str, seed: int) -> dict[str, Any]:
    built = _question_for(skill, slot_index, difficulty, seed)
    proc = built["procedure"]
    question = {
        "contract_version": QUESTION_CONTRACT_VERSION,
        "question_id": f"{assessment_id}_Q{slot_index:03d}",
        "assessment_id": assessment_id,
        "slot_id": f"SLOT_{slot_index:03d}",
        "generation_family_id": CALCULUS_FAMILY_ID,
        "generation_family_version": "1.0.0",
        "subject_code": "MATHEMATICS",
        "topic_code": proc["topic_code"],
        "subtopic_code": "dashboard_demo",
        "micro_skill_code": skill,
        "procedure_code": proc["procedure_id"],
        "prerequisite_skills_used": [],
        "difficulty": difficulty,
        "question_type": "calculus_exact_response",
        "question_origin": "axiomiq_original_generated_demo",
        "parameter_set": {"micro_skill_code": skill, **built["params"]},
        "scenario_template_id": "dashboard_calculus_demo",
        "prompt": built["prompt"],
        "answer_input_schema": "exact_symbolic_or_interval",
        "accepted_units": ["none"],
        "grading_type": "exact_demo",
        "tolerance": {"absolute": 0},
        "expected_answer": {"value": built["answer"], "unit": "none"},
        "solution_steps": built["solution"],
        "known_failure_modes": calculus_family()["known_failure_modes"],
        "scope_validation": {"status": "pass"},
        "answer_validation": {"status": "pass"},
        "generation_seed": f"{seed}:{slot_index}:{skill}",
        "generation_attempt": 1,
        "review_status": "pending",
        "locked": False,
        "validation_status": "pass",
        "status": "demo_unverified",
        "rights_status": "generated_demo",
        "noncanonical": True,
        "canonical_approved": False,
        "eligible_for_alpha_import": False,
        "student_visible": False,
        "human_review_required": True,
    }
    family = calculus_family()
    question["exact_fingerprint"] = exact_fingerprint(question)
    question["structural_fingerprint"] = structural_fingerprint(question, family)
    return question


def skill_sequence(accepted_skills: list[str], count: int) -> list[str]:
    compatible = [skill for skill in CALCULUS_REQUIRED_SKILLS if skill in set(accepted_skills)]
    if not compatible:
        raise ValueError("no compatible Calculus I skills accepted")
    sequence: list[str] = []
    while len(sequence) < count:
        sequence.extend(compatible)
    return sequence[:count]


def generate_calculus_assessment(blueprint: dict[str, Any], accepted_skills: list[str]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    seed = int(blueprint["random_seed"])
    skills = skill_sequence(accepted_skills, int(blueprint["question_count"]))
    difficulties = (["foundational", "standard", "advanced"] * 4)[: len(skills)]
    questions = [_make_question(blueprint["assessment_id"], i, skill, difficulties[i - 1], seed) for i, skill in enumerate(skills, start=1)]
    exact = [q["exact_fingerprint"] for q in questions]
    structural = [q["structural_fingerprint"] for q in questions]
    if len(exact) != len(set(exact)) or len(structural) != len(set(structural)):
        raise ValueError("duplicate Calculus question generated")
    duplicate_report = {
        "requested_count": int(blueprint["question_count"]),
        "generated_count": len(questions),
        "rejected_exact_duplicates": 0,
        "rejected_structural_duplicates": 0,
        "parameter_space_exhausted": False,
        "exact_fingerprints": sorted(exact),
        "structural_fingerprints": sorted(structural),
    }
    assessment = {
        "contract_version": ASSESSMENT_CONTRACT_VERSION,
        "assessment_id": blueprint["assessment_id"],
        "title": blueprint["title"],
        "assessment_type": blueprint["assessment_type"],
        "subject_code": "MATHEMATICS",
        "course_level": "CALCULUS_I",
        "topic_codes": sorted({q["topic_code"] for q in questions}),
        "micro_skill_codes": [q["micro_skill_code"] for q in questions],
        "generation_family_ids": [CALCULUS_FAMILY_ID],
        "review_status": "review_pending",
        "validation_status": "pass",
        "non_live_boundary": dict(NON_LIVE_BOUNDARY),
        "micro_skill_distribution": dict(Counter(q["micro_skill_code"] for q in questions)),
        "questions": questions,
    }
    decisions = {
        "contract_version": "assessment_review_decisions_v1",
        "assessment_id": blueprint["assessment_id"],
        "review_records": [review_record(question_id=q["question_id"], decision="pending") for q in questions],
    }
    return assessment, duplicate_report, decisions


def regenerate_calculus_question(assessment: dict[str, Any], blueprint: dict[str, Any], slot_id: str, child_seed: int) -> dict[str, Any]:
    existing = next(q for q in assessment["questions"] if q["slot_id"] == slot_id)
    if existing.get("locked"):
        raise ValueError("locked question cannot be regenerated")
    slot_index = int(slot_id.rsplit("_", 1)[1])
    replacement = _make_question(blueprint["assessment_id"], slot_index, existing["micro_skill_code"], existing["difficulty"], child_seed)
    replacement["slot_id"] = slot_id
    replacement["question_id"] = existing["question_id"] + "_R001"
    return replacement


def write_calculus_assessment(output_dir, blueprint: dict[str, Any], assessment: dict[str, Any], duplicate_report: dict[str, Any], decisions: dict[str, Any]) -> None:
    from tools.course_compiler_demo.assessment_generation.models import write_json

    output_dir.mkdir(parents=True, exist_ok=True)
    validation = validation_report(assessment=assessment, duplicate_report=duplicate_report, errors=[])
    write_json(output_dir / "assessment_blueprint.json", blueprint)
    write_json(output_dir / "generation_manifest.json", {
        "assessment_id": blueprint["assessment_id"],
        "generation_family_id": CALCULUS_FAMILY_ID,
        "random_seed": blueprint["random_seed"],
        "generated_count": len(assessment["questions"]),
        "validation_status": validation["validation_status"],
        "non_live_boundary": assessment["non_live_boundary"],
    })
    write_json(output_dir / "generated_assessment.json", assessment)
    write_json(output_dir / "duplicate_report.json", duplicate_report)
    write_json(output_dir / "validation_report.json", validation)
    write_json(output_dir / "review_decisions.json", decisions)
    write_exports(assessment, output_dir)


def practice_package(run_id: str, accepted_skills: list[str], seed: int = 2026072301) -> dict[str, Any]:
    skills = skill_sequence(accepted_skills, 10)
    items = []
    for i, skill in enumerate(skills, start=1):
        q = _make_question(f"PRACTICE_{run_id}", i, skill, "foundational" if i <= 4 else "standard", seed)
        items.append({
            "practice_item_id": f"PRACTICE_ITEM_{i:03d}",
            "question_id": q["question_id"],
            "procedure_code": q["procedure_code"],
            "micro_skill_code": q["micro_skill_code"],
            "prompt": q["prompt"],
            "answer": q["expected_answer"],
            "solution_steps": q["solution_steps"],
            "difficulty": q["difficulty"],
            "exact_fingerprint": q["exact_fingerprint"],
            "structural_fingerprint": q["structural_fingerprint"],
            "student_visible": False,
        })
    omitted = [skill for skill in CALCULUS_REQUIRED_SKILLS if skill not in set(accepted_skills)]
    return {
        "practice_package_id": f"PRACTICE_CALCULUS_I_FOUNDATIONS_{run_id}",
        "title": "Calculus I Foundations Practice",
        "status": "demo_unverified",
        "noncanonical": True,
        "canonical_approved": False,
        "eligible_for_alpha_import": False,
        "student_visible": False,
        "human_review_required": True,
        "source_run_id": run_id,
        "generation_family_id": CALCULUS_FAMILY_ID,
        "practice_item_count": len(items),
        "micro_skill_distribution": dict(Counter(item["micro_skill_code"] for item in items)),
        "performance_metrics": ["accuracy_by_micro_skill", "first_attempt_correct", "review_required_count"],
        "readiness_condition": "demo-only: 8 of 10 correct with no canonical or student-visible promotion",
        "content_gaps": [{"gap_id": f"OMITTED_{skill.upper()}", "description": f"No accepted review decision for {skill}."} for skill in omitted],
        "items": items,
    }
