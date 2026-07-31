import pytest
from tools.course_compiler_demo.source_corpus.contracts import ContractError
from tools.course_compiler_demo.source_corpus.generation_requirements import *

def payload(i=1,status="READY",claims=("claim-1",),blockers=(),classifications=("EXISTING_SUPPORTED",)):
 return dict(requirement_id=f"req-{i}",course_id="course-1",unit_id="unit-1",topic_id="topic-1",micro_skill_id=f"skill-{i}",procedure_id=f"procedure-{i}",generation_family_id=f"family-{i}",recipe_requirement_id=f"recipe-{i}",answer_engine_type="numeric_scalar",requested_count=10,difficulty_allocation={"FOUNDATIONAL":.4,"ADVANCED":.6},question_type_allocation={"numeric_scalar":1.0},assessment_roles=("PRACTICE","FORMATIVE"),failure_signals=("UNIT_ERROR",),asset_policy="TEXT_ONLY",duplicate_constraints={"max_semantic_similarity":.9},dependency_classifications=classifications,evidence_claim_ids=claims,status=status,blockers=blockers)
def req(**changes):
 p=payload(); p.update(changes); return GenerationRequirementV1(**p)
def test_compiler_and_manifest_preserve_all_requirement_fields_without_generation():
 p=compile_generation_requirements(package_id="package-1",course_id="course-1",seed="seed-1",synthesized_requirements=(payload(),),known_evidence_claim_ids={"claim-1"})
 m=build_generation_manifest(p)
 item=m.requirements[0]
 assert (item.course_id,item.unit_id,item.topic_id,item.micro_skill_id)==("course-1","unit-1","topic-1","skill-1")
 assert (item.procedure_id,item.generation_family_id,item.recipe_requirement_id,item.answer_engine_type)==("procedure-1","family-1","recipe-1","numeric_scalar")
 assert item.requested_count==10 and item.difficulty_allocation=={"FOUNDATIONAL":.4,"ADVANCED":.6}
 assert item.question_type_allocation=={"numeric_scalar":1.0} and item.assessment_roles==("PRACTICE","FORMATIVE")
 assert item.failure_signals==("UNIT_ERROR",) and item.asset_policy=="TEXT_ONLY" and item.duplicate_constraints=={"max_semantic_similarity":.9}
 assert item.evidence_claim_ids==("claim-1",) and generation_readiness(p)["question_generation_performed"] is False
@pytest.mark.parametrize("change",[
 {"unit_id":""},{"topic_id":""},{"recipe_requirement_id":""},{"difficulty_allocation":{"A":.4}},
 {"question_type_allocation":{}},{"assessment_roles":()},{"failure_signals":()},{"asset_policy":""},{"duplicate_constraints":{}},
 {"difficulty_allocation":{"A":float("nan")}}, {"question_type_allocation":{"A":float("inf")}},
 {"evidence_claim_ids":("",)}, {"failure_signals":("UNIT_ERROR","UNIT_ERROR")},
 {"duplicate_constraints":{"policy":float("nan")}},
 {"dependency_classifications":("UNKNOWN",)},{"status":"READY","dependency_classifications":("NEW_RECIPE_REQUIRED",)},
 {"status":"READY","dependency_classifications":("EXISTING_UNSUPPORTED",)},
 {"status":"READY","dependency_classifications":("ASSET_DEPENDENCY",)},
 {"dependency_classifications":("EXISTING_SUPPORTED","EXISTING_UNSUPPORTED")},
])
def test_required_manifest_fields_and_dependencies_fail_closed(change):
 with pytest.raises(ContractError): req(**change)
def test_blocked_dependency_classes_and_asset_dependencies_are_reviewable():
 for classification in ("EXISTING_UNSUPPORTED","NEW_PROCEDURE_REQUIRED","NEW_GENERATION_FAMILY_REQUIRED","NEW_RECIPE_REQUIRED","NEW_ANSWER_ENGINE_REQUIRED","ASSET_DEPENDENCY","DIAGRAM_DEPENDENCY","OCR_DEPENDENCY"):
  item=req(status="BLOCKED_MISSING_EVIDENCE",evidence_claim_ids=(),blockers=(classification,),dependency_classifications=(classification,))
  assert item.status=="BLOCKED_MISSING_EVIDENCE"
def test_package_and_manifest_fail_closed():
 with pytest.raises(ContractError): GenerationRequirementsPackageV1("p","course-1",(req(),req()),"s")
 blocked=req(status="BLOCKED_CONFLICT",blockers=("conflict",))
 with pytest.raises(ContractError): build_generation_manifest(GenerationRequirementsPackageV1("p","course-1",(blocked,),"s"))
 with pytest.raises(ContractError): compile_generation_requirements(package_id="p",course_id="course-1",seed="s",synthesized_requirements=({"course_id":"course-1"},),known_evidence_claim_ids={"claim-1"})

def test_evidence_resolution_and_deterministic_compilation_fail_closed():
 with pytest.raises(ContractError):
  compile_generation_requirements(package_id="p",course_id="course-1",seed="s",synthesized_requirements=(payload(),),known_evidence_claim_ids=set())
 with pytest.raises(ContractError):
  compile_generation_requirements(package_id="p",course_id="course-1",seed="s",synthesized_requirements=[payload()],known_evidence_claim_ids={"claim-1"})
 package=compile_generation_requirements(package_id="p",course_id="course-1",seed="s",synthesized_requirements=(payload(2),payload(1)),known_evidence_claim_ids={"claim-1"})
 assert tuple(item.requirement_id for item in package.requirements)==("req-1","req-2")
 assert package.to_json()==compile_generation_requirements(package_id="p",course_id="course-1",seed="s",synthesized_requirements=(payload(1),payload(2)),known_evidence_claim_ids={"claim-1"}).to_json()

def test_blocker_and_manifest_boundaries_are_strict():
 with pytest.raises(ContractError): req(status="BLOCKED_MISSING_EVIDENCE",evidence_claim_ids=(),blockers=("",),dependency_classifications=("OCR_DEPENDENCY",))
 with pytest.raises(ContractError): req(status="BLOCKED_CONFLICT",evidence_claim_ids=(),blockers=("conflict",))
 with pytest.raises(ContractError): GenerationRequirementsPackageV1("p","course-1",[req()],"s")
 for field in ("manifest_id","package_id","course_id","seed"):
  values=dict(manifest_id="m",package_id="p",course_id="course-1",requirements=(req(),),seed="s")
  values[field]=""
  with pytest.raises(ContractError): GenerationManifestV1(**values)
 with pytest.raises(ContractError): GenerationManifestV1("m","p","course-1",[req()],"s")
 with pytest.raises(ContractError): GenerationManifestV1("m","p","course-1",("not-a-requirement",),"s")
 with pytest.raises(ContractError): GenerationManifestV1("m","p","course-1",(req(),req()),"s")

def test_public_helpers_require_typed_packages():
 with pytest.raises(ContractError): build_generation_manifest({})
 with pytest.raises(ContractError): generation_readiness({})
