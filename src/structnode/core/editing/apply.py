"""Deterministic engine that applies a typed `Command` to a CEM.

Atomicity contract: `apply_command` either returns a brand new,
fully schema- and topology-valid `CEM` with `revision` incremented and
`provenance` updated, or raises `CommandRejected` leaving the input
`cem` completely untouched (pydantic models are immutable-by-convention
here; we only ever build a new dict and re-validate it from scratch).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from structnode.core.editing.commands import COMMAND_TARGET_COLLECTION, Command
from structnode.core.model import CEM
from structnode.core.validation import (
    findings_to_dicts,
    pydantic_errors_to_dicts,
    validate_topology,
)


class CommandRejected(Exception):
    """Raised when a command would produce an invalid CEM; nothing was applied.

    `findings` is always normalized to the `{code, severity, message,
    path}` dict shape (via `core.validation.report`), regardless of
    whether the rejection came from schema or topology validation, so
    callers (CLI, future REST/MCP) never need to branch on the source.
    """

    def __init__(self, findings: list[dict[str, Any]]) -> None:
        self.findings = findings
        super().__init__(f"{len(findings)} finding(s): {findings!r}")


def apply_command(cem: CEM, command: Command, created_by: str) -> CEM:
    collection = COMMAND_TARGET_COLLECTION[command.op]
    item = command.model_dump(mode="json", exclude={"op"})

    candidate_dict = cem.model_dump(mode="json")
    candidate_dict[collection] = [*candidate_dict[collection], item]
    candidate_dict["revision"] = cem.revision + 1
    candidate_dict["provenance"] = {
        "created_by": created_by,
        "created_at": datetime.now(UTC).isoformat(),
        "parent_revision": cem.content_hash,
        "tool_version": cem.provenance.tool_version,
    }

    try:
        candidate = CEM.model_validate(candidate_dict)
    except ValidationError as exc:
        raise CommandRejected(pydantic_errors_to_dicts(exc)) from exc

    topology = validate_topology(candidate)
    if not topology.ok:
        raise CommandRejected(findings_to_dicts(topology.errors))

    return candidate
