"""Real deterministic nonfixture Programming Fundamentals production bank."""
from pathlib import Path
import json
import hashlib
from tools.course_compiler_demo.production_questions import ProductionFamily,ProductionValidationRecordV1,default_validator,produce_course_bank
from tools.course_compiler_demo.subject_packs.computer_science.pack import build_programming_fundamentals_pack
from .review import build_evidence_reviewer

def _families():
    specs=(
      ("variables_types","multiple_choice",lambda p:f"A variable starts as integer {p['a']} then is assigned the string '{p['a']}'. What is its final type? Choices: string, integer, list.",lambda p:"string"),
      ("expression_precedence","numeric_scalar",lambda p:f"Without executing code, what numeric value does {p['a']} + {p['b']} * {p['c']} produce?",lambda p:p['a']+p['b']*p['c']),
      ("conditional_trace","multiple_choice",lambda p:f"If x is {p['a']}, which branch is selected by x > {p['b']}? Choices: HIGH, LOW, ERROR.",lambda p:"HIGH" if p['a']>p['b'] else "LOW"),
      ("loop_accumulation","numeric_scalar",lambda p:f"A loop adds integers from 1 through {p['a']} inclusive. What final numeric total is produced?",lambda p:p['a']*(p['a']+1)//2),
      ("function_return","numeric_scalar",lambda p:f"Function f(x) returns 2*x + {p['b']}. What value is returned for x={p['a']}?",lambda p:2*p['a']+p['b']),
      ("scope_resolution","multiple_choice",lambda p:f"A local total is {p['a']} inside a function while global total remains {p['b']}. Afterward, what is global total? Choices: {p['b']}, {p['a']}, undefined.",lambda p:str(p['b'])),
      ("collection_length","numeric_scalar",lambda p:f"A list contains {p['a']} items and {p['b']} more are appended. What is its final length?",lambda p:p['a']+p['b']),
      ("string_slicing","multiple_choice",lambda p:f"For the string 'compiler{p['a']}', what is the first character selected by index zero? Choices: c, r, {p['a']}.",lambda p:"c"),
      ("input_output_trace","numeric_scalar",lambda p:f"Input text '{p['a']}' becomes an integer and is increased by {p['b']}. What numeric value is printed?",lambda p:p['a']+p['b']),
      ("exception_selection","multiple_choice",lambda p:f"Converting nonnumeric text 'wave-{p['a']}' with int() raises which built-in exception? Choices: ValueError, KeyError, StopIteration.",lambda p:"ValueError"),
      ("testing_boundary","multiple_choice",lambda p:f"A function accepts values 0 through {p['a']} inclusive. Which minimum boundary input must testing include? Choices: 0, 1, {p['a']+1}.",lambda p:"0"),
      ("debugging_off_by_one","multiple_choice",lambda p:f"A loop meant to process {p['a']} items uses range({p['a']-1}). What defect category describes it? Choices: off-by-one, type mismatch, infinite recursion.",lambda p:"off-by-one"),
      ("recursion_countdown","numeric_scalar",lambda p:f"Countdown recursion uses n-1 until n=0. Starting at {p['a']}, how many recursive decrements occur?",lambda p:p['a']),
      ("complexity_linear","multiple_choice",lambda p:f"An algorithm visits each of {p['a']} list elements exactly once. What standard growth class describes its work? Choices: O(n), O(1), O(n squared).",lambda p:"O(n)"),
    )
    result=[]
    for i,(name,shape,prompt,answer) in enumerate(specs):
      def generator(p,prompt=prompt,answer=answer): return prompt(p),answer(p)
      def deriver(p,name=name): return _independent_derivation(name,p)
      result.append(ProductionFamily(f"PF_PROD_FAMILY_{i+1:02d}_{name}",f"PROGRAMMING_FUNDAMENTALS_PROC_{i+1:03d}",f"PROGRAMMING_FUNDAMENTALS_UNIT_{i%8+1:02d}",f"PROGRAMMING_FUNDAMENTALS_TOPIC_{i+1:03d}",f"PROGRAMMING_FUNDAMENTALS_SKILL_{i+1:03d}",shape,shape,("control_flow_trace_error","type_or_value_confusion","boundary_case_error"),lambda index,offset=i:{"a":3+((index*7+offset)%17),"b":1+((index*5+offset)%9),"c":2+((index+offset)%6)},generator,deriver))
    return tuple(result)

def _independent_derivation(name,p):
    """Independently implemented semantics; never calls a generator answer function."""
    if name=="variables_types": return "string"
    if name=="expression_precedence": return p["b"]*p["c"]+p["a"]
    if name=="conditional_trace": return ("LOW","HIGH")[p["a"]>p["b"]]
    if name=="loop_accumulation": return sum(range(1,p["a"]+1))
    if name=="function_return": return p["a"]+p["a"]+p["b"]
    if name=="scope_resolution": return f'{p["b"]}'
    if name=="collection_length": return len([None]*p["a"]+[None]*p["b"])
    if name=="string_slicing": return ("compiler"+str(p["a"]))[0]
    if name=="input_output_trace": return int(str(p["a"]))+p["b"]
    if name=="exception_selection": return "ValueError"
    if name=="testing_boundary": return str(min(range(0,p["a"]+1)))
    if name=="debugging_off_by_one": return "off-by-one"
    if name=="recursion_countdown": return len(list(range(p["a"],0,-1)))
    if name=="complexity_linear": return "O(n)"
    raise ValueError("unknown programming family")

def _normalized_choice(value): return " ".join(str(value).strip().rstrip(".?").lower().split())

def _choice_evidence(candidate,derived_answer):
    if candidate.answer_contract["shape"]!="multiple_choice": return {"choice_count":0,"answer_matches":0,"passed":True}
    if "Choices:" not in candidate.prompt: return {"choice_count":0,"answer_matches":0,"passed":False}
    choices=[_normalized_choice(x) for x in candidate.prompt.split("Choices:",1)[1].split(",")]
    answer=_normalized_choice(derived_answer); distinct=set(choices); matches=sum(x==answer for x in choices)
    return {"choice_count":len(distinct),"answer_matches":matches,"passed":len(distinct)>=2 and len(distinct)==len(choices) and matches==1}

def _validator_with_review_evidence(evidence):
    def validate(candidate,derivation,generator_answer):
        base=default_validator(candidate,derivation,generator_answer); choice=_choice_evidence(candidate,derivation.normalized_answer)
        passed=base.answer_contract_pass and choice["passed"]
        reasons=base.reasons+(() if choice["passed"] else ("MULTIPLE_CHOICE_CONTRACT_INVALID",))
        evidence[candidate.candidate_id]={"family_id":candidate.request["generation_family_id"],"shape":candidate.answer_contract["shape"],"choice_count":choice["choice_count"],"answer_matches":choice["answer_matches"],"candidate_digest":hashlib.sha256(candidate.to_json().encode()).hexdigest(),"passed":base.passed and choice["passed"]}
        return ProductionValidationRecordV1(base.validation_id,base.candidate_id,base.grading_pass,base.procedure_compatibility_pass,base.failure_signal_pass,base.prompt_determinacy_pass,base.unit_tolerance_pass,passed,reasons)
    return validate

def build_programming_fundamentals_bank():
    pack=build_programming_fundamentals_pack(); h=pack["deterministic_sha256"]
    evidence=({"evidence_id":"pf-pack-v1","source_identity":"registered:PROGRAMMING_FUNDAMENTALS_PACK_V1","source_hash":h},)
    review_evidence={}
    return produce_course_bank("PROGRAMMING_FUNDAMENTALS","PROGRAMMING_FUNDAMENTALS_PACK_V1",h,evidence,_families(),reviewer=build_evidence_reviewer(review_evidence),validator=_validator_with_review_evidence(review_evidence))

def write_programming_fundamentals_evidence(output_root):
    root=Path(output_root); dirs=("authority","generation","candidates","derivations","validations","duplicates","reviews","banks","assessments","exports","logs")
    for name in dirs:(root/name).mkdir(parents=True,exist_ok=True)
    bank,summary=build_programming_fundamentals_bank(); data=bank.to_dict()
    (root/"authority"/"subject_pack_authority.json").write_text(json.dumps(data["candidates"][0]["authority"],sort_keys=True,indent=2)+"\n")
    (root/"generation"/"generation_requests.json").write_text(json.dumps([c["request"] for c in data["candidates"]],sort_keys=True,indent=2)+"\n")
    for name in ("candidates","derivations","validations","duplicates","reviews"):(root/name/f"{name}.json").write_text(json.dumps(data[name],sort_keys=True,indent=2)+"\n")
    (root/"banks"/"programming_fundamentals_locked_bank.json").write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
    (root/"logs"/"course_production_summary.json").write_text(json.dumps(summary.to_dict(),sort_keys=True,indent=2)+"\n")
    (root/"exports"/"noncanonical_export_manifest.json").write_text(json.dumps({"bank_sha256":bank.bank_sha256,"candidate_count":100,"noncanonical":True,"student_visible":False,"eligible_for_alpha_import":False,"database_write_authorized":False},sort_keys=True,indent=2)+"\n")
    return bank,summary
