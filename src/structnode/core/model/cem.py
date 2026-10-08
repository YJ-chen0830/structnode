"""Canonical Engineering Model (CEM) v0.1.

CEM is the engineering source of truth. Everything else (solver decks,
CAD drawings, reports) is a derived representation. This module defines
the data contract only; cross-field engineering/topology rules that need
model-wide context (e.g. "every analysis case needs a stable support
condition") live in `structnode.core.validation`, not here. What *does*
live here is structural data integrity that can never be valid at any
level: duplicate IDs, non-positive section/material properties, zero
length elements referencing the same node twice, etc.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, model_validator

from structnode.core.units import Units

CoordinateSystem = Literal["global_cartesian_rh"]
ElementType = Literal["truss", "frame"]
AnalysisMethod = Literal["linear_static"]
LoadKind = Literal["nodal_force", "nodal_moment", "member_distributed", "gravity"]
CoordinateBasis = Literal["global", "local"]
CreatedBy = str  # "human" | "agent:<name>" | "import:<source>", validated loosely for now


class Node(BaseModel):
    id: str
    position: tuple[float, float, float]
    """Global coordinates in SI meters."""


class Material(BaseModel):
    id: str
    E: float = Field(gt=0, description="Young's modulus, Pa")
    G: float | None = Field(default=None, gt=0, description="Shear modulus, Pa")
    rho: float | None = Field(default=None, ge=0, description="Density, kg/m^3")
    nu: float | None = Field(default=None, gt=-1.0, lt=0.5, description="Poisson's ratio")

    @model_validator(mode="after")
    def _check_isotropic_consistency(self) -> Material:
        if self.G is not None and self.nu is not None:
            expected_g = self.E / (2 * (1 + self.nu))
            rel_err = abs(self.G - expected_g) / expected_g
            if rel_err > 1e-3:
                raise ValueError(
                    f"Material {self.id!r}: G={self.G} is inconsistent with "
                    f"E={self.E}, nu={self.nu} (expected G~={expected_g:.3f}, "
                    f"rel. error {rel_err:.1%} > 0.1%)"
                )
        return self


class FrameSection(BaseModel):
    id: str
    A: float = Field(gt=0, description="Cross-sectional area, m^2")
    Iy: float = Field(gt=0, description="Second moment of area about local y, m^4")
    Iz: float = Field(gt=0, description="Second moment of area about local z, m^4")
    J: float = Field(gt=0, description="Torsional constant, m^4")
    local_axis_hint: tuple[float, float, float] | None = None
    """Reference vector used to resolve the local y/z orientation.

    When omitted, adapters/solvers fall back to a default rule (closest
    global axis) and MUST report that fallback as a warning -- this
    model intentionally does not pick a silent default itself.
    """


class Element(BaseModel):
    id: str
    type: ElementType
    node_ids: tuple[str, str]
    material_id: str
    section_id: str
    releases: tuple[bool, ...] | None = None
    """6 booleans per end (12 total) for frame elements; must be None for truss."""

    @model_validator(mode="after")
    def _check_shape(self) -> Element:
        if self.node_ids[0] == self.node_ids[1]:
            raise ValueError(f"Element {self.id!r}: node_ids must reference two distinct nodes")
        if self.type == "truss" and self.releases is not None:
            raise ValueError(f"Element {self.id!r}: truss elements must not declare releases")
        if self.type == "frame" and self.releases is not None and len(self.releases) != 12:
            raise ValueError(
                f"Element {self.id!r}: frame releases must have 12 entries (6 DOF x 2 ends), "
                f"got {len(self.releases)}"
            )
        return self


class Support(BaseModel):
    node_id: str
    dofs: tuple[bool, bool, bool, bool, bool, bool]
    """Restrained global DOFs: (Tx, Ty, Tz, Rx, Ry, Rz)."""


class LoadCase(BaseModel):
    id: str
    description: str | None = None


class Load(BaseModel):
    id: str
    case_id: str
    kind: LoadKind
    target_id: str
    values: tuple[float, ...]
    coordinate_basis: CoordinateBasis


class AnalysisCase(BaseModel):
    id: str
    load_case_ids: tuple[str, ...]
    method: AnalysisMethod
    solver_options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_nonempty(self) -> AnalysisCase:
        if not self.load_case_ids:
            raise ValueError(f"AnalysisCase {self.id!r}: load_case_ids must not be empty")
        return self


class Provenance(BaseModel):
    created_by: CreatedBy
    created_at: datetime
    parent_revision: str | None = None
    tool_version: str


class _HasId(Protocol):
    id: str


def _duplicate_ids(items: Sequence[_HasId], label: str) -> str | None:
    seen: set[str] = set()
    for item in items:
        if item.id in seen:
            return f"Duplicate {label} id: {item.id!r}"
        seen.add(item.id)
    return None


class CEM(BaseModel):
    """Canonical Engineering Model v0.1 root document."""

    schema_version: Literal["0.1"] = "0.1"
    model_id: str
    revision: int = Field(ge=0)
    units: Units
    coordinate_system: CoordinateSystem
    nodes: list[Node]
    materials: list[Material]
    sections: list[FrameSection]
    elements: list[Element]
    constraints: list[Support]
    load_cases: list[LoadCase]
    loads: list[Load]
    analysis_cases: list[AnalysisCase]
    metadata: dict[str, Any] = Field(default_factory=dict)
    provenance: Provenance

    @model_validator(mode="after")
    def _check_unique_ids(self) -> CEM:
        for items, label in (
            (self.nodes, "node"),
            (self.materials, "material"),
            (self.sections, "section"),
            (self.elements, "element"),
            (self.load_cases, "load_case"),
            (self.analysis_cases, "analysis_case"),
        ):
            error = _duplicate_ids(items, label)
            if error is not None:
                raise ValueError(error)
        return self

    def canonical_json(self) -> bytes:
        """Deterministic serialization used for hashing: sorted keys, no whitespace."""
        return json.dumps(
            self.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json()).hexdigest()
