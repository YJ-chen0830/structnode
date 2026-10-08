"""Typed edit commands an AI agent (or human) may propose against a CEM.

Mirrors the "AI agent boundary" from docs/MASTER_PLAN.md section 1:
agents only ever produce these typed commands, never raw numerical
results or direct document mutation. `structnode.core.editing.apply`
is the deterministic engine that checks and applies them.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from structnode.core.model.cem import AnalysisMethod, CoordinateBasis, ElementType, LoadKind


class CreateNode(BaseModel):
    op: Literal["create_node"] = "create_node"
    id: str
    position: tuple[float, float, float]


class CreateMaterial(BaseModel):
    op: Literal["create_material"] = "create_material"
    id: str
    E: float
    G: float | None = None
    rho: float | None = None
    nu: float | None = None


class CreateFrameSection(BaseModel):
    op: Literal["create_section"] = "create_section"
    id: str
    A: float
    Iy: float
    Iz: float
    J: float
    local_axis_hint: tuple[float, float, float] | None = None


class CreateElement(BaseModel):
    op: Literal["create_element"] = "create_element"
    id: str
    type: ElementType
    node_ids: tuple[str, str]
    material_id: str
    section_id: str
    releases: tuple[bool, ...] | None = None


class AssignSupport(BaseModel):
    op: Literal["assign_support"] = "assign_support"
    node_id: str
    dofs: tuple[bool, bool, bool, bool, bool, bool]


class CreateLoadCase(BaseModel):
    op: Literal["create_load_case"] = "create_load_case"
    id: str
    description: str | None = None


class ApplyLoad(BaseModel):
    op: Literal["apply_load"] = "apply_load"
    id: str
    case_id: str
    kind: LoadKind
    target_id: str
    values: tuple[float, ...]
    coordinate_basis: CoordinateBasis


class CreateAnalysisCase(BaseModel):
    op: Literal["create_analysis_case"] = "create_analysis_case"
    id: str
    load_case_ids: tuple[str, ...]
    method: AnalysisMethod
    solver_options: dict[str, Any] = Field(default_factory=dict)


Command = Annotated[
    CreateNode
    | CreateMaterial
    | CreateFrameSection
    | CreateElement
    | AssignSupport
    | CreateLoadCase
    | ApplyLoad
    | CreateAnalysisCase,
    Field(discriminator="op"),
]

# Maps each command's `op` to the CEM collection it appends to.
COMMAND_TARGET_COLLECTION: dict[str, str] = {
    "create_node": "nodes",
    "create_material": "materials",
    "create_section": "sections",
    "create_element": "elements",
    "assign_support": "constraints",
    "create_load_case": "load_cases",
    "apply_load": "loads",
    "create_analysis_case": "analysis_cases",
}
