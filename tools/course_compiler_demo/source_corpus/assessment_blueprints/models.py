"""Evidence-backed assessment blueprints with fail-closed blocking validation."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import math
from tools.course_compiler_demo.source_corpus.contracts import ContractError,StrictV1
from tools.course_compiler_demo.universal_core import AssessmentBlueprintV1

class BlueprintType(str,Enum):
    PRACTICE="PRACTICE"
    DIAGNOSTIC="DIAGNOSTIC"
    FORMATIVE="FORMATIVE"
    SUMMATIVE="SUMMATIVE"

def _text(v,n):
    if not isinstance(v,str) or not v.strip(): raise ContractError(f"{n} is required")
def _distribution(v,n):
    if not isinstance(v,dict) or not v or any(not isinstance(k,str) or not k.strip() or type(x) not in {int,float} or not math.isfinite(x) or x<0 for k,x in v.items()) or abs(sum(v.values())-1)>1e-9: raise ContractError(f"{n} must be a finite nonnegative distribution summing to one")

@dataclass(frozen=True)
class SourceAssessmentBlueprintV1(StrictV1):
    blueprint_id:str
    blueprint_type:str
    course_id:str
    question_count:int
    time_budget_minutes:int
    topic_weights:dict[str,float]
    difficulty_distribution:dict[str,float]
    question_type_distribution:dict[str,float]
    unit_scope:tuple[str,...]
    micro_skill_coverage:tuple[str,...]
    prerequisite_coverage:tuple[str,...]
    evidence_claim_ids:tuple[str,...]
    assessment_objective_ids:tuple[str,...]
    generation_family_ids:tuple[str,...]
    grading_engine_ids:tuple[str,...]
    source_example_ids:tuple[str,...]
    reuse_policy:dict
    variant_policy:dict
    scoring_rules:dict
    rubrics:tuple[dict,...]
    review_state:str="APPROVED_FOR_COMPILER_REVIEW"
    canonical_authority:bool=False
    version:str="1.0"
    def __post_init__(self):
        for n in ("blueprint_id","course_id","review_state"): _text(getattr(self,n),n)
        try: BlueprintType(self.blueprint_type)
        except ValueError as exc: raise ContractError("unsupported blueprint type") from exc
        if self.version!="1.0" or type(self.question_count) is not int or self.question_count<1 or type(self.time_budget_minutes) is not int or self.time_budget_minutes<1: raise ContractError("invalid blueprint version/count/time")
        for v,n in ((self.topic_weights,"topic_weights"),(self.difficulty_distribution,"difficulty_distribution"),(self.question_type_distribution,"question_type_distribution")): _distribution(v,n)
        if not self.unit_scope or not self.micro_skill_coverage or not self.prerequisite_coverage or not self.evidence_claim_ids or not self.assessment_objective_ids or not self.generation_family_ids or not self.grading_engine_ids or not self.source_example_ids: raise ContractError("blueprint scopes, dependencies, examples, and evidence are mandatory")
        if self.question_count<len(set(self.micro_skill_coverage)) or not self.reuse_policy or not self.variant_policy or not self.scoring_rules or not self.rubrics: raise ContractError("blueprint policies, scoring, rubrics, or capacity incomplete")
        if self.review_state!="APPROVED_FOR_COMPILER_REVIEW" or self.canonical_authority is not False: raise ContractError("blueprint review/canonical boundary invalid")
        super().__post_init__()

def validate_blueprint_blocking(blueprint:SourceAssessmentBlueprintV1,*,course_id:str,unit_ids:set[str],topic_ids:set[str],micro_skill_ids:set[str],prerequisite_ids:set[str],evidence_claim_ids:set[str],assessment_objective_courses:dict[str,str],generation_family_courses:dict[str,str],grading_engine_courses:dict[str,str],source_example_courses:dict[str,str],minimum_minutes_per_question:float=1.0,blocking_conflicts:tuple[str,...]=(),coverage_gaps:tuple[str,...]=())->dict:
    errors=[]
    if blueprint.course_id!=course_id: errors.append("COURSE_MISMATCH")
    if not set(blueprint.unit_scope)<=unit_ids: errors.append("UNKNOWN_UNIT")
    if set(blueprint.topic_weights)!=topic_ids: errors.append("TOPIC_DISTRIBUTION_INCOMPLETE")
    if not set(blueprint.micro_skill_coverage)<=micro_skill_ids: errors.append("UNKNOWN_MICRO_SKILL")
    if not set(blueprint.prerequisite_coverage)<=prerequisite_ids: errors.append("UNKNOWN_PREREQUISITE")
    if not set(blueprint.evidence_claim_ids)<=evidence_claim_ids: errors.append("UNRESOLVED_EVIDENCE")
    def check_owned(ids,owners,missing,foreign):
        if any(x not in owners for x in ids): errors.append(missing)
        if any(x in owners and owners[x]!=course_id for x in ids): errors.append(foreign)
    check_owned(blueprint.assessment_objective_ids,assessment_objective_courses,"UNSUPPORTED_OBJECTIVE","CROSS_COURSE_OBJECTIVE")
    check_owned(blueprint.generation_family_ids,generation_family_courses,"MISSING_GENERATION_FAMILY","CROSS_COURSE_GENERATION_FAMILY")
    check_owned(blueprint.grading_engine_ids,grading_engine_courses,"MISSING_GRADING_ENGINE","CROSS_COURSE_GRADING_ENGINE")
    check_owned(blueprint.source_example_ids,source_example_courses,"MISSING_SOURCE_EXAMPLE","CROSS_COURSE_SOURCE_EXAMPLE")
    if type(minimum_minutes_per_question) not in {int,float} or not math.isfinite(minimum_minutes_per_question) or minimum_minutes_per_question<=0 or blueprint.time_budget_minutes < blueprint.question_count*minimum_minutes_per_question: errors.append("IMPOSSIBLE_TIME_BUDGET")
    if blocking_conflicts: errors.append("SOURCE_CONFLICT_BLOCKED")
    if coverage_gaps: errors.append("SOURCE_COVERAGE_GAP_BLOCKED")
    if errors: raise ContractError(";".join(sorted(set(errors))))
    return {"blueprint_id":blueprint.blueprint_id,"blueprint_type":blueprint.blueprint_type,"valid":True,"blocking_errors":[]}

def to_universal_blueprint(blueprint:SourceAssessmentBlueprintV1)->AssessmentBlueprintV1:
    return AssessmentBlueprintV1(blueprint.blueprint_id,blueprint.course_id,blueprint.question_count,dict(blueprint.topic_weights),dict(blueprint.difficulty_distribution),dict(blueprint.question_type_distribution),blueprint.time_budget_minutes,blueprint.unit_scope,blueprint.micro_skill_coverage,blueprint.prerequisite_coverage,dict(blueprint.reuse_policy),dict(blueprint.variant_policy),dict(blueprint.scoring_rules),blueprint.rubrics,"PROPOSED","1.0")
