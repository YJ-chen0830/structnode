"""Transformed-section stiffness contribution from embedded rebar
(`FrameSection.rebar`). Elastic, uncracked-section method only -- see
docs/ADR/0006-rebar-transformed-section.md for why this is the only
rebar effect in scope (strength/capacity design stays excluded per
MASTER_PLAN.md) and for the assumptions this relies on.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from structnode.core.model.cem import FrameSection, Material


def effective_section_properties(
    section: FrameSection,
    element_material: Material,
    materials: Mapping[str, Material],
) -> tuple[float, float, float]:
    """Returns (A_eff, Iy_eff, Iz_eff) for `section` as used by `element_material`.

    When `section.rebar` is None, returns the section's own (A, Iy, Iz)
    unchanged. Otherwise applies the transformed-section method: each
    bar's area is scaled by (n-1) (n = rebar material's E / element
    material's E) and combined with the gross section about the shifted
    composite centroid (general parallel-axis form, not an "assume the
    centroid doesn't move" shortcut -- RebarLayout's own mirror-symmetry
    validator guarantees the product of inertia stays zero through this
    shift, see its docstring).

    J (torsional constant) is never adjusted: longitudinal rebar's
    contribution to torsional stiffness is treated as negligible, standard
    practice for this kind of elastic section-property calculation.
    """
    if section.rebar is None:
        return section.A, section.Iy, section.Iz

    rebar_material = materials[section.rebar.material_id]
    n = rebar_material.E / element_material.E

    bars = section.rebar.bars
    delta_areas = [(n - 1) * math.pi * (bar.diameter / 2) ** 2 for bar in bars]

    a_eff = section.A + sum(delta_areas)
    y_bar = sum(da * bar.y for da, bar in zip(delta_areas, bars, strict=True)) / a_eff
    z_bar = sum(da * bar.z for da, bar in zip(delta_areas, bars, strict=True)) / a_eff

    iy_eff = (
        section.Iy
        + section.A * z_bar**2
        + sum(da * (bar.z - z_bar) ** 2 for da, bar in zip(delta_areas, bars, strict=True))
    )
    iz_eff = (
        section.Iz
        + section.A * y_bar**2
        + sum(da * (bar.y - y_bar) ** 2 for da, bar in zip(delta_areas, bars, strict=True))
    )
    return a_eff, iy_eff, iz_eff
