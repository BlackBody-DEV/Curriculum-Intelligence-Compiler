"""Proposed, nonauthoritative source-to-course-pack alignment."""
from __future__ import annotations
from dataclasses import asdict,dataclass
from enum import Enum
import hashlib,json,re
from typing import Iterable
class AlignmentError(ValueError): pass
class MatchOutcome(str,Enum):
 EXACT_PROPOSED_MATCH="EXACT_PROPOSED_MATCH"; SYNONYM_PROPOSED_MATCH="SYNONYM_PROPOSED_MATCH"; STRUCTURAL_PROPOSED_MATCH="STRUCTURAL_PROPOSED_MATCH"; NEW_NODE_CANDIDATE="NEW_NODE_CANDIDATE"; REVISION_CANDIDATE="REVISION_CANDIDATE"; CONFLICT="CONFLICT"; INSUFFICIENT_EVIDENCE="INSUFFICIENT_EVIDENCE"
@dataclass(frozen=True)
class SourceAlignmentCandidate:
 candidate_id:str; course_id:str; node_type:str; title:str; evidence_claim_ids:tuple[str,...]; confidence:float; proposed_identity:str=""; parent_identity:str=""; procedure_signature:tuple[str,...]=(); source_version:str=""
 def __post_init__(self):
  if not all(isinstance(x,str) and x.strip() for x in (self.candidate_id,self.course_id,self.node_type,self.title)) or not 0<=self.confidence<=1: raise AlignmentError("source candidate invalid")
  if not isinstance(self.evidence_claim_ids,tuple) or any(not isinstance(x,str) or not x.strip() for x in self.evidence_claim_ids): raise AlignmentError("source evidence identities must be typed nonempty strings")
@dataclass(frozen=True)
class RegisteredIdentity:
 identity:str; pack_id:str; course_id:str; node_type:str; title:str; aliases:tuple[str,...]=(); parent_identity:str=""; procedure_signature:tuple[str,...]=(); version:str=""
 def __post_init__(self):
  if not all(isinstance(x,str) and x.strip() for x in (self.identity,self.pack_id,self.course_id,self.node_type,self.title)): raise AlignmentError("registered identity invalid")
@dataclass(frozen=True)
class ProposedAlignment:
 alignment_id:str; candidate_id:str; outcome:str; mapping_classification:str; source_evidence:tuple[str,...]; matched_identity:str; match_method:str; match_score:float; structural_rationale:str; conflict_status:str; review_requirement:str; canonical_authority:bool=False
 def __post_init__(self):
  if self.mapping_classification!="PROPOSED_NONAUTHORITATIVE_MAPPING" or self.canonical_authority or self.outcome not in {x.value for x in MatchOutcome} or not self.review_requirement: raise AlignmentError("mapping authority/outcome invalid")
  if self.outcome in {MatchOutcome.EXACT_PROPOSED_MATCH.value,MatchOutcome.SYNONYM_PROPOSED_MATCH.value,MatchOutcome.STRUCTURAL_PROPOSED_MATCH.value,MatchOutcome.REVISION_CANDIDATE.value} and (not self.source_evidence or not self.matched_identity or not self.structural_rationale): raise AlignmentError("proposed match lacks evidence")
 def to_dict(self): return asdict(self)
def _norm(v): return re.sub(r"[^a-z0-9]+"," ",v.lower()).strip()
def _validate_registry(targets:tuple[RegisteredIdentity,...],registered_pack_ids:tuple[str,...]):
 if not isinstance(registered_pack_ids,tuple) or len(registered_pack_ids)!=33 or len(set(registered_pack_ids))!=33 or any(not isinstance(x,str) or not x.strip() for x in registered_pack_ids): raise AlignmentError("authoritative registry must declare exactly 33 typed pack identities")
 if {x.pack_id for x in targets}!=set(registered_pack_ids): raise AlignmentError("alignment registry does not exactly match authoritative 33-pack identities")
 if len({x.identity for x in targets})!=len(targets): raise AlignmentError("duplicate registered canonical identity")

def align(candidate:SourceAlignmentCandidate,registry:Iterable[RegisteredIdentity],registered_pack_ids:tuple[str,...])->ProposedAlignment:
 targets=tuple(registry); packs={x.pack_id for x in targets}
 _validate_registry(targets,registered_pack_ids)
 def result(outcome,matched="",method="NONE",score=0.0,rationale="No safe mapping established",conflict="NONE"):
  token=hashlib.sha256((candidate.candidate_id+outcome+matched).encode()).hexdigest()[:20]
  return ProposedAlignment("alignment:"+token,candidate.candidate_id,outcome,"PROPOSED_NONAUTHORITATIVE_MAPPING",candidate.evidence_claim_ids,matched,method,score,rationale,conflict,"HUMAN_REVIEW_REQUIRED",False)
 if not candidate.evidence_claim_ids or candidate.confidence<.5: return result(MatchOutcome.INSUFFICIENT_EVIDENCE.value,rationale="Source-free or low-confidence candidates cannot map")
 safe=[x for x in targets if x.course_id==candidate.course_id and x.node_type==candidate.node_type]
 if candidate.proposed_identity:
  claimed=[x for x in targets if x.identity==candidate.proposed_identity]
  foreign=[x for x in claimed if x.course_id!=candidate.course_id]
  wrong_type=[x for x in claimed if x.course_id==candidate.course_id and x.node_type!=candidate.node_type]
  if foreign:return result(MatchOutcome.CONFLICT.value,method="IDENTITY",rationale="Proposed identity belongs to an unrelated course",conflict="CROSS_COURSE_IDENTITY_BLOCKED")
  if wrong_type:return result(MatchOutcome.CONFLICT.value,method="IDENTITY",rationale="Proposed identity has an unrelated node type",conflict="UNRELATED_IDENTITY_TYPE_BLOCKED")
  exact=[x for x in safe if x.identity==candidate.proposed_identity]
  if len(exact)>1:return result(MatchOutcome.CONFLICT.value,method="IDENTITY",rationale="Multiple registered records claim the same identity",conflict="MULTIPLE_IDENTITY_MATCHES")
  if exact:
   target=exact[0]
   if candidate.source_version and target.version and candidate.source_version!=target.version:return result(MatchOutcome.REVISION_CANDIDATE.value,target.identity,"IDENTITY_VERSION_DELTA",.95,"Identity matches but source and registered versions differ","VERSION_REVIEW_REQUIRED")
   return result(MatchOutcome.EXACT_PROPOSED_MATCH.value,target.identity,"EXACT_IDENTITY",1.0,"Exact identity within the same course and node type")
 if not safe: return result(MatchOutcome.NEW_NODE_CANDIDATE.value,rationale="No related course/type identity exists; unrelated mappings blocked")
 synonyms=[x for x in safe if _norm(candidate.title) in {_norm(a) for a in x.aliases}]
 if len(synonyms)>1:return result(MatchOutcome.CONFLICT.value,method="SYNONYM",rationale="Synonym maps to multiple same-course identities",conflict="AMBIGUOUS_SYNONYM")
 if synonyms:
  target=synonyms[0]
  if candidate.node_type=="PROCEDURE" and (not candidate.procedure_signature or candidate.procedure_signature!=target.procedure_signature): return result(MatchOutcome.CONFLICT.value,method="SYNONYM",rationale="Procedure label agrees but procedure structure does not",conflict="UNRELATED_PROCEDURE_BLOCKED")
  return result(MatchOutcome.SYNONYM_PROPOSED_MATCH.value,target.identity,"CURATED_SYNONYM",.9,"Curated synonym plus same-course structural constraints")
 structural=[x for x in safe if candidate.parent_identity and x.parent_identity==candidate.parent_identity and (candidate.node_type!="PROCEDURE" or candidate.procedure_signature==x.procedure_signature)]
 if len(structural)>1:return result(MatchOutcome.CONFLICT.value,method="STRUCTURAL",rationale="Structure is ambiguous across multiple identities",conflict="AMBIGUOUS_STRUCTURE")
 if structural:return result(MatchOutcome.STRUCTURAL_PROPOSED_MATCH.value,structural[0].identity,"PARENT_AND_SIGNATURE",.8,"Same course, node type, parent, and applicable procedure signature")
 # A matching label without identity/synonym/structure is deliberately not a match.
 if any(_norm(x.title)==_norm(candidate.title) for x in safe): return result(MatchOutcome.INSUFFICIENT_EVIDENCE.value,method="LABEL_ONLY_REJECTED",rationale="Label-only mapping is prohibited",conflict="LABEL_ONLY_BLOCKED")
 return result(MatchOutcome.NEW_NODE_CANDIDATE.value,rationale="Evidence-backed candidate has no safe registered alignment")
def align_all(candidates:Iterable[SourceAlignmentCandidate],registry:Iterable[RegisteredIdentity],registered_pack_ids:tuple[str,...]):
 items=tuple(candidates)
 if len({x.candidate_id for x in items})!=len(items): raise AlignmentError("duplicate source candidate identity")
 targets=tuple(registry); _validate_registry(targets,registered_pack_ids); results=tuple(align(x,targets,registered_pack_ids) for x in items)
 digest=hashlib.sha256(json.dumps([x.to_dict() for x in results],sort_keys=True,separators=(",",":")).encode()).hexdigest()
 return {"classification":"PROPOSED_NONAUTHORITATIVE_MAPPING","alignments":results,"deterministic_sha256":digest,"canonical_authority":False}
