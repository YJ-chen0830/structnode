"""3D sparse assembly: global stiffness matrix + per-load-case load
vectors, for a homogeneous (all-truss or all-frame) CEM model.

Unlike the 2D solver, there is no planarity restriction here -- full
(Fx,Fy,Fz)/(Mx,My,Mz) loads and the full 6-DOF-per-node CEM support
representation apply directly. The S2-era scope guards that still
apply: a single element type per model (mixed truss/frame is not yet
supported), frame end releases, and `coordinate_basis="local"` nodal
loads are explicitly rejected. Uniform member loads
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

from structnode.core.model import CEM, Material
from structnode.fem.assembly.errors import UnsupportedModelError
from structnode.fem.assembly.guards import require_no_end_releases
from structnode.fem.elements.frame3d import (
    frame3d_global_stiffness,
    frame3d_local_axes,
    frame3d_transform_matrix,
)
from structnode.fem.elements.truss3d import truss3d_global_stiffness
from structnode.fem.member_loads import (
    collect_uniform_loads,
    frame3d_fixed_end_loads,
    truss_lumped_warning,
)
from structnode.fem.rebar import effective_section_properties

ElementKind = Literal["truss", "frame"]
SUPPORTED_LOAD_KINDS = frozenset({"nodal_force", "nodal_moment", "member_distributed", "gravity"})


@dataclass
class Model3D:
    element_kind: ElementKind
    dof_per_node: int
    node_order: list[str]
    node_index: dict[str, int]
    ndof: int
    stiffness: sparse.csr_matrix
    warnings: list[str] = field(default_factory=list)


def require_homogeneous_element_kind(cem: CEM) -> ElementKind:
    kinds = {el.type for el in cem.elements}
    if len(kinds) != 1:
        raise UnsupportedModelError(
            "S3 native 3D solver requires a single element type across the whole "
            f"model (all truss or all frame); found {sorted(kinds)}"
        )
    return next(iter(kinds))


def resolve_shear_modulus(material: Material) -> float:
    if material.G is not None:
        return material.G
    if material.nu is not None:
        return material.E / (2.0 * (1.0 + material.nu))
    raise UnsupportedModelError(
        f"Material {material.id!r}: 3D frame elements need a shear modulus for "
        "torsional stiffness; provide either G or nu"
    )


def _truss_dofs(i: int, j: int) -> tuple[int, int, int, int, int, int]:
    return (3 * i, 3 * i + 1, 3 * i + 2, 3 * j, 3 * j + 1, 3 * j + 2)


def _frame_dofs(i: int, j: int) -> tuple[int, ...]:
    return tuple(6 * i + k for k in range(6)) + tuple(6 * j + k for k in range(6))


def build_model_3d(cem: CEM) -> Model3D:
    element_kind = require_homogeneous_element_kind(cem)
    require_no_end_releases(cem, "S3 native 3D solver")
    dof_per_node = 3 if element_kind == "truss" else 6

    node_order = [n.id for n in cem.nodes]
    node_index = {nid: i for i, nid in enumerate(node_order)}
    ndof = len(node_order) * dof_per_node

    materials = {m.id: m for m in cem.materials}
    sections = {s.id: s for s in cem.sections}
    nodes_by_id = {n.id: n for n in cem.nodes}

    k_global = sparse.lil_matrix((ndof, ndof), dtype=np.float64)
    warnings: list[str] = []

    for el in cem.elements:
        n1, n2 = nodes_by_id[el.node_ids[0]], nodes_by_id[el.node_ids[1]]
        material = materials[el.material_id]
        section = sections[el.section_id]
        a_eff, iy_eff, iz_eff = effective_section_properties(section, material, materials)
        x1, y1, z1 = n1.position
        x2, y2, z2 = n2.position

        if element_kind == "truss":
            k_el = truss3d_global_stiffness(material.E, a_eff, x1, y1, z1, x2, y2, z2)
            dofs: Sequence[int] = _truss_dofs(node_index[n1.id], node_index[n2.id])
        else:
            g = resolve_shear_modulus(material)
            k_el, warning = frame3d_global_stiffness(
                material.E,
                g,
                a_eff,
                iy_eff,
                iz_eff,
                section.J,
                x1,
                y1,
                z1,
                x2,
                y2,
                z2,
                section.local_axis_hint,
            )
            if warning is not None:
                warnings.append(f"Element {el.id!r}: {warning}")
            dofs = _frame_dofs(node_index[n1.id], node_index[n2.id])

        for a, gi in enumerate(dofs):
            for b, gj in enumerate(dofs):
                k_global[gi, gj] += k_el[a, b]

    return Model3D(
        element_kind=element_kind,
        dof_per_node=dof_per_node,
        node_order=node_order,
        node_index=node_index,
        ndof=ndof,
        stiffness=k_global.tocsr(),
        warnings=warnings,
    )


@dataclass
class LoadVector3D:
    f: NDArray[np.float64]
    """Global nodal load vector, including member-load equivalents."""
    fixed_end_local: dict[str, NDArray[np.float64]] = field(default_factory=dict)
    """Per-frame-element equivalent nodal loads in local axes (12 entries) --
    subtracted from k @ u during end-force recovery."""
    warnings: list[str] = field(default_factory=list)


def _add_member_loads(
    cem: CEM, model: Model3D, case_factors: Mapping[str, float], out: LoadVector3D
) -> None:
    nodes_by_id = {n.id: n for n in cem.nodes}
    elements = {el.id: el for el in cem.elements}
    sections = {s.id: s for s in cem.sections}
    for el_id, load in collect_uniform_loads(cem, case_factors).items():
        el = elements[el_id]
        n1, n2 = nodes_by_id[el.node_ids[0]], nodes_by_id[el.node_ids[1]]
        i, j = model.node_index[n1.id], model.node_index[n2.id]

        if model.element_kind == "truss":
            if np.any(load.w_local != 0.0):
                raise UnsupportedModelError(
                    f"Element {el_id!r}: coordinate_basis='local' member loads need "
                    "a member orientation, which 3D truss elements don't define; "
                    "give the load in global axes"
                )
            length = float(np.linalg.norm(np.subtract(n2.position, n1.position)))
            half = 0.5 * length * load.w_global
            for k, gi in enumerate(_truss_dofs(i, j)):
                out.f[gi] += half[k % 3]
            out.warnings.append(truss_lumped_warning(el_id))
            continue

        local_x, local_y, local_z, length, _ = frame3d_local_axes(
            *n1.position, *n2.position, sections[el.section_id].local_axis_hint
        )
        rot = np.vstack([local_x, local_y, local_z])  # global -> local
        wx, wy, wz = rot @ load.w_global + load.w_local
        f_local = frame3d_fixed_end_loads(float(wx), float(wy), float(wz), length)
        f_global = frame3d_transform_matrix(local_x, local_y, local_z).T @ f_local
        out.fixed_end_local[el_id] = f_local
        for k, gi in enumerate(_frame_dofs(i, j)):
            out.f[gi] += f_global[k]


def build_load_vector(cem: CEM, model: Model3D, case_factors: Mapping[str, float]) -> LoadVector3D:
    out = LoadVector3D(f=np.zeros(model.ndof, dtype=np.float64))
    f = out.f
    _add_member_loads(cem, model, case_factors, out)

    for load in cem.loads:
        if load.case_id not in case_factors:
            continue
        factor = case_factors[load.case_id]
        if load.kind not in SUPPORTED_LOAD_KINDS:
            raise UnsupportedModelError(
                f"Load {load.id!r}: kind {load.kind!r} is not supported by the S3 native 3D solver"
            )
        if load.kind in ("member_distributed", "gravity"):
            continue  # handled by _add_member_loads
        if load.coordinate_basis != "global":
            raise UnsupportedModelError(
                f"Load {load.id!r}: only coordinate_basis='global' is supported "
                "by the S3 native 3D solver"
            )
        if len(load.values) != 3:
            raise UnsupportedModelError(
                f"Load {load.id!r}: expected 3 components, got {len(load.values)}"
            )

        node_i = model.node_index[load.target_id]
        base = model.dof_per_node * node_i

        if load.kind == "nodal_force":
            f[base : base + 3] += factor * np.asarray(load.values, dtype=np.float64)
        else:  # nodal_moment
            if model.element_kind != "frame":
                raise UnsupportedModelError(
                    f"Load {load.id!r}: nodal_moment requires a frame model "
                    "(a truss-only 3D model has no rotational DOF)"
                )
            f[base + 3 : base + 6] += factor * np.asarray(load.values, dtype=np.float64)

    return out
