"""Benchmark family #8 (docs/MASTER_PLAN.md section 4): cross-solver
comparison against OpenSeesPy, with a documented mapping and
tolerance.

Skipped automatically in any environment where `openseespy` isn't
importable -- which, as of this writing, includes this project's own
dev/CI environment (see adapters/opensees/adapter.py's module
docstring for why). That is a skip, not a pass: it means this file has
never actually executed. Anyone running it where openseespy imports
successfully will exercise it for real and should treat a first run as
the actual verification of the adapter, not these two solvers simply
existing.

Test models use a doubly-symmetric section (Iy == Iz) deliberately:
the adapter's local-axis convention for `vecxz` has not been confirmed
to agree with this project's own (see the adapter's module docstring),
and a doubly-symmetric section makes bending axisymmetric about the
member axis, so that ambiguity can't affect the comparison.
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from structnode.adapters.opensees import is_available, run_linear_static_opensees
from structnode.core.model import CEM
from structnode.fem.solvers import solve_linear_static_3d

# Looser than the native-vs-analytical 1e-6: two independently
# implemented solvers with different internal numerics, not the same
# formula evaluated twice.
RELATIVE_TOLERANCE = 1e-4

pytestmark = pytest.mark.skipif(
    not is_available(),
    reason="openseespy is not importable in this environment (see adapters/opensees/adapter.py)",
)


def _cantilever_cem() -> dict[str, Any]:
    e, g, i, a, j, length, p = 2.0e11, 7.7e10, 8e-6, 0.01, 1.5e-5, 1.0, 1_000.0
    return {
        "schema_version": "0.1",
        "model_id": "cross-solver-cantilever",
        "revision": 0,
        "units": {"length": "m", "force": "N"},
        "coordinate_system": "global_cartesian_rh",
        "nodes": [
            {"id": "N1", "position": [0.0, 0.0, 0.0]},
            {"id": "N2", "position": [length, 0.0, 0.0]},
        ],
        "materials": [{"id": "M1", "E": e, "G": g}],
        "sections": [{"id": "S1", "A": a, "Iy": i, "Iz": i, "J": j}],
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
                "values": [0.0, -p, 0.0],
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


def test_native_3d_matches_opensees_cantilever() -> None:
    cem = CEM.model_validate(_cantilever_cem())
    native = solve_linear_static_3d(cem, "AC1")
    opensees = run_linear_static_opensees(cem, "AC1")

    for component in ("Ux", "Uy", "Uz", "Rx", "Ry", "Rz"):
        assert math.isclose(
            native.displacements["N2"][component],
            opensees.displacements["N2"][component],
            rel_tol=RELATIVE_TOLERANCE,
            abs_tol=1e-9,
        ), f"displacement {component} mismatch"

    for component in ("Fx", "Fy", "Fz", "Mx", "My", "Mz"):
        assert math.isclose(
            native.reactions["N1"][component],
            opensees.reactions["N1"][component],
            rel_tol=RELATIVE_TOLERANCE,
            abs_tol=1e-6,
        ), f"reaction {component} mismatch"
