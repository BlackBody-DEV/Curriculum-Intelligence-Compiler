"""Evidence-backed generation requirements; this module never generates questions."""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any
from tools.course_compiler_demo.source_corpus.contracts import ContractError, StrictV1

class RequirementStatus(str, Enum):
    READY="READY"
    BLOCKED_MISSING_EVIDENCE="BLOCKED_MISSING_EVIDENCE"
    BLOCKED_CONFLICT="BLOCKED_CONFLICT"
    NOT_APPLICABLE="NOT_APPLICABLE"

class DependencyClassification(str, Enum):
    EXISTING_SUPPORTED="EXISTING_SUPPORTED"
    EXISTING_UNSUPPORTED="EXISTING_UNSUPPORTED"
    NEW_PROCEDURE_REQUIRED="NEW_PROCEDURE_REQUIRED"
    NEW_GENERATION_FAMILY_REQUIRED="NEW_GENERATION_FAMILY_REQUIRED"
    NEW_RECIPE_REQUIRED="NEW_RECIPE_REQUIRED"
    NEW_ANSWER_ENGINE_REQUIRED="NEW_ANSWER_ENGINE_REQUIRED"
    ASSET_DEPENDENCY="ASSET_DEPENDENCY"
    DIAGRAM_DEPENDENCY="DIAGRAM_DEPENDENCY"
    OCR_DEPENDENCY="OCR_DEPENDENCY"

def _text(value,name):
    if not isinstance(value,str) or not value.strip(): raise ContractError(f"{name} is required")
def _texts(value,name):
    if not isinstance(value,tuple) or not value or any(not isinstance(x,str) or not x.strip() for x in value): raise ContractError(f"{name} must be nonempty text identities")
def _distribution(value,name):
    if not isinstance(value,dict) or not value or any(not isinstance(k,str) or not k.strip() or type(v) not in (int,float) or v<0 for k,v in value.items()) or abs(sum(value.values())-1)>1e-9: raise ContractError(f"{name} must sum to one")

@dataclass(frozen=True)
class GenerationRequirementV1(StrictV1):
    requirement_id:str
    course_id:str
    unit_id:str
    topic_id:str
    micro_skill_id:str
    procedure_id:str
    generation_family_id:str
    recipe_requirement_id:str
    answer_engine_type:str
    requested_count:int
    difficulty_allocation:dict[str,float]
    question_type_allocation:dict[str,float]
    assessment_roles:tuple[str,...]
    failure_signals:tuple[str,...]
    asset_policy:str
    duplicate_constraints:dict
    dependency_classifications:tuple[str,...]
    evidence_claim_ids:tuple[str,...]
    status:str
    blockers:tuple[str,...]=()
    review_required:bool=True
    version:str="1.0"
    def __post_init__(self):
        for n in ("requirement_id","course_id","unit_id","topic_id","micro_skill_id","procedure_id","generation_family_id","recipe_requirement_id","answer_engine_type","asset_policy"): _text(getattr(self,n),n)
        _texts(self.assessment_roles,"assessment_roles"); _texts(self.failure_signals,"failure_signals"); _texts(self.dependency_classifications,"dependency_classifications")
        _distribution(self.difficulty_allocation,"difficulty_allocation"); _distribution(self.question_type_allocation,"question_type_allocation")
        if not isinstance(self.duplicate_constraints,dict) or not self.duplicate_constraints: raise ContractError("duplicate_constraints are required")
        try: classifications={DependencyClassification(x) for x in self.dependency_classifications}; status=RequirementStatus(self.status)
        except ValueError as exc: raise ContractError("unsupported requirement status or dependency classification") from exc
        if self.version!="1.0" or type(self.requested_count) is not int or self.requested_count<1 or self.review_required is not True: raise ContractError("invalid requirement version/count/review flag")
        if status==RequirementStatus.READY and (not self.evidence_claim_ids or self.blockers or DependencyClassification.EXISTING_UNSUPPORTED in classifications or any(x.name.startswith("NEW_") for x in classifications)): raise ContractError("ready requirement must be supported, evidenced, and unblocked")
        if status in {RequirementStatus.BLOCKED_MISSING_EVIDENCE,RequirementStatus.BLOCKED_CONFLICT} and not self.blockers: raise ContractError("blocked requirement needs blockers")
        if status==RequirementStatus.NOT_APPLICABLE and (self.evidence_claim_ids or self.blockers): raise ContractError("not-applicable requirement must be empty")
        super().__post_init__()

@dataclass(frozen=True)
class GenerationRequirementsPackageV1(StrictV1):
    package_id:str
    course_id:str
    requirements:tuple[GenerationRequirementV1,...]
    seed:str
    canonical_authority:bool=False
    version:str="1.0"
    def __post_init__(self):
        _text(self.package_id,"package_id"); _text(self.course_id,"course_id"); _text(self.seed,"seed")
        if self.version!="1.0" or self.canonical_authority is not False or not self.requirements: raise ContractError("invalid requirements package boundary")
        if any(not isinstance(x,GenerationRequirementV1) or x.course_id!=self.course_id for x in self.requirements): raise ContractError("requirement course mismatch")
        ids=[x.requirement_id for x in self.requirements]
        if len(ids)!=len(set(ids)): raise ContractError("duplicate requirement identity")
        super().__post_init__()

@dataclass(frozen=True)
class GenerationManifestV1(StrictV1):
    manifest_id:str
    package_id:str
    course_id:str
    requirements:tuple[GenerationRequirementV1,...]
    seed:str
    review_status:str="PROPOSED"
    canonical_authority:bool=False
    version:str="1.0"
    def __post_init__(self):
        if self.review_status!="PROPOSED" or self.canonical_authority is not False or self.version!="1.0" or not self.requirements: raise ContractError("invalid proposed manifest boundary")
        if any(x.status!=RequirementStatus.READY.value or x.course_id!=self.course_id for x in self.requirements): raise ContractError("manifest contains unresolved requirements")
        super().__post_init__()

def compile_generation_requirements(*,package_id:str,course_id:str,seed:str,synthesized_requirements:tuple[dict,...])->GenerationRequirementsPackageV1:
    """Compile synthesized curriculum declarations into reviewable, fail-closed requirements."""
    try: requirements=tuple(GenerationRequirementV1(**item) for item in synthesized_requirements)
    except (TypeError,ContractError) as exc: raise ContractError(f"invalid synthesized generation requirement: {exc}") from exc
    return GenerationRequirementsPackageV1(package_id,course_id,requirements,seed)

def build_generation_manifest(package:GenerationRequirementsPackageV1)->GenerationManifestV1:
    ready=tuple(sorted((x for x in package.requirements if x.status==RequirementStatus.READY.value),key=lambda x:x.requirement_id))
    if not ready: raise ContractError("manifest requires at least one READY requirement")
    return GenerationManifestV1(f"generation-manifest:{package.package_id}",package.package_id,package.course_id,ready,package.seed)

def generation_readiness(package:GenerationRequirementsPackageV1)->dict[str,Any]:
    statuses={status.value:0 for status in RequirementStatus}
    for item in package.requirements: statuses[item.status]+=1
    return {"package_id":package.package_id,"course_id":package.course_id,"statuses":statuses,"question_generation_performed":False,"canonical_authority":False}
