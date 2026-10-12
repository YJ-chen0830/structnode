"""The 2D and 3D native solvers are independent implementations
(separate element stiffness formulas, separate assembly, separate
partition/elimination code). On a model that's valid for both --
planar, in-plane loads only -- they must agree exactly on every shared
quantity. This is a stronger check than either solver's own analytical
benchmarks: it's two different pieces of code converging on the same
answer, not the same formula evaluated twice.

Uses `reporting.compare_results` (the same tool `structnode compare`
exposes) rather than hand-rolled assertions, so this test doubles as a
regression check on that comparison logic too.
"""

from __future__ import annotations

import json
from pathlib import Path

from structnode.core.model import CEM
from structnode.fem.solvers import solve_linear_static_2d, solve_linear_static_3d
from structnode.reporting import compare_results

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"


def test_2d_and_3d_solvers_agree_on_equivalent_planar_cantilever() -> None:
    cem_2d = CEM.model_validate(
        json.loads((EXAMPLES / "cantilever.cem.json").read_text(encoding="utf-8"))
    )
    cem_3d = CEM.model_validate(
        json.loads((EXAMPLES / "cantilever_3d.cem.json").read_text(encoding="utf-8"))
    )

    result_2d = solve_linear_static_2d(cem_2d, "AC1").to_dict()
    result_3d = solve_linear_static_3d(cem_3d, "AC1").to_dict()

    # element_forces is deliberately excluded: the 2D solver reports
    # local end forces as (N,V,M) per end while the 3D solver reports
    # (N,Vy,Vz,T,My,Mz) -- genuinely different naming conventions for a
    # 2-DOF-vs-6-DOF local system, not a disagreement to reconcile here.
    # displacements/reactions use the same names (Ux,Uy,Rz / Fx,Fy,Mz)
    # in both, which is the actual apples-to-apples comparison.
    comparison = compare_results(
        {k: v for k, v in result_2d.items() if k in ("displacements", "reactions")},
        {k: v for k, v in result_3d.items() if k in ("displacements", "reactions")},
        tolerance=1e-9,
    )

    shared_components = {"Ux", "Uy", "Rz", "Fx", "Fy", "Mz"}
    relevant_diffs = [d for d in comparison.diffs if d.component in shared_components]
    assert relevant_diffs, "expected at least one shared quantity to compare"
    for diff in relevant_diffs:
        assert diff.rel_diff is None or diff.rel_diff <= 1e-9, diff

    # The 3D result additionally reports Uz/Rx/Ry/Fz/Mx/My (out-of-plane
    # DOFs the 2D model doesn't model at all) -- those are *expected* to
    # be "missing" on the 2D side, not a disagreement.
    out_of_plane = {"Uz", "Rx", "Ry", "Fz", "Mx", "My"}
    unexpected_missing = [
        m for m in comparison.missing_in_a if not any(m.endswith(c) for c in out_of_plane)
    ]
    assert unexpected_missing == []
