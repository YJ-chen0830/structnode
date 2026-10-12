"""MCP server exposing the same service layer (`structnode.service`) as
the CLI and REST API -- no FEM logic lives here, only tool registration
and docstrings an agent reads to decide what to call
(docs/MASTER_PLAN.md section 1: "MCP exposes the same service layer as
CLI and REST; never implement separate FEM logic inside MCP handlers").

Tools are narrow and stateless over JSON: every tool takes and returns
plain dicts, and only `model_snapshot` ever touches the filesystem --
and only when the caller passes `confirm=True` (default `False`),
matching section 1's "high-impact operations ... require explicit
human confirmation." A first call with `confirm=False` is a safe dry
run that reports what *would* be written.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from structnode import service

mcp = MCPServer(
    name="structnode",
    version="0.1.0",
    instructions=(
        "Structural engineering tools over the Canonical Engineering Model "
        "(CEM). Always call model_validate before model_apply/analysis_run "
        "on a model you didn't just build yourself. model_snapshot defaults "
        "to a dry run (confirm=False) -- call it again with confirm=True "
        "only after reviewing the dry-run output, since it writes to disk."
    ),
)


@mcp.tool()
def model_validate(cem: dict[str, Any]) -> dict[str, Any]:
    """Validate a CEM document: schema, then topology/engineering sanity.
    Always call this before model_apply or analysis_run on a model you
    did not just construct yourself in this conversation."""
    return service.model_validate(cem)


@mcp.tool()
def model_apply(
    cem: dict[str, Any], command: dict[str, Any], created_by: str = "agent"
) -> dict[str, Any]:
    """Apply one typed edit command (e.g. create_node, create_element,
    assign_support, apply_load) to a CEM document. Atomic: on any
    rejection, nothing is applied and `cem` in the response is absent --
    only `errors` is populated. Returns the new CEM under `cem` on
    success, which you should treat as the model going forward (the
    input `cem` is not mutated)."""
    return service.model_apply(cem, command, created_by=created_by)


@mcp.tool()
def model_diff(cem_a: dict[str, Any], cem_b: dict[str, Any]) -> dict[str, Any]:
    """Structured diff (added/removed/changed, per collection) between
    two CEM documents."""
    return service.model_diff(cem_a, cem_b)


@mcp.tool()
def model_snapshot(cem: dict[str, Any], directory: str, confirm: bool = False) -> dict[str, Any]:
    """Write an immutable, content-hash-addressed snapshot of a CEM
    document to `directory` on disk. HIGH-IMPACT: writes to the
    filesystem. With the default confirm=False this is a dry run --
    nothing is written, and the response's `would_write` field shows
    the path that a `confirm=True` call would produce. Only call with
    confirm=True after a human has reviewed the dry run, or when a
    human explicitly asked you to save."""
    return service.model_snapshot(cem, directory, confirm=confirm)


@mcp.tool()
def analysis_run(
    cem: dict[str, Any], analysis_case_id: str, solver: str = "native-2d"
) -> dict[str, Any]:
    """Run a linear-static analysis for one analysis_case_id in `cem`.
    `solver` is one of 'native-2d' (planar models only), 'native-3d', or
    'opensees' (cross-check; may be unavailable depending on the host
    environment -- check capabilities_list first if unsure). Read-only:
    results are returned, never written to disk."""
    return service.analysis_run(cem, analysis_case_id, solver=solver)


@mcp.tool()
def analysis_compare(
    results_a: dict[str, Any], results_b: dict[str, Any], tolerance: float = 1e-6
) -> dict[str, Any]:
    """Compare two analysis results payloads (e.g. two solvers, or 2D vs
    3D on the same planar model) quantity-by-quantity. `ok=false` means
    either a quantity differs by more than `tolerance` (relative) or a
    quantity/node/element is present in one result but not the other --
    check `missing_in_a`/`missing_in_b` before concluding they simply
    disagree numerically."""
    return service.analysis_compare(results_a, results_b, tolerance=tolerance)


@mcp.tool()
def report_generate(results: dict[str, Any], report_format: str = "markdown") -> dict[str, Any]:
    """Render a human-readable report from an analysis_run results
    payload. Currently only report_format='markdown' is supported."""
    return service.report_generate(results, fmt=report_format)


@mcp.tool()
def capabilities_list() -> dict[str, Any]:
    """List what each solver backend supports (element types,
    dimensionality, load kinds) and whether it's actually usable right
    now in this environment (e.g. the opensees backend may be
    unavailable). Safe to call anytime, no model required."""
    return service.capabilities_list()
