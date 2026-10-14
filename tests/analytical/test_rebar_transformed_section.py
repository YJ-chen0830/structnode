"""Benchmark: cantilever beam deflection with embedded rebar via the
transformed-section method (docs/ADR/0006-rebar-transformed-section.md).
Demonstrates rebar genuinely changes the analysis result (not just
metadata) -- same cantilever-tip-load formula as
test_benchmark_3_cantilever_tip_load (tests/analytical/test_benchmarks_2d.py),
but with an independently hand-computed transformed Iz_eff/A_eff instead
of the gross section's.
"""

from __future__ import annotations

import math
from typing import Any

from structnode.core.model import CEM
from structnode.fem.solvers import solve_linear_static_2d

RELATIVE_TOLERANCE = 1e-6


def _base_cem(**overrides: Any) -> dict[str, Any]:
    base = {
        "schema_version": "0.1",
        "model_id": "rebar-benchmark",
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


def test_rebar_transformed_section_changes_cantilever_deflection() -> None:
    """Rectangular RC cantilever, symmetric 4-corner rebar. The solved tip
    deflection must match PL^3/(3*E_concrete*Iz_eff) -- using the
    transformed Iz_eff, not the gross section's Iz -- proving rebar
    actually changes the result, not just decorative metadata."""
    e_concrete, e_rebar = 25e9, 200e9
    length, p = 2.0, 1_000.0

    b, h = 0.3, 0.5  # section width (local y), depth (local z), m
    a_gross = b * h
    iz_gross = h * b**3 / 12

    bar_diameter = 0.025
    bar_area = math.pi * (bar_diameter / 2) ** 2
    y0, z0 = 0.1, 0.2
    bar_positions = [(y0, z0), (-y0, z0), (y0, -z0), (-y0, -z0)]

    # Independent hand-calculation of the transformed section (mirrors
    # ADR 0006's formula, computed separately from
    # structnode.fem.rebar.effective_section_properties so this test
    # isn't just checking the implementation against itself).
    n = e_rebar / e_concrete
    delta_a = (n - 1) * bar_area
    a_eff = a_gross + 4 * delta_a
    # Symmetric 4-corner layout: combined centroid stays at the origin.
    iz_eff = iz_gross + sum(delta_a * y**2 for y, _z in bar_positions)
    assert a_eff > a_gross  # sanity: transformed area is strictly larger

    cem = CEM.model_validate(
        _base_cem(
            nodes=[
                {"id": "N1", "position": [0.0, 0.0, 0.0]},
                {"id": "N2", "position": [length, 0.0, 0.0]},
            ],
            materials=[
                {"id": "CONCRETE", "E": e_concrete},
                {"id": "REBAR", "E": e_rebar},
            ],
            sections=[
                {
                    "id": "S1",
                    "A": a_gross,
                    "Iy": iz_gross,
                    "Iz": iz_gross,
                    "J": 1e-6,
                    "rebar": {
                        "material_id": "REBAR",
                        "bars": [
                            {"y": y, "z": z, "diameter": bar_diameter} for y, z in bar_positions
                        ],
                    },
                }
            ],
            elements=[
                {
                    "id": "E1",
                    "type": "frame",
                    "node_ids": ["N1", "N2"],
                    "material_id": "CONCRETE",
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

    expected_delta = -p * length**3 / (3 * e_concrete * iz_eff)
    assert math.isclose(
        result.displacements["N2"]["Uy"], expected_delta, rel_tol=RELATIVE_TOLERANCE
    )

    # And the rebar genuinely changed the result vs. the plain gross
    # section -- not just numerically identical by coincidence (the
    # whole point of this benchmark).
    gross_delta = -p * length**3 / (3 * e_concrete * iz_gross)
    assert not math.isclose(expected_delta, gross_delta, rel_tol=1e-3)
