"""3D sparse assembly: global stiffness matrix + per-load-case load
vectors, for a homogeneous (all-truss or all-frame) CEM model.

Unlike the 2D solver, there is no planarity restriction here -- full
(Fx,Fy,Fz)/(Mx,My,Mz) loads and the full 6-DOF-per-node CEM support
representation apply directly. The S2-era scope guards that still
apply: a single element type per model (mixed truss/frame is not yet
supported), `member_distributed`/`gravity` loads, and
`coordinate_basis="local"` loads are all explicitly rejected.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from scipy import sparse

from structnode.core.model import CEM, Material
from structnode.fem.assembly.errors import UnsupportedModelError
from structnode.fem.elements.frame3d import frame3d_global_stiffness
from structnode.fem.elements.truss3d import truss3d_global_stiffness

ElementKind = Literal["truss", "frame"]
SUPPORTED_LOAD_KINDS = frozenset({"nodal_force", "nodal_moment"})


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
        x1, y1, z1 = n1.position
        x2, y2, z2 = n2.position

        if element_kind == "truss":
            k_el = truss3d_global_stiffness(material.E, section.A, x1, y1, z1, x2, y2, z2)
            dofs: Sequence[int] = _truss_dofs(node_index[n1.id], node_index[n2.id])
        else:
            g = resolve_shear_modulus(material)
            k_el, warning = frame3d_global_stiffness(
                material.E,
                g,
                section.A,
                section.Iy,
                section.Iz,
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


def build_load_vector(
    cem: CEM, model: Model3D, load_case_ids: Sequence[str]
) -> NDArray[np.float64]:
    f = np.zeros(model.ndof, dtype=np.float64)
    selected = set(load_case_ids)

    for load in cem.loads:
        if load.case_id not in selected:
            continue
        if load.kind not in SUPPORTED_LOAD_KINDS:
            raise UnsupportedModelError(
                f"Load {load.id!r}: kind {load.kind!r} is not supported by the S3 "
                "native 3D solver (only nodal_force/nodal_moment -- "
                "member_distributed/gravity are a later milestone)"
            )
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
            f[base : base + 3] += load.values
        else:  # nodal_moment
            if model.element_kind != "frame":
                raise UnsupportedModelError(
                    f"Load {load.id!r}: nodal_moment requires a frame model "
                    "(a truss-only 3D model has no rotational DOF)"
                )
            f[base + 3 : base + 6] += load.values

    return f
