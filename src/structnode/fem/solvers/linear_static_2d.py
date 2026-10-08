"""Native linear-static 2D solver: partition/elimination + reaction
recovery + element end-force recovery, with explicit singularity
detection (docs/MASTER_PLAN.md section 4: "do not return plausible-
looking numbers on failure").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.linalg import LinAlgError

from structnode.core.model import CEM
from structnode.fem.assembly import Model2D, build_load_vector, build_model_2d
from structnode.fem.elements.frame2d import frame2d_local_end_forces
from structnode.fem.elements.truss2d import truss2d_axial_force

SOLVER_NAME = "structnode-native-2d"
SOLVER_VERSION = "0.1.0"
MAX_CONDITION_NUMBER = 1e12

# Index into the 6-tuple Support.dofs (Tx, Ty, Tz, Rx, Ry, Rz) that each
# 2D local DOF slot corresponds to.
_SUPPORT_DOF_INDEX: dict[str, tuple[int, ...]] = {
    "truss": (0, 1),
    "frame": (0, 1, 5),
}
_DOF_COMPONENT_NAMES: dict[str, tuple[str, ...]] = {
    "truss": ("Fx", "Fy"),
    "frame": ("Fx", "Fy", "Mz"),
}
_DISPLACEMENT_COMPONENT_NAMES: dict[str, tuple[str, ...]] = {
    "truss": ("Ux", "Uy"),
    "frame": ("Ux", "Uy", "Rz"),
}


class AnalysisCaseNotFoundError(Exception):
    pass


class SingularStiffnessError(Exception):
    """The free-DOF stiffness submatrix is singular/ill-conditioned --
    an unrestrained mechanism or rigid-body mode that the coarse
    topology check did not catch for this specific geometry."""


@dataclass
class AnalysisResult2D:
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


def _restrained_dofs(cem: CEM, model: Model2D) -> set[int]:
    support_indices = _SUPPORT_DOF_INDEX[model.element_kind]
    restrained: set[int] = set()
    for support in cem.constraints:
        node_i = model.node_index.get(support.node_id)
        if node_i is None:
            continue  # unknown node -- already an error at topology validation
        for slot, dof_index in enumerate(support_indices):
            if support.dofs[dof_index]:
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


def solve_linear_static_2d(cem: CEM, analysis_case_id: str) -> AnalysisResult2D:
    analysis_case = next((ac for ac in cem.analysis_cases if ac.id == analysis_case_id), None)
    if analysis_case is None:
        raise AnalysisCaseNotFoundError(f"No analysis case {analysis_case_id!r} in this model")

    model = build_model_2d(cem)
    f_full = build_load_vector(cem, model, analysis_case.load_case_ids)

    restrained = _restrained_dofs(cem, model)
    free = [i for i in range(model.ndof) if i not in restrained]

    u_f = _solve_free_dofs(model.stiffness, free, f_full)

    u_full = np.zeros(model.ndof, dtype=np.float64)
    for local_i, global_i in enumerate(free):
        u_full[global_i] = u_f[local_i]

    reaction_full = model.stiffness @ u_full - f_full

    disp_names = _DISPLACEMENT_COMPONENT_NAMES[model.element_kind]
    reaction_names = _DOF_COMPONENT_NAMES[model.element_kind]

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
        x1, y1, x2, y2 = n1.position[0], n1.position[1], n2.position[0], n2.position[1]

        if model.element_kind == "truss":
            u_el = np.array(
                [
                    u_full[2 * i1],
                    u_full[2 * i1 + 1],
                    u_full[2 * i2],
                    u_full[2 * i2 + 1],
                ]
            )
            n_force = truss2d_axial_force(material.E, section.A, x1, y1, x2, y2, u_el)
            element_forces[el.id] = {"N": n_force}
        else:
            u_el = np.array(
                [
                    u_full[3 * i1],
                    u_full[3 * i1 + 1],
                    u_full[3 * i1 + 2],
                    u_full[3 * i2],
                    u_full[3 * i2 + 1],
                    u_full[3 * i2 + 2],
                ]
            )
            forces = frame2d_local_end_forces(
                material.E, section.A, section.Iz, x1, y1, x2, y2, u_el
            )
            element_forces[el.id] = {
                "N1": float(forces[0]),
                "V1": float(forces[1]),
                "M1": float(forces[2]),
                "N2": float(forces[3]),
                "V2": float(forces[4]),
                "M2": float(forces[5]),
            }

    return AnalysisResult2D(
        analysis_case_id=analysis_case_id,
        element_kind=model.element_kind,
        solver_name=SOLVER_NAME,
        solver_version=SOLVER_VERSION,
        displacements=displacements,
        reactions=reactions,
        element_forces=element_forces,
    )
