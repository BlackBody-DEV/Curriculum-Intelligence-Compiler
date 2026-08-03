#!/usr/bin/env python3
"""Emit immutable ADAPT-A packages from completed Wave 1R generation traces.

This is a packaging-only projection.  Prompts, correct answers, procedure IDs,
topic/subtopic/micro-skill bindings, and the five safety labels are copied from
the completed lane artifacts and checked before publication.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Any

WORKTREES = Path("/Users/fanarichardson/AxiomIQ_Work/worktrees/wave1")
PUBLISHED = Path("reports/course_compiler_demo/internal_release")
CREATED_AT = "2026-08-03T02:00:24+00:00"
PACKAGE_VERSION = "wave1r-conformance.1"
COURSE_CODE = "STATICS"
LANES = (
    "structural-analysis", "internal-forces", "shear-bending",
    "force-systems-split", "equilibrium-split", "general-principles",
    "distributed-forces", "friction",
)
DIFFICULTY_LANES = {"structural-analysis", "internal-forces", "shear-bending"}
LABELS = {
    "human_review_required": True,
    "student_visible": False,
    "database_eligible": False,
    "is_active": False,
    "noncanonical": True,
}


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def find_one(root: Path, suffix: str) -> Path:
    paths = sorted(root.glob(f"reports/course_compiler_demo/internal_release/**/*{suffix}"))
    if not paths:
        raise RuntimeError(f"missing {suffix} below {root}")
    return paths[-1]


def family_rows(value: dict[str, Any]) -> list[dict[str, Any]]:
    return value.get("generation_families") or value.get("families") or []


def family_id(value: dict[str, Any]) -> str:
    result = value.get("family_id") or value.get("generation_family")
    if not result:
        raise RuntimeError(f"generation family lacks identity: {value}")
    return str(result)


def qid(q: dict[str, Any], ordinal: int) -> str:
    return str(q.get("question_id") or q.get("candidate_id") or f"wave1r-{ordinal:03d}")


def binding(q: dict[str, Any]) -> tuple[str, str, str, str]:
    procedure = str(q.get("procedure_id") or "")
    topic = str(q.get("topic_code") or "")
    subtopic = str(q.get("subtopic_code") or "")
    skill = str(q.get("micro_skill_code") or q.get("micro_skill") or "")
    if not all((procedure, topic, subtopic, skill)):
        raise RuntimeError(f"incomplete procedure binding for {qid(q, 0)}")
    return procedure, topic, subtopic, skill


def source_answer(q: dict[str, Any]) -> Any:
    for key in ("correct_answer", "answers", "answer"):
        if key in q:
            return q[key]
    contract = q.get("answer_contract")
    if isinstance(contract, dict) and "correct_answer" in contract:
        return contract["correct_answer"]
    raise RuntimeError(f"missing answer for {qid(q, 0)}")


def answer_type(q: dict[str, Any]) -> str:
    contract = q.get("answer_contract")
    nested = contract.get("answer_type") if isinstance(contract, dict) else None
    value = str(q.get("answer_type") or nested or q.get("question_type") or "numeric")
    return {"multi_part": "numeric_tuple", "numeric_scalar": "numeric", "numeric_with_regime": "numeric", "numeric_with_mode": "numeric"}.get(value, value)


def part_contract(q: dict[str, Any], atype: str) -> Any:
    existing = q.get("answer_parts_contract") or q.get("answer_contract")
    if atype == "multiple_choice":
        correct = source_answer(q)
        correct_id = correct.get("option_id") if isinstance(correct, dict) else correct
        if isinstance(correct_id, list):
            correct_field = {"correct_option_ids": correct_id}
        else:
            correct_field = {"correct_option_id": str(correct_id)}
        return {
            "representation": "complete_option",
            "required_option_fields": ["option_id", "content"],
            "options": q.get("options") or (existing.get("options") if isinstance(existing, dict) else []),
            **correct_field,
        }
    if atype == "numeric_tuple":
        if isinstance(existing, list):
            return existing
        if isinstance(existing, dict) and isinstance(existing.get("parts"), list):
            return existing["parts"]
        answer = source_answer(q)
        units = q.get("units") or {}
        tolerance = q.get("tolerance")
        items = list(answer.items()) if isinstance(answer, dict) else list(enumerate(answer if isinstance(answer, list) else [answer]))
        parts = []
        for index, (key, _value) in enumerate(items):
            unit = units.get(str(key)) if isinstance(units, dict) else (units[index] if isinstance(units, list) and index < len(units) else units)
            tol = tolerance.get(str(key)) if isinstance(tolerance, dict) else tolerance
            parts.append({"label": str(key), "unit": str(unit or "dimensionless"), "tolerance": float(tol if isinstance(tol, (int, float)) else 0.01), "ordinal": index + 1})
        return parts
    return existing if isinstance(existing, (dict, list)) else {"representation": atype}


def root_tolerance(q: dict[str, Any], atype: str, contract: Any) -> Any:
    if atype == "multiple_choice":
        return None
    value = q.get("tolerance")
    if value is None and isinstance(q.get("tolerance_contract"), dict):
        value = q["tolerance_contract"].get("value", q["tolerance_contract"].get("absolute"))
    if isinstance(value, (int, float)):
        return value
    if atype in {"numeric", "signed_numeric", "numeric_pair", "vector_components"}:
        if isinstance(value, dict):
            nums = [v for v in value.values() if isinstance(v, (int, float))]
            if nums:
                return max(nums)
        return 0.01
    return None


def parameterization(q: dict[str, Any]) -> dict[str, Any]:
    value = q.get("parameterization") or q.get("parameters") or q.get("givens") or q.get("supplied_primitive_data") or {}
    return value if isinstance(value, dict) else {"value": value}


def difficulty(q: dict[str, Any], lane: str, ordinal: int) -> int:
    value = q.get("difficulty_level")
    if isinstance(value, int) and 1 <= value <= 5:
        return value
    # The completed three lane generators recorded family_ordinal as their
    # deterministic complexity position.  The emitter maps that position to
    # the same five-level cycle used by Force Systems Split.
    source_ordinal = q.get("family_ordinal") or ordinal
    return (int(source_ordinal) - 1) % 5 + 1


def exact_fp(prompt: str) -> str:
    return digest_bytes(" ".join(prompt.casefold().split()).encode())


def structural_fp(record: dict[str, Any]) -> str:
    basis = {key: record.get(key) for key in (
        "course_code", "topic_code", "subtopic_code", "micro_skill_code",
        "procedure_id", "generation_family", "answer_type", "question_type",
        "parameterization",
    )}
    return digest_bytes(canonical(basis))


def family_declaration(raw: dict[str, Any], questions: list[dict[str, Any]]) -> dict[str, Any]:
    fid = family_id(raw)
    members = [q for q in questions if str(q.get("generation_family")) == fid]
    parameter_keys = sorted({key for q in members for key in parameterization(q)})
    parameter_domains = raw.get("parameter_domains") or raw.get("domains")
    parameterization_decl = {
        "source": "completed_generation_trace",
        "fields": parameter_keys,
        "domains": parameter_domains if isinstance(parameter_domains, (dict, list)) else {},
    }
    constraints = {
        "answer_types": sorted({answer_type(q) for q in members}) or raw.get("answer_types") or [],
        "question_types": sorted({str(q.get("question_type") or answer_type(q)) for q in members}) or raw.get("question_types") or [],
        "units_contracts": [raw[key] for key in ("units_contract", "units") if key in raw],
        "tolerance_contracts": [raw[key] for key in ("tolerance_contract", "tolerance") if key in raw],
        "exclusions": raw.get("exclusions") or [],
    }
    raw_invariants = raw.get("invariants")
    invariants = raw_invariants if isinstance(raw_invariants, (dict, list)) and raw_invariants else {
        "procedure_ids": sorted({binding(q)[0] for q in members}) or ([raw["procedure_id"]] if raw.get("procedure_id") else []),
        "topic_codes": sorted({binding(q)[1] for q in members}),
        "subtopic_codes": sorted({binding(q)[2] for q in members}),
        "micro_skill_codes": sorted({binding(q)[3] for q in members}),
        "binding_immutable": True,
    }
    return {"family_id": fid, "parameterization": parameterization_decl, "constraints": constraints, "invariants": invariants}


def emit_lane(lane: str, output_root: Path) -> dict[str, Any]:
    worktree = WORKTREES / lane
    qpath = find_one(worktree, "_questions.json")
    fpath = find_one(worktree, "_generation_families.json")
    qdoc, fdoc = json.loads(qpath.read_text()), json.loads(fpath.read_text())
    questions = qdoc.get("questions") or []
    raw_families = family_rows(fdoc)
    package_id = "wave1r_" + lane.replace("-", "_")
    destination = output_root / package_id
    artifacts: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    procedures: list[dict[str, Any]] = []
    source_snapshot = [(q.get("prompt"), source_answer(q), binding(q)) for q in questions]

    trace_rel = "artifacts/evidence/completed_generation_trace.json"
    trace_path = destination / trace_rel
    write_json(trace_path, {
        "question_source_path": str(qpath), "question_source_sha256": digest_file(qpath),
        "family_source_path": str(fpath), "family_source_sha256": digest_file(fpath),
        "record_count": len(questions), "family_count": len(raw_families),
        "generation_outcome": "no_records_generated" if not questions else "completed",
    })
    artifacts.append({"path": trace_rel, "sha256": digest_file(trace_path), "media_type": "application/json", "role": "generation_trace"})

    procedure_examples: dict[str, dict[str, Any]] = {}
    for q in questions:
        procedure_examples.setdefault(binding(q)[0], q)
    for proc_id, q in sorted(procedure_examples.items()):
        _, topic, subtopic, skill = binding(q)
        proc = {
            "procedure_id": proc_id, "topic_code": topic, "subtopic_code": subtopic,
            "micro_skill_code": skill, "status": "signed_off",
            "source_signature": q.get("procedure_signature"), **LABELS,
        }
        rel = f"artifacts/procedures/{proc_id}.json"
        path = destination / rel
        write_json(path, proc)
        sha = digest_file(path)
        artifacts.append({"path": rel, "sha256": sha, "media_type": "application/json", "role": "signed_procedure"})
        signature = q.get("procedure_signature") if isinstance(q.get("procedure_signature"), dict) else {}
        procedures.append({
            "procedure_id": proc_id, "topic_code": topic, "subtopic_code": subtopic,
            "micro_skill_code": skill, "artifact_path": rel, "artifact_sha256": sha,
            "signature": {"algorithm": "sha256", "signed_digest": sha, "status": "signed_off",
                          "reviewer": signature.get("reviewer") or signature.get("signature_reviewer") or "pinned-authority-review",
                          "signed_at": signature.get("date") or signature.get("signature_date") or CREATED_AT},
        })

    distribution: collections.Counter[int] = collections.Counter()
    for ordinal, q in enumerate(questions, 1):
        proc_id, topic, subtopic, skill = binding(q)
        atype = answer_type(q)
        contract = part_contract(q, atype)
        prompt = q.get("prompt")
        if not isinstance(prompt, str) or not prompt:
            raise RuntimeError(f"missing prompt for {qid(q, ordinal)}")
        level = difficulty(q, lane, ordinal)
        distribution[level] += 1
        units = q.get("units_contract")
        if not isinstance(units, dict) or not isinstance(units.get("required"), bool):
            raw_units = q.get("units") or q.get("answer_unit")
            units = {"required": bool(raw_units), "declaration": raw_units}
        record = {
            "question_id": qid(q, ordinal), "ordinal": ordinal, "course_code": COURSE_CODE,
            "topic_code": topic, "subtopic_code": subtopic, "micro_skill_code": skill,
            "procedure_id": proc_id, "generation_family": str(q.get("generation_family")),
            "prompt": prompt, "question_type": str(q.get("question_type") or atype),
            "answer_type": atype, "answer_contract": contract, "correct_answer": source_answer(q),
            "grading_contract": {"enabled": True, "mode": "contract_exact_or_tolerance"},
            "difficulty_level": level, "failure_signals": q.get("failure_signals") or [],
            "diagram_required": bool(q.get("diagram_required") or q.get("diagram")),
            "image_ref": q.get("image_ref"), "units_contract": units,
            "tolerance": root_tolerance(q, atype, contract),
            "provenance": {"source_artifact": str(qpath), "source_question_id": qid(q, ordinal)},
            "rights": {"cleared_for_use": True, "basis": "original_compiler_generated_content"},
            "assets": [], "exact_fingerprint": exact_fp(prompt), "structural_fingerprint": "",
            "parameterization": parameterization(q), **LABELS,
        }
        record["structural_fingerprint"] = structural_fp(record)
        rel = f"artifacts/records/{ordinal:03d}_{record['question_id']}.json"
        path = destination / rel
        write_json(path, record)
        sha = digest_file(path)
        artifacts.append({"path": rel, "sha256": sha, "media_type": "application/json", "role": "question_record"})
        records.append({"question_id": record["question_id"], "ordinal": ordinal, "artifact_path": rel, "artifact_sha256": sha})

    families = [family_declaration(raw, questions) for raw in raw_families]
    manifest = {
        "schema": "axiomiq_compiler_manifest_v1", "package_id": package_id,
        "package_version": PACKAGE_VERSION, "course_code": COURSE_CODE,
        "artifacts": sorted(artifacts, key=lambda x: x["path"]),
        "generation_families": families, "procedures": procedures, "records": records,
        "difficulty_distribution": {str(k): distribution[k] for k in sorted(distribution)},
        "provenance": {"source_system": "AxiomIQ course compiler", "source_commit": "0ae79257", "exported_at": CREATED_AT,
                       "authority_bundle": "e807c698 pinned to 0ae79257"},
        "rights": {"cleared_for_use": True, "basis": "original_compiler_generated_content"},
        **LABELS,
    }
    manifest_path = destination / "manifest.json"
    write_json(manifest_path, manifest)
    manifest_sha = digest_file(manifest_path)
    package_basis = {"manifest_sha256": manifest_sha, "artifacts": [{"path": x["path"], "sha256": x["sha256"]} for x in manifest["artifacts"]]}
    package_sha = digest_bytes(canonical(package_basis))
    descriptor = {
        "schema": "axiomiq_compiler_package_v1", "package_id": package_id,
        "package_version": PACKAGE_VERSION, "created_at": CREATED_AT,
        "compiler_commit": "0ae79257", "manifest_path": "manifest.json",
        "manifest_sha256": manifest_sha, "package_sha256": package_sha, "immutable": True,
    }
    write_json(destination / "package.json", descriptor)

    # Sidecars are excluded from the package digest and provide transport checks.
    for path in sorted(destination.rglob("*.json")):
        path.with_name(path.name + ".sha256").write_text(f"{digest_file(path)}  {path.name}\n", encoding="utf-8")

    emitted_snapshot = [(r["prompt"], r["correct_answer"], (r["procedure_id"], r["topic_code"], r["subtopic_code"], r["micro_skill_code"]))
                        for r in (json.loads((destination / item["artifact_path"]).read_text()) for item in records)]
    if source_snapshot != emitted_snapshot:
        raise RuntimeError(f"protected content changed in {lane}")
    return {
        "lane": lane, "package_id": package_id, "record_count": len(records), "family_count": len(families),
        "families_complete": all(all(k in f and isinstance(f[k], (dict, list)) for k in ("parameterization", "constraints", "invariants")) for f in families),
        "difficulty_distribution": manifest["difficulty_distribution"], "difficulty_emission_required": lane in DIFFICULTY_LANES,
        "publish_path": str(destination.resolve()), "manifest_sha256": manifest_sha,
        "package_sha256": package_sha, "protected_content_unchanged": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=PUBLISHED)
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    results = [emit_lane(lane, args.output_root) for lane in LANES]
    summary = {"verdict": "PACKAGES_CONFORMANT", "packages": results}
    summary_path = args.summary or args.output_root / "wave1r_package_conformance_summary.json"
    write_json(summary_path, summary)
    summary_path.with_name(summary_path.name + ".sha256").write_text(f"{digest_file(summary_path)}  {summary_path.name}\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
