"""Typed REST API over the same service layer (`structnode.service`) as
the CLI and MCP server -- see service.py's module docstring for the
"no separate FEM logic" rule this follows.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from structnode import service

app = FastAPI(
    title="StructNode API",
    description=(
        "AI-native, solver-neutral structural engineering platform. "
        "EXPERIMENTAL -- not for engineering design without independent review."
    ),
    version="0.1.0",
)


class ModelValidateRequest(BaseModel):
    cem: dict[str, Any]


class ModelApplyRequest(BaseModel):
    cem: dict[str, Any]
    command: dict[str, Any]
    created_by: str = "agent"


class ModelDiffRequest(BaseModel):
    cem_a: dict[str, Any]
    cem_b: dict[str, Any]


class ModelSnapshotRequest(BaseModel):
    cem: dict[str, Any]
    directory: str
    confirm: bool = False


class AnalysisRunRequest(BaseModel):
    cem: dict[str, Any]
    analysis_case_id: str
    solver: str = "native-2d"


class AnalysisCompareRequest(BaseModel):
    results_a: dict[str, Any]
    results_b: dict[str, Any]
    tolerance: float = 1e-6


class ReportGenerateRequest(BaseModel):
    results: dict[str, Any]
    format: str = "markdown"


@app.post("/models/validate")
def models_validate(body: ModelValidateRequest) -> dict[str, Any]:
    return service.model_validate(body.cem)


@app.post("/models/apply")
def models_apply(body: ModelApplyRequest) -> dict[str, Any]:
    return service.model_apply(body.cem, body.command, created_by=body.created_by)


@app.post("/models/diff")
def models_diff(body: ModelDiffRequest) -> dict[str, Any]:
    return service.model_diff(body.cem_a, body.cem_b)


@app.post("/models/snapshot")
def models_snapshot(body: ModelSnapshotRequest) -> dict[str, Any]:
    """HIGH-IMPACT when confirm=true: writes to the filesystem. See
    service.model_snapshot's docstring."""
    return service.model_snapshot(body.cem, body.directory, confirm=body.confirm)


@app.post("/analysis/run")
def analysis_run(body: AnalysisRunRequest) -> dict[str, Any]:
    return service.analysis_run(body.cem, body.analysis_case_id, solver=body.solver)


@app.post("/analysis/compare")
def analysis_compare(body: AnalysisCompareRequest) -> dict[str, Any]:
    return service.analysis_compare(body.results_a, body.results_b, tolerance=body.tolerance)


@app.post("/reports/generate")
def reports_generate(body: ReportGenerateRequest) -> dict[str, Any]:
    return service.report_generate(body.results, fmt=body.format)


@app.get("/capabilities")
def capabilities() -> dict[str, Any]:
    return service.capabilities_list()
