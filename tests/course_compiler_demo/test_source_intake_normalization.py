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
