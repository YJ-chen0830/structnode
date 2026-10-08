"""StructNode CLI (Typer). S0/S1 scope: `structnode model validate|apply|diff|snapshot`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import TypeAdapter, ValidationError

from structnode.core.editing import Command, CommandRejected, apply_command
from structnode.core.model import CEM, diff_cem
from structnode.core.snapshot import save_snapshot
from structnode.core.validation import (
    findings_to_dicts,
    pydantic_errors_to_dicts,
    validate_topology,
)

app = typer.Typer(no_args_is_help=True)
model_app = typer.Typer(no_args_is_help=True)
app.add_typer(model_app, name="model")

_command_adapter: TypeAdapter[Command] = TypeAdapter(Command)


def _empty_result() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "status": "ok",
        "warnings": [],
        "errors": [],
        "model_hash": None,
        "provenance": None,
        "artifact_paths": [],
    }


def _load_cem_or_none(path: Path) -> tuple[CEM | None, dict[str, Any]]:
    """Load + fully validate (schema, then topology) a CEM document.

    Returns `(cem, result)` on success or `(None, result)` with
    `result["errors"]` populated on any failure -- callers emit
    `result` either way and only need to branch on whether `cem` is
    `None`.
    """
    result = _empty_result()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result["status"] = "error"
        result["errors"].append(
            {
                "code": "CEM-SCHEMA-INVALID_JSON",
                "severity": "error",
                "message": str(exc),
                "path": "<root>",
            }
        )
        return None, result

    try:
        cem = CEM.model_validate(data)
    except ValidationError as exc:
        result["status"] = "error"
        result["errors"].extend(pydantic_errors_to_dicts(exc))
        return None, result

    topology = validate_topology(cem)
    result["errors"].extend(findings_to_dicts(topology.errors))
    result["warnings"].extend(findings_to_dicts(topology.warnings))
    result["model_hash"] = cem.content_hash
    result["provenance"] = cem.provenance.model_dump(mode="json")

    if not topology.ok:
        result["status"] = "error"
        return None, result

    return cem, result


@model_app.command("validate")
def model_validate(
    path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON")] = False,
) -> None:
    """Validate a CEM JSON document: schema, then topology/engineering sanity."""
    cem, result = _load_cem_or_none(path)
    _emit(result, as_json)
    if cem is None:
        raise typer.Exit(code=1)


@model_app.command("apply")
def model_apply(
    path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    command_path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    out: Annotated[Path, typer.Option("--out", help="Where to write the resulting CEM")],
    created_by: Annotated[str, typer.Option("--created-by")] = "human",
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON")] = False,
) -> None:
    """Apply one typed edit command (JSON file) to a CEM document.

    Atomic: on any rejection, `path` and `out` are both left untouched.
    """
    cem, result = _load_cem_or_none(path)
    if cem is None:
        _emit(result, as_json)
        raise typer.Exit(code=1)

    try:
        command_data = json.loads(command_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result["status"] = "error"
        result["errors"] = [
            {
                "code": "CEM-SCHEMA-INVALID_JSON",
                "severity": "error",
                "message": str(exc),
                "path": "<command>",
            }
        ]
        _emit(result, as_json)
        raise typer.Exit(code=1) from exc

    try:
        command = _command_adapter.validate_python(command_data)
    except ValidationError as exc:
        result["status"] = "error"
        result["errors"] = pydantic_errors_to_dicts(exc)
        _emit(result, as_json)
        raise typer.Exit(code=1) from exc

    try:
        new_cem = apply_command(cem, command, created_by=created_by)
    except CommandRejected as exc:
        result["status"] = "error"
        result["errors"] = exc.findings
        _emit(result, as_json)
        raise typer.Exit(code=1) from exc

    out.write_bytes(new_cem.canonical_json())
    result = _empty_result()
    result["model_hash"] = new_cem.content_hash
    result["provenance"] = new_cem.provenance.model_dump(mode="json")
    result["artifact_paths"] = [str(out)]
    _emit(result, as_json)


@model_app.command("diff")
def model_diff(
    old_path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    new_path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON")] = False,
) -> None:
    """Show a structured diff between two CEM documents."""
    old_cem, old_result = _load_cem_or_none(old_path)
    if old_cem is None:
        _emit(old_result, as_json)
        raise typer.Exit(code=1)
    new_cem, new_result = _load_cem_or_none(new_path)
    if new_cem is None:
        _emit(new_result, as_json)
        raise typer.Exit(code=1)

    diff = diff_cem(old_cem, new_cem)
    result = _empty_result()
    result["model_hash"] = new_cem.content_hash
    result["diff"] = diff.to_dict()
    if as_json:
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
        return
    for name, collection_diff in diff.to_dict().items():
        if any(collection_diff.values()):
            typer.echo(f"{name}: {collection_diff}")
    if diff.is_empty:
        typer.echo("no differences")


@model_app.command("snapshot")
def model_snapshot(
    path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    directory: Annotated[Path, typer.Option("--dir")] = Path(".structnode/snapshots"),
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON")] = False,
) -> None:
    """Write an immutable, content-hash-addressed snapshot of a CEM document."""
    cem, result = _load_cem_or_none(path)
    if cem is None:
        _emit(result, as_json)
        raise typer.Exit(code=1)

    snapshot_path = save_snapshot(cem, directory)
    result["artifact_paths"] = [str(snapshot_path)]
    _emit(result, as_json)


def _emit(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        typer.echo(json.dumps(result, indent=2, ensure_ascii=False))
        return
    status = result["status"]
    typer.echo(f"status: {status}")
    for e in result["errors"]:
        typer.echo(f"  [error] {e['code']} ({e['path']}): {e['message']}", err=True)
    for w in result["warnings"]:
        typer.echo(f"  [warn]  {w['code']} ({w['path']}): {w['message']}")
    if result["model_hash"]:
        typer.echo(f"model_hash: {result['model_hash']}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
