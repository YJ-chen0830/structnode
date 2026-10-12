"""Global-equilibrium check on `examples/l_frame_3d.cem.json`: a genuinely
3D load path (an out-of-plane tip load bends the horizontal beam and
transmits torsion into the vertical column), not just axis-aligned
bending like the other benchmarks. Reaction moments must balance the
applied load's moment about the base node (M = r x F), independent of
internal member mechanics -- a strong, mechanics-agnostic sanity check.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from structnode.core.model import CEM
from structnode.fem.solvers import solve_linear_static_3d

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "l_frame_3d.cem.json"
RELATIVE_TOLERANCE = 1e-6


def test_lframe_reactions_balance_applied_load_moment() -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    cem = CEM.model_validate(data)
    result = solve_linear_static_3d(cem, "AC1")

    base_position = np.array(next(n.position for n in cem.nodes if n.id == "N1"))
    load = next(load_ for load_ in cem.loads if load_.id == "F1")
    load_position = np.array(next(n.position for n in cem.nodes if n.id == load.target_id))
    force = np.array(load.values)

    r = load_position - base_position
    applied_moment_about_base = np.cross(r, force)

    reaction = result.reactions["N1"]
    reaction_force = np.array([reaction["Fx"], reaction["Fy"], reaction["Fz"]])
    reaction_moment = np.array([reaction["Mx"], reaction["My"], reaction["Mz"]])

    # Sum of forces = 0.
    np.testing.assert_allclose(reaction_force, -force, rtol=RELATIVE_TOLERANCE, atol=1e-6)
    # Sum of moments about the base = 0.
    np.testing.assert_allclose(
        reaction_moment, -applied_moment_about_base, rtol=RELATIVE_TOLERANCE, atol=1e-6
    )


def test_lframe_internal_end_forces_match_reactions_at_base() -> None:
    """The column's base-end local forces, transformed back to global,
    must equal the support reaction (Newton's third law at the joint)."""
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    cem = CEM.model_validate(data)
    result = solve_linear_static_3d(cem, "AC1")

    # Column E1 runs N1(base)->N2(top): N1=(0,0,0) -> local x = global z.
    # For this orientation (local_axis_hint=(0,1,0) on a vertical
    # member) local (Vz1, My1, T1) at the base end lines up 1:1 with
    # global (Fy, Mx, Mz) at the reaction -- confirmed numerically here
    # rather than re-derived, since the transform itself is already
    # covered by the rotation-invariance benchmark elsewhere.
    column_end1 = result.element_forces["E1"]
    reaction = result.reactions["N1"]

    assert math.isclose(column_end1["Vz1"], reaction["Fy"], rel_tol=RELATIVE_TOLERANCE)
    assert math.isclose(column_end1["My1"], reaction["Mx"], rel_tol=RELATIVE_TOLERANCE)
    assert math.isclose(column_end1["T1"], reaction["Mz"], rel_tol=RELATIVE_TOLERANCE)
