"""StructNode CLI (Typer). S0 scope: `structnode model validate`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import ValidationError

from structnode.core.model import CEM
from structnode.core.validation import validate_topology

app = typer.Typer(no_args_is_help=True)
model_app = typer.Typer(no_args_is_help=True)
app.add_typer(model_app, name="model")


def _pydantic_errors_to_findings(exc: ValidationError) -> list[dict[str, Any]]:
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


def _finding_to_dict(f: Any) -> dict[str, Any]:
    return {"code": f.code, "severity": f.severity.value, "message": f.message, "path": f.path}


@model_app.command("validate")
def model_validate(
    path: Annotated[Path, typer.Argument(exists=True, readable=True)],
    as_json: Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON")] = False,
) -> None:
    """Validate a CEM JSON document: schema, then topology/engineering sanity."""
    raw = path.read_text(encoding="utf-8")

    result: dict[str, Any] = {
        "schema_version": "0.1",
        "status": "ok",
        "warnings": [],
        "errors": [],
        "model_hash": None,
        "provenance": None,
        "artifact_paths": [],
    }

    try:
        data = json.loads(raw)
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
        _emit(result, as_json)
        raise typer.Exit(code=1) from exc

    try:
        cem = CEM.model_validate(data)
    except ValidationError as exc:
        result["status"] = "error"
        result["errors"].extend(_pydantic_errors_to_findings(exc))
        _emit(result, as_json)
        raise typer.Exit(code=1) from exc

    topology = validate_topology(cem)
    result["errors"].extend(_finding_to_dict(f) for f in topology.errors)
    result["warnings"].extend(_finding_to_dict(f) for f in topology.warnings)
    result["model_hash"] = cem.content_hash
    result["provenance"] = cem.provenance.model_dump(mode="json")

    if not topology.ok:
        result["status"] = "error"
        _emit(result, as_json)
        raise typer.Exit(code=1)

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
