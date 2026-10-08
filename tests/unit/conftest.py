from __future__ import annotations

import copy
from typing import Any

import pytest


@pytest.fixture
def valid_cem_dict() -> dict[str, Any]:
    """A minimal, structurally valid CEM document (deep-copy before mutating)."""
    return copy.deepcopy(
        {
            "schema_version": "0.1",
            "model_id": "unit-test-model",
            "revision": 0,
            "units": {"length": "m", "force": "N"},
            "coordinate_system": "global_cartesian_rh",
            "nodes": [
                {"id": "N1", "position": [0.0, 0.0, 0.0]},
                {"id": "N2", "position": [1.0, 0.0, 0.0]},
            ],
            "materials": [{"id": "M1", "E": 2.0e11, "rho": 7850.0}],
            "sections": [{"id": "S1", "A": 0.01, "Iy": 8.333e-6, "Iz": 8.333e-6, "J": 1.666e-5}],
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
            "load_cases": [{"id": "LC1", "description": "Tip load"}],
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
            "analysis_cases": [
                {
                    "id": "AC1",
                    "load_case_ids": ["LC1"],
                    "method": "linear_static",
                    "solver_options": {},
                }
            ],
            "metadata": {},
            "provenance": {
                "created_by": "human",
                "created_at": "2026-10-08T00:00:00Z",
                "tool_version": "0.0.1",
            },
        }
    )
