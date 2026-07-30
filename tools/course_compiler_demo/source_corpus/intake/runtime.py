"""Offline file intake and normalization with explicit unsupported boundaries."""
from __future__ import annotations
import csv,hashlib,io,json,re
from pathlib import Path
from typing import Any,Iterable

from tools.course_compiler_demo.source_corpus.contracts import SourceType

FLAGS={"OCR_REQUIRED","DIAGRAM_INTERPRETATION_REQUIRED","LOW_TEXT_DENSITY","EMBEDDED_ASSET_PRESENT","UNSUPPORTED_ENCRYPTION"}

def streaming_sha256(path:Path,chunk_size:int=1024*1024)->str:
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for chunk in iter(lambda:f.read(chunk_size),b""):h.update(chunk)
 return h.hexdigest()

def detect_source_type(path:Path)->str:
 p=Path(path); name=p.name.lower(); suffix=p.suffix.lower()
 if suffix==".pdf":return SourceType.TEXT_NATIVE_PDF.value
 if suffix==".csv":return SourceType.STRUCTURED_CSV.value
 if suffix==".json":return SourceType.COURSE_DEFINITION_PACKAGE.value if "course" in name else SourceType.STRUCTURED_JSON.value
 if "syllabus" in name:return SourceType.SYLLABUS.value
 if "standard" in name:return SourceType.STANDARDS_DOCUMENT.value
 if "chapter" in name or "textbook" in name:return SourceType.TEXTBOOK_OR_CHAPTER.value
 if "question" in name or "bank" in name:return SourceType.QUESTION_BANK.value
 if suffix in {".txt",".md",".syllabus",".standards",".chapter",".questions"}:return SourceType.PLAIN_TEXT.value
 raise ValueError(f"unsupported source type: {p}")

def _extract(path:Path,source_type:str)->tuple[list[tuple[str,str]],list[dict[str,Any]],set[str]]:
 flags=set(); assets=[]
 if source_type==SourceType.TEXT_NATIVE_PDF.value:
  from tools.course_compiler_demo.dashboard.pdf_intake import DashboardPdfIntakeError,extract_text_native_pdf_from_path
  try:r=extract_text_native_pdf_from_path(path.name,path,retain_extracted_text=True)
  except DashboardPdfIntakeError as exc:
   token=str(exc)
   flags.add("UNSUPPORTED_ENCRYPTION" if "ENCRYPT" in token else "OCR_REQUIRED")
   return [],assets,flags
  lines=[(f"page-or-section:{i+1}",x) for i,x in enumerate(r.text.splitlines()) if x.strip()]
  if len(r.text.strip())<100:flags.add("LOW_TEXT_DENSITY")
  return lines,assets,flags
 text=path.read_text(encoding="utf-8")
 if source_type in {SourceType.STRUCTURED_JSON.value,SourceType.COURSE_DEFINITION_PACKAGE.value}:
  data=json.loads(text); rows=[]
  def walk(value,loc="$"):
   if isinstance(value,dict):
    for k,v in sorted(value.items()):walk(v,f"{loc}.{k}")
   elif isinstance(value,list):
    for i,v in enumerate(value):walk(v,f"{loc}[{i}]")
   elif value is not None:rows.append((loc,f"{loc}: {value}"))
  walk(data); return rows,assets,flags
 if source_type==SourceType.STRUCTURED_CSV.value:
  rows=list(csv.reader(io.StringIO(text))); return [(f"row:{i+1}"," | ".join(row)) for i,row in enumerate(rows)],assets,flags
 lines=[]; section="section:1"
 for i,raw in enumerate(text.splitlines(),1):
  value=" ".join(raw.split())
  if not value:continue
  if raw.lstrip().startswith("#") or (value.endswith(":") and len(value)<100):section=f"heading:{value.lstrip('#').strip(': ')}"
  if re.search(r"!\[[^]]*\]\([^)]+\)|<img\b",raw,re.I):
   flags.add("EMBEDDED_ASSET_PRESENT");flags.add("DIAGRAM_INTERPRETATION_REQUIRED");assets.append({"location":section,"line":i,"interpreted":False})
  lines.append((section,value))
 if len(text.strip())<40:flags.add("LOW_TEXT_DENSITY")
 return lines,assets,flags

def intake_file(path:Path)->dict[str,Any]:
 p=Path(path).resolve(strict=True); sha=streaming_sha256(p); source_type=detect_source_type(p); extracted,assets,flags=_extract(p,source_type)
 segments=[]
 for index,(location,text) in enumerate(extracted):
  segments.append({"segment_id":"SEG_"+hashlib.sha256(f"{sha}:{location}:{index}:{text}".encode()).hexdigest()[:24],"source_hash":sha,"index":index,"location":{"locator_type":"PAGE_OR_SECTION","locator":location},"text":text,"heading":location.removeprefix("heading:") if location.startswith("heading:") else None})
 return {"path":str(p),"source_type":source_type,"source_hash":sha,"size_bytes":p.stat().st_size,"segments":segments,"assets":assets,"boundary_flags":sorted(flags),"ocr_used":False,"diagram_interpreted":False}

def build_corpus_manifest(paths:Iterable[Path])->dict[str,Any]:
 documents=[intake_file(Path(p)) for p in sorted(paths,key=lambda x:str(Path(x).resolve()))]; first={}; duplicates=[]
 for doc in documents:
  if doc["source_hash"] in first:duplicates.append({"source_hash":doc["source_hash"],"original_path":first[doc["source_hash"]],"duplicate_path":doc["path"]})
  else:first[doc["source_hash"]]=doc["path"]
 material={"documents":documents,"duplicates":duplicates,"document_count":len(documents),"segment_count":sum(len(x["segments"]) for x in documents)}
 return {**material,"manifest_sha256":hashlib.sha256(json.dumps(material,sort_keys=True,separators=(",",":")).encode()).hexdigest(),"restart_safe":True,"reopen_verified":False}

def checkpoint_manifest(path:Path,manifest:dict[str,Any])->str:
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n");return streaming_sha256(p)

def reopen_manifest(path:Path)->dict[str,Any]:
 data=json.loads(Path(path).read_text()); material={k:data[k] for k in ("documents","duplicates","document_count","segment_count")}; expected=hashlib.sha256(json.dumps(material,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 if data.get("manifest_sha256")!=expected:raise ValueError("corpus manifest integrity failure")
 return {**data,"reopen_verified":True}

def run_external_scale_proof(corpus_root:Path,output_path:Path,*,minimum_documents:int=100,minimum_segments:int=5000)->dict[str,Any]:
 root=Path(corpus_root).resolve(strict=True); output=Path(output_path).resolve()
 if not root.is_dir():raise ValueError("external corpus root must be a directory")
 if output==root or root in output.parents:raise ValueError("scale-proof output must be outside the source corpus")
 def discover()->list[Path]:return sorted((p for p in root.rglob("*") if p.is_file()),key=lambda p:str(p.resolve()))
 first_paths=discover(); first=build_corpus_manifest(first_paths)
 if first["document_count"]<minimum_documents or first["segment_count"]<minimum_segments:raise ValueError("external corpus does not satisfy scale minimums")
 checkpoint_manifest(output,first)
 reopened=reopen_manifest(output)
 second_paths=discover(); second=build_corpus_manifest(second_paths)
 def identities(manifest):return [segment["segment_id"] for document in manifest["documents"] for segment in document["segments"]]
 def hashes(manifest):return [document["source_hash"] for document in manifest["documents"]]
 comparisons={
  "document_count":first["document_count"]==second["document_count"]==reopened["document_count"],
  "segment_count":first["segment_count"]==second["segment_count"]==reopened["segment_count"],
  "source_hashes":hashes(first)==hashes(second)==hashes(reopened),
  "segment_identities":identities(first)==identities(second)==identities(reopened),
  "duplicates":first["duplicates"]==second["duplicates"]==reopened["duplicates"],
  "manifest_sha256":first["manifest_sha256"]==second["manifest_sha256"]==reopened["manifest_sha256"],
 }
 if not all(comparisons.values()):raise ValueError("restarted intake was not deterministic")
 evidence={"proof_type":"EXTERNAL_CORPUS_RESTART_SCALE_PROOF","corpus_root":str(root),"output_path":str(output),"first_manifest_sha256":first["manifest_sha256"],"restarted_manifest_sha256":second["manifest_sha256"],"document_count":first["document_count"],"segment_count":first["segment_count"],"duplicate_count":len(first["duplicates"]),"reopen_verified":reopened["reopen_verified"],"restarted_intake_rebuilt":True,"comparisons":comparisons,"validated":True}
 output.write_text(json.dumps({"manifest":first,"scale_proof":evidence},sort_keys=True,indent=2)+"\n")
 return evidence
