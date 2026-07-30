"""Deterministic candidate extraction that never grants canonical authority."""
from __future__ import annotations
import hashlib,re
from typing import Any,Iterable
from tools.course_compiler_demo.source_corpus.contracts import (
 EvidenceBoundary,ExtractedCurriculumCandidateV1,SourceCorpusV1,SourceDocumentV1,
 SourceEvidenceClaimV1,SourceEvidenceGraphV1,SourceEvidenceLinkV1,reject_performance_fields,
)

TARGETS=("domain","subject","course","unit","topic","subtopic","micro-skill","prerequisite","procedure","generation family","assessment objective","difficulty expectation","question type","answer type","timeline or sequence")
ALIASES={"micro skill":"micro-skill","generation_family":"generation family","assessment_objective":"assessment objective","difficulty":"difficulty expectation","timeline":"timeline or sequence","sequence":"timeline or sequence"}

def _identity(prefix,*parts):return prefix+"_"+hashlib.sha256("|".join(str(x) for x in parts).encode()).hexdigest()[:24]

def build_evidence_graph(corpus:SourceCorpusV1)->SourceEvidenceGraphV1:
 claims=[];links=[]
 for document in corpus.documents:
  for segment in document.segments:
   cid=_identity("CLAIM",document.document_id,segment.segment_id,segment.text)
   claims.append(SourceEvidenceClaimV1(cid,document.document_id,document.source_hash,segment.location,segment.segment_id,segment.extraction_method,segment.confidence,segment.review_state,segment.rights_classification,segment.text))
 return SourceEvidenceGraphV1(_identity("GRAPH",corpus.corpus_id,corpus.manifest_sha256),corpus,tuple(claims),tuple(links))

def _parse_target(text:str)->tuple[str,str]|None:
 match=re.match(r"^\s*([A-Za-z _-]+)\s*:\s*(.+?)\s*$",text)
 if not match:return None
 raw=" ".join(match.group(1).lower().replace("_"," ").split());target=ALIASES.get(raw,raw);title=match.group(2).strip()
 return (target,title) if target in TARGETS else None

def extract_curriculum_candidates(corpus:SourceCorpusV1)->dict[str,Any]:
 graph=build_evidence_graph(corpus); claim_by_segment={c.segment_id:c for c in graph.claims}; grouped={}; unsupported=[]
 for document in corpus.documents:
  for segment in document.segments:
   claim=claim_by_segment[segment.segment_id]; parsed=_parse_target(segment.text)
   if parsed is None:
    unsupported.append({"candidate_id":_identity("UNSUPPORTED",claim.claim_id),"source_claim_id":claim.claim_id,"text":segment.text,"inference_boundary":EvidenceBoundary.UNSUPPORTED.value,"reason":"no supported extraction target recognized"});continue
   target,title=parsed;key=(target," ".join(title.lower().split()));grouped.setdefault(key,{"title":title,"claims":[]});grouped[key]["claims"].append(claim.claim_id)
 candidates=[]
 for (target,_),value in sorted(grouped.items()):
  claim_ids=tuple(sorted(set(value["claims"])));confidence=min(graph.claims[[c.claim_id for c in graph.claims].index(cid)].confidence for cid in claim_ids)
  candidates.append(ExtractedCurriculumCandidateV1(_identity("CURRICULUM",target,value["title"]),target.upper().replace(" ","_").replace("-","_"),value["title"],claim_ids,confidence,"PROPOSED",EvidenceBoundary.DIRECT_SOURCE_EVIDENCE.value,"direct labeled source extraction"))
 result={"evidence_graph":graph,"candidates":tuple(candidates),"unsupported_candidates":tuple(unsupported),"target_counts":{target:sum(c.candidate_type==target.upper().replace(" ","_").replace("-","_") for c in candidates) for target in TARGETS},"canonical_authority":False}
 reject_performance_fields({"candidates":[x.to_dict() for x in candidates],"unsupported":unsupported});return result

def extract_question_bank(document:SourceDocumentV1,questions:Iterable[dict[str,Any]])->tuple[dict[str,Any],...]:
 if document.source_type!="QUESTION_BANK":raise ValueError("question extraction requires QUESTION_BANK source")
 segments=list(document.segments);out=[]
 for index,raw in enumerate(questions):
  reject_performance_fields(raw)
  prompt=raw.get("prompt");answer=raw.get("answer")
  if not isinstance(prompt,str) or not prompt.strip() or answer is None:raise ValueError("question prompt and answer required")
  segment=segments[index%len(segments)] if segments else None
  if segment is None:raise ValueError("question bank requires source segments")
  out.append({"extracted_question_id":_identity("QUESTION",document.document_id,index,prompt),"source_document_id":document.document_id,"source_hash":document.source_hash,"source_segment_id":segment.segment_id,"source_location":segment.location.to_dict(),"prompt":prompt,"answer":answer,"solution":raw.get("solution"),"question_type":raw.get("question_type","UNKNOWN"),"answer_type":raw.get("answer_type","UNKNOWN"),"curriculum_hints":tuple(raw.get("curriculum_hints",())),"difficulty_hints":tuple(raw.get("difficulty_hints",())),"procedure_hints":tuple(raw.get("procedure_hints",())),"asset_references":tuple(raw.get("asset_references",())),"noncanonical":True,"unvalidated":True,"human_review_required":True,"canonical_authority":False})
 return tuple(out)
