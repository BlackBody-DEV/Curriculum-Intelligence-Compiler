from tools.course_compiler_demo.production_questions import ProductionFamily,produce_course_bank
from tools.course_compiler_demo.production_quality import *

def family(i,course_token="fixture"):
    def params(n): return {"a":n+i+1,"b":i+2}
    def gen(p):
        if i%2: return (f"Which option equals {p['a']} plus {p['b']} in {course_token} family {i}?", "A")
        return (f"What is {p['a']} plus {p['b']} in {course_token} production family {i}?",p["a"]+p["b"])
    def derive(p): return "A" if i%2 else p["a"]+p["b"]
    shape="multiple_choice" if i%2 else "numeric_scalar"
    return ProductionFamily(f"F{i}",f"P{i%5}",f"U{i%2}",f"T{i}",f"S{i}","multiple_choice" if i%2 else "numeric_scalar",shape,("reasoning_error",),params,gen,derive)
def bank(cid): return produce_course_bank(cid,"PACK","a"*64,({"evidence_id":"E","source_identity":"PACK","source_hash":"b"*64},),tuple(family(i,cid) for i in range(10)))[0]
def test_quality_assessment_and_export():
    banks=[bank(f"C{i}") for i in range(6)]
    assert all(measure_course_bank_coverage(x)["candidates"]==100 for x in banks)
    assert all(len(select_independent_review_sample(x))==20 for x in banks)
    assert aggregate_duplicate_results(banks)=={"records":600,"unique_candidates":600,"exact_duplicates":0,"fingerprint_conflicts":0}
    assert all(lock_validated_production_bank(x)["locked"] for x in banks)
    assessments=compile_assessment_variants(banks); assert assessments["compiled_variants"]==36
    export=build_production_beta_dry_run(banks,assessments)
    assert len(export["question_references"])==600 and not export["would_write"] and export["performance_fields_absent"]
    assert compile_assessment_variants(list(reversed(banks)))==assessments

def test_duplicate_courses_and_nested_forbidden_fields_fail_closed():
    banks=[bank(f"C{i}") for i in range(6)]
    import pytest
    with pytest.raises(ValueError): compile_assessment_variants([banks[0]]*6)
    assessments=compile_assessment_variants(banks)
    assessments["definitions"][0]["studentAnalytics"]=True
    with pytest.raises(ValueError): build_production_beta_dry_run(banks,assessments)

def test_assessment_topology_and_binding_fail_closed():
    import copy,pytest
    banks=[bank(f"C{i}") for i in range(6)]; valid=compile_assessment_variants(banks)
    for mutate in (
        lambda x:x.update(definitions=[]),
        lambda x:x["definitions"][0].update(course_id="OTHER"),
        lambda x:x["variants"].append(copy.deepcopy(x["variants"][0])),
        lambda x:x["variants"][0].update(sha256="0"*64),
        lambda x:x["definitions"][0].update(variant_ids=["bogus:1","bogus:2","bogus:3"]),
        lambda x:x["definitions"][0].update(candidate_role_policy="anything"),
        lambda x:x["variants"][0].update(role="summative"),
        lambda x:x["variants"][0].update(coverage={"families":0,"procedures":0,"difficulties":[],"answer_shapes":[]}),
        lambda x:x["blueprints"][0].update(course_node_id="OTHER"),
    ):
        payload=copy.deepcopy(valid); mutate(payload)
        with pytest.raises(ValueError): build_production_beta_dry_run(banks,payload)
