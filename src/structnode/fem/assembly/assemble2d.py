"""2D sparse assembly: global stiffness matrix + per-load-case load
vectors, for a homogeneous (all-truss or all-frame) planar CEM model.

S2 scope guard -- rejected outright rather than silently approximated
(docs/MASTER_PLAN.md "No unsupported feature is silently approximated"):
mixed truss/frame element types in one model, frame end releases, any
node outside the z=0 plane, any load with a non-zero out-of-plane component, and any
nodal load with `coordinate_basis="local"`. Uniform member loads
(`member_distributed`/`gravity`) are turned into fixed-end nodal loads --
see `structnode.fem.member_loads`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy import sparse

from structnode.core.model import CEM
from structnode.fem.assembly.errors import UnsupportedModelError
from structnode.fem.assembly.guards import require_no_end_releases
from structnode.fem.elements.frame2d import frame2d_global_stiffness, frame2d_transform_matrix
from structnode.fem.elements.truss2d import truss2d_direction_cosines, truss2d_global_stiffness
from structnode.fem.member_loads import (
    collect_uniform_loads,
    frame2d_fixed_end_loads,
    truss_lumped_warning,
)
from structnode.fem.rebar import effective_section_properties

PLANAR_EPS_M = 1e-9
OUT_OF_PLANE_EPS = 1e-9
ElementKind = Literal["truss", "frame"]
SUPPORTED_LOAD_KINDS = frozenset({"nodal_force", "nodal_moment", "member_distributed", "gravity"})


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
    require_no_end_releases(cem, "S2 native 2D solver")

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
        a_eff, _iy_eff, iz_eff = effective_section_properties(section, material, materials)
        x1, y1 = n1.position[0], n1.position[1]
        x2, y2 = n2.position[0], n2.position[1]

        if element_kind == "truss":
            k_el = truss2d_global_stiffness(material.E, a_eff, x1, y1, x2, y2)
            dofs: Sequence[int] = _truss_dofs(node_index[n1.id], node_index[n2.id])
        else:
            k_el = frame2d_global_stiffness(material.E, a_eff, iz_eff, x1, y1, x2, y2)
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


@dataclass
class LoadVector2D:
    f: NDArray[np.float64]
    """Global nodal load vector, including member-load equivalents."""
    fixed_end_local: dict[str, NDArray[np.float64]] = field(default_factory=dict)
    """Per-element equivalent nodal loads in local axes (u1,v1,t1,u2,v2,t2 for
    frames, u1,v1,u2,v2 for trusses) -- subtracted from k @ u during end-force
    recovery so the reported forces include the member load's own effect."""
    warnings: list[str] = field(default_factory=list)


def _add_member_loads(
    cem: CEM, model: Model2D, case_factors: Mapping[str, float], out: LoadVector2D
) -> None:
    nodes_by_id = {n.id: n for n in cem.nodes}
    elements = {el.id: el for el in cem.elements}
    for el_id, load in collect_uniform_loads(cem, case_factors).items():
        el = elements[el_id]
        n1, n2 = nodes_by_id[el.node_ids[0]], nodes_by_id[el.node_ids[1]]
        c, s, length = truss2d_direction_cosines(
            n1.position[0], n1.position[1], n2.position[0], n2.position[1]
        )
        if abs(load.w_global[2]) > OUT_OF_PLANE_EPS or abs(load.w_local[2]) > OUT_OF_PLANE_EPS:
            raise UnsupportedModelError(
                f"Element {el_id!r}: member load has a non-zero out-of-plane (z) "
                "component, not representable by the S2 native 2D solver"
            )
        rot = np.array([[c, s], [-s, c]], dtype=np.float64)  # global -> local
        wx, wy = rot @ load.w_global[:2] + load.w_local[:2]
        i, j = model.node_index[n1.id], model.node_index[n2.id]

        if model.element_kind == "frame":
            f_local = frame2d_fixed_end_loads(float(wx), float(wy), length)
            f_global = frame2d_transform_matrix(c, s).T @ f_local
            dofs: Sequence[int] = _frame_dofs(i, j)
        else:
            half = 0.5 * length
            f_local = np.array([wx * half, wy * half, wx * half, wy * half])
            w_global = rot.T @ np.array([wx, wy])
            f_global = np.concatenate([w_global * half, w_global * half])
            dofs = _truss_dofs(i, j)
            out.warnings.append(truss_lumped_warning(el_id))

        out.fixed_end_local[el_id] = f_local
        for k, gi in enumerate(dofs):
            out.f[gi] += f_global[k]


def build_load_vector(cem: CEM, model: Model2D, case_factors: Mapping[str, float]) -> LoadVector2D:
    out = LoadVector2D(f=np.zeros(model.ndof, dtype=np.float64))
    f = out.f
    _add_member_loads(cem, model, case_factors, out)

    for load in cem.loads:
        if load.case_id not in case_factors:
            continue
        factor = case_factors[load.case_id]
        if load.kind not in SUPPORTED_LOAD_KINDS:
            raise UnsupportedModelError(
                f"Load {load.id!r}: kind {load.kind!r} is not supported by the S2 native 2D solver"
            )
        if load.kind in ("member_distributed", "gravity"):
            continue  # handled by _add_member_loads
        if load.coordinate_basis != "global":
            raise UnsupportedModelError(
                f"Load {load.id!r}: only coordinate_basis='global' is supported "
                "by the S2 native 2D solver"
            )

        node_i = model.node_index[load.target_id]
        base = model.dof_per_node * node_i

        if load.kind == "nodal_force":
            fx, fy = _require_in_plane(load.values, f"Load {load.id!r}")
            f[base + 0] += factor * fx
            f[base + 1] += factor * fy
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
            f[base + 2] += factor * mz

    return out
