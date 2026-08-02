"""Math 113 Pre-Algebra checkpoint: 75 questions completing the first 100."""
from __future__ import annotations
import hashlib
import json
from typing import Any
from tools.course_compiler_demo.generation_recipes import GenerationContextV1
from tools.course_compiler_demo.universal_integration.capability_catalog_wave_044 import (
    compile_course_pilot, discover_course_catalog, discover_generation_recipe_runtime,
)
COURSE_ID = "PRE_ALGEBRA"
FIRST_NEW_VARIANT = 5
LAST_NEW_VARIANT = 19

def _prompt_fingerprint(prompt: str) -> str:
    return hashlib.sha256(" ".join(prompt.strip().lower().split()).encode()).hexdigest()

def build_checkpoint_bank() -> tuple[tuple[dict[str, Any], ...], dict[str, Any]]:
    catalog = discover_course_catalog()
    course = catalog["new"][COURSE_ID]
    orchestration = discover_generation_recipe_runtime(catalog["new"])
    existing = compile_course_pilot(course, orchestration)
    if existing["status"] != "PASS" or existing["validated"] != 25 or existing["locked"] != 25:
        raise ValueError("authoritative 25-question starting bank is unavailable")
    accepted = [row for row in orchestration["accepted"].values() if row["recipe"].binding.course_id == COURSE_ID]
    if len(accepted) != 5:
        raise ValueError("exactly five existing course recipes are required")
    seen_semantic = {q["semantic_fingerprint"] for q in existing["questions"]}
    seen_prompts = {_prompt_fingerprint(q["prompt"]) for q in existing["questions"]}
    existing_ids = {q["candidate_id"] for q in existing["questions"]}
    rows = []
    difficulties = ("FOUNDATIONAL", "DEVELOPING", "ADVANCED")
    for row in sorted(accepted, key=lambda item: item["recipe"].recipe_id):
        recipe = row["recipe"]; binding = recipe.binding; family = row["family"]
        for variant in range(FIRST_NEW_VARIANT, LAST_NEW_VARIANT + 1):
            context = GenerationContextV1(binding, row["topic"]["title"], row["skill"]["title"],
                tuple(row["procedure"]["steps"]), f"math113:{COURSE_ID}:{binding.family_id}", variant)
            result = orchestration["runtime"].generate(recipe.recipe_id, context, family)
            contract = recipe.build_contract(dict(result.parameters))
            semantic_fingerprint = result.content_sha256
            prompt_fingerprint = _prompt_fingerprint(result.prompt)
            question_id = f"production-question:{COURSE_ID.lower()}:{recipe.recipe_id.rsplit(':', 1)[-1].lower()}:{variant:02d}"
            operation_statuses = {"normalization": result.normalization_result.status,
                "independent_derivation": result.derivation_result.status, "grading": result.grading_result.status}
            if any(status != "PASS" for status in operation_statuses.values()):
                raise ValueError("answer-engine validation failed closed")
            if question_id in existing_ids or semantic_fingerprint in seen_semantic or prompt_fingerprint in seen_prompts:
                raise ValueError("duplicate against existing or newly generated question")
            seen_semantic.add(semantic_fingerprint); seen_prompts.add(prompt_fingerprint); existing_ids.add(question_id)
            validation = {"operation_statuses": operation_statuses,
                "normalization_result": result.normalization_result.to_dict(),
                "derivation_result": result.derivation_result.to_dict(),
                "grading_result": result.grading_result.to_dict(),
                "procedure_compatible": binding.procedure_id == row["procedure"]["procedure_id"],
                "prompt_determinate": bool(result.prompt.strip()) and "{{" not in result.prompt,
                "failure_signals_valid": bool(family.get("failure_signals")),
                "answer_contract_valid": contract.engine_type == binding.engine_type}
            rows.append({"question_id": question_id, "course_id": COURSE_ID,
                "unit_id": row["topic"]["unit_id"], "topic_id": binding.topic_id, "subtopic_ids": [],
                "micro_skill_id": binding.micro_skill_id, "procedure_id": binding.procedure_id,
                "generation_family_id": binding.family_id, "recipe_id": recipe.recipe_id,
                "difficulty": difficulties[(variant - FIRST_NEW_VARIANT) % len(difficulties)],
                "prompt": result.prompt, "normalized_answer": result.normalized_answer,
                "answer_contract": contract.to_dict(),
                "grading_rule": {"engine_type": binding.engine_type, "normalization_required": True,
                    "independent_derivation_required": True, "unsupported_shapes_fail_closed": True},
                "failure_signals": tuple(family.get("failure_signals", ())),
                "provenance": {"provider": row["provider"], "recipe_version": recipe.recipe_version,
                    "deterministic_seed": context.seed, "variant_index": variant,
                    "content_sha256": result.content_sha256},
                "semantic_fingerprint": semantic_fingerprint, "prompt_fingerprint": prompt_fingerprint,
                "duplicate_status": "UNIQUE", "production_status": "LOCKED_PRODUCTION_VALIDATED",
                "noncanonical": True, "student_visible": False,
                "independent_derivation": result.derivation_result.to_dict(), "validation": validation})
    identities = {row["question_id"] for row in rows}
    semantic = {row["semantic_fingerprint"] for row in rows}
    prompts = {row["prompt_fingerprint"] for row in rows}
    if len(rows) != 75 or len(identities) != 75 or len(semantic) != 75 or len(prompts) != 75:
        raise ValueError("75-question uniqueness contract failed")
    gates = ("procedure_compatible", "prompt_determinate", "failure_signals_valid", "answer_contract_valid")
    if not all(all(row["validation"][key] for key in gates) for row in rows):
        raise ValueError("question metadata validation failed")
    payload_hash = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":"), default=list).encode()).hexdigest()
    return tuple(rows), {"course_id": COURSE_ID, "before": 25, "added": 75, "after": 100,
        "generated": 75, "validated": 75, "locked": 75, "exact_duplicates": 0,
        "identity_duplicates": 0, "prompt_duplicates": 0, "fingerprint_duplicates": 0,
        "bank_sha256": payload_hash, "status": "PASS"}

def audit_checkpoint() -> dict[str, Any]:
    rows, summary = build_checkpoint_bank(); replay, replay_summary = build_checkpoint_bank()
    return {**summary, "deterministic_replay": summary["bank_sha256"] == replay_summary["bank_sha256"]
        and [row["question_id"] for row in rows] == [row["question_id"] for row in replay],
        "metadata_complete": all(row["semantic_fingerprint"] and row["prompt_fingerprint"]
        and row["production_status"] == "LOCKED_PRODUCTION_VALIDATED" for row in rows)}
