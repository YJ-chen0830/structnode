"""Shared service layer: "MCP exposes the same service layer as CLI and
REST; never implement separate FEM logic inside MCP handlers"
(docs/MASTER_PLAN.md section 1).

Every function here takes and returns plain JSON-compatible dicts (no
CEM/pydantic objects crossing the boundary) and does no I/O beyond what
its docstring says explicitly -- `model_snapshot` is the only function
that touches the filesystem, and only when `confirm=True`. MCP and REST
are both thin protocol adapters over this module; neither re-derives
FEM results or validation on its own.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from structnode.adapters.opensees import OpenSeesUnavailableError, run_linear_static_opensees
from structnode.adapters.opensees import capabilities as opensees_capabilities
from structnode.core.editing import Command, CommandRejected, apply_command
from structnode.core.model import CEM, diff_cem
from structnode.core.snapshot import save_snapshot
from structnode.core.validation import (
    findings_to_dicts,
    pydantic_errors_to_dicts,
    validate_topology,
)
from structnode.fem.assembly import UnsupportedModelError
from structnode.fem.solvers import (
    AnalysisCaseNotFoundError,
    AnalysisResult2D,
    AnalysisResult3D,
    SingularStiffnessError,
    solve_linear_static_2d,
    solve_linear_static_3d,
)
from structnode.reporting import compare_results, render_markdown_report

_SOLVER_ERRORS = (
    AnalysisCaseNotFoundError,
    UnsupportedModelError,
    SingularStiffnessError,
    OpenSeesUnavailableError,
)

_command_adapter: TypeAdapter[Command] = TypeAdapter(Command)


def _empty_result() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "status": "ok",
        "warnings": [],
        "errors": [],
        "model_hash": None,
        "provenance": None,
    }


def _validate_cem_dict(cem_dict: dict[str, Any]) -> tuple[CEM | None, dict[str, Any]]:
    result = _empty_result()
    try:
        cem = CEM.model_validate(cem_dict)
    except ValidationError as exc:
        result["status"] = "error"
        result["errors"] = pydantic_errors_to_dicts(exc)
        return None, result

    topology = validate_topology(cem)
    result["errors"] = findings_to_dicts(topology.errors)
    result["warnings"] = findings_to_dicts(topology.warnings)
    result["model_hash"] = cem.content_hash
    result["provenance"] = cem.provenance.model_dump(mode="json")
    if not topology.ok:
        result["status"] = "error"
        return None, result
    return cem, result


def model_validate(cem_dict: dict[str, Any]) -> dict[str, Any]:
    """Validate a CEM document: schema, then topology/engineering sanity."""
    _, result = _validate_cem_dict(cem_dict)
    return result


def model_apply(
    cem_dict: dict[str, Any], command_dict: dict[str, Any], created_by: str
) -> dict[str, Any]:
    """Apply one typed edit command. Atomic: `cem_dict` is never mutated
    in place, and failure never returns a partially-applied model."""
    cem, result = _validate_cem_dict(cem_dict)
    if cem is None:
        return result

    try:
        command = _command_adapter.validate_python(command_dict)
    except ValidationError as exc:
        result["status"] = "error"
        result["errors"] = pydantic_errors_to_dicts(exc)
        return result

    try:
        new_cem = apply_command(cem, command, created_by=created_by)
    except CommandRejected as exc:
        result["status"] = "error"
        result["errors"] = exc.findings
        return result

    result["model_hash"] = new_cem.content_hash
    result["provenance"] = new_cem.provenance.model_dump(mode="json")
    result["cem"] = new_cem.model_dump(mode="json")
    return result


def model_diff(cem_dict_a: dict[str, Any], cem_dict_b: dict[str, Any]) -> dict[str, Any]:
    """Structured diff between two CEM documents."""
    result = _empty_result()
    cem_a, result_a = _validate_cem_dict(cem_dict_a)
    if cem_a is None:
        result_a["status"] = "error"
        return result_a
    cem_b, result_b = _validate_cem_dict(cem_dict_b)
    if cem_b is None:
        result_b["status"] = "error"
        return result_b

    result["diff"] = diff_cem(cem_a, cem_b).to_dict()
    result["model_hash"] = cem_b.content_hash
    return result


def model_snapshot(cem_dict: dict[str, Any], directory: str, confirm: bool) -> dict[str, Any]:
    """Write an immutable snapshot of `cem_dict` to `directory`.

    High-impact (persists to the filesystem): per
    docs/MASTER_PLAN.md section 1, "high-impact operations ... require
    explicit human confirmation." With `confirm=False` (the default a
    caller should use for a preview), nothing is written -- the result
    describes what *would* be written (path, hash) so a human/agent can
    review before setting `confirm=True`.
    """
    cem, result = _validate_cem_dict(cem_dict)
    if cem is None:
        return result

    path = Path(directory) / f"{cem.content_hash}.cem.json"
    if not confirm:
        result["dry_run"] = True
        result["would_write"] = str(path)
        return result

    written_path = save_snapshot(cem, Path(directory))
    result["dry_run"] = False
    result["artifact_path"] = str(written_path)
    return result


def analysis_run(cem_dict: dict[str, Any], analysis_case_id: str, solver: str) -> dict[str, Any]:
    """Run a linear-static analysis. Read-only: never writes to disk --
    the caller decides whether/where to persist the returned results."""
    cem, result = _validate_cem_dict(cem_dict)
    if cem is None:
        return result

    solve_fn: Callable[[CEM, str], AnalysisResult2D | AnalysisResult3D]
    if solver in ("native", "native-2d"):
        solve_fn = solve_linear_static_2d
    elif solver == "native-3d":
        solve_fn = solve_linear_static_3d
    elif solver == "opensees":
        solve_fn = run_linear_static_opensees
    else:
        result["status"] = "error"
        result["errors"] = [
            {
                "code": "CEM-SOLVER-UNIMPLEMENTED",
                "severity": "error",
                "message": f"solver {solver!r} is not implemented",
                "path": "<solver>",
            }
        ]
        return result

    try:
        analysis_result = solve_fn(cem, analysis_case_id)
    except _SOLVER_ERRORS as exc:
        result["status"] = "error"
        result["errors"] = [
            {
                "code": "CEM-SOLVER-" + type(exc).__name__.upper(),
                "severity": "error",
                "message": str(exc),
                "path": f"analysis_cases[{analysis_case_id!r}]",
            }
        ]
        return result

    result.update(analysis_result.to_dict())
    return result


def analysis_compare(
    results_a: dict[str, Any], results_b: dict[str, Any], tolerance: float
) -> dict[str, Any]:
    """Compare two analysis results payloads quantity-by-quantity."""
    return compare_results(results_a, results_b, tolerance=tolerance).to_dict()


def report_generate(results: dict[str, Any], fmt: str) -> dict[str, Any]:
    """Render a human-readable report from an analysis results payload."""
    if fmt != "markdown":
        return {
            "status": "error",
            "errors": [
                {
                    "code": "CEM-REPORT-UNSUPPORTED_FORMAT",
                    "severity": "error",
                    "message": f"format {fmt!r} is not supported (only 'markdown')",
                    "path": "<format>",
                }
            ],
        }
    return {"status": "ok", "format": "markdown", "content": render_markdown_report(results)}


def capabilities_list() -> dict[str, Any]:
    """Static capability description of every solver backend -- always
    safe to call, no model required (docs/MASTER_PLAN.md section 3:
    "capability negotiation")."""
    return {
        "solvers": {
            "native-2d": {
                "element_types": ["truss", "frame"],
                "dimensionality": "2d",
                "requires_planar": True,
                "load_kinds": ["nodal_force", "nodal_moment", "member_distributed", "gravity"],
            },
            "native-3d": {
                "element_types": ["truss", "frame"],
                "dimensionality": "3d",
                "requires_planar": False,
                "load_kinds": ["nodal_force", "nodal_moment", "member_distributed", "gravity"],
            },
            "opensees": opensees_capabilities(),
        },
        "report_formats": ["markdown"],
    }
