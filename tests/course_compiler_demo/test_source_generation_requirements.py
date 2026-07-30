import pytest
from tools.course_compiler_demo.source_corpus.contracts import ContractError
from tools.course_compiler_demo.source_corpus.generation_requirements import *

def payload(i=1,status="READY",claims=("claim-1",),blockers=(),classifications=("EXISTING_SUPPORTED",)):
 return dict(requirement_id=f"req-{i}",course_id="course-1",unit_id="unit-1",topic_id="topic-1",micro_skill_id=f"skill-{i}",procedure_id=f"procedure-{i}",generation_family_id=f"family-{i}",recipe_requirement_id=f"recipe-{i}",answer_engine_type="numeric_scalar",requested_count=10,difficulty_allocation={"FOUNDATIONAL":.4,"ADVANCED":.6},question_type_allocation={"numeric_scalar":1.0},assessment_roles=("PRACTICE","FORMATIVE"),failure_signals=("UNIT_ERROR",),asset_policy="TEXT_ONLY",duplicate_constraints={"max_semantic_similarity":.9},dependency_classifications=classifications,evidence_claim_ids=claims,status=status,blockers=blockers)
def req(**changes):
 p=payload(); p.update(changes); return GenerationRequirementV1(**p)
def test_compiler_and_manifest_preserve_all_requirement_fields_without_generation():
 p=compile_generation_requirements(package_id="package-1",course_id="course-1",seed="seed-1",synthesized_requirements=(payload(),))
 m=build_generation_manifest(p)
 assert m.requirements[0].unit_id=="unit-1" and m.requirements[0].topic_id=="topic-1"
 assert m.requirements[0].recipe_requirement_id=="recipe-1" and m.requirements[0].assessment_roles==("PRACTICE","FORMATIVE")
 assert m.requirements[0].duplicate_constraints and generation_readiness(p)["question_generation_performed"] is False
@pytest.mark.parametrize("change",[
 {"unit_id":""},{"topic_id":""},{"recipe_requirement_id":""},{"difficulty_allocation":{"A":.4}},
 {"question_type_allocation":{}},{"assessment_roles":()},{"failure_signals":()},{"asset_policy":""},{"duplicate_constraints":{}},
 {"dependency_classifications":("UNKNOWN",)},{"status":"READY","dependency_classifications":("NEW_RECIPE_REQUIRED",)},
 {"status":"READY","dependency_classifications":("EXISTING_UNSUPPORTED",)},
])
def test_required_manifest_fields_and_dependencies_fail_closed(change):
 with pytest.raises(ContractError): req(**change)
def test_blocked_dependency_classes_and_asset_dependencies_are_reviewable():
 for classification in ("NEW_PROCEDURE_REQUIRED","NEW_GENERATION_FAMILY_REQUIRED","NEW_RECIPE_REQUIRED","NEW_ANSWER_ENGINE_REQUIRED","ASSET_DEPENDENCY","DIAGRAM_DEPENDENCY","OCR_DEPENDENCY"):
  item=req(status="BLOCKED_MISSING_EVIDENCE",evidence_claim_ids=(),blockers=(classification,),dependency_classifications=(classification,))
  assert item.status=="BLOCKED_MISSING_EVIDENCE"
def test_package_and_manifest_fail_closed():
 with pytest.raises(ContractError): GenerationRequirementsPackageV1("p","course-1",(req(),req()),"s")
 blocked=req(status="BLOCKED_CONFLICT",blockers=("conflict",))
 with pytest.raises(ContractError): build_generation_manifest(GenerationRequirementsPackageV1("p","course-1",(blocked,),"s"))
 with pytest.raises(ContractError): compile_generation_requirements(package_id="p",course_id="course-1",seed="s",synthesized_requirements=({"course_id":"course-1"},))
