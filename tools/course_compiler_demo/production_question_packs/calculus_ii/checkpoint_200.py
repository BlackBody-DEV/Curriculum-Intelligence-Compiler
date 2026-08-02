"""Math 125 Calculus II checkpoint: 100 questions taking the course to 200."""
from __future__ import annotations
import hashlib,json
from collections import Counter
from typing import Any
from tools.course_compiler_demo.generation_recipes import GenerationContextV1
from tools.course_compiler_demo.universal_integration.capability_catalog_wave_044 import compile_course_pilot,discover_course_catalog,discover_generation_recipe_runtime
from .bank import _prompt_fingerprint,_structural_fingerprint,build_checkpoint_bank
COURSE_ID="CALCULUS_II"; FIRST_NEW_VARIANT=20

def build_checkpoint_200_bank()->tuple[tuple[dict[str,Any],...],dict[str,Any]]:
    catalog=discover_course_catalog(); course=catalog["new"][COURSE_ID]; orchestration=discover_generation_recipe_runtime(catalog["new"]); pilot=compile_course_pilot(course,orchestration); checkpoint_100,summary_100=build_checkpoint_bank()
    if pilot["validated"]!=25 or pilot["locked"]!=25 or summary_100["after"]!=100: raise ValueError("authoritative 100-question starting inventory is unavailable")
    accepted=[row for row in orchestration["accepted"].values() if row["recipe"].binding.course_id==COURSE_ID]
    if len(accepted)!=5: raise ValueError("exactly five existing course recipes are required")
    seen_ids={q["candidate_id"] for q in pilot["questions"]}|{q["question_id"] for q in checkpoint_100}; seen_semantic={q["semantic_fingerprint"] for q in pilot["questions"]}|{q["semantic_fingerprint"] for q in checkpoint_100}; seen_prompts={_prompt_fingerprint(q["prompt"]) for q in pilot["questions"]}|{q["prompt_fingerprint"] for q in checkpoint_100}
    rows=[]; difficulties=("FOUNDATIONAL","DEVELOPING","ADVANCED")
    for source in sorted(accepted,key=lambda item:item["recipe"].recipe_id):
        recipe=source["recipe"]; binding=recipe.binding; family=source["family"]; family_added=0
        for variant in range(FIRST_NEW_VARIANT,FIRST_NEW_VARIANT+1000):
            if family_added==20: break
            context=GenerationContextV1(binding,source["topic"]["title"],source["skill"]["title"],tuple(source["procedure"]["steps"]),f"math125:{COURSE_ID}:{binding.family_id}",variant); result=orchestration["runtime"].generate(recipe.recipe_id,context,family); contract=recipe.build_contract(dict(result.parameters)); semantic=result.content_sha256; prompt_fp=_prompt_fingerprint(result.prompt); question_id=f"production-question:{COURSE_ID.lower()}:math125:{recipe.recipe_id.rsplit(':',1)[-1].lower()}:{variant:02d}"
            statuses={"normalization":result.normalization_result.status,"independent_derivation":result.derivation_result.status,"grading":result.grading_result.status}
            if any(value!="PASS" for value in statuses.values()): raise ValueError("answer-engine validation failed closed")
            if question_id in seen_ids or semantic in seen_semantic or prompt_fp in seen_prompts: continue
            seen_ids.add(question_id); seen_semantic.add(semantic); seen_prompts.add(prompt_fp); validation={"operation_statuses":statuses,"normalization_result":result.normalization_result.to_dict(),"derivation_result":result.derivation_result.to_dict(),"grading_result":result.grading_result.to_dict(),"procedure_compatible":binding.procedure_id==source["procedure"]["procedure_id"] and len(source["procedure"]["steps"])>=3,"prompt_determinate":bool(result.prompt.strip()) and "{{" not in result.prompt,"failure_signals_valid":bool(family.get("failure_signals")),"answer_contract_valid":contract.engine_type==binding.engine_type}
            rows.append({"question_id":question_id,"course_id":COURSE_ID,"unit_id":source["topic"]["unit_id"],"topic_id":binding.topic_id,"subtopic_ids":[],"micro_skill_id":binding.micro_skill_id,"procedure_id":binding.procedure_id,"generation_family_id":binding.family_id,"recipe_id":recipe.recipe_id,"difficulty":difficulties[family_added%3],"coverage_mode":"MULTI_STEP" if contract.engine_type=="multiple_choice" else "DIRECT_APPLICATION","prompt":result.prompt,"normalized_answer":result.normalized_answer,"answer_contract":contract.to_dict(),"grading_rule":{"engine_type":binding.engine_type,"normalization_required":True,"independent_derivation_required":True,"unsupported_shapes_fail_closed":True},"failure_signals":tuple(family.get("failure_signals",())),"provenance":{"provider":source["provider"],"recipe_version":recipe.recipe_version,"deterministic_seed":context.seed,"variant_index":variant,"content_sha256":result.content_sha256},"semantic_fingerprint":semantic,"prompt_fingerprint":prompt_fp,"structural_fingerprint":_structural_fingerprint(result.prompt),"duplicate_status":"UNIQUE","production_status":"LOCKED_PRODUCTION_VALIDATED","noncanonical":True,"student_visible":False,"independent_derivation":result.derivation_result.to_dict(),"validation":validation}); family_added+=1
        if family_added!=20: raise ValueError("unable to allocate 20 unique variants for generation family")
    ids={q["question_id"] for q in rows}; semantics={q["semantic_fingerprint"] for q in rows}; prompts={q["prompt_fingerprint"] for q in rows}; gates=("procedure_compatible","prompt_determinate","failure_signals_valid","answer_contract_valid")
    if len(rows)!=100 or len(ids)!=100 or len(semantics)!=100 or len(prompts)!=100: raise ValueError("100-question uniqueness contract failed")
    if not all(all(q["validation"][gate] for gate in gates) for q in rows): raise ValueError("question metadata validation failed")
    families=Counter(q["generation_family_id"] for q in rows); structures=Counter(q["structural_fingerprint"] for q in rows); topics=Counter(q["topic_id"] for q in rows); modes=Counter(q["coverage_mode"] for q in rows)
    if len(families)<5 or max(families.values())>25 or max(structures.values())>25 or len(modes)!=2: raise ValueError("coverage or diversity gate failed")
    bank_hash=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":"),default=list).encode()).hexdigest()
    return tuple(rows),{"course_id":COURSE_ID,"before":100,"added":100,"after":200,"generated":100,"validated":100,"locked":100,"identity_duplicates":0,"prompt_duplicates":0,"fingerprint_duplicates":0,"exact_duplicates":0,"family_distribution":dict(sorted(families.items())),"topic_distribution":dict(sorted(topics.items())),"coverage_distribution":dict(sorted(modes.items())),"difficulty_levels":sorted({q["difficulty"] for q in rows}),"maximum_family_share":max(families.values())/100,"maximum_structural_share":max(structures.values())/100,"excessive_parameter_only_repetition":False,"bank_sha256":bank_hash,"status":"PASS"}

def audit_checkpoint_200()->dict[str,Any]:
    rows,summary=build_checkpoint_200_bank(); replay,replay_summary=build_checkpoint_200_bank()
    return {**summary,"deterministic_replay":summary["bank_sha256"]==replay_summary["bank_sha256"] and [q["question_id"] for q in rows]==[q["question_id"] for q in replay],"metadata_complete":all(q["semantic_fingerprint"] and q["prompt_fingerprint"] and q["production_status"]=="LOCKED_PRODUCTION_VALIDATED" for q in rows)}
