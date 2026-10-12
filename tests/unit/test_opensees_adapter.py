"""The dev/CI environment for this project does not have a working
openseespy install (see adapters/opensees/adapter.py's module
docstring), so these tests exercise the *unavailable* path -- which is
exactly the path real users on an unsupported platform will hit, and
it must fail clearly rather than silently.
"""

from __future__ import annotations

from typing import Any

import pytest

from structnode.adapters.opensees import (
    OpenSeesUnavailableError,
    capabilities,
    is_available,
    run_linear_static_opensees,
)
from structnode.core.model import CEM


@pytest.fixture
def valid_cem_dict() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "model_id": "opensees-adapter-test",
        "revision": 0,
        "units": {"length": "m", "force": "N"},
        "coordinate_system": "global_cartesian_rh",
        "nodes": [
            {"id": "N1", "position": [0.0, 0.0, 0.0]},
            {"id": "N2", "position": [1.0, 0.0, 0.0]},
        ],
        "materials": [{"id": "M1", "E": 2.0e11, "G": 7.7e10}],
        "sections": [{"id": "S1", "A": 0.01, "Iy": 8e-6, "Iz": 8e-6, "J": 1e-5}],
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
            "created_at": "2026-10-12T00:00:00Z",
            "tool_version": "0.0.1",
        },
    }


def test_capabilities_report_unavailable_in_this_environment() -> None:
    caps = capabilities()
    assert caps["name"] == "opensees"
    assert caps["available"] is False  # true for this project's dev/CI environment
    assert "truss" in caps["element_types"]
    assert "frame" in caps["element_types"]


def test_is_available_false_in_this_environment() -> None:
    assert is_available() is False


def test_run_raises_clear_error_when_unavailable(valid_cem_dict: dict[str, Any]) -> None:
    cem = CEM.model_validate(valid_cem_dict)
    with pytest.raises(OpenSeesUnavailableError, match="not usable in this environment"):
        run_linear_static_opensees(cem, "AC1")
