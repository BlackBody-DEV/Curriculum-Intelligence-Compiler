from __future__ import annotations
from collections import Counter
import hashlib,json,random
from typing import Any,Iterable
from tools.course_compiler_demo.production_questions import ProductionQuestionBankV1,ProductionQuestionCandidateV1,SAFETY,export_locked_bank
from tools.course_compiler_demo.beta_export import build_beta_export
from tools.course_compiler_demo.universal_integration import strict_beta_dry_run_validate

def _universal_evidence(items):
    return [{"evidence_id":e["evidence_id"],"source_type":e.get("source_type","PRODUCTION_SUBJECT_PACK"),"source_identity":e["source_identity"],"source_hash":e["source_hash"],"locator":e.get("locator","production-wave-032"),"excerpt":e.get("excerpt","Noncanonical production authority."),"review_status":"PROPOSED","version":"1.0"} for e in items]

def validate_course_bank(bank:ProductionQuestionBankV1|dict[str,Any])->dict[str,Any]:
    obj=bank if isinstance(bank,ProductionQuestionBankV1) else ProductionQuestionBankV1(**bank)
    candidates=[ProductionQuestionCandidateV1(**x) for x in obj.candidates]
    families=Counter(x.request["generation_family_id"] for x in candidates); procedures={x.procedure_id for x in candidates}; skills={x.micro_skill_id for x in candidates}
    difficulty=Counter(x.request["difficulty"] for x in candidates); roles=Counter(x.request["assessment_role"] for x in candidates); shapes={x.answer_contract["shape"] for x in candidates}
    family_reviews={x["subject_id"] for x in obj.reviews if x["review_level"]=="FAMILY" and x["status"]=="PASS"}
    instance_reviews={x["subject_id"] for x in obj.reviews if x["review_level"]=="INSTANCE" and x["status"]=="PASS"}
    if len(candidates)!=100 or len(families)<10 or max(families.values())>15 or len(procedures)<5 or len(skills)<10 or len(shapes)<2: raise ValueError("coverage insufficient")
    if difficulty!=Counter({"introductory":30,"intermediate":50,"advanced":20}) or roles!=Counter({"practice":70,"assessment":30}): raise ValueError("distribution mismatch")
    if family_reviews!=set(families) or len(instance_reviews)<20: raise ValueError("review coverage insufficient")
    return {"course_id":obj.course_id,"candidates":100,"families":dict(sorted(families.items())),"procedures":len(procedures),"micro_skills":len(skills),"answer_shapes":sorted(shapes),"difficulty":dict(difficulty),"assessment_roles":dict(roles),"instance_reviews":len(instance_reviews),"bank_sha256":obj.bank_sha256}

def measure_course_bank_coverage(bank):
    """Return the fail-closed family, difficulty, role, answer and review audit."""
    return validate_course_bank(bank)

def select_independent_review_sample(bank,minimum=20):
    obj=bank if isinstance(bank,ProductionQuestionBankV1) else ProductionQuestionBankV1(**bank)
    reviewed={x["subject_id"] for x in obj.reviews if x["review_level"]=="INSTANCE" and x["status"]=="PASS"}
    selected=[x for x in obj.candidates if x["candidate_id"] in reviewed]
    if minimum < 20 or len(selected)<minimum: raise ValueError("independent review sample insufficient")
    difficulties={x["request"]["difficulty"] for x in selected}; roles={x["request"]["assessment_role"] for x in selected}; shapes={x["answer_contract"]["shape"] for x in selected}
    all_families={x["request"]["generation_family_id"] for x in obj.candidates}; reviewed_families={x["request"]["generation_family_id"] for x in selected}
    all_procedures={x["procedure_id"] for x in obj.candidates}; reviewed_procedures={x["procedure_id"] for x in selected}
    high_risk={x["request"]["generation_family_id"] for x in obj.candidates if x["request"]["difficulty"]=="advanced"}
    if difficulties!={"introductory","intermediate","advanced"} or roles!={"practice","assessment"} or len(shapes)<2 or reviewed_families!=all_families or reviewed_procedures!=all_procedures or not high_risk.issubset(reviewed_families): raise ValueError("independent review sample coverage insufficient")
    return tuple(x["candidate_id"] for x in selected)

def aggregate_duplicate_results(banks):
    records=[]; fingerprints=set(); candidate_ids=set()
    for raw in banks:
        bank=raw if isinstance(raw,ProductionQuestionBankV1) else ProductionQuestionBankV1(**raw)
        validate_course_bank(bank)
        for record in bank.duplicates:
            if record["classification"] not in {"UNIQUE","PARAMETERIZED_SIBLING"} or record["candidate_id"] in candidate_ids or record["fingerprint"] in fingerprints: raise ValueError("duplicate production candidate")
            records.append(record); candidate_ids.add(record["candidate_id"]); fingerprints.add(record["fingerprint"])
    return {"records":len(records),"unique_candidates":len(candidate_ids),"exact_duplicates":0,"fingerprint_conflicts":0}

def lock_validated_production_bank(bank):
    validate_course_bank(bank); select_independent_review_sample(bank)
    obj=bank if isinstance(bank,ProductionQuestionBankV1) else ProductionQuestionBankV1(**bank)
    return export_locked_bank(obj)

def compile_assessment_variants(banks:Iterable[ProductionQuestionBankV1|dict[str,Any]])->dict[str,Any]:
    definitions=[]; variants=[]; normalized=[]
    for raw in banks:
        bank=raw if isinstance(raw,ProductionQuestionBankV1) else ProductionQuestionBankV1(**raw)
        validate_course_bank(bank); normalized.append(bank)
    normalized.sort(key=lambda x:x.course_id)
    if len(normalized)!=6 or len({x.course_id for x in normalized})!=6: raise ValueError("six unique course banks required")
    blueprints=[]
    for bank in normalized:
        candidates=list(bank.candidates)
        for role,count in (("practice",25),("summative",40)):
            aid=f"{bank.course_id}:{role}:v1"; variant_ids=[]
            for variant in range(3):
                role_pool=[x for x in candidates if x["request"]["assessment_role"]==("practice" if role=="practice" else "assessment")]
                ranked=sorted(role_pool,key=lambda x:hashlib.sha256(f"{aid}:{variant}:{x['candidate_id']}".encode()).hexdigest())
                # Summative banks contain 30 assessment-role candidates by contract;
                # fill the final ten from practice as an explicit enrichment policy.
                if len(ranked)<count:
                    enrichment=sorted((x for x in candidates if x not in role_pool),key=lambda x:hashlib.sha256(f"{aid}:enrichment:{variant}:{x['candidate_id']}".encode()).hexdigest())
                    ranked+=enrichment
                required=lambda x:(x["request"]["generation_family_id"],x["procedure_id"],x["request"]["difficulty"],x["answer_contract"]["shape"])
                chosen=[]; families=set(); procedures=set(); difficulties=set(); shapes=set()
                for x in ranked:
                    f,p,d,s=required(x)
                    if f not in families or p not in procedures or d not in difficulties or s not in shapes:
                        chosen.append(x); families.add(f); procedures.add(p); difficulties.add(d); shapes.add(s)
                chosen=(chosen+[x for x in ranked if x not in chosen])[:count]
                if len({x["candidate_id"] for x in chosen})!=count or any(x["request"]["course_id"]!=bank.course_id for x in chosen): raise ValueError("assessment isolation or uniqueness failed")
                expected_difficulties={"introductory","intermediate"} if role=="practice" else {"introductory","intermediate","advanced"}
                if len(families)<10 or len(procedures)<5 or difficulties!=expected_difficulties or len(shapes)<2: raise ValueError("assessment coverage insufficient")
                if role=="practice" and any(x["request"]["assessment_role"]!="practice" for x in chosen): raise ValueError("practice role contamination")
                if role=="summative" and sum(x["request"]["assessment_role"]=="assessment" for x in chosen)!=30: raise ValueError("summative role allocation invalid")
                vid=f"{aid}:variant:{variant}"; variant_ids.append(vid)
                variants.append({"variant_id":vid,"assessment_id":aid,"course_id":bank.course_id,"role":role,"question_ids":[x["candidate_id"] for x in chosen],"coverage":{"families":len(families),"procedures":len(procedures),"difficulties":sorted(difficulties),"answer_shapes":sorted(shapes)},"reuse_policy":{"within_variant":False,"cross_variant":True},"safety":dict(SAFETY),"sha256":hashlib.sha256(json.dumps([x["candidate_id"] for x in chosen],sort_keys=True).encode()).hexdigest()})
            definition={"assessment_id":aid,"course_id":bank.course_id,"role":role,"question_count":count,"time_budget_minutes":50 if role=="practice" else 100,"candidate_role_policy":"practice_only" if role=="practice" else "30_assessment_plus_10_practice_enrichment","coverage_policy":{"families_min":10,"procedures_min":5,"all_difficulties":True,"answer_shapes_min":2},"reuse_policy":{"within_variant":False,"cross_variant":True},"variant_ids":variant_ids,"safety":dict(SAFETY)}; definitions.append(definition)
            blueprints.append({"blueprint_id":aid,"course_node_id":bank.course_id,"question_count":count,"topic_weights":{},"difficulty_distribution":{},"question_type_distribution":{},"time_budget_minutes":definition["time_budget_minutes"],"unit_scope":[],"micro_skill_coverage":[],"prerequisite_coverage":[],"reuse_policy":definition["reuse_policy"],"variant_policy":{"deterministic":True,"variant_ids":variant_ids},"scoring_rules":{"default_points":1},"rubrics":[],"review_status":"PROPOSED","version":"1.0"})
    if len(definitions)!=12 or len(variants)!=36: raise ValueError("assessment totals invalid")
    return {"definitions":definitions,"blueprints":blueprints,"variants":variants,"practice_assessments":6,"summative_assessments":6,"compiled_variants":36,"shortfalls":[]}

def build_production_beta_dry_run(banks,assessment_payload)->dict[str,Any]:
    normalized=[]
    for raw in banks:
        bank=raw if isinstance(raw,ProductionQuestionBankV1) else ProductionQuestionBankV1(**raw)
        validate_course_bank(bank); normalized.append(bank)
    normalized.sort(key=lambda x:x.course_id)
    if len(normalized)!=6 or len({x.course_id for x in normalized})!=6: raise ValueError("six unique course banks required")
    course_ids={x.course_id for x in normalized}; candidate_by_id={x["candidate_id"]:x for bank in normalized for x in bank.candidates}; candidate_course={qid:x["request"]["course_id"] for qid,x in candidate_by_id.items()}
    definitions=assessment_payload.get("definitions",()); blueprints=assessment_payload.get("blueprints",()); variants=assessment_payload.get("variants",())
    definition_ids={x.get("assessment_id") for x in definitions}; blueprint_ids={x.get("blueprint_id") for x in blueprints}; variant_ids={x.get("variant_id") for x in variants}
    if len(definitions)!=12 or len(definition_ids)!=12 or len(blueprints)!=12 or blueprint_ids!=definition_ids or len(variants)!=36 or len(variant_ids)!=36: raise ValueError("assessment export topology invalid")
    by_assessment={aid:[] for aid in definition_ids}
    for definition in definitions:
        role=definition.get("role"); expected=25 if role=="practice" else 40 if role=="summative" else 0
        expected_policy="practice_only" if role=="practice" else "30_assessment_plus_10_practice_enrichment"
        if definition.get("course_id") not in course_ids or definition.get("question_count")!=expected or definition.get("candidate_role_policy")!=expected_policy or definition.get("safety")!=SAFETY or definition.get("reuse_policy")!={"within_variant":False,"cross_variant":True}: raise ValueError("assessment definition invalid")
    for variant in variants:
        aid=variant.get("assessment_id"); ids=variant.get("question_ids",()); definition=next((x for x in definitions if x["assessment_id"]==aid),None)
        if definition is None or variant.get("course_id")!=definition["course_id"] or variant.get("role")!=definition["role"] or len(ids)!=definition["question_count"] or len(set(ids))!=len(ids) or any(candidate_course.get(q)!=definition["course_id"] for q in ids) or variant.get("safety")!=SAFETY: raise ValueError("assessment variant invalid")
        selected=[candidate_by_id[q] for q in ids]; actual_roles=Counter(x["request"]["assessment_role"] for x in selected)
        actual_coverage={"families":len({x["request"]["generation_family_id"] for x in selected}),"procedures":len({x["procedure_id"] for x in selected}),"difficulties":sorted({x["request"]["difficulty"] for x in selected}),"answer_shapes":sorted({x["answer_contract"]["shape"] for x in selected})}
        if variant.get("coverage")!=actual_coverage or actual_coverage["families"]<10 or actual_coverage["procedures"]<5 or len(actual_coverage["answer_shapes"])<2: raise ValueError("assessment variant coverage invalid")
        if definition["role"]=="practice" and actual_roles!=Counter({"practice":25}): raise ValueError("practice role policy invalid")
        if definition["role"]=="summative" and actual_roles!=Counter({"assessment":30,"practice":10}): raise ValueError("summative role policy invalid")
        expected_hash=hashlib.sha256(json.dumps(ids,sort_keys=True).encode()).hexdigest()
        if variant.get("sha256")!=expected_hash: raise ValueError("assessment variant hash invalid")
        by_assessment[aid].append(variant["variant_id"])
    if any(len(ids)!=3 for ids in by_assessment.values()): raise ValueError("three variants per assessment required")
    if any(set(x.get("variant_ids",()))!=set(by_assessment[x["assessment_id"]]) for x in definitions): raise ValueError("definition variants unbound")
    for blueprint in blueprints:
        definition=next(x for x in definitions if x["assessment_id"]==blueprint["blueprint_id"])
        if blueprint.get("course_node_id")!=definition["course_id"] or blueprint.get("question_count")!=definition["question_count"] or blueprint.get("time_budget_minutes")!=definition["time_budget_minutes"] or set(blueprint.get("variant_policy",{}).get("variant_ids",()))!=set(by_assessment[blueprint["blueprint_id"]]): raise ValueError("blueprint topology or variants invalid")
    references=[]
    for bank in normalized:
        for candidate in bank.candidates:
            references.append({"question_id":candidate["candidate_id"],"question_revision":"production-v1","procedure_id":candidate["procedure_id"],"generation_family_id":candidate["request"]["generation_family_id"],"answer_contract_id":f"answer:{candidate['candidate_id']}","validation_result_id":f"validation:{candidate['candidate_id']}","source_evidence":_universal_evidence(candidate["authority"]["source_evidence"]),"curriculum_mapping":{"course_id":bank.course_id,"unit_id":candidate["unit_id"],"topic_id":candidate["topic_id"],"micro_skill_ids":[candidate["micro_skill_id"]]},"proposed_canonical_mapping_status":"PROPOSED","difficulty":candidate["request"]["difficulty"],"grading_contract":candidate["answer_contract"],"failure_signals":[{"code":x} for x in candidate["failure_signals"]],"assessment_identity":f"{bank.course_id}:{candidate['request']['assessment_role']}:v1","assessment_role":candidate["request"]["assessment_role"],"provenance":{"production_candidate":True,"synthetic_fixture":False,"authority_id":candidate["authority"]["authority_id"]},"asset_references":[],"version_data":{"schema_version":"1.0","question_type":candidate["answer_contract"]["shape"]},"review_status":"PROPOSED","version":"1.0"})
    all_evidence=tuple(e for bank in normalized for e in _universal_evidence(bank.candidates[0]["authority"]["source_evidence"]))
    package=build_beta_export("production-wave-032","production-six-course",references,blueprints=assessment_payload["blueprints"],source_evidence=all_evidence)
    strict=strict_beta_dry_run_validate(package.to_dict())
    payload={"schema_version":"1.0","universal_beta_package":package.to_dict(),"question_references":references,"assessment_references":assessment_payload["definitions"],"variant_references":assessment_payload["variants"],"canonical_authority":False,"would_write":False,"safety":dict(SAFETY)}
    def inspect(value):
        if isinstance(value,dict):
            for k,v in value.items():
                token="".join(c for c in str(k).lower() if c.isalnum())
                if token in {"studentid","studentscore","studentanalytics","attempt","score","mastery","progress","performancehistory","adaptiveassignment"}: raise ValueError("performance field forbidden")
                if token=="canonicalauthority" and v is not False: raise ValueError("canonical authority forbidden")
                if token=="studentvisible" and v is not False: raise ValueError("student visibility forbidden")
                inspect(v)
        elif isinstance(value,(list,tuple)):
            for x in value: inspect(x)
    inspect(payload)
    if len(references)!=600 or len({x["question_id"] for x in references})!=600 or any(x["safety"]!=SAFETY for x in assessment_payload["definitions"]+assessment_payload["variants"]): raise ValueError("Beta dry-run boundary invalid")
    encoded=json.dumps(payload,sort_keys=True,separators=(",",":"))
    return {**payload,"sha256":hashlib.sha256(encoded.encode()).hexdigest(),"performance_fields_absent":True,"schema_result":"PASS","universal_dry_run":strict}
