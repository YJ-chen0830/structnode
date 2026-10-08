"""Unit system declarations and SI conversion factors.

CEM always stores values internally in SI (meters, Newtons, radians,
Pascals, kilograms). `Units` only records which units the *source* data
was expressed in, so adapters/importers can convert at the boundary and
provenance can explain where a number came from.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

LengthUnit = Literal["m", "mm", "cm", "ft", "in"]
ForceUnit = Literal["N", "kN", "lbf", "kip"]

_LENGTH_TO_M: dict[str, float] = {
    "m": 1.0,
    "mm": 1e-3,
    "cm": 1e-2,
    "ft": 0.3048,
    "in": 0.0254,
}

_FORCE_TO_N: dict[str, float] = {
    "N": 1.0,
    "kN": 1e3,
    "lbf": 4.4482216152605,
    "kip": 4448.2216152605,
}


def length_to_si(value: float, unit: LengthUnit) -> float:
    return value * _LENGTH_TO_M[unit]


def force_to_si(value: float, unit: ForceUnit) -> float:
    return value * _FORCE_TO_N[unit]


class Units(BaseModel):
    """Declares the unit convention the *source* data was authored in.

    Internal CEM storage is always SI; this is metadata for boundary
    conversion and audit, not a toggle that changes how stored numbers
    are interpreted.
    """

    length: LengthUnit
    force: ForceUnit
