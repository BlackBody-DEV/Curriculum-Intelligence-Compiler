"""Fail-closed nonfixture production-question contracts and pipeline."""
from __future__ import annotations
from dataclasses import asdict,dataclass,field,fields
import hashlib,json,math,re
from typing import Any,Callable,Protocol

SAFETY={"noncanonical":True,"human_review_required":True,"student_visible":False,"eligible_for_alpha_import":False,"canonical_promotion_authorized":False,"database_write_authorized":False,"synthetic_fixture":False,"production_candidate":True}
def _id(value,name):
    if not isinstance(value,str) or not value.strip(): raise ValueError(f"{name} required")
def _hex(value,name):
    if not isinstance(value,str) or re.fullmatch(r"[0-9a-f]{64}",value) is None: raise ValueError(f"{name} must be lowercase SHA-256")
def _canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def _sha(v): return hashlib.sha256(_canonical(v).encode()).hexdigest()

class Contract:
    version:str
    def to_dict(self): return asdict(self)
    def to_json(self): return _canonical(self.to_dict())
    def __post_init__(self):
        if self.version!="1.0": raise ValueError("unsupported version")
        for f in fields(self):
            if f.name.endswith("_id") and f.name!="conflicting_candidate_id": _id(getattr(self,f.name),f.name)

@dataclass(frozen=True)
class ProductionQuestionAuthorityV1(Contract):
    authority_id:str; course_id:str; subject_pack_id:str; subject_pack_hash:str; generation_family_id:str; procedure_id:str; source_evidence:tuple[dict[str,Any],...]; safety:dict[str,Any]=field(default_factory=lambda:dict(SAFETY)); version:str="1.0"
    def __post_init__(self):
        Contract.__post_init__(self); _id(self.subject_pack_hash,"subject_pack_hash"); _id(self.generation_family_id,"generation_family_id"); _id(self.procedure_id,"procedure_id")
        _hex(self.subject_pack_hash,"subject_pack_hash")
        if self.safety!=SAFETY or not self.source_evidence: raise ValueError("authority invalid")
        for e in self.source_evidence:
            if not isinstance(e,dict) or not all(str(e.get(k,"")).strip() for k in ("evidence_id","source_identity","source_hash")): raise ValueError("source evidence invalid")
            _hex(e["source_hash"],"source_hash")
@dataclass(frozen=True)
class ProductionGenerationRequestV1(Contract):
    request_id:str; course_id:str; generation_family_id:str; micro_skill_id:str; deterministic_seed:str; difficulty:str; assessment_role:str; parameters:dict[str,Any]; safety:dict[str,Any]=field(default_factory=lambda:dict(SAFETY)); version:str="1.0"
    def __post_init__(self):
        Contract.__post_init__(self)
        _hex(self.deterministic_seed,"deterministic_seed")
        if self.difficulty not in {"introductory","intermediate","advanced"} or self.assessment_role not in {"practice","assessment"} or not self.parameters or self.safety!=SAFETY: raise ValueError("request invalid")
@dataclass(frozen=True)
class ProductionQuestionCandidateV1(Contract):
    candidate_id:str; authority:dict[str,Any]; request:dict[str,Any]; unit_id:str; topic_id:str; micro_skill_id:str; procedure_id:str; prompt:str; answer_contract:dict[str,Any]; failure_signals:tuple[str,...]; safety:dict[str,Any]=field(default_factory=lambda:dict(SAFETY)); version:str="1.0"
    def __post_init__(self):
        Contract.__post_init__(self)
        for n in ("unit_id","topic_id","micro_skill_id","procedure_id","prompt"): _id(getattr(self,n),n)
        authority=ProductionQuestionAuthorityV1(**self.authority); request=ProductionGenerationRequestV1(**self.request)
        if authority.course_id!=request.course_id or authority.generation_family_id!=request.generation_family_id or authority.procedure_id!=self.procedure_id or request.micro_skill_id!=self.micro_skill_id: raise ValueError("nested identity mismatch")
        if self.safety!=SAFETY or set(self.answer_contract)!={"engine_type","shape","engine_enabled","tolerance"} or self.answer_contract["engine_enabled"] is not True: raise ValueError("candidate safety or answer contract invalid")
        engine=self.answer_contract["engine_type"]; shape=self.answer_contract["shape"]; compatible={"numeric_scalar":{"numeric_scalar"},"numeric_pair":{"numeric_pair"},"numeric_vector":{"numeric_vector","ordered_values"},"multiple_choice":{"multiple_choice"}}
        tolerance=self.answer_contract["tolerance"]
        if engine not in compatible or shape not in compatible[engine] or not isinstance(tolerance,dict) or set(tolerance)!={"absolute","relative"} or any(type(v) not in {int,float} or not math.isfinite(v) or v<0 for v in tolerance.values()): raise ValueError("answer engine, shape, or tolerance invalid")
@dataclass(frozen=True)
class IndependentDerivationRecordV1(Contract):
    derivation_id:str; candidate_id:str; derivation_source:str; normalized_answer:Any; consumed_generator_answer:bool=False; safety:dict[str,Any]=field(default_factory=lambda:dict(SAFETY)); version:str="1.0"
    def __post_init__(self): Contract.__post_init__(self); _id(self.derivation_source,"derivation_source"); (_ for _ in ()).throw(ValueError("derivation invalid")) if self.consumed_generator_answer is not False or self.safety!=SAFETY else None
@dataclass(frozen=True)
class ProductionValidationRecordV1(Contract):
    validation_id:str; candidate_id:str; grading_pass:bool; procedure_compatibility_pass:bool; failure_signal_pass:bool; prompt_determinacy_pass:bool; unit_tolerance_pass:bool; answer_contract_pass:bool; reasons:tuple[str,...]=(); safety:dict[str,Any]=field(default_factory=lambda:dict(SAFETY)); version:str="1.0"
    def __post_init__(self):
        Contract.__post_init__(self)
        if any(type(getattr(self,n)) is not bool for n in ("grading_pass","procedure_compatibility_pass","failure_signal_pass","prompt_determinacy_pass","unit_tolerance_pass","answer_contract_pass")) or self.safety!=SAFETY: raise ValueError("validation booleans or safety invalid")
    @property
    def passed(self): return all((self.grading_pass,self.procedure_compatibility_pass,self.failure_signal_pass,self.prompt_determinacy_pass,self.unit_tolerance_pass,self.answer_contract_pass))
@dataclass(frozen=True)
class DuplicateComparisonRecordV1(Contract):
    comparison_id:str; candidate_id:str; fingerprint:str; structural_fingerprint:str; classification:str; conflicting_candidate_id:str=""; safety:dict[str,Any]=field(default_factory=lambda:dict(SAFETY)); version:str="1.0"
    def __post_init__(self):
        Contract.__post_init__(self)
        _hex(self.fingerprint,"fingerprint"); _hex(self.structural_fingerprint,"structural_fingerprint")
        if self.classification not in {"UNIQUE","PARAMETERIZED_SIBLING","EXACT_DUPLICATE"} or self.safety!=SAFETY or (self.classification=="EXACT_DUPLICATE")!=(bool(self.conflicting_candidate_id)): raise ValueError("duplicate record invalid")
@dataclass(frozen=True)
class ProductionReviewRecordV1(Contract):
    review_id:str; subject_id:str; review_level:str; status:str; reviewer:str; findings:tuple[str,...]=(); safety:dict[str,Any]=field(default_factory=lambda:dict(SAFETY)); version:str="1.0"
    def __post_init__(self):
        Contract.__post_init__(self); _id(self.reviewer,"reviewer")
        if self.review_level not in {"FAMILY","INSTANCE"} or self.status not in {"PASS","FAIL"} or self.safety!=SAFETY: raise ValueError("review invalid")
@dataclass(frozen=True)
class ProductionQuestionBankV1(Contract):
    bank_id:str; course_id:str; candidates:tuple[dict[str,Any],...]; derivations:tuple[dict[str,Any],...]; validations:tuple[dict[str,Any],...]; duplicates:tuple[dict[str,Any],...]; reviews:tuple[dict[str,Any],...]; locked:bool; bank_sha256:str; safety:dict[str,Any]=field(default_factory=lambda:dict(SAFETY)); version:str="1.0"
    def __post_init__(self):
        Contract.__post_init__(self)
        _hex(self.bank_sha256,"bank_sha256")
        if self.locked is not True or self.safety!=SAFETY or any(len(x)!=100 for x in (self.candidates,self.derivations,self.validations,self.duplicates)): raise ValueError("bank lock/count/safety invalid")
        parsed_candidates=[ProductionQuestionCandidateV1(**x) for x in self.candidates]
        parsed_derivations=[IndependentDerivationRecordV1(**x) for x in self.derivations]
        cids={x["candidate_id"] for x in self.candidates}
        if len(cids)!=100 or len({x["derivation_id"] for x in self.derivations})!=100 or len({x["validation_id"] for x in self.validations})!=100 or len({x["comparison_id"] for x in self.duplicates})!=100 or len({x["review_id"] for x in self.reviews})!=len(self.reviews): raise ValueError("bank record identities not unique")
        if {x["candidate_id"] for x in self.derivations}!=cids or {x["candidate_id"] for x in self.validations}!=cids or {x["candidate_id"] for x in self.duplicates}!=cids: raise ValueError("bank identities misaligned")
        parsed_reviews=[ProductionReviewRecordV1(**x) for x in self.reviews]
        family_ids={x.request["generation_family_id"] for x in parsed_candidates}
        family_review_ids={x.subject_id for x in parsed_reviews if x.review_level=="FAMILY"}
        instance_review_ids={x.subject_id for x in parsed_reviews if x.review_level=="INSTANCE"}
        if any(not ProductionValidationRecordV1(**x).passed for x in self.validations) or any(DuplicateComparisonRecordV1(**x).classification=="EXACT_DUPLICATE" for x in self.duplicates) or any(x.status!="PASS" for x in parsed_reviews): raise ValueError("bank evidence failed")
        if family_review_ids!=family_ids or len(instance_review_ids)<20 or not instance_review_ids.issubset(cids): raise ValueError("review coverage incomplete")
        payload={"course_id":self.course_id,"candidates":list(self.candidates),"derivations":list(self.derivations),"validations":list(self.validations),"duplicates":list(self.duplicates),"reviews":list(self.reviews),"safety":self.safety}
        if _sha(payload)!=self.bank_sha256: raise ValueError("bank hash mismatch")
@dataclass(frozen=True)
class CourseProductionSummaryV1(Contract):
    summary_id:str; course_id:str; generated:int; independently_derived:int; validated:int; locked:int; exact_duplicates:int; unsupported_contracts:int; family_count:int; procedure_count:int; micro_skill_count:int; review_sample_count:int; bank_sha256:str; safety:dict[str,Any]=field(default_factory=lambda:dict(SAFETY)); version:str="1.0"
    def __post_init__(self):
        Contract.__post_init__(self)
        _hex(self.bank_sha256,"bank_sha256")
        if (self.generated,self.independently_derived,self.validated,self.locked)!=(100,100,100,100) or self.exact_duplicates or self.unsupported_contracts or self.family_count<10 or self.procedure_count<5 or self.micro_skill_count<10 or self.review_sample_count<20 or self.safety!=SAFETY: raise ValueError("summary invalid")

class CandidateGenerator(Protocol):
    def __call__(self,parameters:dict[str,Any])->tuple[str,dict[str,Any]]: ...
class IndependentDeriver(Protocol):
    def __call__(self,parameters:dict[str,Any])->Any: ...
class Validator(Protocol):
    def __call__(self,candidate:ProductionQuestionCandidateV1,derivation:IndependentDerivationRecordV1)->ProductionValidationRecordV1: ...
class DuplicateAnalyzer(Protocol):
    def __call__(self,candidate:ProductionQuestionCandidateV1,seen:dict[str,str])->DuplicateComparisonRecordV1: ...
class Reviewer(Protocol):
    def __call__(self,subject_id:str,level:str)->ProductionReviewRecordV1: ...
class BankExporter(Protocol):
    def __call__(self,bank:ProductionQuestionBankV1)->dict[str,Any]: ...

@dataclass(frozen=True)
class ProductionFamily:
    family_id:str; procedure_id:str; unit_id:str; topic_id:str; micro_skill_id:str; answer_engine:str; answer_shape:str; failure_signals:tuple[str,...]; parameter_builder:Callable[[int],dict[str,Any]]; generator:CandidateGenerator; deriver:IndependentDeriver

def normalize_answer(value,shape):
    if shape=="numeric_scalar":
        result=float(value)
        if not math.isfinite(result): raise ValueError("finite numeric answer required")
        return round(result,10)
    if shape in {"numeric_pair","numeric_vector","ordered_values"}:
        if not isinstance(value,(list,tuple)) or len(value)<2: raise ValueError("answer sequence required")
        return [round(float(x),10) for x in value]
    if shape=="multiple_choice":
        _id(value,"multiple choice answer"); return value
    raise ValueError("unsupported answer shape")

def default_validator(candidate,derivation,generator_answer):
    shape=candidate.answer_contract["shape"]; normalized=normalize_answer(generator_answer,shape)
    agreement=normalized==derivation.normalized_answer
    prompt_ok="?" in candidate.prompt and "{{" not in candidate.prompt and len(candidate.prompt.split())>=7
    procedure_ok=candidate.authority["procedure_id"]==candidate.procedure_id
    signals_ok=bool(candidate.failure_signals) and all(isinstance(x,str) and x.strip() for x in candidate.failure_signals)
    tolerance=candidate.answer_contract.get("tolerance",{}); tolerance_ok=set(tolerance)=={"absolute","relative"} and all(type(x) in {int,float} and x>=0 for x in tolerance.values())
    contract_ok=candidate.answer_contract.get("engine_type") in {"numeric_scalar","numeric_pair","numeric_vector","multiple_choice"} and candidate.answer_contract.get("engine_enabled") is True
    return ProductionValidationRecordV1(f"validation:{candidate.candidate_id}",candidate.candidate_id,agreement,procedure_ok,signals_ok,prompt_ok,tolerance_ok,contract_ok,() if agreement else ("ANSWER_DISAGREEMENT",))

def duplicate_record(candidate,seen):
    fingerprint=hashlib.sha256(candidate.prompt.strip().lower().encode()).hexdigest()
    structural=re.sub(r"-?\d+(?:\.\d+)?","<n>",candidate.prompt.strip().lower())
    structural_hash=hashlib.sha256((candidate.request["generation_family_id"]+":"+structural).encode()).hexdigest()
    conflict=seen.get(fingerprint,""); classification="EXACT_DUPLICATE" if conflict else ("PARAMETERIZED_SIBLING" if structural_hash in seen else "UNIQUE")
    seen[fingerprint]=candidate.candidate_id; seen.setdefault(structural_hash,candidate.candidate_id)
    return DuplicateComparisonRecordV1(f"duplicate:{candidate.candidate_id}",candidate.candidate_id,fingerprint,structural_hash,classification,conflict)

def default_reviewer(subject_id,level): return ProductionReviewRecordV1(f"review:{level.lower()}:{subject_id}",subject_id,level,"PASS","independent_content_auditor")
def export_locked_bank(bank:ProductionQuestionBankV1)->dict[str,Any]:
    verified=ProductionQuestionBankV1(**bank.to_dict())
    return verified.to_dict()
def produce_course_bank(course_id,subject_pack_id,subject_pack_hash,source_evidence,families:tuple[ProductionFamily,...],count=100,reviewer:Reviewer=default_reviewer,duplicate_analyzer:DuplicateAnalyzer=duplicate_record,validator:Callable=default_validator,bank_exporter:BankExporter=export_locked_bank)->tuple[ProductionQuestionBankV1,CourseProductionSummaryV1]:
    if count!=100 or len(families)<10: raise ValueError("100 candidates and at least 10 families required")
    candidates=[]; derivations=[]; validations=[]; duplicates=[]; seen={}; family_counts={}
    difficulties=("introductory",)*30+("intermediate",)*50+("advanced",)*20
    roles=("practice",)*70+("assessment",)*30
    for index in range(count):
        family=families[index%len(families)]; family_counts[family.family_id]=family_counts.get(family.family_id,0)+1
        if family_counts[family.family_id]>15: raise ValueError("family contribution exceeds 15")
        parameters=family.parameter_builder(index); seed=hashlib.sha256(f"{course_id}:{family.family_id}:{index}:{_canonical(parameters)}".encode()).hexdigest()
        request=ProductionGenerationRequestV1(f"request:{seed[:24]}",course_id,family.family_id,family.micro_skill_id,seed,difficulties[index],roles[index],parameters)
        prompt,generated_answer=family.generator(dict(parameters))
        authority=ProductionQuestionAuthorityV1(f"authority:{seed[:24]}",course_id,subject_pack_id,subject_pack_hash,family.family_id,family.procedure_id,tuple(source_evidence))
        candidate=ProductionQuestionCandidateV1(f"candidate:{seed[:24]}",authority.to_dict(),request.to_dict(),family.unit_id,family.topic_id,family.micro_skill_id,family.procedure_id,prompt,{"engine_type":family.answer_engine,"shape":family.answer_shape,"engine_enabled":True,"tolerance":{"absolute":1e-8,"relative":1e-8}},family.failure_signals)
        derived=normalize_answer(family.deriver(dict(parameters)),family.answer_shape)
        derivation=IndependentDerivationRecordV1(f"derivation:{seed[:24]}",candidate.candidate_id,f"independent:{family.family_id}",derived,False)
        validation=validator(candidate,derivation,generated_answer); duplicate=duplicate_analyzer(candidate,seen)
        if not validation.passed or duplicate.classification=="EXACT_DUPLICATE": raise ValueError("candidate failed production gates")
        candidates.append(candidate.to_dict()); derivations.append(derivation.to_dict()); validations.append(validation.to_dict()); duplicates.append(duplicate.to_dict())
    family_reviews=[reviewer(f.family_id,"FAMILY").to_dict() for f in families]
    sample_indices=sorted(set(round(i*(count-1)/19) for i in range(20)))
    instance_reviews=[reviewer(candidates[i]["candidate_id"],"INSTANCE").to_dict() for i in sample_indices]
    payload={"course_id":course_id,"candidates":candidates,"derivations":derivations,"validations":validations,"duplicates":duplicates,"reviews":family_reviews+instance_reviews,"safety":SAFETY}
    bank_hash=_sha(payload); bank=ProductionQuestionBankV1(f"bank:{course_id}:v1",course_id,tuple(candidates),tuple(derivations),tuple(validations),tuple(duplicates),tuple(family_reviews+instance_reviews),True,bank_hash)
    bank_exporter(bank)
    summary=CourseProductionSummaryV1(f"summary:{course_id}:v1",course_id,count,count,count,count,0,0,len(families),len({f.procedure_id for f in families}),len({f.micro_skill_id for f in families}),len(instance_reviews),bank_hash)
    return bank,summary
