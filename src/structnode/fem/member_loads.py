"""Uniform member loads: `member_distributed` and `gravity` (self-weight).

Both reduce to a uniform force per unit length `w` along the full member
(see docs/ADR/0007-uniform-member-loads.md):

- `member_distributed`: `values` is `w` itself (N/m, per unit *member*
  length, not projected length), in global or member-local axes.
- `gravity`: `values` is an acceleration vector (m/s^2, global axes only);
  `w = rho * A * g` with the element material's `rho` and the section's
  gross `A`. `target_id` is one element id, or `"*"` for every element.

Frames take the standard fixed-end (consistent) nodal loads -- wL/2 per
end plus wL^2/12 end moments -- so displacements, reactions and end forces
are exact for Euler-Bernoulli members. Trusses have no rotational DOF, so
`w` is lumped as wL/2 to each end node and a warning says so.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from structnode.core.model import CEM
from structnode.fem.assembly.errors import UnsupportedModelError

GRAVITY_ALL_ELEMENTS = "*"
MEMBER_LOAD_KINDS = frozenset({"member_distributed", "gravity"})


@dataclass
class ElementUniformLoad:
    """Factored uniform load on one element, split by the basis it was given in."""

    w_global: NDArray[np.float64] = field(default_factory=lambda: np.zeros(3))
    w_local: NDArray[np.float64] = field(default_factory=lambda: np.zeros(3))


def collect_uniform_loads(
    cem: CEM, case_factors: Mapping[str, float]
) -> dict[str, ElementUniformLoad]:
    """Sums every active member_distributed/gravity load into a per-element
    uniform `w`, already scaled by its load case factor."""
    elements = {el.id: el for el in cem.elements}
    materials = {m.id: m for m in cem.materials}
    sections = {s.id: s for s in cem.sections}
    loads: dict[str, ElementUniformLoad] = {}

    for load in cem.loads:
        if load.case_id not in case_factors or load.kind not in MEMBER_LOAD_KINDS:
            continue
        factor = case_factors[load.case_id]
        if len(load.values) != 3:
            raise UnsupportedModelError(
                f"Load {load.id!r}: expected 3 components, got {len(load.values)}"
            )
        values = factor * np.asarray(load.values, dtype=np.float64)

        if load.kind == "member_distributed":
            if load.target_id not in elements:
                raise UnsupportedModelError(
                    f"Load {load.id!r}: member_distributed targets unknown element "
                    f"{load.target_id!r}"
                )
            entry = loads.setdefault(load.target_id, ElementUniformLoad())
            if load.coordinate_basis == "global":
                entry.w_global = entry.w_global + values
            else:
                entry.w_local = entry.w_local + values
            continue

        # gravity
        if load.coordinate_basis != "global":
            raise UnsupportedModelError(
                f"Load {load.id!r}: gravity is an acceleration in global axes; "
                "coordinate_basis must be 'global'"
            )
        if load.target_id == GRAVITY_ALL_ELEMENTS:
            targets = list(elements)
        elif load.target_id in elements:
            targets = [load.target_id]
        else:
            raise UnsupportedModelError(
                f"Load {load.id!r}: gravity target must be an element id or "
                f"{GRAVITY_ALL_ELEMENTS!r}, got {load.target_id!r}"
            )
        for el_id in targets:
            el = elements[el_id]
            material = materials[el.material_id]
            if material.rho is None:
                raise UnsupportedModelError(
                    f"Load {load.id!r}: element {el_id!r} material {material.id!r} "
                    "has no density (rho), so its self-weight is undefined"
                )
            mass_per_length = material.rho * sections[el.section_id].A
            entry = loads.setdefault(el_id, ElementUniformLoad())
            entry.w_global = entry.w_global + mass_per_length * values

    return loads


def frame2d_fixed_end_loads(wx: float, wy: float, length: float) -> NDArray[np.float64]:
    """Equivalent nodal loads, local DOF order (u1, v1, t1, u2, v2, t2), for a
    uniform local load (wx axial, wy transverse) over a fixed-fixed member."""
    half = 0.5 * length
    m = wy * length**2 / 12.0
    return np.array([wx * half, wy * half, m, wx * half, wy * half, -m], dtype=np.float64)


def frame3d_fixed_end_loads(wx: float, wy: float, wz: float, length: float) -> NDArray[np.float64]:
    """Equivalent nodal loads, local DOF order (u1,v1,w1,tx1,ty1,tz1, u2,...),
    for a uniform local load over a fixed-fixed member. The My terms carry the
    opposite sign to Mz for the same reason frame3d's y-bending stiffness block
    does: theta_y = -dw/dx while theta_z = +dv/dx."""
    half = 0.5 * length
    my = wz * length**2 / 12.0
    mz = wy * length**2 / 12.0
    return np.array(
        [wx * half, wy * half, wz * half, 0.0, -my, mz]
        + [wx * half, wy * half, wz * half, 0.0, my, -mz],
        dtype=np.float64,
    )


def truss_lumped_warning(element_id: str) -> str:
    return (
        f"Element {element_id!r}: distributed/gravity load on a truss element is "
        "lumped as wL/2 to each end node; reported N is the mean axial force, "
        "and member bending from any transverse component is not represented"
    )
