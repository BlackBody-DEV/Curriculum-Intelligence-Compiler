import pytest
from tools.course_compiler_demo.source_corpus.contracts import ContractError
from tools.course_compiler_demo.source_corpus.assessment_blueprints import *
def bp(kind="DIAGNOSTIC"):
 return SourceAssessmentBlueprintV1(f"bp-{kind.lower()}",kind,"course-1",2,10,{"topic-1":1.0},{"FOUNDATIONAL":.5,"ADVANCED":.5},{"numeric_scalar":1.0},("unit-1",),("skill-1","skill-2"),("prereq-1",),("claim-1",),("objective-1",),("family-1",),("engine-1",),("example-1",),{"allow_reuse":False},{"variant_count":3},{"points_per_question":1},({"rubric_id":"r1"},))
CTX=dict(course_id="course-1",unit_ids={"unit-1"},topic_ids={"topic-1"},micro_skill_ids={"skill-1","skill-2"},prerequisite_ids={"prereq-1"},evidence_claim_ids={"claim-1"},assessment_objective_courses={"objective-1":"course-1"},generation_family_courses={"family-1":"course-1"},grading_engine_courses={"engine-1":"course-1"},source_example_courses={"example-1":"course-1"})
def test_four_types_validate_and_project():
 for kind in ("PRACTICE","DIAGNOSTIC","FORMATIVE","SUMMATIVE"):
  item=bp(kind); assert validate_blueprint_blocking(item,**CTX)["valid"]
  projected=to_universal_blueprint(item); assert projected.blueprint_id==item.blueprint_id and projected.question_count==2
@pytest.mark.parametrize("change,kwargs",[
 ({"course_id":"other"},{}),({"unit_scope":("missing",)},{}),({"topic_weights":{"missing":1.0}},{}),
 ({"micro_skill_coverage":("missing",)},{}),({"prerequisite_coverage":("missing",)},{}),({"evidence_claim_ids":("missing",)},{}),
 ({}, {"blocking_conflicts":("conflict",)}),({}, {"coverage_gaps":("gap",)}),
 ({"assessment_objective_ids":("missing",)},{}),({"generation_family_ids":("missing",)},{}),
 ({"grading_engine_ids":("missing",)},{}),({"source_example_ids":("missing",)},{}),
 ({"assessment_objective_ids":("foreign",)},{"assessment_objective_courses":{**CTX["assessment_objective_courses"],"foreign":"course-2"}}),
 ({"generation_family_ids":("foreign",)},{"generation_family_courses":{**CTX["generation_family_courses"],"foreign":"course-2"}}),
 ({"grading_engine_ids":("foreign",)},{"grading_engine_courses":{**CTX["grading_engine_courses"],"foreign":"course-2"}}),
 ({"source_example_ids":("foreign",)},{"source_example_courses":{**CTX["source_example_courses"],"foreign":"course-2"}}),
 ({"question_count":20,"time_budget_minutes":10},{}),
])
def test_every_source_resolution_failure_blocks(change,kwargs):
 item=bp(); payload=item.to_dict(); payload.update(change); item=SourceAssessmentBlueprintV1(**payload)
 context={**CTX,**kwargs}
 with pytest.raises(ContractError): validate_blueprint_blocking(item,**context)
@pytest.mark.parametrize("change",[
 {"blueprint_type":"OTHER"},{"topic_weights":{"t":.5}},{"unit_scope":()},{"micro_skill_coverage":()},
 {"evidence_claim_ids":()},{"reuse_policy":{}},{"rubrics":()},{"canonical_authority":True},{"review_state":"PENDING"},
 {"assessment_objective_ids":()},{"generation_family_ids":()},{"grading_engine_ids":()},{"source_example_ids":()},
])
def test_contract_fields_fail_closed(change):
 payload=bp().to_dict(); payload.update(change)
 with pytest.raises(ContractError): SourceAssessmentBlueprintV1(**payload)

def test_missing_context_dependencies_fail_closed():
 for key in ("assessment_objective_courses","generation_family_courses","grading_engine_courses","source_example_courses"):
  context={**CTX,key:{}}
  with pytest.raises(ContractError): validate_blueprint_blocking(bp(),**context)
