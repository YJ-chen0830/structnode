"""2D sparse assembly: global stiffness matrix + per-load-case load
vectors, for a homogeneous (all-truss or all-frame) planar CEM model.

S2 scope guard -- rejected outright rather than silently approximated
(docs/MASTER_PLAN.md "No unsupported feature is silently approximated"):
mixed truss/frame element types in one model, any node outside the
z=0 plane, any load with a non-zero out-of-plane component, any load
kind other than `nodal_force`/`nodal_moment`, and any load with
`coordinate_basis="local"`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy import sparse

from structnode.core.model import CEM
from structnode.fem.elements.frame2d import frame2d_global_stiffness
from structnode.fem.elements.truss2d import truss2d_global_stiffness

PLANAR_EPS_M = 1e-9
OUT_OF_PLANE_EPS = 1e-9
ElementKind = Literal["truss", "frame"]
SUPPORTED_LOAD_KINDS = frozenset({"nodal_force", "nodal_moment"})


class UnsupportedModelError(Exception):
    """Raised when the CEM model is outside the S2 native 2D solver's scope."""


@dataclass
class Model2D:
    element_kind: ElementKind
    dof_per_node: int
    node_order: list[str]
    node_index: dict[str, int]
    ndof: int
    stiffness: sparse.csr_matrix


def _require_homogeneous_element_kind(cem: CEM) -> ElementKind:
    kinds = {el.type for el in cem.elements}
    if len(kinds) != 1:
        raise UnsupportedModelError(
            "S2 native 2D solver requires a single element type across the whole "
            f"model (all truss or all frame); found {sorted(kinds)}"
        )
    return next(iter(kinds))


def _require_planar(cem: CEM) -> None:
    offenders = [n.id for n in cem.nodes if abs(n.position[2]) > PLANAR_EPS_M]
    if offenders:
        raise UnsupportedModelError(
            "S2 native 2D solver requires all nodes in the z=0 plane; "
            f"non-planar nodes: {offenders}"
        )


def _truss_dofs(i: int, j: int) -> tuple[int, int, int, int]:
    return (2 * i, 2 * i + 1, 2 * j, 2 * j + 1)


def _frame_dofs(i: int, j: int) -> tuple[int, int, int, int, int, int]:
    return (3 * i, 3 * i + 1, 3 * i + 2, 3 * j, 3 * j + 1, 3 * j + 2)


def build_model_2d(cem: CEM) -> Model2D:
    element_kind = _require_homogeneous_element_kind(cem)
    _require_planar(cem)

    dof_per_node = 2 if element_kind == "truss" else 3
    node_order = [n.id for n in cem.nodes]
    node_index = {nid: i for i, nid in enumerate(node_order)}
    ndof = len(node_order) * dof_per_node

    materials = {m.id: m for m in cem.materials}
    sections = {s.id: s for s in cem.sections}
    nodes_by_id = {n.id: n for n in cem.nodes}

    k_global = sparse.lil_matrix((ndof, ndof), dtype=np.float64)

    for el in cem.elements:
        n1, n2 = nodes_by_id[el.node_ids[0]], nodes_by_id[el.node_ids[1]]
        material = materials[el.material_id]
        section = sections[el.section_id]
        x1, y1 = n1.position[0], n1.position[1]
        x2, y2 = n2.position[0], n2.position[1]

        if element_kind == "truss":
            k_el = truss2d_global_stiffness(material.E, section.A, x1, y1, x2, y2)
            dofs: Sequence[int] = _truss_dofs(node_index[n1.id], node_index[n2.id])
        else:
            k_el = frame2d_global_stiffness(material.E, section.A, section.Iz, x1, y1, x2, y2)
            dofs = _frame_dofs(node_index[n1.id], node_index[n2.id])

        for a, gi in enumerate(dofs):
            for b, gj in enumerate(dofs):
                k_global[gi, gj] += k_el[a, b]

    return Model2D(
        element_kind=element_kind,
        dof_per_node=dof_per_node,
        node_order=node_order,
        node_index=node_index,
        ndof=ndof,
        stiffness=k_global.tocsr(),
    )


def _require_in_plane(values: tuple[float, ...], label: str) -> tuple[float, float]:
    """Validates a 3-component (x, y, z) load vector is planar; returns (x, y)."""
    if len(values) != 3:
        raise UnsupportedModelError(f"{label}: expected 3 components (x, y, z), got {len(values)}")
    x, y, z = values
    if abs(z) > OUT_OF_PLANE_EPS:
        raise UnsupportedModelError(
            f"{label}: non-zero out-of-plane component (z={z}) is not "
            f"representable by the S2 native 2D solver"
        )
    return x, y


def build_load_vector(
    cem: CEM, model: Model2D, load_case_ids: Sequence[str]
) -> NDArray[np.float64]:
    f = np.zeros(model.ndof, dtype=np.float64)
    selected = set(load_case_ids)

    for load in cem.loads:
        if load.case_id not in selected:
            continue
        if load.kind not in SUPPORTED_LOAD_KINDS:
            raise UnsupportedModelError(
                f"Load {load.id!r}: kind {load.kind!r} is not supported by the S2 "
                "native 2D solver (only nodal_force/nodal_moment -- "
                "member_distributed/gravity are a later milestone)"
            )
        if load.coordinate_basis != "global":
            raise UnsupportedModelError(
                f"Load {load.id!r}: only coordinate_basis='global' is supported "
                "by the S2 native 2D solver"
            )

        node_i = model.node_index[load.target_id]
        base = model.dof_per_node * node_i

        if load.kind == "nodal_force":
            fx, fy = _require_in_plane(load.values, f"Load {load.id!r}")
            f[base + 0] += fx
            f[base + 1] += fy
        else:  # nodal_moment -- (Mx, My, Mz); unlike forces, the *in-plane*
            # component for a 2D (XY-plane) model is Mz, not Mx/My: a moment
            # vector about the global Z axis is what produces in-plane
            # rotation (the Rz DOF); Mx/My would bend the member out of plane.
            if model.element_kind != "frame":
                raise UnsupportedModelError(
                    f"Load {load.id!r}: nodal_moment requires a frame model "
                    "(a truss-only 2D model has no rotational DOF)"
                )
            if len(load.values) != 3:
                raise UnsupportedModelError(
                    f"Load {load.id!r}: expected 3 components (Mx, My, Mz), got {len(load.values)}"
                )
            mx, my, mz = load.values
            if abs(mx) > OUT_OF_PLANE_EPS or abs(my) > OUT_OF_PLANE_EPS:
                raise UnsupportedModelError(
                    f"Load {load.id!r}: only the Mz component of nodal_moment is "
                    "representable by the S2 native 2D solver"
                )
            f[base + 2] += mz

    return f
