"""S2 scope-guard tests: things the native 2D solver must reject
outright rather than silently approximate."""

from __future__ import annotations

from typing import Any

import pytest

from structnode.core.model import CEM
from structnode.fem.assembly import UnsupportedModelError
from structnode.fem.solvers import AnalysisCaseNotFoundError, solve_linear_static_2d


def _frame_cem(**overrides: dict[str, Any]) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema_version": "0.1",
        "model_id": "guard-test",
        "revision": 0,
        "units": {"length": "m", "force": "N"},
        "coordinate_system": "global_cartesian_rh",
        "nodes": [
            {"id": "N1", "position": [0.0, 0.0, 0.0]},
            {"id": "N2", "position": [1.0, 0.0, 0.0]},
        ],
        "materials": [{"id": "M1", "E": 2.0e11}],
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
        "load_cases": [{"id": "LC1"}],
        "loads": [
            {
                "id": "F1",
                "case_id": "LC1",
                "kind": "nodal_force",
                "target_id": "N2",
                "values": [0.0, -1000.0, 0.0],
                "coordinate_basis": "global",
            }
        ],
        "analysis_cases": [{"id": "AC1", "load_case_ids": ["LC1"], "method": "linear_static"}],
        "metadata": {},
        "provenance": {
            "created_by": "human",
            "created_at": "2026-10-08T00:00:00Z",
            "tool_version": "0.0.1",
        },
    }
    base.update(overrides)
    return base


def test_mixed_element_types_rejected() -> None:
    data = _frame_cem()
    data["elements"].append(
        {
            "id": "E2",
            "type": "truss",
            "node_ids": ["N1", "N2"],
            "material_id": "M1",
            "section_id": "S1",
        }
    )
    cem = CEM.model_validate(data)
    with pytest.raises(UnsupportedModelError, match="single element type"):
        solve_linear_static_2d(cem, "AC1")


def test_non_planar_model_rejected() -> None:
    data = _frame_cem()
    data["nodes"][1]["position"] = [1.0, 0.0, 0.5]
    cem = CEM.model_validate(data)
    with pytest.raises(UnsupportedModelError, match="z=0 plane"):
        solve_linear_static_2d(cem, "AC1")


def test_member_distributed_load_rejected() -> None:
    data = _frame_cem()
    data["loads"][0] = {
        "id": "F1",
        "case_id": "LC1",
        "kind": "member_distributed",
        "target_id": "E1",
        "values": [0.0, -500.0, 0.0],
        "coordinate_basis": "global",
    }
    cem = CEM.model_validate(data)
    with pytest.raises(UnsupportedModelError, match="member_distributed"):
        solve_linear_static_2d(cem, "AC1")


def test_local_basis_load_rejected() -> None:
    data = _frame_cem()
    data["loads"][0]["coordinate_basis"] = "local"
    cem = CEM.model_validate(data)
    with pytest.raises(UnsupportedModelError, match="coordinate_basis"):
        solve_linear_static_2d(cem, "AC1")


def test_out_of_plane_force_component_rejected() -> None:
    data = _frame_cem()
    data["loads"][0]["values"] = [0.0, -1000.0, 5.0]  # non-zero Fz
    cem = CEM.model_validate(data)
    with pytest.raises(UnsupportedModelError, match="out-of-plane"):
        solve_linear_static_2d(cem, "AC1")


def test_nodal_moment_on_truss_only_model_rejected() -> None:
    data = _frame_cem()
    data["elements"][0]["type"] = "truss"
    data["elements"][0]["releases"] = None
    data["loads"][0] = {
        "id": "F1",
        "case_id": "LC1",
        "kind": "nodal_moment",
        "target_id": "N2",
        "values": [0.0, 0.0, 10.0],
        "coordinate_basis": "global",
    }
    cem = CEM.model_validate(data)
    with pytest.raises(UnsupportedModelError, match="no rotational DOF"):
        solve_linear_static_2d(cem, "AC1")


def test_unknown_analysis_case_raises() -> None:
    cem = CEM.model_validate(_frame_cem())
    with pytest.raises(AnalysisCaseNotFoundError):
        solve_linear_static_2d(cem, "NOPE")
