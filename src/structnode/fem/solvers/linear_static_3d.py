"""Native linear-static 3D solver -- same partition/elimination +
reaction recovery + singularity detection as the 2D solver, but the
full 6-DOF-per-node CEM support representation now applies directly
(no 2D-only DOF subsetting)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.linalg import LinAlgError

from structnode.core.model import CEM
from structnode.fem.assembly import (
    Model3D,
    build_load_vector_3d,
    build_model_3d,
    resolve_shear_modulus,
)
from structnode.fem.elements.frame3d import frame3d_local_end_forces
from structnode.fem.elements.truss3d import truss3d_axial_force
from structnode.fem.solvers.errors import AnalysisCaseNotFoundError, SingularStiffnessError

SOLVER_NAME = "structnode-native-3d"
SOLVER_VERSION = "0.1.0"
MAX_CONDITION_NUMBER = 1e12

_DISPLACEMENT_COMPONENT_NAMES: dict[str, tuple[str, ...]] = {
    "truss": ("Ux", "Uy", "Uz"),
    "frame": ("Ux", "Uy", "Uz", "Rx", "Ry", "Rz"),
}
_REACTION_COMPONENT_NAMES: dict[str, tuple[str, ...]] = {
    "truss": ("Fx", "Fy", "Fz"),
    "frame": ("Fx", "Fy", "Fz", "Mx", "My", "Mz"),
}


@dataclass
class AnalysisResult3D:
    analysis_case_id: str
    element_kind: str
    solver_name: str
    solver_version: str
    displacements: dict[str, dict[str, float]]
    reactions: dict[str, dict[str, float]]
    element_forces: dict[str, dict[str, float]]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_case_id": self.analysis_case_id,
            "element_kind": self.element_kind,
            "solver_name": self.solver_name,
            "solver_version": self.solver_version,
            "displacements": self.displacements,
            "reactions": self.reactions,
            "element_forces": self.element_forces,
            "warnings": self.warnings,
        }


def _restrained_dofs(cem: CEM, model: Model3D) -> set[int]:
    restrained: set[int] = set()
    for support in cem.constraints:
        node_i = model.node_index.get(support.node_id)
        if node_i is None:
            continue  # unknown node -- already an error at topology validation
        for slot in range(model.dof_per_node):
            if support.dofs[slot]:
                restrained.add(model.dof_per_node * node_i + slot)
    return restrained


def _solve_free_dofs(stiffness: Any, free: list[int], f_full: np.ndarray) -> np.ndarray:
    if not free:
        return np.zeros(0, dtype=np.float64)

    k_ff = stiffness[np.ix_(free, free)].toarray()
    f_f = f_full[free]

    cond = np.linalg.cond(k_ff)
    if not np.isfinite(cond) or cond > MAX_CONDITION_NUMBER:
        raise SingularStiffnessError(
            f"Free-DOF stiffness submatrix is singular or ill-conditioned "
            f"(condition number={cond:.3e}); this is likely an unrestrained "
            f"mechanism or rigid-body mode, not a numerical fluke"
        )
    try:
        return np.asarray(np.linalg.solve(k_ff, f_f), dtype=np.float64)
    except LinAlgError as exc:
        raise SingularStiffnessError(f"Failed to solve free-DOF system: {exc}") from exc


def solve_linear_static_3d(cem: CEM, analysis_case_id: str) -> AnalysisResult3D:
    analysis_case = next((ac for ac in cem.analysis_cases if ac.id == analysis_case_id), None)
    if analysis_case is None:
        raise AnalysisCaseNotFoundError(f"No analysis case {analysis_case_id!r} in this model")

    model = build_model_3d(cem)
    f_full = build_load_vector_3d(cem, model, analysis_case.load_case_ids)

    restrained = _restrained_dofs(cem, model)
    free = [i for i in range(model.ndof) if i not in restrained]

    u_f = _solve_free_dofs(model.stiffness, free, f_full)

    u_full = np.zeros(model.ndof, dtype=np.float64)
    for local_i, global_i in enumerate(free):
        u_full[global_i] = u_f[local_i]

    reaction_full = model.stiffness @ u_full - f_full

    disp_names = _DISPLACEMENT_COMPONENT_NAMES[model.element_kind]
    reaction_names = _REACTION_COMPONENT_NAMES[model.element_kind]

    displacements: dict[str, dict[str, float]] = {}
    for node_id, node_i in model.node_index.items():
        base = model.dof_per_node * node_i
        displacements[node_id] = {
            name: float(u_full[base + k]) for k, name in enumerate(disp_names)
        }

    reactions: dict[str, dict[str, float]] = {}
    restrained_by_node: dict[str, list[int]] = {}
    for global_dof in restrained:
        node_i, slot = divmod(global_dof, model.dof_per_node)
        restrained_by_node.setdefault(model.node_order[node_i], []).append(slot)
    for node_id, slots in restrained_by_node.items():
        node_i = model.node_index[node_id]
        base = model.dof_per_node * node_i
        reactions[node_id] = {
            reaction_names[slot]: float(reaction_full[base + slot]) for slot in slots
        }

    nodes_by_id = {n.id: n for n in cem.nodes}
    materials = {m.id: m for m in cem.materials}
    sections = {s.id: s for s in cem.sections}

    element_forces: dict[str, dict[str, float]] = {}
    for el in cem.elements:
        n1, n2 = nodes_by_id[el.node_ids[0]], nodes_by_id[el.node_ids[1]]
        material = materials[el.material_id]
        section = sections[el.section_id]
        i1, i2 = model.node_index[n1.id], model.node_index[n2.id]
        x1, y1, z1 = n1.position
        x2, y2, z2 = n2.position

        if model.element_kind == "truss":
            u_el = np.concatenate([u_full[3 * i1 : 3 * i1 + 3], u_full[3 * i2 : 3 * i2 + 3]])
            n_force = truss3d_axial_force(material.E, section.A, x1, y1, z1, x2, y2, z2, u_el)
            element_forces[el.id] = {"N": n_force}
        else:
            g = resolve_shear_modulus(material)
            u_el = np.concatenate([u_full[6 * i1 : 6 * i1 + 6], u_full[6 * i2 : 6 * i2 + 6]])
            forces = frame3d_local_end_forces(
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
                u_el,
            )
            element_forces[el.id] = {
                "N1": float(forces[0]),
                "Vy1": float(forces[1]),
                "Vz1": float(forces[2]),
                "T1": float(forces[3]),
                "My1": float(forces[4]),
                "Mz1": float(forces[5]),
                "N2": float(forces[6]),
                "Vy2": float(forces[7]),
                "Vz2": float(forces[8]),
                "T2": float(forces[9]),
                "My2": float(forces[10]),
                "Mz2": float(forces[11]),
            }

    return AnalysisResult3D(
        analysis_case_id=analysis_case_id,
        element_kind=model.element_kind,
        solver_name=SOLVER_NAME,
        solver_version=SOLVER_VERSION,
        displacements=displacements,
        reactions=reactions,
        element_forces=element_forces,
        warnings=list(model.warnings),
    )
