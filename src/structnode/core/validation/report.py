"""Canonical conversion of validation outcomes into the `{code, severity,
message, path}` finding shape used by every machine-readable surface
(CLI today; REST/MCP later) -- kept in `core.validation` so CLI, the
command-editing engine, and future API/MCP layers share one definition
instead of each re-inventing the mapping.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from structnode.core.validation.topology import Finding


def pydantic_errors_to_dicts(exc: ValidationError) -> list[dict[str, Any]]:
    findings = []
    for err in exc.errors():
        path = ".".join(str(p) for p in err["loc"]) or "<root>"
        findings.append(
            {
                "code": "CEM-SCHEMA-" + err["type"].upper(),
                "severity": "error",
                "message": err["msg"],
                "path": path,
            }
        )
    return findings


def finding_to_dict(finding: Finding) -> dict[str, Any]:
    return {
        "code": finding.code,
        "severity": finding.severity.value,
        "message": finding.message,
        "path": finding.path,
    }


def findings_to_dicts(findings: list[Finding]) -> list[dict[str, Any]]:
    return [finding_to_dict(f) for f in findings]
