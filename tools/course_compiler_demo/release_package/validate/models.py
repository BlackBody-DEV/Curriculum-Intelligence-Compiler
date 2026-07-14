"""Stable validation result models for portable release packages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


VALIDATOR_NAME = "compiler_release_package_semantic_validator"
VALIDATOR_VERSION = "1.0.0"


@dataclass(order=True)
class ValidationIssue:
    rule_id: str
    severity: str
    message: str
    scope: str = "package"
    field: str | None = None
    evidence: str | None = None
    recommended_action: str = "Correct the package and rerun validation."

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity,
            "message": self.message,
            "artifact_id": self.scope,
            "field": self.field,
            "path": self.field,
            "evidence": self.evidence,
            "recommended_action": self.recommended_action,
        }


@dataclass
class RuleResult:
    rule_id: str
    status: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"rule_id": self.rule_id, "status": self.status, "message": self.message}


@dataclass
class ValidationContext:
    package_path: str
    validation_started_at: str = field(default_factory=lambda: now_iso())
    package_id: str | None = None
    package_contract: str | None = None
    package_version: str | None = None
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    rule_results: list[RuleResult] = field(default_factory=list)
    artifact_results: list[dict[str, Any]] = field(default_factory=list)

    def add_error(
        self,
        rule_id: str,
        message: str,
        *,
        scope: str = "package",
        field: str | None = None,
        evidence: str | None = None,
        recommended_action: str = "Correct the package and rerun validation.",
    ) -> None:
        self.errors.append(
            ValidationIssue(
                rule_id=rule_id,
                severity="error",
                message=message,
                scope=scope,
                field=field,
                evidence=evidence,
                recommended_action=recommended_action,
            )
        )

    def add_warning(
        self,
        rule_id: str,
        message: str,
        *,
        scope: str = "package",
        field: str | None = None,
        evidence: str | None = None,
        recommended_action: str = "Review the warning before protected integration review.",
    ) -> None:
        self.warnings.append(
            ValidationIssue(
                rule_id=rule_id,
                severity="warning",
                message=message,
                scope=scope,
                field=field,
                evidence=evidence,
                recommended_action=recommended_action,
            )
        )

    def set_rule(self, rule_id: str, status: str, message: str) -> None:
        self.rule_results.append(RuleResult(rule_id=rule_id, status=status, message=message))


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
