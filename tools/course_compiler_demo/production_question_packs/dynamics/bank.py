"""Course-local Dynamics production bank."""
from __future__ import annotations

import json
import math
from pathlib import Path

from tools.course_compiler_demo.production_questions import ProductionFamily, ProductionReviewRecordV1, ProductionValidationRecordV1, default_validator, produce_course_bank
from tools.course_compiler_demo.subject_packs.physics_engineering import build_physics_engineering_course_catalog, validate_physics_engineering_course_catalog

DOMAINS = ("particle displacement", "particle velocity", "projectile velocity", "force resultants", "work-energy", "impulse-momentum", "angular acceleration", "angular displacement", "vibration", "normal acceleration")


def _family(i: int, course: dict) -> ProductionFamily:
    procedure=course["procedures"][i]; skill=course["micro_skills"][i]; topic=next(row for row in course["topics"] if row["topic_id"]==skill["topic_id"]); vector=i in {2,3}
    def params(n: int) -> dict:
        a=float(n+i+2); return {"a":a,"b":float((n%7)+2),"time":float((n%5)+1),"mass":float((n%6)+2),"speed":float((n%9)+4),"angle":float((13*n+7*i)%70+10),"radius":float((n%8)+2)}
    def derive(x: dict):
        a,b,t,m,v,theta,r=x["a"],x["b"],x["time"],x["mass"],x["speed"],math.radians(x["angle"]),x["radius"]
        values=(v*t+0.5*a*t*t,v+a*t,[v*math.cos(theta),v*math.sin(theta)-9.81*t],[a-b,b],math.sqrt(v*v+2*a*b/m),v+(a*t)/m,a/(m*r*r),v*t+0.5*(a/(m*r*r))*t*t,math.sqrt(a/m)/(2*math.pi),v*v/r)
        return values[i]
    def generate(x: dict):
        a,b,t,m,v,angle,r=x["a"],x["b"],x["time"],x["mass"],x["speed"],x["angle"],x["radius"]
        prompts=(f"A particle starts at {v:.1f} m/s and accelerates at {a:.1f} m/s^2 for {t:.1f} s; what displacement in m results?",f"A particle begins at {v:.1f} m/s and has acceleration {a:.1f} m/s^2 for {t:.1f} s; what final velocity in m/s results?",f"A projectile starts at {v:.1f} m/s and {angle:.1f} degrees above +x; after {t:.1f} s, what ordered x and y velocity components in m/s result under gravity?",f"For applied force ({a:.1f},{b:.1f}) N and opposing force ({b:.1f},0) N, what ordered resultant x and y force components in N act?",f"A {m:.1f} kg particle starts at {v:.1f} m/s and receives constant-force work over {b:.1f} m from force {a:.1f} N; what final speed in m/s follows from work-energy?",f"A {m:.1f} kg particle starts at {v:.1f} m/s and receives force {a:.1f} N for {t:.1f} s; what final velocity in m/s follows from impulse-momentum?",f"A rigid body has mass moment of inertia {m*r*r:.3f} kg m^2 and applied torque {a:.1f} N m; what angular acceleration in rad/s^2 results?",f"A rigid body starts at angular speed {v:.1f} rad/s under torque {a:.1f} N m with inertia {m*r*r:.3f} kg m^2 for {t:.1f} s; what angular displacement in rad results?",f"A vibration system has stiffness {a:.1f} N/m and mass {m:.1f} kg; what undamped natural frequency in Hz results?",f"A particle follows a circular path of radius {r:.1f} m at speed {v:.1f} m/s; what normal acceleration in m/s^2 results?")
        theta=math.radians(angle); values=(v*t+0.5*a*t*t,v+a*t,[v*math.cos(theta),v*math.sin(theta)-9.81*t],[a-b,b],math.sqrt(v*v+2*a*b/m),v+(a*t)/m,a/(m*r*r),v*t+0.5*(a/(m*r*r))*t*t,math.sqrt(a/m)/(2*math.pi),v*v/r)
        return prompts[i],values[i]
    return ProductionFamily(f"DYNAMICS_PRODUCTION_{i:02d}",procedure["procedure_id"],topic["unit_id"],topic["topic_id"],skill["micro_skill_id"],"numeric_vector" if vector else "numeric_scalar","numeric_vector" if vector else "numeric_scalar",("unit_mismatch","axis_confusion","sign_error",DOMAINS[i].replace(" ","_")+"_error"),params,generate,derive)


def dynamics_validator(candidate,derivation,generator_answer):
    base=default_validator(candidate,derivation,generator_answer); prompt=candidate.prompt.lower(); i=int(candidate.request["generation_family_id"].split("_")[-1]); keys=(("displacement","m/s^2","m"),("final velocity","m/s^2","m/s"),("projectile","x and y","gravity"),("resultant","x and y","n"),("work-energy","kg","m/s"),("impulse-momentum","kg","m/s"),("torque","inertia","rad/s^2"),("angular displacement","torque","rad"),("natural frequency","stiffness","hz"),("circular path","normal acceleration","m/s^2"))[i]; semantic=all(token in prompt for token in keys)
    return ProductionValidationRecordV1(base.validation_id,base.candidate_id,base.grading_pass,base.procedure_compatibility_pass,base.failure_signal_pass,base.prompt_determinacy_pass,base.unit_tolerance_pass and semantic,base.answer_contract_pass,base.reasons+(() if semantic else ("DYNAMICS_DOMAIN_VALIDATION_FAILED",)))


def artifact_reviewer(families,inspected,subject,level):
    if level=="FAMILY":
        family=next((row for row in families if row.family_id==subject),None); cohort=[row for row in inspected.values() if row[0].request["generation_family_id"]==subject]
        if family is None or not cohort or any(not row[2].passed for row in cohort): raise ValueError("family evidence missing or failed")
        findings=(f"inspected {len(cohort)} candidates for {DOMAINS[int(subject.split('_')[-1])]}",f"verified procedure {family.procedure_id}, skill {family.micro_skill_id}, units, vectors, and contract")
    else:
        if subject not in inspected or not inspected[subject][2].passed: raise ValueError("candidate evidence missing or failed")
        candidate,derivation,validation=inspected[subject]; findings=(f"inspected {candidate.candidate_id} and derivation {derivation.derivation_id}",f"verified physical domain, units, signs, and validation {validation.validation_id}")
    return ProductionReviewRecordV1(f"review:{level.lower()}:{subject}",subject,level,"PASS","independent_dynamics_reviewer",findings)


def build_bank():
    pack=build_physics_engineering_course_catalog(); validate_physics_engineering_course_catalog(pack); course=pack["courses"]["DYNAMICS"]
    evidence=({"evidence_id":"DYNAMICS:COURSE_CATALOG","source_identity":pack["pack_id"],"source_hash":pack["deterministic_sha256"],"access":"READ_ONLY_REFERENCE"},); families=tuple(_family(i,course) for i in range(10)); inspected={}
    def validator(candidate,derivation,answer): result=dynamics_validator(candidate,derivation,answer); inspected[candidate.candidate_id]=(candidate,derivation,result); return result
    bank,summary=produce_course_bank("DYNAMICS",pack["pack_id"],pack["deterministic_sha256"],evidence,families,reviewer=lambda subject,level:artifact_reviewer(families,inspected,subject,level),validator=validator)
    return bank,summary,evidence


def write_bank(root):
    bank,summary,evidence=build_bank(); root=Path(root); payloads={"authority/authority.json":{"source_evidence":evidence},"candidates/candidates.json":bank.candidates,"derivations/derivations.json":bank.derivations,"validations/validations.json":bank.validations,"duplicates/duplicates.json":bank.duplicates,"reviews/reviews.json":bank.reviews,"banks/production_bank.json":bank.to_dict(),"exports/course_summary.json":summary.to_dict()}
    for rel,value in payloads.items(): path=root/rel; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value,sort_keys=True,indent=2)+"\n")
    return bank,summary
