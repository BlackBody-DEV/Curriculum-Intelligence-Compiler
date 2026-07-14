"""Normalize and compare reproduction run outputs."""

from __future__ import annotations

import copy
from typing import Any

from tools.course_compiler_demo.integration_readiness.models import VOLATILE_OBSERVABILITY_FIELDS


def normalize_validator(result: dict[str, Any]) -> dict[str, Any]:
    data = copy.deepcopy(result)
    for key in VOLATILE_OBSERVABILITY_FIELDS:
        data.pop(key, None)
    return data


def normalize_consumer(result: dict[str, Any]) -> dict[str, Any]:
    data = copy.deepcopy(result)
    for key in VOLATILE_OBSERVABILITY_FIELDS:
        data.pop(key, None)
    return data


def compare_runs(run_results: list[dict[str, Any]]) -> dict[str, Any]:
    first = run_results[0]
    validator_baseline = normalize_validator(first["validator_result"])
    consumer_baseline = normalize_consumer(first["consumer_result"])
    validator_match = []
    consumer_match = []
    for run in run_results:
        validator_match.append(normalize_validator(run["validator_result"]) == validator_baseline)
        consumer_match.append(normalize_consumer(run["consumer_result"]) == consumer_baseline)
    consumer_results = [run["consumer_result"] for run in run_results]
    return {
        "validator_results_match": all(validator_match),
        "consumer_results_match": all(consumer_match),
        "manifest_digest_match": len({run["input_inventory"]["manifest_digest"] for run in run_results}) == 1,
        "artifact_digest_match": len({tuple(sorted(run["input_inventory"]["artifact_digests"].items())) for run in run_results}) == 1,
        "artifact_order_match": len({tuple(item["artifact_id"] for item in result["declared_artifacts"]) for result in consumer_results}) == 1,
        "dependency_order_match": len({tuple(result["dependency_order"]) for result in consumer_results}) == 1,
        "reference_resolution_match": len({str(result["resolved_references"]) + str(result["unresolved_references"]) for result in consumer_results}) == 1,
        "error_order_match": len({str(result["errors"]) for result in consumer_results}) == 1,
        "warning_order_match": len({str(result["warnings"]) for result in consumer_results}) == 1,
        "unexpected_differences": []
        if all(validator_match) and all(consumer_match)
        else ["validator or consumer normalized output drift"],
    }
