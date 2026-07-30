import pytest
from tools.course_compiler_demo.source_corpus.alignment import *
def registry():
 return tuple(RegisteredIdentity("topic:linear","pack:00","ALGEBRA_I","TOPIC","Linear Equations",("solving equations",),"unit:a",(),"1") if i==0 else RegisteredIdentity(f"id:{i}",f"pack:{i:02d}",f"COURSE_{i}","TOPIC",f"Topic {i}") for i in range(33))
REGISTERED_PACK_IDS=tuple(f"pack:{i:02d}" for i in range(33))
def test_exact_synonym_structural_revision_and_new_outcomes():
 r=registry(); evidence=("claim:1",)
 exact=align(SourceAlignmentCandidate("c1","ALGEBRA_I","TOPIC","Anything",evidence,.9,"topic:linear"),r,REGISTERED_PACK_IDS)
 synonym=align(SourceAlignmentCandidate("c2","ALGEBRA_I","TOPIC","Solving equations",evidence,.9),r,REGISTERED_PACK_IDS)
 structural=align(SourceAlignmentCandidate("c3","ALGEBRA_I","TOPIC","Equation Methods",evidence,.9,parent_identity="unit:a"),r,REGISTERED_PACK_IDS)
 revision=align(SourceAlignmentCandidate("c4","ALGEBRA_I","TOPIC","Anything",evidence,.9,"topic:linear",source_version="2"),r,REGISTERED_PACK_IDS)
 new=align(SourceAlignmentCandidate("c5","ALGEBRA_I","TOPIC","Novel Topic",evidence,.9),r,REGISTERED_PACK_IDS)
 assert [x.outcome for x in (exact,synonym,structural,revision,new)]==["EXACT_PROPOSED_MATCH","SYNONYM_PROPOSED_MATCH","STRUCTURAL_PROPOSED_MATCH","REVISION_CANDIDATE","NEW_NODE_CANDIDATE"]
 assert all(x.mapping_classification=="PROPOSED_NONAUTHORITATIVE_MAPPING" and not x.canonical_authority and x.review_requirement=="HUMAN_REVIEW_REQUIRED" for x in (exact,synonym,structural,revision,new))
def test_source_free_cross_course_label_only_and_unrelated_procedure_fail_closed():
 r=registry()
 assert align(SourceAlignmentCandidate("a","ALGEBRA_I","TOPIC","X",(),.9),r,REGISTERED_PACK_IDS).outcome=="INSUFFICIENT_EVIDENCE"
 assert align(SourceAlignmentCandidate("b","PHYSICS","TOPIC","Linear Equations",("c",),.9),r,REGISTERED_PACK_IDS).outcome=="NEW_NODE_CANDIDATE"
 assert align(SourceAlignmentCandidate("c","ALGEBRA_I","TOPIC","Linear Equations",("c",),.9),r,REGISTERED_PACK_IDS).match_method=="LABEL_ONLY_REJECTED"
 proc=list(r)+[RegisteredIdentity("proc:x","pack:01","ALGEBRA_I","PROCEDURE","Balance",("balance",),"",("step-a",))]
 # retain 33 unique packs while replacing pack:01 record
 proc=tuple(x for x in proc if not (x.pack_id=="pack:01" and x.identity!="proc:x"))
 assert align(SourceAlignmentCandidate("d","ALGEBRA_I","PROCEDURE","Balance",("c",),.9,procedure_signature=("other",)),proc,REGISTERED_PACK_IDS).outcome in {"CONFLICT","INSUFFICIENT_EVIDENCE"}
def test_all_outcomes_and_determinism():
 assert len(MatchOutcome)==7
 x=SourceAlignmentCandidate("x","ALGEBRA_I","TOPIC","Solving equations",("c",),.9); a=align_all((x,),registry(),REGISTERED_PACK_IDS); b=align_all((x,),registry(),REGISTERED_PACK_IDS); assert a["deterministic_sha256"]==b["deterministic_sha256"] and not a["canonical_authority"]

def test_registry_must_exactly_match_authoritative_33_pack_identity_list():
 r=registry()
 with pytest.raises(AlignmentError): align(SourceAlignmentCandidate("x","ALGEBRA_I","TOPIC","X",("c",),.9),r,tuple(f"fake:{i}" for i in range(33)))
 with pytest.raises(AlignmentError): align(SourceAlignmentCandidate("x","ALGEBRA_I","TOPIC","X",("c",),.9),r,REGISTERED_PACK_IDS[:-1])

def test_evidence_ids_are_typed_and_foreign_proposed_identity_is_explicitly_blocked():
 with pytest.raises(AlignmentError): SourceAlignmentCandidate("x","ALGEBRA_I","TOPIC","X",(True,),.9)
 result=align(SourceAlignmentCandidate("x","OTHER_COURSE","TOPIC","X",("claim",),.9,"topic:linear"),registry(),REGISTERED_PACK_IDS)
 assert result.outcome=="CONFLICT" and result.conflict_status=="CROSS_COURSE_IDENTITY_BLOCKED" and not result.matched_identity
