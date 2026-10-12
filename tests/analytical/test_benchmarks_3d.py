"""3D benchmark families from docs/MASTER_PLAN.md section 4: #5 (local-
to-global rotation invariance and member orientation) and #7 (mesh
refinement / split-element invariance), plus 3D analogues of #1
(axial bar) and #6 (rigid-body mode rejection). 2D-equivalent coverage
for #2/#3/#4 already lives in test_benchmarks_2d.py.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest

from structnode.core.model import CEM
from structnode.fem.elements.truss3d import truss3d_axial_force, truss3d_global_stiffness
from structnode.fem.solvers import SingularStiffnessError, solve_linear_static_3d

RELATIVE_TOLERANCE = 1e-6


def _rotation_matrix(axis: np.ndarray, angle: float) -> np.ndarray:
    """Rodrigues' rotation formula; `axis` need not be pre-normalized."""
    axis = axis / np.linalg.norm(axis)
    kx, ky, kz = axis
    k = np.array([[0, -kz, ky], [kz, 0, -kx], [-ky, kx, 0]])
    return np.eye(3) + math.sin(angle) * k + (1 - math.cos(angle)) * (k @ k)


def _base_cem(**overrides: Any) -> dict[str, Any]:
    base = {
        "schema_version": "0.1",
        "model_id": "benchmark-3d",
        "revision": 0,
        "units": {"length": "m", "force": "N"},
        "coordinate_system": "global_cartesian_rh",
        "metadata": {},
        "provenance": {
            "created_by": "human",
            "created_at": "2026-10-12T00:00:00Z",
            "tool_version": "0.0.1",
        },
    }
    base.update(overrides)
    return base


def _cantilever_frame_cem(
    tip_force: tuple[float, float, float],
    tip_position: tuple[float, float, float],
    local_axis_hint: tuple[float, float, float] | None = None,
) -> dict[str, Any]:
    e, iy, iz, j, a = 2.0e11, 6e-6, 8.333e-6, 1e-5, 0.01
    g = e / (2.6)  # arbitrary consistent-ish shear modulus, not load-bearing for this check
    return _base_cem(
        nodes=[
            {"id": "N1", "position": [0.0, 0.0, 0.0]},
            {"id": "N2", "position": list(tip_position)},
        ],
        materials=[{"id": "M1", "E": e, "G": g}],
        sections=[
            {
                "id": "S1",
                "A": a,
                "Iy": iy,
                "Iz": iz,
                "J": j,
                **({"local_axis_hint": list(local_axis_hint)} if local_axis_hint else {}),
            }
        ],
        elements=[
            {
                "id": "E1",
                "type": "frame",
                "node_ids": ["N1", "N2"],
                "material_id": "M1",
                "section_id": "S1",
            }
        ],
        constraints=[{"node_id": "N1", "dofs": [True, True, True, True, True, True]}],
        load_cases=[{"id": "LC1"}],
        loads=[
            {
                "id": "F1",
                "case_id": "LC1",
                "kind": "nodal_force",
                "target_id": "N2",
                "values": list(tip_force),
                "coordinate_basis": "global",
            }
        ],
        analysis_cases=[{"id": "AC1", "load_case_ids": ["LC1"], "method": "linear_static"}],
    )


def test_cantilever_bending_about_local_z_uses_Iz() -> None:
    """Member along global X, tip load in global Y: bending couples with
    local z (Iz), matching the already-verified 2D cantilever formula."""
    e, iz, length, p = 2.0e11, 8.333e-6, 1.0, 1_000.0
    cem = CEM.model_validate(
        _cantilever_frame_cem(tip_force=(0.0, -p, 0.0), tip_position=(length, 0.0, 0.0))
    )
    result = solve_linear_static_3d(cem, "AC1")

    expected_delta = -p * length**3 / (3 * e * iz)
    assert math.isclose(
        result.displacements["N2"]["Uy"], expected_delta, rel_tol=RELATIVE_TOLERANCE
    )
    assert abs(result.displacements["N2"]["Uz"]) < 1e-9


def test_cantilever_bending_about_local_y_uses_Iy() -> None:
    """Member along global X, tip load in global Z: bending couples with
    local y (Iy) -- the critical independent check of the y-bending
    stiffness block's sign convention."""
    e, iy, length, p = 2.0e11, 6e-6, 1.0, 1_000.0
    cem = CEM.model_validate(
        _cantilever_frame_cem(tip_force=(0.0, 0.0, -p), tip_position=(length, 0.0, 0.0))
    )
    result = solve_linear_static_3d(cem, "AC1")

    expected_delta = -p * length**3 / (3 * e * iy)
    assert math.isclose(
        result.displacements["N2"]["Uz"], expected_delta, rel_tol=RELATIVE_TOLERANCE
    )
    assert abs(result.displacements["N2"]["Uy"]) < 1e-9


def test_truss3d_element_matches_axial_formula() -> None:
    """Direct check of the 3D truss element formula for a bar not
    aligned with any global axis. Not run through the solver: a single
    off-axis bar with one free end has zero stiffness in the 2 lateral
    directions regardless of load, so it is not itself a stable system
    -- this isolates the element's own stiffness/force formula, which
    is what "u=PL/(EA) in 3D" actually reduces to verifying."""
    e, a = 2.0e11, 0.01
    x1, y1, z1 = 0.0, 0.0, 0.0
    direction = np.array([1.0, 1.0, 1.0]) / math.sqrt(3.0)
    length = 2.0
    x2, y2, z2 = (direction * length).tolist()

    elongation = 1e-4
    u1 = np.zeros(3)
    u2 = direction * elongation  # pure stretch along the bar's own axis
    u_global = np.concatenate([u1, u2])

    axial = truss3d_axial_force(e, a, x1, y1, z1, x2, y2, z2, u_global)
    assert math.isclose(axial, e * a * elongation / length, rel_tol=RELATIVE_TOLERANCE)

    k = truss3d_global_stiffness(e, a, x1, y1, z1, x2, y2, z2)
    nodal_force_at_2 = (k @ u_global)[3:]
    expected_force_at_2 = direction * (e * a * elongation / length)
    np.testing.assert_allclose(
        nodal_force_at_2, expected_force_at_2, rtol=RELATIVE_TOLERANCE, atol=1e-9
    )


def test_benchmark_5_rotation_invariance() -> None:
    """Rigidly rotating the whole model (geometry + load + cross-section
    orientation) must rotate the response the same way -- the defining
    property of a correct local-to-global coordinate transform.

    The cross-section orientation (`local_axis_hint`) must be rotated
    along with everything else: without an explicit hint, the *default*
    reference vector is a fixed global direction, so rotating the
    member changes its orientation *relative to that fixed reference*
    -- a physically different cross-section twist, not the same beam
    rotated. Rotation invariance is a property of the transform, not of
    the convenience default.
    """
    length, p = 1.0, 1_000.0
    base_hint = (0.0, 0.0, 1.0)
    base = CEM.model_validate(
        _cantilever_frame_cem(
            tip_force=(0.0, -p, 0.0), tip_position=(length, 0.0, 0.0), local_axis_hint=base_hint
        )
    )
    base_result = solve_linear_static_3d(base, "AC1")
    base_disp = base_result.displacements["N2"]
    base_translation = np.array([base_disp["Ux"], base_disp["Uy"], base_disp["Uz"]])
    base_rotation = np.array([base_disp["Rx"], base_disp["Ry"], base_disp["Rz"]])

    r = _rotation_matrix(np.array([1.0, 2.0, 3.0]), 0.7)
    rotated_tip = r @ np.array([length, 0.0, 0.0])
    rotated_force = r @ np.array([0.0, -p, 0.0])
    rotated_hint = r @ np.array(base_hint)

    rotated = CEM.model_validate(
        _cantilever_frame_cem(
            tip_force=tuple(rotated_force.tolist()),
            tip_position=tuple(rotated_tip.tolist()),
            local_axis_hint=tuple(rotated_hint.tolist()),
        )
    )
    rotated_result = solve_linear_static_3d(rotated, "AC1")
    rotated_disp = rotated_result.displacements["N2"]
    rotated_translation = np.array([rotated_disp["Ux"], rotated_disp["Uy"], rotated_disp["Uz"]])
    rotated_rotation = np.array([rotated_disp["Rx"], rotated_disp["Ry"], rotated_disp["Rz"]])

    # Rotating the response back should reproduce the un-rotated case.
    recovered_translation = r.T @ rotated_translation
    recovered_rotation = r.T @ rotated_rotation

    np.testing.assert_allclose(recovered_translation, base_translation, rtol=1e-6, atol=1e-12)
    np.testing.assert_allclose(recovered_rotation, base_rotation, rtol=1e-6, atol=1e-12)


def test_benchmark_7_mesh_refinement_invariance() -> None:
    """Splitting a straight prismatic cantilever into two elements at
    its midpoint must not change the tip deflection under a tip point
    load -- Euler-Bernoulli cubic shape functions are exact here."""
    e, iz, length, p = 2.0e11, 8.333e-6, 2.0, 1_000.0

    single = CEM.model_validate(
        _cantilever_frame_cem(tip_force=(0.0, -p, 0.0), tip_position=(length, 0.0, 0.0))
    )
    single_result = solve_linear_static_3d(single, "AC1")

    data = _cantilever_frame_cem(tip_force=(0.0, -p, 0.0), tip_position=(length, 0.0, 0.0))
    data["nodes"].insert(1, {"id": "NM", "position": [length / 2, 0.0, 0.0]})
    data["elements"] = [
        {
            "id": "E1",
            "type": "frame",
            "node_ids": ["N1", "NM"],
            "material_id": "M1",
            "section_id": "S1",
        },
        {
            "id": "E2",
            "type": "frame",
            "node_ids": ["NM", "N2"],
            "material_id": "M1",
            "section_id": "S1",
        },
    ]
    split = CEM.model_validate(data)
    split_result = solve_linear_static_3d(split, "AC1")

    expected_delta = -p * length**3 / (3 * e * iz)
    assert math.isclose(
        single_result.displacements["N2"]["Uy"], expected_delta, rel_tol=RELATIVE_TOLERANCE
    )
    assert math.isclose(
        split_result.displacements["N2"]["Uy"],
        single_result.displacements["N2"]["Uy"],
        rel_tol=RELATIVE_TOLERANCE,
    )


def test_benchmark_6_3d_rigid_body_mode_is_rejected() -> None:
    """A truss restrained only along its own axis is a mechanism in the
    lateral directions -- must be rejected, not silently solved."""
    cem = CEM.model_validate(
        _base_cem(
            nodes=[
                {"id": "N1", "position": [0.0, 0.0, 0.0]},
                {"id": "N2", "position": [1.0, 0.0, 0.0]},
            ],
            materials=[{"id": "M1", "E": 2.0e11}],
            sections=[{"id": "S1", "A": 0.01, "Iy": 1e-6, "Iz": 1e-6, "J": 1e-6}],
            elements=[
                {
                    "id": "E1",
                    "type": "truss",
                    "node_ids": ["N1", "N2"],
                    "material_id": "M1",
                    "section_id": "S1",
                }
            ],
            constraints=[
                {"node_id": "N1", "dofs": [True, True, True, True, True, True]},
                # Only Tx restrained at N2 -- Ty, Tz are free, zero-stiffness modes.
                {"node_id": "N2", "dofs": [True, False, False, True, True, True]},
            ],
            load_cases=[{"id": "LC1"}],
            loads=[
                {
                    "id": "F1",
                    "case_id": "LC1",
                    "kind": "nodal_force",
                    "target_id": "N2",
                    "values": [0.0, 1.0, 0.0],
                    "coordinate_basis": "global",
                }
            ],
            analysis_cases=[{"id": "AC1", "load_case_ids": ["LC1"], "method": "linear_static"}],
        )
    )

    with pytest.raises(SingularStiffnessError):
        solve_linear_static_3d(cem, "AC1")


def test_vertical_member_uses_global_y_fallback_and_warns() -> None:
    """Member parallel to global Z (no local_axis_hint) must fall back to
    global Y as the reference and report the fallback as a warning."""
    length, p = 1.0, 1_000.0
    cem = CEM.model_validate(
        _cantilever_frame_cem(tip_force=(p, 0.0, 0.0), tip_position=(0.0, 0.0, length))
    )
    result = solve_linear_static_3d(cem, "AC1")

    assert any("global Y" in w for w in result.warnings)
    # Sanity: still solves to a finite, nonzero tip deflection.
    disp = result.displacements["N2"]
    assert math.isfinite(disp["Ux"])
    assert abs(disp["Ux"]) > 0
