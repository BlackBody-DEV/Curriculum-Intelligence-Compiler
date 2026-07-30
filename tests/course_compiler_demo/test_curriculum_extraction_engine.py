import pytest
from tools.course_compiler_demo.source_corpus.contracts import *
from tools.course_compiler_demo.source_corpus.extraction import *

def rights():return SourceRightsClassificationV1("INTERNAL_FIXTURE","mixed extraction fixture",verified=True)
def loc(n):return SourceLocationV1("SECTION",f"section-{n}",section=f"Section {n}")
def document(doc_id,source_type,lines):
 sha=(hex(sum(map(ord,doc_id))%16)[2:])*64
 segs=tuple(SourceSegmentV1(f"{doc_id}-s{i}",doc_id,sha,text,loc(i),"TEXT_NATIVE",.95,"PROPOSED",rights()) for i,text in enumerate(lines,1))
 return SourceDocumentV1(doc_id,source_type,sha,doc_id,rights(),segs)

def test_all_targets_mixed_sources_evidence_aggregation_and_unsupported():
 lines=[f"{target}: Example {target}" for target in TARGETS]+["Topic: Shared topic","unlabeled narrative"]
 docs=(document("syllabus","SYLLABUS",lines[:5]),document("textbook","TEXTBOOK_OR_CHAPTER",lines[5:9]),document("standards","STANDARDS_DOCUMENT",lines[9:12]+["Topic: Shared topic"]),document("questions","QUESTION_BANK",lines[12:]),document("course","COURSE_DEFINITION_PACKAGE",["Course: Example course","Unit: Example unit"]))
 corpus=SourceCorpusV1("mixed",docs,"a"*64);result=extract_curriculum_candidates(corpus)
 assert all(result["target_counts"][target]>=1 for target in TARGETS)
 shared=next(x for x in result["candidates"] if x.title=="Shared topic");assert len(shared.evidence_claim_ids)==2
 assert result["unsupported_candidates"] and all(x["inference_boundary"]=="UNSUPPORTED" for x in result["unsupported_candidates"])
 assert all(x.evidence_claim_ids and 0<=x.confidence<=1 and x.review_state=="PROPOSED" for x in result["candidates"])
 assert result["canonical_authority"] is False

def test_question_bank_fields_and_noncanonical_boundary():
 doc=document("qb","QUESTION_BANK",["Question type: numeric","Topic: vectors"])
 q=extract_question_bank(doc,[{"prompt":"What is 2+2?","answer":4,"solution":"Add.","question_type":"numeric","answer_type":"integer","curriculum_hints":["arithmetic"],"difficulty_hints":["introductory"],"procedure_hints":["addition"],"asset_references":[{"asset_id":"a"}]}])[0]
 for field in ("prompt","answer","solution","question_type","answer_type","curriculum_hints","difficulty_hints","procedure_hints","asset_references"):assert field in q
 assert q["noncanonical"] and q["unvalidated"] and q["human_review_required"] and not q["canonical_authority"]

def test_question_bank_and_performance_fail_closed():
 with pytest.raises(ValueError):extract_question_bank(document("x","SYLLABUS",["Topic: X"]),[])
 doc=document("qb","QUESTION_BANK",["Topic: X"])
 with pytest.raises(ContractError):extract_question_bank(doc,[{"prompt":"x?","answer":"y","studentScore":1}])
