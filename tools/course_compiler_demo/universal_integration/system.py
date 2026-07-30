"""Minimal deterministic wiring across the reviewed universal compiler lanes."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
from typing import Any

from tools.course_compiler_demo.answer_engines import build_default_registry
from tools.course_compiler_demo.assessment_compiler import compile_assessment
from tools.course_compiler_demo.batch_generation import BatchOrchestrator
from tools.course_compiler_demo.beta_export import build_beta_export, dry_run_import_validate
from tools.course_compiler_demo.subject_packs.chemistry import build_general_chemistry_pack, validate_general_chemistry_pack
from tools.course_compiler_demo.subject_packs.computer_science import build_programming_fundamentals_pack, validate_programming_fundamentals_pack
from tools.course_compiler_demo.subject_packs.mathematics import build_mathematics_reference_pack, validate_mathematics_reference_pack
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_reference_pack, validate_physics_engineering_reference_pack
from tools.course_compiler_demo.universal_core import CurriculumNodeV1, CurriculumRelationshipV1, GenerationManifestV1, SourceEvidenceV1, UniversalCurriculumPackageV1

COURSE_ORDER=("ALGEBRA_I","CALCULUS_I","STATICS","ELECTRICITY_AND_MAGNETISM","PROGRAMMING_FUNDAMENTALS","GENERAL_CHEMISTRY")

def _courses(pack:dict[str,Any])->list[dict[str,Any]]:
    value=pack.get("courses")
    return list(value.values()) if isinstance(value,dict) else ([pack["course"]] if value is None else list(value))

def build_course_registry()->dict[str,dict[str,Any]]:
    packs=[
        (build_mathematics_reference_pack,validate_mathematics_reference_pack),
        (build_physics_engineering_reference_pack,validate_physics_engineering_reference_pack),
        (build_programming_fundamentals_pack,validate_programming_fundamentals_pack),
        (build_general_chemistry_pack,validate_general_chemistry_pack),
    ]
    found={}
    for builder,validator in packs:
        pack=builder(); validator(pack)
        for course in _courses(pack):
            cid=course["course_id"]
            if cid in found: raise ValueError("duplicate course identity")
            found[cid]={"course":course,"pack":pack,"validator":validator}
    if tuple(found)!=COURSE_ORDER: raise ValueError("course registry order or membership mismatch")
    return found

def build_service_registry()->dict[str,Any]:
    return {
        "answer_engines":build_default_registry(),
        "subject_packs":build_course_registry(),
        "assessment_compilers":{"universal_v1":compile_assessment},
        "beta_exporters":{"beta_v1":build_beta_export,"beta_v1_dry_run":strict_beta_dry_run_validate},
    }

def strict_beta_dry_run_validate(payload:dict[str,Any])->dict[str,Any]:
    forbidden={"studentid","attempt","attempts","score","scores","mastery","progress","performancehistory","adaptiveassignment","studentanalytics"}
    def walk(value):
        if isinstance(value,dict):
            for key,item in value.items():
                normalized="".join(character for character in str(key).lower() if character.isalnum())
                if normalized in forbidden: raise ValueError(f"student-performance field forbidden: {key}")
                walk(item)
        elif isinstance(value,(list,tuple)):
            for item in value: walk(item)
    walk(payload)
    return dry_run_import_validate(payload)

def normalized_source_evidence(course:dict[str,Any],pack:dict[str,Any])->tuple[dict[str,Any],...]:
    if course["course_id"]=="STATICS" and pack.get("statics_authority_references"):
        return tuple(SourceEvidenceV1(f"evidence:STATICS:{r['authority_identity']}","READ_ONLY_AUTHORITY_REFERENCE",r["authority_identity"],r["sha256"],locator=r["relative_path"],excerpt="Reference only; does not grant canonical authority.").to_dict() for r in pack["statics_authority_references"])
    return (SourceEvidenceV1(f"evidence:{course['course_id']}:REFERENCE_PACK","NONCANONICAL_REFERENCE_PACK",f"{pack['pack_id']}:{course['course_id']}",pack["deterministic_sha256"],locator=f"subject-pack:{pack['pack_id']}",excerpt="Proposed reference-pack provenance; human review required.").to_dict(),)

def build_universal_package(course:dict[str,Any],pack:dict[str,Any]|None=None)->UniversalCurriculumPackageV1:
    nodes=[CurriculumNodeV1(course["course_id"],"COURSE",course["course_id"].replace("_"," ").title()).to_dict()]
    rels=[]
    def add(items,id_key,level,parent_key=None):
        for item in items:
            nodes.append(CurriculumNodeV1(item[id_key],level,str(item.get("title",item[id_key]))).to_dict())
            if parent_key:
                parent=item[parent_key]
                rels.append(CurriculumRelationshipV1(f"contains:{parent}:{item[id_key]}",parent,item[id_key],"CONTAINS").to_dict())
    add(course["units"],"unit_id","UNIT")
    for unit in course["units"]:
        rels.append(CurriculumRelationshipV1(f"contains:{course['course_id']}:{unit['unit_id']}",course["course_id"],unit["unit_id"],"CONTAINS").to_dict())
    add(course["topics"],"topic_id","TOPIC","unit_id")
    add(course["micro_skills"],"micro_skill_id","MICRO_SKILL","topic_id")
    add(course["procedures"],"procedure_id","PROCEDURE")
    for p in course["procedures"]:
        for sid in p["micro_skill_ids"]:
            rels.append(CurriculumRelationshipV1(f"implements:{p['procedure_id']}:{sid}",p["procedure_id"],sid,"IMPLEMENTS").to_dict())
    add(course["generation_families"],"family_id","GENERATION_FAMILY")
    for f in course["generation_families"]:
        rels.append(CurriculumRelationshipV1(f"implements:{f['family_id']}:{f['procedure_id']}",f["family_id"],f["procedure_id"],"IMPLEMENTS").to_dict())
    rels.extend(CurriculumRelationshipV1(r["relationship_id"],r["source_node_id"],r["target_node_id"],r["relationship_type"]).to_dict() for r in course["relationships"])
    evidence=normalized_source_evidence(course,pack) if pack is not None else ()
    return UniversalCurriculumPackageV1(f"universal:{course['course_id']}",tuple(nodes),tuple(rels),evidence,(),review_status="PROPOSED")

@dataclass(frozen=True)
class IntegratedJob:
    job_id:str; course_id:str; unit_id:str; topic_id:str; micro_skill_id:str
    generation_family_id:str; answer_engine:str; difficulty:str; assessment_role:str
    deterministic_seed:int; executable:bool; blocker:str|None; validated_status:str|None
    def to_dict(self): return asdict(self)

def plan_course_jobs(course:dict[str,Any],count:int=300,seed:str="SYNTHESIS_030")->tuple[IntegratedJob,...]:
    if count!=300 or len(course["generation_families"])!=15: raise ValueError("exact 300-job, 15-family plan required")
    registry=build_default_registry(); jobs=[]
    for index in range(count):
        family=course["generation_families"][index%15]
        procedure=next(p for p in course["procedures"] if p["procedure_id"]==family["procedure_id"])
        skill=next(s for s in course["micro_skills"] if s["micro_skill_id"]==procedure["micro_skill_ids"][index%len(procedure["micro_skill_ids"])])
        topic=next(t for t in course["topics"] if t["topic_id"]==skill["topic_id"])
        engine=family["answer_engine"]; decision=registry.lookup(engine)
        executable=decision.status=="SUPPORTED" and family.get("engine_enabled",True) is True
        blocker=None if executable else (decision.reasons[0] if decision.status!="SUPPORTED" else "FAMILY_ENGINE_DISABLED")
        token=hashlib.sha256(f"{seed}:{course['course_id']}:{family['family_id']}:{index}".encode()).hexdigest()
        jobs.append(IntegratedJob(f"job-{token[:24]}",course["course_id"],topic["unit_id"],topic["topic_id"],skill["micro_skill_id"],family["family_id"],engine,("FOUNDATIONAL","DEVELOPING","ADVANCED")[index%3],("PRACTICE","SUMMATIVE")[index%2],int(token[:16],16),executable,blocker,None))
    if len({j.job_id for j in jobs})!=count: raise ValueError("duplicate planned identity")
    manifest=GenerationManifestV1(f"manifest:{course['course_id']}",f"universal:{course['course_id']}",tuple(f["family_id"] for f in course["generation_families"]),count,seed)
    if len(set(manifest.generation_family_ids))!=15: raise ValueError("manifest families unresolved")
    return tuple(jobs)

def secure_batch_orchestrator(output_root:Path,provider)->BatchOrchestrator:
    requested=Path(output_root)
    if not requested.is_absolute(): raise ValueError("output root must be absolute")
    cursor=requested
    while not cursor.exists() and cursor!=cursor.parent: cursor=cursor.parent
    if cursor.is_symlink(): raise ValueError("symlink path component forbidden")
    relative=requested.relative_to(cursor)
    current=cursor
    for part in relative.parts:
        current=current/part
        if current.exists() and current.is_symlink(): raise ValueError("symlink path component forbidden")
    resolved_parent=cursor.resolve(strict=True)
    canonical=resolved_parent.joinpath(relative)
    for ancestor in (resolved_parent,*resolved_parent.parents):
        if (ancestor/".git").exists(): raise ValueError("resolved output root is inside repository")
    orchestrator=BatchOrchestrator(canonical,provider)
    for ancestor in (orchestrator.root,*orchestrator.root.parents):
        if (ancestor/".git").exists(): raise ValueError("resolved output root is inside repository")
    return orchestrator
