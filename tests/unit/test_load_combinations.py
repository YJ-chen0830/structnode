"""AnalysisCase.factors: lets one AnalysisCase represent a code load
combination (e.g. "1.2D + 1.6L") via linear superposition over existing
load cases, instead of duplicating load data under pre-scaled copies."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from structnode.core.model import CEM
from structnode.fem.solvers import solve_linear_static_2d
from structnode.fem.solvers.linear_static_3d import solve_linear_static_3d


def _two_case_cem(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "0.1",
        "model_id": "combo-test",
        "revision": 0,
        "units": {"length": "m", "force": "N"},
        "coordinate_system": "global_cartesian_rh",
        "nodes": [
            {"id": "N1", "position": [0.0, 0.0, 0.0]},
            {"id": "N2", "position": [1.0, 0.0, 0.0]},
        ],
        "materials": [{"id": "M1", "E": 2.0e11, "G": 7.7e10}],
        "sections": [{"id": "S1", "A": 0.01, "Iy": 8e-6, "Iz": 8e-6, "J": 1e-6}],
        "elements": [
            {
                "id": "E1",
                "type": "frame",
                "node_ids": ["N1", "N2"],
                "material_id": "M1",
                "section_id": "S1",
            }
        ],
        "constraints": [{"node_id": "N1", "dofs": [True, True, True, True, True, True]}],
        "load_cases": [{"id": "D"}, {"id": "L"}],
        "loads": [
            {
                "id": "FD",
                "case_id": "D",
                "kind": "nodal_force",
                "target_id": "N2",
                "values": [0.0, -1000.0, 0.0],
                "coordinate_basis": "global",
            },
            {
                "id": "FL",
                "case_id": "L",
                "kind": "nodal_force",
                "target_id": "N2",
                "values": [0.0, -500.0, 0.0],
                "coordinate_basis": "global",
            },
        ],
        "analysis_cases": [
            {"id": "AC_D", "load_case_ids": ["D"], "method": "linear_static"},
            {"id": "AC_L", "load_case_ids": ["L"], "method": "linear_static"},
            {
                "id": "AC_COMBO",
                "load_case_ids": ["D", "L"],
                "factors": [1.2, 1.6],
                "method": "linear_static",
            },
        ],
        "metadata": {},
        "provenance": {
            "created_by": "human",
            "created_at": "2026-10-08T00:00:00Z",
            "tool_version": "0.0.1",
        },
    }
    base.update(overrides)
    return base


def test_factors_length_mismatch_rejected() -> None:
    payload = _two_case_cem(
        analysis_cases=[
            {
                "id": "AC_BAD",
                "load_case_ids": ["D", "L"],
                "factors": [1.2],
                "method": "linear_static",
            }
        ]
    )
    with pytest.raises(ValidationError, match="factors must have the same length"):
        CEM.model_validate(payload)


def test_no_factors_defaults_to_unweighted_sum() -> None:
    cem = CEM.model_validate(_two_case_cem())
    ac = next(ac for ac in cem.analysis_cases if ac.id == "AC_D")
    assert ac.case_factors() == {"D": 1.0}


def test_combo_factors_scale_each_case() -> None:
    cem = CEM.model_validate(_two_case_cem())
    ac = next(ac for ac in cem.analysis_cases if ac.id == "AC_COMBO")
    assert ac.case_factors() == {"D": 1.2, "L": 1.6}


def test_2d_combo_equals_linear_superposition_of_factored_cases() -> None:
    cem = CEM.model_validate(_two_case_cem())

    result_d = solve_linear_static_2d(cem, "AC_D")
    result_l = solve_linear_static_2d(cem, "AC_L")
    result_combo = solve_linear_static_2d(cem, "AC_COMBO")

    uy_d = result_d.displacements["N2"]["Uy"]
    uy_l = result_l.displacements["N2"]["Uy"]
    uy_combo = result_combo.displacements["N2"]["Uy"]

    assert uy_combo == pytest.approx(1.2 * uy_d + 1.6 * uy_l)


def test_3d_combo_equals_linear_superposition_of_factored_cases() -> None:
    cem = CEM.model_validate(_two_case_cem())

    result_d = solve_linear_static_3d(cem, "AC_D")
    result_l = solve_linear_static_3d(cem, "AC_L")
    result_combo = solve_linear_static_3d(cem, "AC_COMBO")

    uy_d = result_d.displacements["N2"]["Uy"]
    uy_l = result_l.displacements["N2"]["Uy"]
    uy_combo = result_combo.displacements["N2"]["Uy"]

    assert uy_combo == pytest.approx(1.2 * uy_d + 1.6 * uy_l)
