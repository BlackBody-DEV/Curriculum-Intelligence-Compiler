import json
from pathlib import Path
import pytest
from tools.course_compiler_demo.batch_generation import DeterministicFixtureProvider
from tools.course_compiler_demo.universal_core import BetaExportPackageV1,ContractError,UniversalCurriculumPackageV1
from tools.course_compiler_demo.universal_integration import *

def test_registries_and_six_universal_packages():
    services=build_service_registry(); assert tuple(services["subject_packs"])==COURSE_ORDER
    assert tuple(services["assessment_compilers"])==("universal_v1",) and "beta_v1" in services["beta_exporters"]
    for engine in ("numeric_scalar","numeric_pair","numeric_vector","multiple_choice"): assert services["answer_engines"].lookup(engine).status=="SUPPORTED"
    for cid,item in services["subject_packs"].items():
        package=build_universal_package(item["course"],item["pack"]); assert UniversalCurriculumPackageV1.from_json(package.to_json()).to_json()==package.to_json()
        assert package.source_evidence
        assert not item["pack"]["canonical_authority"] and item["pack"]["noncanonical"]

def test_1800_identity_planning_and_disabled_fail_closed():
    courses=build_course_registry(); jobs=[j for cid in COURSE_ORDER for j in plan_course_jobs(courses[cid]["course"])]
    assert len(jobs)==1800==len({j.job_id for j in jobs})
    assert len({(j.course_id,j.unit_id,j.topic_id,j.micro_skill_id,j.generation_family_id,j.job_id) for j in jobs})==1800
    blocked=[j for j in jobs if not j.executable]
    assert len(blocked)==120 and {j.answer_engine for j in blocked}=={"code_execution","chemical_reaction"}
    assert all(j.validated_status is None and j.blocker for j in blocked)

def test_scale_assessment_and_beta_proofs(tmp_path):
    scale=run_scale_proof(tmp_path/"scale"); assert scale["planned_jobs"]==1800 and scale["duplicates"]==0 and scale["manifest_deterministic"]
    assessment,package=run_assessment_export_proof()
    assert assessment["practice_assessments"]==assessment["summative_assessments"]==6 and assessment["variants"]==18
    assert BetaExportPackageV1.from_json(package.to_json()).to_json()==package.to_json() and assessment["dry_run_result"]["would_write"] is False
    bad=package.to_dict(); bad["source_evidence"]=({"student_id":"forbidden"},)
    with pytest.raises(ContractError): BetaExportPackageV1.from_dict(bad)
    for field in ("attempt","score","student analytics","student-analytics","studentAnalytics"):
        bad=package.to_dict(); bad["question_references"][0]["provenance"][field]="forbidden"
        with pytest.raises(ValueError): strict_beta_dry_run_validate(bad)
    assert all(q["source_evidence"] for q in package.question_references)

def test_secure_output_root_rejects_symlink_ancestor(tmp_path):
    repo=tmp_path/"repo"; repo.mkdir(); (repo/".git").mkdir(); alias=tmp_path/"alias"; alias.symlink_to(repo,target_is_directory=True)
    with pytest.raises(ValueError): secure_batch_orchestrator(alias/"outputs",DeterministicFixtureProvider())
    target=tmp_path/"plain"; target.mkdir(); plain_alias=tmp_path/"plain_alias"; plain_alias.symlink_to(target,target_is_directory=True)
    with pytest.raises(ValueError): secure_batch_orchestrator(plain_alias/"outputs",DeterministicFixtureProvider())

def test_course_isolation_and_determinism():
    courses=build_course_registry()
    for cid in COURSE_ORDER:
        a=plan_course_jobs(courses[cid]["course"]); b=plan_course_jobs(courses[cid]["course"])
        assert a==b and {x.course_id for x in a}=={cid}
