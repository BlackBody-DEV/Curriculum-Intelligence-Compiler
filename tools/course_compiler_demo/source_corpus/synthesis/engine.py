"""Fail-closed cross-source curriculum synthesis and coverage reporting."""
from __future__ import annotations
from dataclasses import asdict,dataclass
from enum import Enum
import hashlib,json,re
from typing import Any,Iterable

class SynthesisError(ValueError): pass
class ConflictClass(str,Enum):
 COURSE_SCOPE_CONFLICT="COURSE_SCOPE_CONFLICT"; TOPIC_HIERARCHY_CONFLICT="TOPIC_HIERARCHY_CONFLICT"; PREREQUISITE_CONFLICT="PREREQUISITE_CONFLICT"; PROCEDURE_CONFLICT="PROCEDURE_CONFLICT"; TERMINOLOGY_CONFLICT="TERMINOLOGY_CONFLICT"; DIFFICULTY_CONFLICT="DIFFICULTY_CONFLICT"; SEQUENCE_CONFLICT="SEQUENCE_CONFLICT"; ASSESSMENT_CONFLICT="ASSESSMENT_CONFLICT"; RIGHTS_CONFLICT="RIGHTS_CONFLICT"; SOURCE_VERSION_CONFLICT="SOURCE_VERSION_CONFLICT"
class Completeness(str,Enum):
 SOURCE_COMPLETE="SOURCE_COMPLETE"; COURSE_PACK_COMPLETE="COURSE_PACK_COMPLETE"; SYNTHESIZED_WITH_GAPS="SYNTHESIZED_WITH_GAPS"; INSUFFICIENT_EVIDENCE="INSUFFICIENT_EVIDENCE"; CONFLICT_BLOCKED="CONFLICT_BLOCKED"
@dataclass(frozen=True)
class SynthesisCandidate:
 candidate_id:str; candidate_type:str; title:str; source_id:str; evidence_claim_ids:tuple[str,...]; confidence:float; hierarchy_path:tuple[str,...]=(); prerequisites:tuple[str,...]=(); procedure_steps:tuple[str,...]=(); difficulty:str=""; sequence:int|None=None; assessment_objectives:tuple[str,...]=(); rights:str="UNKNOWN"; source_version:str=""; synonym_key:str=""; terminology_context:str=""
 def __post_init__(self):
  if not all(isinstance(x,str) and x.strip() for x in (self.candidate_id,self.candidate_type,self.title,self.source_id)) or not self.evidence_claim_ids or not 0<=self.confidence<=1 or not isinstance(self.terminology_context,str): raise SynthesisError("candidate identity/evidence/confidence invalid")
@dataclass(frozen=True)
class ReconciledNode:
 node_id:str; candidate_type:str; title:str; member_ids:tuple[str,...]; source_ids:tuple[str,...]; evidence_claim_ids:tuple[str,...]; confidence:float; reconciliation:str; hierarchy_path:tuple[str,...]; prerequisites:tuple[str,...]; procedure_steps:tuple[str,...]; difficulty:str; sequence:int|None; assessment_objectives:tuple[str,...]; rights:tuple[str,...]; source_versions:tuple[str,...]; review_required:bool=True
@dataclass(frozen=True)
class PreservedConflict:
 conflict_id:str; conflict_class:str; candidate_ids:tuple[str,...]; evidence_claim_ids:tuple[str,...]; resolution_state:str="UNRESOLVED"
@dataclass(frozen=True)
class CoverageReport:
 unit_coverage:float; topic_coverage:float; micro_skill_coverage:float; procedure_coverage:float; assessment_objective_coverage:float; source_coverage:float; unsupported_content_coverage:float; gaps:tuple[dict[str,Any],...]
@dataclass(frozen=True)
class SynthesisResult:
 nodes:tuple[ReconciledNode,...]; conflicts:tuple[PreservedConflict,...]; coverage:CoverageReport; completeness:str; deterministic_sha256:str
 def to_dict(self): return asdict(self)

def _norm(value): return re.sub(r"[^a-z0-9]+"," ",value.lower()).strip()
def _conflict_classes(a,b):
 differences=(
  (a.rights!=b.rights,ConflictClass.RIGHTS_CONFLICT.value),
  (a.source_version!=b.source_version,ConflictClass.SOURCE_VERSION_CONFLICT.value),
  (a.hierarchy_path!=b.hierarchy_path,ConflictClass.TOPIC_HIERARCHY_CONFLICT.value),
  (a.prerequisites!=b.prerequisites,ConflictClass.PREREQUISITE_CONFLICT.value),
  (a.procedure_steps!=b.procedure_steps,ConflictClass.PROCEDURE_CONFLICT.value),
  (a.difficulty!=b.difficulty,ConflictClass.DIFFICULTY_CONFLICT.value),
  (a.sequence!=b.sequence,ConflictClass.SEQUENCE_CONFLICT.value),
  (a.assessment_objectives!=b.assessment_objectives,ConflictClass.ASSESSMENT_CONFLICT.value),
  (bool(a.terminology_context and b.terminology_context and _norm(a.terminology_context)!=_norm(b.terminology_context)),ConflictClass.TERMINOLOGY_CONFLICT.value),
  (a.candidate_type!=b.candidate_type,ConflictClass.COURSE_SCOPE_CONFLICT.value),
 )
 return tuple(kind for differs,kind in differences if differs)
def synthesize(candidates:Iterable[SynthesisCandidate],known_claim_ids:set[str],source_weights:dict[str,float],expected:dict[str,set[str]],course_pack_complete:bool=False)->SynthesisResult:
 items=tuple(candidates)
 if not items or not known_claim_ids:
  coverage=CoverageReport(0,0,0,0,0,0,1,({"gap_type":"EVIDENCE_GAP","identity":"course","rationale":"No resolvable source evidence"},)); payload={"nodes":[],"conflicts":[],"coverage":asdict(coverage),"completeness":Completeness.INSUFFICIENT_EVIDENCE.value}; digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest(); return SynthesisResult((),(),coverage,Completeness.INSUFFICIENT_EVIDENCE.value,digest)
 if len({x.candidate_id for x in items})!=len(items) or any(not set(x.evidence_claim_ids)<=known_claim_ids for x in items): raise SynthesisError("duplicate identity or unresolved evidence")
 if set(x.source_id for x in items)-set(source_weights) or any(type(v) not in {int,float} or not 0<v<=1 for v in source_weights.values()): raise SynthesisError("source weights invalid")
 groups={}
 for item in items: groups.setdefault(_norm(item.synonym_key or item.title),[]).append(item)
 nodes=[]; conflicts=[]
 for key,group in sorted(groups.items()):
  conflict_pairs=[(a,b,classes) for index,a in enumerate(group) for b in group[index+1:] if (classes:=_conflict_classes(a,b))]
  if conflict_pairs:
   for a,b,classes in conflict_pairs:
    evidence=tuple(sorted(set(a.evidence_claim_ids+b.evidence_claim_ids)))
    for conflict_class in classes:
     pair=tuple(sorted((a.candidate_id,b.candidate_id))); token=hashlib.sha256((pair[0]+pair[1]+conflict_class).encode()).hexdigest()[:16]
     conflicts.append(PreservedConflict("conflict:"+token,conflict_class,pair,evidence))
   continue
  total=sum(source_weights[x.source_id] for x in group); confidence=sum(x.confidence*source_weights[x.source_id] for x in group)/total
  members=tuple(sorted(x.candidate_id for x in group)); title=sorted((x.title for x in group),key=lambda x:(_norm(x),x))[0]; token=hashlib.sha256((group[0].candidate_type+"|"+"|".join(members)).encode()).hexdigest()[:16]
  first=group[0]
  nodes.append(ReconciledNode("node:"+token,first.candidate_type,title,members,tuple(sorted({x.source_id for x in group})),tuple(sorted({c for x in group for c in x.evidence_claim_ids})),round(confidence,10),"EXACT_DEDUPLICATION" if len({_norm(x.title) for x in group})==1 else "SYNONYM_RECONCILIATION",first.hierarchy_path,first.prerequisites,first.procedure_steps,first.difficulty,first.sequence,first.assessment_objectives,tuple(sorted({x.rights for x in group})),tuple(sorted({x.source_version for x in group}))))
 present={kind:{_norm(n.title) for n in nodes if n.candidate_type==kind} for kind in expected}; gaps=[]
 for kind,required in expected.items():
  for identity in sorted({_norm(x) for x in required}-present.get(kind,set())): gaps.append({"gap_type":kind+"_GAP","identity":identity,"rationale":"No nonconflicting evidence-backed candidate"})
 def ratio(kind):
  required={_norm(x) for x in expected.get(kind,set())}; return 1.0 if not required else round(len(required&present.get(kind,set()))/len(required),10)
 unsupported=sum(1 for n in nodes if n.candidate_type=="UNSUPPORTED"); coverage=CoverageReport(ratio("UNIT"),ratio("TOPIC"),ratio("MICRO_SKILL"),ratio("PROCEDURE"),ratio("ASSESSMENT_OBJECTIVE"),round(len({s for n in nodes for s in n.source_ids})/len(source_weights),10),round(unsupported/len(nodes),10) if nodes else 0.0,tuple(gaps))
 completeness=Completeness.CONFLICT_BLOCKED.value if conflicts else (Completeness.COURSE_PACK_COMPLETE.value if course_pack_complete and not gaps else (Completeness.SOURCE_COMPLETE.value if not gaps else Completeness.SYNTHESIZED_WITH_GAPS.value))
 payload={"nodes":[asdict(x) for x in nodes],"conflicts":[asdict(x) for x in conflicts],"coverage":asdict(coverage),"completeness":completeness}; digest=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 return SynthesisResult(tuple(nodes),tuple(conflicts),coverage,completeness,digest)
