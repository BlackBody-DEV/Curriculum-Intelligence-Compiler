import json
import pytest
from tools.course_compiler_demo.production_questions import *

def _family(i):
    def params(n): return {"a":n+i+2,"b":i+3}
    def generate(p): return (f"What is {p['a']} plus {p['b']} for production family {i}?",p["a"]+p["b"])
    def derive(p): return sum((p["a"],p["b"]))
    return ProductionFamily(f"F{i:02d}",f"P{i:02d}","U1",f"T{i:02d}",f"S{i:02d}","numeric_scalar","numeric_scalar",("arithmetic_error",),params,generate,derive)
EVIDENCE=({"evidence_id":"E","source_identity":"PACK","source_hash":"b"*64},)

def test_real_bank_pipeline_and_separation():
    bank,summary=produce_course_bank("COURSE","PACK","a"*64,EVIDENCE,tuple(_family(i) for i in range(10)))
    assert len(bank.candidates)==len(bank.derivations)==len(bank.validations)==len(bank.duplicates)==100
    assert summary.validated==summary.locked==100 and summary.review_sample_count>=20
    assert all(not x["consumed_generator_answer"] for x in bank.derivations)
    assert all(x["classification"]!="EXACT_DUPLICATE" for x in bank.duplicates)
    assert all(x["safety"]==SAFETY for x in bank.candidates) and bank.safety==SAFETY

def test_deterministic_and_fail_closed():
    a=produce_course_bank("COURSE","PACK","a"*64,EVIDENCE,tuple(_family(i) for i in range(10)))[0]
    b=produce_course_bank("COURSE","PACK","a"*64,EVIDENCE,tuple(_family(i) for i in range(10)))[0]
    assert a.to_json()==b.to_json()
    with pytest.raises(ValueError): IndependentDerivationRecordV1("D","C","source",1,True)
    with pytest.raises(ValueError): normalize_answer(1,"symbolic_expression")

def test_fail_closed_bank_validation_review_duplicate_and_authority():
    bank,_=produce_course_bank("COURSE","PACK","a"*64,EVIDENCE,tuple(_family(i) for i in range(10)))
    payload=bank.to_dict(); payload["locked"]=False
    with pytest.raises(ValueError): ProductionQuestionBankV1(**payload)
    with pytest.raises(ValueError): ProductionValidationRecordV1("V","C","yes",True,True,True,True,True)
    with pytest.raises(ValueError): ProductionReviewRecordV1("R","S","OTHER","PASS","auditor")
    with pytest.raises(ValueError): DuplicateComparisonRecordV1("D","C","x","y","MAYBE")
    with pytest.raises(ValueError): ProductionQuestionAuthorityV1("A","C","P","a"*64,"F","P",({"truthy":True},))
