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


_REBAR_POS_TOL = 1e-6  # meters -- exact-ish coordinate/diameter match for mirror pairing


class RebarBar(BaseModel):
    y: float = Field(description="Local y-offset from the section centroid, m")
    z: float = Field(description="Local z-offset from the section centroid, m")
    diameter: float = Field(gt=0, description="Bar diameter, m")


def _bars_mirror_symmetric(bars: tuple[RebarBar, ...], *, flip_y: bool) -> bool:
    """True if every bar has a matching partner (same diameter) under
    reflection across y=0 (flip_y=True, y -> -y) or z=0 (flip_y=False,
    z -> -z) -- including a bar that lies exactly on the mirror axis,
    which is its own partner. See RebarLayout's validator for why this
    (rather than a looser "centroid is balanced" check) is required.
    """
    n = len(bars)
    matched = [False] * n
    for i in range(n):
        if matched[i]:
            continue
        bar = bars[i]
        ty = -bar.y if flip_y else bar.y
        tz = bar.z if flip_y else -bar.z
        found = False
        for j in range(n):
            if j == i or matched[j]:
                continue
            other = bars[j]
            if (
                abs(other.y - ty) < _REBAR_POS_TOL
                and abs(other.z - tz) < _REBAR_POS_TOL
                and abs(other.diameter - bar.diameter) < _REBAR_POS_TOL
            ):
                matched[i] = matched[j] = True
                found = True
                break
        if not found and abs(ty - bar.y) < _REBAR_POS_TOL and abs(tz - bar.z) < _REBAR_POS_TOL:
            matched[i] = True  # bar sits on the mirror axis -- its own partner
            found = True
        if not found:
            return False
    return True


class RebarLayout(BaseModel):
    """Reinforcement embedded in a FrameSection, for the transformed-section
    stiffness contribution (see `structnode.fem.rebar`) -- NOT a capacity/
    strength-design representation (no development length, spacing code
    checks, etc.; see ADR 0006 and MASTER_PLAN.md's "detailed RC design"
    exclusion, which this does not reopen).
    """

    material_id: str
    """References a Material in the model (the rebar steel) -- looked up
    together with the hosting element's own material to compute the
    modular ratio n = E_rebar / E_element at assembly time."""
    bars: tuple[RebarBar, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_mirror_symmetric(self) -> RebarLayout:
        # Mirror symmetry about *either* local axis provably zeroes the
        # product of inertia Iyz regardless of the modular ratio -- without
        # it, the transformed section's principal axes would be rotated
        # relative to y/z, which this project's frame elements (decoupled
        # Iy/Iz only, no Iyz term) cannot represent. Silently ignoring that
        # coupling would be exactly the "silently approximated" result
        # MASTER_PLAN.md's non-negotiables forbid -- so an asymmetric
        # layout is rejected outright rather than approximated.
        if not (
            _bars_mirror_symmetric(self.bars, flip_y=True)
            or _bars_mirror_symmetric(self.bars, flip_y=False)
        ):
            raise ValueError(
                "RebarLayout: bars must be mirror-symmetric about the local "
                "y=0 or z=0 axis (every bar needs a same-diameter partner at "
                "the reflected position, or lie exactly on the axis) -- an "
                "asymmetric layout would have a nonzero product of inertia "
                "(Iyz) that this project's decoupled Iy/Iz frame elements "
                "cannot represent"
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
    rebar: RebarLayout | None = None
    """Optional embedded reinforcement. When present, assembly computes an
    effective (transformed-section) A/Iy/Iz for elements using this section
    -- see `structnode.fem.rebar.effective_section_properties`. `A`, `Iy`,
    `Iz` above remain the plain (gross, unreinforced) section properties."""


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
    factors: tuple[float, ...] | None = None
    """Optional per-load-case scale factors, same length and order as
    `load_case_ids`. Lets one AnalysisCase represent a code load
    combination (e.g. "1.2D + 1.6L") via linear superposition over
    existing load cases, instead of duplicating load data under a scaled
    copy. `None` means every load case contributes at 1.0 (unweighted
    sum, the pre-factors behavior)."""
    solver_options: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_nonempty(self) -> AnalysisCase:
        if not self.load_case_ids:
            raise ValueError(f"AnalysisCase {self.id!r}: load_case_ids must not be empty")
        if self.factors is not None and len(self.factors) != len(self.load_case_ids):
            raise ValueError(
                f"AnalysisCase {self.id!r}: factors must have the same length as "
                f"load_case_ids ({len(self.load_case_ids)}), got {len(self.factors)}"
            )
        return self

    def case_factors(self) -> dict[str, float]:
        """Map each of this case's load_case_ids to its scale factor."""
        if self.factors is None:
            return dict.fromkeys(self.load_case_ids, 1.0)
        return dict(zip(self.load_case_ids, self.factors, strict=True))


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
