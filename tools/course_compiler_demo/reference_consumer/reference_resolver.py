"""Internal reference resolution and dependency ordering."""

from __future__ import annotations

from typing import Any


MANIFEST_LISTS = [
    "procedure_artifact_ids",
    "question_artifact_ids",
    "generation_family_artifact_ids",
    "signal_mapping_artifact_ids",
    "performance_tracking_artifact_ids",
    "review_artifact_ids",
    "validation_artifact_ids",
    "asset_artifact_ids",
]


def resolve_references(manifest: dict[str, Any], payloads: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    artifacts = {item["artifact_id"]: item for item in manifest.get("artifact_inventory", [])}
    artifact_ids = set(artifacts)
    source_ids = {source.get("source_id") for source in manifest.get("source_references", [])}
    micro_skills = set(manifest.get("micro_skill_codes", []))
    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    def add(kind: str, origin: str, target: str | None, status: str) -> None:
        item = {"reference_type": kind, "origin": origin, "target": target, "status": status}
        if status == "unresolved":
            unresolved.append(item)
        else:
            resolved.append(item)

    for list_name in MANIFEST_LISTS:
        values = manifest.get(list_name, [])
        if not values:
            add(f"manifest.{list_name}", "manifest", None, "not_applicable")
        for artifact_id in values:
            add(f"manifest.{list_name}", "manifest", artifact_id, "resolved" if artifact_id in artifact_ids else "unresolved")

    for artifact in manifest.get("artifact_inventory", []):
        artifact_id = artifact["artifact_id"]
        deps = artifact.get("depends_on_artifact_ids", [])
        if not deps:
            add("artifact_dependency", artifact_id, None, "not_applicable")
        for dep in deps:
            add("artifact_dependency", artifact_id, dep, "resolved" if dep in artifact_ids else "unresolved")
        sources = artifact.get("source_reference_ids", [])
        if not sources:
            add("source_reference", artifact_id, None, "resolved_with_warning")
        for source_id in sources:
            add("source_reference", artifact_id, source_id, "resolved" if source_id in source_ids else "unresolved")

        payload = payloads.get(artifact_id, {})
        artifact_type = artifact.get("artifact_type")
        if artifact_type == "question_candidate":
            dep_status = "resolved" if set(deps) & set(manifest.get("procedure_artifact_ids", [])) else "resolved_with_warning"
            add("question_to_procedure", artifact_id, next(iter(sorted(set(deps) & set(manifest.get("procedure_artifact_ids", [])))), None), dep_status)
        elif artifact_type == "generation_family_candidate":
            target = next(iter(sorted(set(deps) & artifact_ids)), None)
            add("generation_family_reference", artifact_id, target, "resolved" if target else "resolved_with_warning")
        elif artifact_type == "signal_mapping":
            target = payload.get("target")
            targets = micro_skills | set(manifest.get("procedure_artifact_ids", [])) | set(manifest.get("question_artifact_ids", []))
            add("signal_mapping_target", artifact_id, target, "resolved" if not target or target in targets else "unresolved")
        elif artifact_type == "performance_tracking_target":
            for outcome in payload.get("tracked_outcomes", []):
                add("performance_target_curriculum_reference", artifact_id, outcome, "resolved_with_warning")
        elif artifact_type == "review_record":
            add("review_record_target", artifact_id, payload.get("review_target_id"), "resolved_with_warning")
        elif artifact_type == "validation_report":
            add("validation_record_target", artifact_id, payload.get("validation_target_id"), "resolved_with_warning")
        elif artifact_type == "asset_reference":
            add("asset_reference", artifact_id, payload.get("asset_ref"), "resolved_with_warning")

    return (
        sorted(resolved, key=lambda item: (item["reference_type"], item["origin"], str(item["target"]))),
        sorted(unresolved, key=lambda item: (item["reference_type"], item["origin"], str(item["target"]))),
    )


def dependency_order(manifest: dict[str, Any]) -> tuple[list[str], bool]:
    graph = {
        item["artifact_id"]: sorted(item.get("depends_on_artifact_ids", []))
        for item in manifest.get("artifact_inventory", [])
    }
    visiting: set[str] = set()
    visited: set[str] = set()
    ordered: list[str] = []
    cycle = False

    def visit(node: str) -> None:
        nonlocal cycle
        if node in visiting:
            cycle = True
            return
        if node in visited:
            return
        visiting.add(node)
        for dep in graph.get(node, []):
            if dep in graph:
                visit(dep)
        visiting.remove(node)
        visited.add(node)
        ordered.append(node)

    for node in sorted(graph):
        visit(node)
    return ordered, cycle
