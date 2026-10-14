"""OpenSeesPy adapter: an independent cross-check solver behind a
capability-negotiated boundary (docs/MASTER_PLAN.md section 1:
"External solver is an optional plugin, not an implicit dependency";
section 3: "capability negotiation").

`openseespy` is imported lazily, on first use, so the rest of
structnode has zero OpenSees dependency. When it can't be imported
(not installed, or -- a known, common issue -- a Windows DLL load
failure even after a successful `pip install`, typically a missing
MSVC runtime or a Python-version/wheel mismatch) every public function
here raises `OpenSeesUnavailableError` with the underlying error
attached, rather than silently skipping or fabricating a result.

IMPORTANT PROVENANCE NOTE: this adapter was written and reviewed
without ever running against a live OpenSeesPy process -- it would not
import in the development environment (see the project history / PR
description). The CEM-to-OpenSees translation below follows the
documented OpenSeesPy API as faithfully as reasonably possible, but it
has not been exercised end-to-end. Treat results from this adapter as
unverified until someone runs it in an environment where openseespy
actually imports, and cross-checks at least one benchmark.

Local-axis caveat: OpenSees's `geomTransf` `vecxz` parameter resolves
local y/z via its own cross-product convention, which has not been
confirmed to agree with this project's own (`frame3d_local_axes`).
For a doubly-symmetric section (`Iy == Iz`) this doesn't matter --
bending stiffness is axisymmetric about the member axis, so whichever
convention "wins" doesn't change the global response. For `Iy != Iz`,
treat orientation-sensitive OpenSees results (which local axis gets
which bending stiffness) as unverified until cross-checked.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from structnode.core.model import CEM
from structnode.fem.assembly import (
    UnsupportedModelError,
    require_homogeneous_element_kind,
    resolve_shear_modulus,
)
from structnode.fem.elements.frame3d import frame3d_local_axes
from structnode.fem.solvers import AnalysisCaseNotFoundError, AnalysisResult3D

SOLVER_NAME = "opensees"
SOLVER_VERSION = "openseespy (version resolved at runtime; see capabilities())"


class OpenSeesUnavailableError(Exception):
    """openseespy could not be imported/used in this environment."""


@lru_cache(maxsize=1)
def _import_ops() -> Any:
    try:
        import openseespy.opensees as ops  # type: ignore[import-not-found]
    except Exception as exc:  # pragma: no cover - only exercised if installed
        raise OpenSeesUnavailableError(
            f"openseespy is not usable in this environment: {exc}"
        ) from exc
    return ops


def is_available() -> bool:
    try:
        _import_ops()
    except OpenSeesUnavailableError:
        return False
    return True


def capabilities() -> dict[str, Any]:
    """Static description of adapter capability, independent of whether
    it's actually importable right now."""
    return {
        "name": SOLVER_NAME,
        "available": is_available(),
        "element_types": ["truss", "frame"],
        "analysis_methods": ["linear_static"],
        "load_kinds": ["nodal_force", "nodal_moment"],
        "coordinate_basis": ["global"],
        "limitations": [
            "single element type per model (no mixed truss/frame)",
            "no member_distributed or gravity loads",
            "no shear deformation",
            "local-axis orientation for Iy != Iz sections is unverified "
            "against this project's own convention (see module docstring)",
        ],
    }


def run_linear_static_opensees(cem: CEM, analysis_case_id: str) -> AnalysisResult3D:
    """Translate `cem` into an OpenSeesPy model, solve, and return results
    in the same shape as `solve_linear_static_3d` for direct comparison."""
    ops = _import_ops()

    analysis_case = next((ac for ac in cem.analysis_cases if ac.id == analysis_case_id), None)
    if analysis_case is None:
        raise AnalysisCaseNotFoundError(f"No analysis case {analysis_case_id!r} in this model")

    element_kind = require_homogeneous_element_kind(cem)
    dof_per_node = 3 if element_kind == "truss" else 6

    node_ids = [n.id for n in cem.nodes]
    node_tag = {nid: i + 1 for i, nid in enumerate(node_ids)}
    nodes_by_id = {n.id: n for n in cem.nodes}
    materials = {m.id: m for m in cem.materials}
    sections = {s.id: s for s in cem.sections}

    ops.wipe()
    ops.model("basic", "-ndm", 3, "-ndf", dof_per_node)

    for nid in node_ids:
        x, y, z = nodes_by_id[nid].position
        ops.node(node_tag[nid], x, y, z)

    for support in cem.constraints:
        tag = node_tag.get(support.node_id)
        if tag is None:
            continue
        ops.fix(tag, *[1 if support.dofs[i] else 0 for i in range(dof_per_node)])

    if element_kind == "truss":
        mat_tag = {m.id: i + 1 for i, m in enumerate(cem.materials)}
        for m in cem.materials:
            ops.uniaxialMaterial("Elastic", mat_tag[m.id], m.E)
        for i, el in enumerate(cem.elements, start=1):
            section = sections[el.section_id]
            n1, n2 = el.node_ids
            ops.element(
                "Truss",
                i,
                node_tag[n1],
                node_tag[n2],
                section.A,
                mat_tag[el.material_id],
            )
    else:
        for i, el in enumerate(cem.elements, start=1):
            material = materials[el.material_id]
            section = sections[el.section_id]
            g = resolve_shear_modulus(material)
            n1_node, n2_node = nodes_by_id[el.node_ids[0]], nodes_by_id[el.node_ids[1]]
            _, _, local_z, _, _ = frame3d_local_axes(
                *n1_node.position, *n2_node.position, section.local_axis_hint
            )
            transf_tag = i
            ops.geomTransf("Linear", transf_tag, *local_z.tolist())
            ops.element(
                "elasticBeamColumn",
                i,
                node_tag[el.node_ids[0]],
                node_tag[el.node_ids[1]],
                section.A,
                material.E,
                g,
                section.J,
                section.Iy,
                section.Iz,
                transf_tag,
            )

    load_by_node: dict[str, list[float]] = {nid: [0.0] * dof_per_node for nid in node_ids}
    case_factors = analysis_case.case_factors()
    for load in cem.loads:
        if load.case_id not in case_factors:
            continue
        factor = case_factors[load.case_id]
        if load.coordinate_basis != "global":
            raise UnsupportedModelError(
                f"Load {load.id!r}: only coordinate_basis='global' is supported"
            )
        if load.kind == "nodal_force":
            load_by_node[load.target_id][0] += factor * load.values[0]
            load_by_node[load.target_id][1] += factor * load.values[1]
            load_by_node[load.target_id][2] += factor * load.values[2]
        elif load.kind == "nodal_moment" and dof_per_node == 6:
            load_by_node[load.target_id][3] += factor * load.values[0]
            load_by_node[load.target_id][4] += factor * load.values[1]
            load_by_node[load.target_id][5] += factor * load.values[2]
        else:
            raise UnsupportedModelError(
                f"Load {load.id!r}: kind {load.kind!r} unsupported by this adapter"
            )

    ops.timeSeries("Linear", 1)
    ops.pattern("Plain", 1, 1)
    for nid, values in load_by_node.items():
        if any(values):
            ops.load(node_tag[nid], *values)

    ops.system("BandSPD")
    ops.numberer("RCM")
    ops.constraints("Plain")
    ops.integrator("LoadControl", 1.0)
    ops.algorithm("Linear")
    ops.analysis("Static")
    ops.analyze(1)
    ops.reactions()

    disp_names = ("Ux", "Uy", "Uz") if dof_per_node == 3 else ("Ux", "Uy", "Uz", "Rx", "Ry", "Rz")
    reaction_names = (
        ("Fx", "Fy", "Fz") if dof_per_node == 3 else ("Fx", "Fy", "Fz", "Mx", "My", "Mz")
    )

    displacements: dict[str, dict[str, float]] = {}
    reactions: dict[str, dict[str, float]] = {}
    restrained_by_node = {s.node_id: s.dofs for s in cem.constraints}
    for nid in node_ids:
        tag = node_tag[nid]
        disp_vals = ops.nodeDisp(tag)
        displacements[nid] = dict(zip(disp_names, disp_vals, strict=True))
        if nid in restrained_by_node:
            dofs = restrained_by_node[nid]
            reaction_vals = ops.nodeReaction(tag)
            reactions[nid] = {
                name: reaction_vals[i] for i, name in enumerate(reaction_names) if dofs[i]
            }

    element_forces: dict[str, dict[str, float]] = {}
    for i, el in enumerate(cem.elements, start=1):
        if element_kind == "truss":
            # `basicForce` returns the force(s) in the element's own basic
            # system, which for a 2-node truss is just [N] (tension +ve) --
            # avoids re-deriving the axial projection from end forces.
            element_forces[el.id] = {"N": ops.basicForce(i)[0]}
        else:
            forces = ops.eleForce(i)
            element_forces[el.id] = {
                "N1": forces[0],
                "Vy1": forces[1],
                "Vz1": forces[2],
                "T1": forces[3],
                "My1": forces[4],
                "Mz1": forces[5],
                "N2": forces[6],
                "Vy2": forces[7],
                "Vz2": forces[8],
                "T2": forces[9],
                "My2": forces[10],
                "Mz2": forces[11],
            }

    return AnalysisResult3D(
        analysis_case_id=analysis_case_id,
        element_kind=element_kind,
        solver_name=SOLVER_NAME,
        solver_version=SOLVER_VERSION,
        displacements=displacements,
        reactions=reactions,
        element_forces=element_forces,
        warnings=[
            "opensees adapter: local-axis convention for Iy != Iz sections "
            "is unverified against this project's own convention"
        ],
    )
