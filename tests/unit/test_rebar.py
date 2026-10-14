"""Unit tests for rebar transformed-section properties (ADR 0006):
`effective_section_properties` itself, and `RebarLayout`'s mirror-symmetry
validator (the asymmetric/Iyz-coupling rejection case is the important
negative test here)."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from structnode.core.model.cem import FrameSection, Material, RebarBar, RebarLayout
from structnode.fem.rebar import effective_section_properties


def _section(**overrides: object) -> FrameSection:
    base = {"id": "S1", "A": 0.15, "Iy": 1e-3, "Iz": 1e-3, "J": 1e-6}
    base.update(overrides)
    return FrameSection.model_validate(base)


def test_no_rebar_returns_gross_properties_unchanged() -> None:
    section = _section()
    concrete = Material(id="C", E=25e9)
    a, iy, iz = effective_section_properties(section, concrete, {"C": concrete})
    assert (a, iy, iz) == (section.A, section.Iy, section.Iz)


def test_symmetric_four_corner_bars_increase_area_and_inertia() -> None:
    concrete = Material(id="CONCRETE", E=25e9)
    rebar_steel = Material(id="REBAR", E=200e9)
    materials = {"CONCRETE": concrete, "REBAR": rebar_steel}

    bar_diameter = 0.025
    bar_area = math.pi * (bar_diameter / 2) ** 2
    y0, z0 = 0.1, 0.2
    bars = [
        RebarBar(y=y0, z=z0, diameter=bar_diameter),
        RebarBar(y=-y0, z=z0, diameter=bar_diameter),
        RebarBar(y=y0, z=-z0, diameter=bar_diameter),
        RebarBar(y=-y0, z=-z0, diameter=bar_diameter),
    ]
    section = _section(
        A=0.15, Iy=0.001125, Iz=0.001125, rebar={"material_id": "REBAR", "bars": bars}
    )

    a_eff, iy_eff, iz_eff = effective_section_properties(section, concrete, materials)

    n = 200e9 / 25e9
    delta_a = (n - 1) * bar_area
    expected_a = 0.15 + 4 * delta_a
    expected_iz = 0.001125 + 4 * delta_a * y0**2
    expected_iy = 0.001125 + 4 * delta_a * z0**2

    assert a_eff == pytest.approx(expected_a)
    assert iz_eff == pytest.approx(expected_iz)
    assert iy_eff == pytest.approx(expected_iy)


def test_unequal_top_bottom_bars_shifts_centroid_correctly() -> None:
    """3 bars bottom (z=-z0), 2 bars top (z=+z0), left-right symmetric
    about y=0 -- a realistic unequal-reinforcement case. The combined
    centroid must shift toward the heavier (bottom) side, and Iy_eff must
    match the general parallel-axis formula, not the "centroid stays at
    origin" shortcut (which would be wrong here)."""
    concrete = Material(id="CONCRETE", E=25e9)
    rebar_steel = Material(id="REBAR", E=200e9)
    materials = {"CONCRETE": concrete, "REBAR": rebar_steel}

    dia = 0.02
    bar_area = math.pi * (dia / 2) ** 2
    z0 = 0.2
    bars = [
        RebarBar(y=-0.1, z=-z0, diameter=dia),
        RebarBar(y=0.0, z=-z0, diameter=dia),
        RebarBar(y=0.1, z=-z0, diameter=dia),
        RebarBar(y=-0.1, z=z0, diameter=dia),
        RebarBar(y=0.1, z=z0, diameter=dia),
    ]
    a_gross, iy_gross = 0.15, 0.001125
    section = _section(A=a_gross, Iy=iy_gross, Iz=iy_gross, rebar={
        "material_id": "REBAR", "bars": bars
    })

    a_eff, iy_eff, _iz_eff = effective_section_properties(section, concrete, materials)

    n = 200e9 / 25e9
    delta_a = (n - 1) * bar_area
    expected_a = a_gross + 5 * delta_a
    z_bar = (3 * delta_a * (-z0) + 2 * delta_a * z0) / expected_a
    expected_iy = (
        iy_gross
        + a_gross * z_bar**2
        + 3 * delta_a * (-z0 - z_bar) ** 2
        + 2 * delta_a * (z0 - z_bar) ** 2
    )

    assert a_eff == pytest.approx(expected_a)
    assert z_bar < 0  # centroid pulled toward the heavier (bottom) side
    assert iy_eff == pytest.approx(expected_iy)


def test_bars_with_no_mirror_partner_rejected() -> None:
    """Diagonal-only bars: the (n-1)-weighted centroid is at the origin,
    but Iyz = sum((n-1)*a*y*z) != 0 -- the layout isn't mirror-symmetric
    about either axis, and must be rejected (see ADR 0006)."""
    with pytest.raises(ValidationError, match="mirror-symmetric"):
        RebarLayout(
            material_id="REBAR",
            bars=[
                RebarBar(y=0.1, z=0.1, diameter=0.02),
                RebarBar(y=-0.1, z=-0.1, diameter=0.02),
            ],
        )


def test_bars_symmetric_about_y_axis_only_accepted() -> None:
    # top-bottom symmetric (about z=0: z -> -z), not left-right symmetric
    RebarLayout(
        material_id="REBAR",
        bars=[
            RebarBar(y=0.1, z=0.2, diameter=0.02),
            RebarBar(y=0.1, z=-0.2, diameter=0.02),
        ],
    )


def test_bars_symmetric_about_z_axis_only_accepted() -> None:
    # left-right symmetric (about y=0: y -> -y), not top-bottom symmetric
    RebarLayout(
        material_id="REBAR",
        bars=[
            RebarBar(y=0.1, z=0.2, diameter=0.02),
            RebarBar(y=-0.1, z=0.2, diameter=0.02),
        ],
    )


def test_single_bar_on_both_axes_is_its_own_mirror() -> None:
    RebarLayout(
        material_id="REBAR",
        bars=[RebarBar(y=0.0, z=0.0, diameter=0.02)],
    )


def test_empty_bars_rejected() -> None:
    with pytest.raises(ValidationError):
        RebarLayout(material_id="REBAR", bars=[])


def test_mismatched_diameter_mirror_rejected() -> None:
    # Off-axis (z != 0, y != 0) so neither bar trivially self-matches by
    # lying on a mirror axis -- a real partner is required, and the
    # mismatched diameter means there isn't one.
    with pytest.raises(ValidationError, match="mirror-symmetric"):
        RebarLayout(
            material_id="REBAR",
            bars=[
                RebarBar(y=0.1, z=0.1, diameter=0.02),
                RebarBar(y=-0.1, z=0.1, diameter=0.025),
            ],
        )
