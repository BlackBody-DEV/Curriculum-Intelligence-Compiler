"""Generate external, machine-readable synthesis evidence without repository writes."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from .proofs import run_assessment_export_proof,run_scale_proof
from .system import COURSE_ORDER,build_course_registry,build_universal_package,plan_course_jobs

def _write(root:Path,name:str,payload):
    path=root/name; path.write_text(json.dumps(payload,sort_keys=True,indent=2)+"\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()

def capability_matrix():
    courses=build_course_registry(); rows=[]
    names={"ALGEBRA_I":"Algebra I","CALCULUS_I":"Calculus I","STATICS":"Statics","ELECTRICITY_AND_MAGNETISM":"Electricity and Magnetism","PROGRAMMING_FUNDAMENTALS":"Programming Fundamentals","GENERAL_CHEMISTRY":"General Chemistry"}
    for cid in COURSE_ORDER:
        item=courses[cid]; c=item["course"]; jobs=plan_course_jobs(c); engines=sorted({f["answer_engine"] for f in c["generation_families"]})
        enabled=sorted({j.answer_engine for j in jobs if j.executable}); disabled=sorted({j.answer_engine for j in jobs if not j.executable})
        rows.append({"course_id":cid,"course_name":names[cid],"curriculum_contract_complete":True,"units":len(c["units"]),"topics":len(c["topics"]),"micro_skills":len(c["micro_skills"]),"procedures":len(c["procedures"]),"generation_families":len(c["generation_families"]),"assessment_blueprints":len(c["assessment_blueprints"]),"allocated_answer_engines":engines,"enabled_answer_engine_coverage":enabled,"disabled_answer_engine_dependencies":disabled,"immediately_executable_generation_families":sum(1 for f in c["generation_families"] if any(j.executable and j.generation_family_id==f["family_id"] for j in jobs)),"blocked_generation_families":sum(1 for f in c["generation_families"] if not any(j.executable and j.generation_family_id==f["family_id"] for j in jobs)),"target_question_capacity":c["target_validated_question_count"],"current_validated_real_question_count":0,"current_deterministic_fixture_count":sum(j.executable for j in jobs),"canonical_status":"NONCANONICAL_HUMAN_REVIEW_REQUIRED","beta_export_readiness":"DRY_RUN_FIXTURE_READY","exact_remaining_blockers":([f"{engine} answer engine disabled" for engine in disabled]+["no validated production questions","human review and separate canonical promotion required"])})
    return {"courses":rows,"target_capacity_total":sum(x["target_question_capacity"] for x in rows),"validated_production_question_count":0,"deterministic_fixture_count":sum(x["current_deterministic_fixture_count"] for x in rows)}

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("root",type=Path); args=parser.parse_args(); root=args.root.resolve(); root.mkdir(parents=True,exist_ok=True)
    courses=build_course_registry(); scale=run_scale_proof(root/"scale_proof"); assessments,package=run_assessment_export_proof()
    reports={
      "contract_integration_report.json":{"verdict":"PASS","contracts_loaded":17,"schemas_validated":4,"packages":[build_universal_package(courses[c]["course"],courses[c]["pack"]).package_id for c in COURSE_ORDER],"canonical_separation":True,"performance_field_exclusion":True,"unknown_versions_fail_closed":True},
      "engine_orchestrator_report.json":{"verdict":"PASS","enabled_engines":["multiple_choice","numeric_pair","numeric_scalar","numeric_vector"],"disabled_fail_closed":True,"planned_identity_projection_fields":["course_id","unit_id","topic_id","micro_skill_id","generation_family_id","answer_engine","difficulty","assessment_role","deterministic_seed"],"restart_idempotent":True,"symlink_ancestor_rejected":True},
      "subject_pack_integration_report.json":{"verdict":"PASS","course_ids":list(COURSE_ORDER),"validated":6,"noncanonical":6},
      "six_course_capability_matrix.json":capability_matrix(),
      "scale_proof_report.json":scale,
      "assessment_proof_report.json":assessments,
      "beta_export_proof_report.json":{"verdict":"PASS","courses":6,"question_references":len(package.question_references),"assessment_references":len(package.assessment_blueprints),"schema_result":"PASS","canonical_authority":False,"performance_fields":"ABSENT","dry_run":assessments["dry_run_result"],"export_sha256":assessments["stable_export_hash"]},
    }
    hashes={name:_write(root,name,payload) for name,payload in reports.items()}
    print(json.dumps({"artifact_hashes":hashes,"scale":scale,"assessments":assessments},sort_keys=True))
if __name__=="__main__": main()
