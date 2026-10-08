"""Required benchmark families from docs/MASTER_PLAN.md section 4,
numbers 1-4 and 6 (3D frame / mesh-refinement / cross-solver benchmarks
are S3/S4 scope). Tolerances per that section: exact analytical linear
cases relative error <= 1e-6 where well-conditioned.
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from structnode.core.model import CEM
from structnode.fem.solvers import SingularStiffnessError, solve_linear_static_2d

RELATIVE_TOLERANCE = 1e-6


def _base_cem(**overrides: Any) -> dict[str, Any]:
    base = {
        "schema_version": "0.1",
        "model_id": "benchmark",
        "revision": 0,
        "units": {"length": "m", "force": "N"},
        "coordinate_system": "global_cartesian_rh",
        "metadata": {},
        "provenance": {
            "created_by": "human",
            "created_at": "2026-10-08T00:00:00Z",
            "tool_version": "0.0.1",
        },
    }
    base.update(overrides)
    return base


def test_benchmark_1_axial_bar() -> None:
    """u = PL/(EA); single truss element, tip load along its own axis."""
    e, a, length, p = 2.0e11, 0.01, 2.0, 1_000.0
    cem = CEM.model_validate(
        _base_cem(
            nodes=[
                {"id": "N1", "position": [0.0, 0.0, 0.0]},
                {"id": "N2", "position": [length, 0.0, 0.0]},
            ],
            materials=[{"id": "M1", "E": e}],
            sections=[{"id": "S1", "A": a, "Iy": 1e-6, "Iz": 1e-6, "J": 1e-6}],
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
                {"node_id": "N2", "dofs": [False, True, True, True, True, True]},
            ],
            load_cases=[{"id": "LC1"}],
            loads=[
                {
                    "id": "F1",
                    "case_id": "LC1",
                    "kind": "nodal_force",
                    "target_id": "N2",
                    "values": [p, 0.0, 0.0],
                    "coordinate_basis": "global",
                }
            ],
            analysis_cases=[{"id": "AC1", "load_case_ids": ["LC1"], "method": "linear_static"}],
        )
    )

    result = solve_linear_static_2d(cem, "AC1")

    expected_u = p * length / (e * a)
    actual_u = result.displacements["N2"]["Ux"]
    assert math.isclose(actual_u, expected_u, rel_tol=RELATIVE_TOLERANCE)

    # Equilibrium: support reaction balances the applied load.
    assert math.isclose(result.reactions["N1"]["Fx"], -p, rel_tol=RELATIVE_TOLERANCE)
    assert math.isclose(result.element_forces["E1"]["N"], p, rel_tol=RELATIVE_TOLERANCE)


def test_benchmark_2_simply_supported_beam_midspan_load() -> None:
    """delta=PL^3/(48EI) at midspan, reactions P/2 each, two-element frame."""
    e, iz, a, span, p = 2.0e11, 8.333e-6, 0.01, 4.0, 1_000.0
    half = span / 2.0
    cem = CEM.model_validate(
        _base_cem(
            nodes=[
                {"id": "N1", "position": [0.0, 0.0, 0.0]},
                {"id": "N2", "position": [half, 0.0, 0.0]},
                {"id": "N3", "position": [span, 0.0, 0.0]},
            ],
            materials=[{"id": "M1", "E": e}],
            sections=[{"id": "S1", "A": a, "Iy": iz, "Iz": iz, "J": 1e-6}],
            elements=[
                {
                    "id": "E1",
                    "type": "frame",
                    "node_ids": ["N1", "N2"],
                    "material_id": "M1",
                    "section_id": "S1",
                },
                {
                    "id": "E2",
                    "type": "frame",
                    "node_ids": ["N2", "N3"],
                    "material_id": "M1",
                    "section_id": "S1",
                },
            ],
            constraints=[
                {"node_id": "N1", "dofs": [True, True, True, True, True, False]},
                {"node_id": "N3", "dofs": [False, True, True, True, True, False]},
            ],
            load_cases=[{"id": "LC1"}],
            loads=[
                {
                    "id": "F1",
                    "case_id": "LC1",
                    "kind": "nodal_force",
                    "target_id": "N2",
                    "values": [0.0, -p, 0.0],
                    "coordinate_basis": "global",
                }
            ],
            analysis_cases=[{"id": "AC1", "load_case_ids": ["LC1"], "method": "linear_static"}],
        )
    )

    result = solve_linear_static_2d(cem, "AC1")

    expected_delta = -p * span**3 / (48 * e * iz)
    actual_delta = result.displacements["N2"]["Uy"]
    assert math.isclose(actual_delta, expected_delta, rel_tol=RELATIVE_TOLERANCE)

    assert math.isclose(result.reactions["N1"]["Fy"], p / 2, rel_tol=RELATIVE_TOLERANCE)
    assert math.isclose(result.reactions["N3"]["Fy"], p / 2, rel_tol=RELATIVE_TOLERANCE)


def test_benchmark_3_cantilever_tip_load() -> None:
    """delta=PL^3/(3EI), tip rotation=PL^2/(2EI)."""
    e, iz, a, length, p = 2.0e11, 8.333e-6, 0.01, 1.0, 1_000.0
    cem = CEM.model_validate(
        _base_cem(
            nodes=[
                {"id": "N1", "position": [0.0, 0.0, 0.0]},
                {"id": "N2", "position": [length, 0.0, 0.0]},
            ],
            materials=[{"id": "M1", "E": e}],
            sections=[{"id": "S1", "A": a, "Iy": iz, "Iz": iz, "J": 1e-6}],
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
                    "values": [0.0, -p, 0.0],
                    "coordinate_basis": "global",
                }
            ],
            analysis_cases=[{"id": "AC1", "load_case_ids": ["LC1"], "method": "linear_static"}],
        )
    )

    result = solve_linear_static_2d(cem, "AC1")

    expected_delta = -p * length**3 / (3 * e * iz)
    expected_rotation = -p * length**2 / (2 * e * iz)

    assert math.isclose(
        result.displacements["N2"]["Uy"], expected_delta, rel_tol=RELATIVE_TOLERANCE
    )
    assert math.isclose(
        result.displacements["N2"]["Rz"], expected_rotation, rel_tol=RELATIVE_TOLERANCE
    )
    assert math.isclose(result.reactions["N1"]["Fy"], p, rel_tol=RELATIVE_TOLERANCE)


def test_benchmark_4_symmetric_truss() -> None:
    """Symmetric A-frame: equal member forces, symmetric reactions, zero
    horizontal displacement at the apex under a purely vertical load."""
    e, a, p = 2.0e11, 0.001, 1_000.0
    cem = CEM.model_validate(
        _base_cem(
            nodes=[
                {"id": "N1", "position": [-1.0, 0.0, 0.0]},
                {"id": "N2", "position": [1.0, 0.0, 0.0]},
                {"id": "N3", "position": [0.0, 1.0, 0.0]},
            ],
            materials=[{"id": "M1", "E": e}],
            sections=[{"id": "S1", "A": a, "Iy": 1e-6, "Iz": 1e-6, "J": 1e-6}],
            elements=[
                {
                    "id": "E1",
                    "type": "truss",
                    "node_ids": ["N1", "N3"],
                    "material_id": "M1",
                    "section_id": "S1",
                },
                {
                    "id": "E2",
                    "type": "truss",
                    "node_ids": ["N2", "N3"],
                    "material_id": "M1",
                    "section_id": "S1",
                },
            ],
            constraints=[
                {"node_id": "N1", "dofs": [True, True, True, True, True, True]},
                {"node_id": "N2", "dofs": [True, True, True, True, True, True]},
            ],
            load_cases=[{"id": "LC1"}],
            loads=[
                {
                    "id": "F1",
                    "case_id": "LC1",
                    "kind": "nodal_force",
                    "target_id": "N3",
                    "values": [0.0, -p, 0.0],
                    "coordinate_basis": "global",
                }
            ],
            analysis_cases=[{"id": "AC1", "load_case_ids": ["LC1"], "method": "linear_static"}],
        )
    )

    result = solve_linear_static_2d(cem, "AC1")

    assert abs(result.displacements["N3"]["Ux"]) < 1e-9
    assert math.isclose(
        result.reactions["N1"]["Fy"], result.reactions["N2"]["Fy"], rel_tol=RELATIVE_TOLERANCE
    )
    assert math.isclose(
        result.reactions["N1"]["Fy"] + result.reactions["N2"]["Fy"],
        p,
        rel_tol=RELATIVE_TOLERANCE,
    )
    assert math.isclose(
        result.reactions["N1"]["Fx"], -result.reactions["N2"]["Fx"], rel_tol=RELATIVE_TOLERANCE
    )
    assert math.isclose(
        abs(result.element_forces["E1"]["N"]),
        abs(result.element_forces["E2"]["N"]),
        rel_tol=RELATIVE_TOLERANCE,
    )


def test_benchmark_6_rigid_body_mode_is_rejected() -> None:
    """A truss chain restrained only along its own axis has zero lateral
    stiffness at the free end -- a mechanism the coarse topology check
    (which only requires *some* translational restraint somewhere) does
    not catch, but the solver must."""
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
                # Only Tx restrained at N2 -- Ty is a free, zero-stiffness mode.
                {"node_id": "N2", "dofs": [True, False, True, True, True, True]},
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
        solve_linear_static_2d(cem, "AC1")
