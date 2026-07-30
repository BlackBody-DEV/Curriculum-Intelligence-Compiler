import json
from pathlib import Path
from tools.course_compiler_demo.source_corpus.intake import *

def test_mixed_intake_hash_types_headings_tables_assets_duplicates_and_restart(tmp_path):
 files=[]
 payloads={"syllabus.md":"# Unit One\nSkill A\n![diagram](x.png)","standards.txt":"Standard:\nEvidence statement", "chapter.txt":"Chapter 1:\nExposition", "questions.txt":"Question 1\nAnswer A", "course.json":json.dumps({"course":"X","units":["U"]}),"data.json":json.dumps({"a":1}),"table.csv":"name,value\nalpha,2\n"}
 for name,text in payloads.items():p=tmp_path/name;p.write_text(text);files.append(p)
 dup=tmp_path/"duplicate-syllabus.md";dup.write_bytes(files[0].read_bytes());files.append(dup)
 m=build_corpus_manifest(files); assert m["document_count"]==8 and m["segment_count"]>=10 and len(m["duplicates"])==1
 assert len({x["source_type"] for x in m["documents"]})>=5 and any("EMBEDDED_ASSET_PRESENT" in x["boundary_flags"] for x in m["documents"])
 cp=tmp_path/"checkpoint.json"; checkpoint_manifest(cp,m); reopened=reopen_manifest(cp)
 assert reopened["reopen_verified"] and reopened["manifest_sha256"]==m["manifest_sha256"]
 assert build_corpus_manifest(files)["manifest_sha256"]==m["manifest_sha256"]

def test_scale_100_files_5000_segments_no_external_artifacts(tmp_path):
 files=[]
 for i in range(100):
  suffix=("syllabus","standards","chapter","questions","txt")[i%5];p=tmp_path/f"source_{i:03d}_{suffix}.txt";p.write_text("\n".join(f"Segment {i}-{j}" for j in range(50)));files.append(p)
 files[-1].write_bytes(files[0].read_bytes())
 first=build_corpus_manifest(files); cp=tmp_path/"scale-checkpoint.json";checkpoint_manifest(cp,first);second=reopen_manifest(cp)
 assert first["document_count"]==100 and first["segment_count"]==5000 and len(first["duplicates"])==1
 assert [s["segment_id"] for d in first["documents"] for s in d["segments"]]==[s["segment_id"] for d in second["documents"] for s in d["segments"]]
 assert second["manifest_sha256"]==first["manifest_sha256"]

def test_boundary_flags_are_explicit():
 assert FLAGS=={"OCR_REQUIRED","DIAGRAM_INTERPRETATION_REQUIRED","LOW_TEXT_DENSITY","EMBEDDED_ASSET_PRESENT","UNSUPPORTED_ENCRYPTION"}

def test_external_scale_runner_rebuilds_after_checkpoint(tmp_path):
 corpus=tmp_path/"caller-supplied-corpus";corpus.mkdir();output=tmp_path/"evidence"/"proof.json"
 for i in range(4):(corpus/f"source_{i}_syllabus.txt").write_text("\n".join(f"Segment {i}-{j}" for j in range(5)))
 (corpus/"duplicate.txt").write_bytes((corpus/"source_0_syllabus.txt").read_bytes())
 proof=run_external_scale_proof(corpus,output,minimum_documents=5,minimum_segments=25)
 assert proof["validated"] and proof["restarted_intake_rebuilt"] and proof["reopen_verified"]
 assert proof["document_count"]==5 and proof["segment_count"]==25 and proof["duplicate_count"]==1
 assert all(proof["comparisons"].values())
 saved=json.loads(output.read_text());assert saved["scale_proof"]==proof and saved["manifest"]["manifest_sha256"]==proof["first_manifest_sha256"]

def test_ocr_and_encryption_boundaries_are_behavioral(tmp_path,monkeypatch):
 import tools.course_compiler_demo.dashboard.pdf_intake as pdf_intake
 pdf=tmp_path/"scan.pdf";pdf.write_bytes(b"%PDF-placeholder")
 def fail_ocr(*args,**kwargs):raise pdf_intake.DashboardPdfIntakeError(pdf_intake.PDF_TEXT_EXTRACTION_REQUIRED_OCR_NOT_SUPPORTED)
 monkeypatch.setattr(pdf_intake,"extract_text_native_pdf_from_path",fail_ocr)
 result=intake_file(pdf);assert result["boundary_flags"]==["OCR_REQUIRED"] and not result["ocr_used"]
 def fail_encrypted(*args,**kwargs):raise pdf_intake.DashboardPdfIntakeError(pdf_intake.PDF_ENCRYPTED_OR_PASSWORD_PROTECTED)
 monkeypatch.setattr(pdf_intake,"extract_text_native_pdf_from_path",fail_encrypted)
 result=intake_file(pdf);assert result["boundary_flags"]==["UNSUPPORTED_ENCRYPTION"] and not result["ocr_used"]

def test_diagram_boundary_inventories_without_interpretation(tmp_path):
 source=tmp_path/"chapter.md";source.write_text("# Forces\n![free body diagram](fbd.png)\nSupporting prose keeps this text-native source above the low-density reporting threshold.\n")
 result=intake_file(source)
 assert result["boundary_flags"]==["DIAGRAM_INTERPRETATION_REQUIRED","EMBEDDED_ASSET_PRESENT"]
 assert result["assets"]==[{"location":"heading:Forces","line":2,"interpreted":False}] and not result["diagram_interpreted"]
