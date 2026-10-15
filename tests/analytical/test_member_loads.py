"""Benchmarks for uniform member loads (`member_distributed`, `gravity`;
docs/ADR/0007-uniform-member-loads.md) against closed-form Euler-Bernoulli
results. Fixed-end-force sign conventions are the classic place for a
silent bug, so every bending plane (2D, 3D local y, 3D local z) is checked
against a textbook formula, not just against another solver path."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest

from structnode.core.model import CEM
from structnode.fem.assembly import UnsupportedModelError
from structnode.fem.solvers import solve_linear_static_2d, solve_linear_static_3d

REL = 1e-9
E, G = 2.0e11, 8.0e10
A, IY, IZ, J = 0.01, 4.0e-6, 9.0e-6, 1.0e-6
W = 1_500.0  # N/m
L = 3.0


def _cem(
    nodes: list[tuple[str, tuple[float, float, float]]],
    elements: list[tuple[str, str, str]],
    supports: list[str],
    loads: list[dict[str, Any]],
    *,
    element_type: str = "frame",
    rho: float | None = None,
    factors: list[float] | None = None,
    local_axis_hint: tuple[float, float, float] | None = (0.0, 0.0, 1.0),
) -> CEM:
    material: dict[str, Any] = {"id": "M1", "E": E, "G": G}
    if rho is not None:
        material["rho"] = rho
    return CEM.model_validate(
        {
            "schema_version": "0.1",
            "model_id": "member-loads",
            "revision": 0,
            "units": {"length": "m", "force": "N"},
            "coordinate_system": "global_cartesian_rh",
            "nodes": [{"id": nid, "position": list(pos)} for nid, pos in nodes],
            "materials": [material],
            "sections": [
                {
                    "id": "S1",
                    "A": A,
                    "Iy": IY,
                    "Iz": IZ,
                    "J": J,
                    "local_axis_hint": list(local_axis_hint) if local_axis_hint else None,
                }
            ],
            "elements": [
                {
                    "id": eid,
                    "type": element_type,
                    "node_ids": [n1, n2],
                    "material_id": "M1",
                    "section_id": "S1",
                }
                for eid, n1, n2 in elements
            ],
            "constraints": [{"node_id": nid, "dofs": [True] * 6} for nid in supports],
            "load_cases": [{"id": "LC1"}],
            "loads": [{"case_id": "LC1", "coordinate_basis": "global", **ld} for ld in loads],
            "analysis_cases": [
                {
                    "id": "AC1",
                    "load_case_ids": ["LC1"],
                    "method": "linear_static",
                    "factors": factors,
                }
            ],
            "metadata": {},
            "provenance": {
                "created_by": "human",
                "created_at": "2026-10-15T00:00:00Z",
                "tool_version": "0.0.1",
            },
        }
    )


def _udl(target: str, values: tuple[float, float, float], **extra: Any) -> dict[str, Any]:
    return {
        "id": f"W-{target}",
        "kind": "member_distributed",
        "target_id": target,
        "values": list(values),
        **extra,
    }


def _cantilever(values: tuple[float, float, float], **kw: Any) -> CEM:
    return _cem(
        [("N1", (0.0, 0.0, 0.0)), ("N2", (L, 0.0, 0.0))],
        [("E1", "N1", "N2")],
        ["N1"],
        [_udl("E1", values)],
        **kw,
    )


def test_2d_cantilever_udl_matches_closed_form() -> None:
    result = solve_linear_static_2d(_cantilever((0.0, -W, 0.0)), "AC1")

    tip = result.displacements["N2"]
    assert math.isclose(tip["Uy"], -W * L**4 / (8 * E * IZ), rel_tol=REL)
    assert math.isclose(tip["Rz"], -W * L**3 / (6 * E * IZ), rel_tol=REL)

    assert math.isclose(result.reactions["N1"]["Fy"], W * L, rel_tol=REL)
    assert math.isclose(result.reactions["N1"]["Mz"], W * L**2 / 2, rel_tol=REL)

    forces = result.element_forces["E1"]
    assert math.isclose(forces["V1"], W * L, rel_tol=REL)
    assert math.isclose(forces["M1"], W * L**2 / 2, rel_tol=REL)
    # Free end carries nothing -- only true once the fixed-end loads are
    # subtracted back out of k @ u.
    assert abs(forces["V2"]) < 1e-9 * W * L
    assert abs(forces["M2"]) < 1e-9 * W * L**2


def test_2d_propped_fixed_fixed_beam_midspan_and_end_moments() -> None:
    """Fixed-fixed beam, two elements: midspan deflection wL^4/(384EI),
    end moments wL^2/12, midspan moment wL^2/24."""
    cem = _cem(
        [("N1", (0.0, 0.0, 0.0)), ("N2", (L / 2, 0.0, 0.0)), ("N3", (L, 0.0, 0.0))],
        [("E1", "N1", "N2"), ("E2", "N2", "N3")],
        ["N1", "N3"],
        [_udl("E1", (0.0, -W, 0.0)), _udl("E2", (0.0, -W, 0.0))],
    )
    result = solve_linear_static_2d(cem, "AC1")

    assert math.isclose(result.displacements["N2"]["Uy"], -W * L**4 / (384 * E * IZ), rel_tol=REL)
    assert math.isclose(result.reactions["N1"]["Mz"], W * L**2 / 12, rel_tol=REL)
    assert math.isclose(result.reactions["N3"]["Mz"], -W * L**2 / 12, rel_tol=REL)
    assert math.isclose(result.element_forces["E1"]["M2"], W * L**2 / 24, rel_tol=REL)


def test_2d_inclined_member_local_and_global_basis_agree() -> None:
    """A load given in member-local axes must solve identically to the same
    load rotated into global axes by hand."""
    angle = math.radians(30.0)
    c, s = math.cos(angle), math.sin(angle)
    nodes = [("N1", (0.0, 0.0, 0.0)), ("N2", (L * c, L * s, 0.0))]
    wx_local, wy_local = 200.0, -W

    local = _cem(
        nodes,
        [("E1", "N1", "N2")],
        ["N1"],
        [_udl("E1", (wx_local, wy_local, 0.0), coordinate_basis="local")],
    )
    global_values = (c * wx_local - s * wy_local, s * wx_local + c * wy_local, 0.0)
    glob = _cem(nodes, [("E1", "N1", "N2")], ["N1"], [_udl("E1", global_values)])

    r_local = solve_linear_static_2d(local, "AC1")
    r_global = solve_linear_static_2d(glob, "AC1")
    for key, value in r_global.displacements["N2"].items():
        assert math.isclose(r_local.displacements["N2"][key], value, rel_tol=1e-9, abs_tol=1e-15)
    for key, value in r_global.element_forces["E1"].items():
        assert math.isclose(r_local.element_forces["E1"][key], value, rel_tol=1e-9, abs_tol=1e-9)


@pytest.mark.parametrize(
    ("values", "disp_key", "inertia", "shear_key", "moment_key", "moment_sign"),
    [
        # Load along global -Y = local -y (hint +Z puts local y on global Y):
        # bending about local z.
        ((0.0, -W, 0.0), "Uy", IZ, "Vy1", "Mz1", 1.0),
        # Load along global -Z = local -z: bending about local y, the plane
        # whose fixed-end moments carry the opposite sign.
        ((0.0, 0.0, -W), "Uz", IY, "Vz1", "My1", -1.0),
    ],
)
def test_3d_cantilever_udl_both_bending_planes(
    values: tuple[float, float, float],
    disp_key: str,
    inertia: float,
    shear_key: str,
    moment_key: str,
    moment_sign: float,
) -> None:
    result = solve_linear_static_3d(_cantilever(values), "AC1")

    assert math.isclose(
        result.displacements["N2"][disp_key], -W * L**4 / (8 * E * inertia), rel_tol=REL
    )
    forces = result.element_forces["E1"]
    assert math.isclose(forces[shear_key], W * L, rel_tol=REL)
    assert math.isclose(forces[moment_key], moment_sign * W * L**2 / 2, rel_tol=REL)
    for key in ("N2", "Vy2", "Vz2", "T2", "My2", "Mz2"):
        assert abs(forces[key]) < 1e-9 * W * L**2


def test_2d_and_3d_agree_on_planar_frame_with_udl() -> None:
    cem = _cem(
        [("N1", (0.0, 0.0, 0.0)), ("N2", (0.0, L, 0.0)), ("N3", (L, L, 0.0))],
        [("E1", "N1", "N2"), ("E2", "N2", "N3")],
        ["N1", "N3"],
        [_udl("E1", (W / 3, 0.0, 0.0)), _udl("E2", (0.0, -W, 0.0))],
    )
    r2 = solve_linear_static_2d(cem, "AC1")
    r3 = solve_linear_static_3d(cem, "AC1")
    for key in ("Ux", "Uy"):
        assert math.isclose(r2.displacements["N2"][key], r3.displacements["N2"][key], rel_tol=1e-9)
    assert math.isclose(r2.displacements["N2"]["Rz"], r3.displacements["N2"]["Rz"], rel_tol=1e-9)


def test_gravity_self_weight_on_all_elements() -> None:
    rho, g = 7850.0, 9.80665
    cem = _cem(
        [("N1", (0.0, 0.0, 0.0)), ("N2", (L / 2, 0.0, 0.0)), ("N3", (L, 0.0, 0.0))],
        [("E1", "N1", "N2"), ("E2", "N2", "N3")],
        ["N1"],
        [{"id": "SW", "kind": "gravity", "target_id": "*", "values": [0.0, -g, 0.0]}],
        rho=rho,
    )
    result = solve_linear_static_2d(cem, "AC1")

    w = rho * A * g
    assert math.isclose(result.reactions["N1"]["Fy"], w * L, rel_tol=REL)
    assert math.isclose(result.displacements["N3"]["Uy"], -w * L**4 / (8 * E * IZ), rel_tol=REL)


def test_gravity_on_one_element_and_load_factor_scales_it() -> None:
    rho, g = 2400.0, 9.81
    cem = _cem(
        [("N1", (0.0, 0.0, 0.0)), ("N2", (L, 0.0, 0.0))],
        [("E1", "N1", "N2")],
        ["N1"],
        [{"id": "SW", "kind": "gravity", "target_id": "E1", "values": [0.0, -g, 0.0]}],
        rho=rho,
        factors=[1.2],
    )
    result = solve_linear_static_3d(cem, "AC1")
    assert math.isclose(result.reactions["N1"]["Fy"], 1.2 * rho * A * g * L, rel_tol=REL)


def test_gravity_without_density_rejected() -> None:
    cem = _cem(
        [("N1", (0.0, 0.0, 0.0)), ("N2", (L, 0.0, 0.0))],
        [("E1", "N1", "N2")],
        ["N1"],
        [{"id": "SW", "kind": "gravity", "target_id": "*", "values": [0.0, -9.81, 0.0]}],
    )
    with pytest.raises(UnsupportedModelError, match="density"):
        solve_linear_static_2d(cem, "AC1")


def test_gravity_local_basis_rejected() -> None:
    cem = _cem(
        [("N1", (0.0, 0.0, 0.0)), ("N2", (L, 0.0, 0.0))],
        [("E1", "N1", "N2")],
        ["N1"],
        [
            {
                "id": "SW",
                "kind": "gravity",
                "target_id": "*",
                "values": [0.0, -9.81, 0.0],
                "coordinate_basis": "local",
            }
        ],
        rho=7850.0,
    )
    with pytest.raises(UnsupportedModelError, match="global"):
        solve_linear_static_3d(cem, "AC1")


@pytest.mark.parametrize("solve", [solve_linear_static_2d, solve_linear_static_3d])
def test_truss_member_load_lumped_with_warning(solve: Any) -> None:
    """Two-bar truss under self-weight: total vertical reaction equals total
    weight, and the result says the load was lumped."""
    rho, g = 7850.0, 9.81
    cem = _cem(
        [("N1", (0.0, 0.0, 0.0)), ("N2", (2.0, 1.5, 0.0)), ("N3", (4.0, 0.0, 0.0))],
        [("E1", "N1", "N2"), ("E2", "N2", "N3")],
        ["N1", "N3"],
        [{"id": "SW", "kind": "gravity", "target_id": "*", "values": [0.0, -g, 0.0]}],
        element_type="truss",
        rho=rho,
        local_axis_hint=None,
    )
    if solve is solve_linear_static_3d:
        # Out-of-plane stability for the 3D truss: pin N2 in Z.
        cem.constraints.append(
            type(cem.constraints[0])(node_id="N2", dofs=(False, False, True, False, False, False))
        )
    result = solve(cem, "AC1")

    total_weight = rho * A * g * 2 * 2.5  # two 2.5 m members
    total_fy = sum(r.get("Fy", 0.0) for r in result.reactions.values())
    assert math.isclose(total_fy, total_weight, rel_tol=REL)
    assert sum("lumped" in w for w in result.warnings) == 2


def test_portal_frame_example_reactions_balance_factored_load() -> None:
    """examples/portal_frame_udl.cem.json: total vertical reaction equals the
    hand-summed factored load (self-weight of all members + beam UDLs), and
    the 2D/3D solvers agree."""
    path = Path(__file__).resolve().parents[2] / "examples" / "portal_frame_udl.cem.json"
    cem = CEM.model_validate_json(path.read_text(encoding="utf-8"))
    rho, g = 2400.0, 9.80665
    self_weight = rho * g * (0.16 * 3.5 * 2 + 0.18 * 6.0)
    expected = 1.2 * (self_weight + 12_000.0 * 6.0) + 1.6 * 9_000.0 * 6.0

    for solve in (solve_linear_static_2d, solve_linear_static_3d):
        result = solve(cem, "1.2D+1.6L")
        total_fy = sum(r["Fy"] for r in result.reactions.values())
        assert math.isclose(total_fy, expected, rel_tol=REL)
