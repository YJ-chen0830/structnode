"""2D truss (pin-jointed, axial-only) element stiffness.

DOF order per node: (u, v) -- translation in global X, Y only. Truss
elements carry no moment and have no rotational DOF, per
docs/MASTER_PLAN.md section 3 ("clear truss vs frame DOF rules").
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray


def truss2d_direction_cosines(
    x1: float, y1: float, x2: float, y2: float
) -> tuple[float, float, float]:
    """Returns (cos, sin, length) of the member's local x-axis."""
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    return dx / length, dy / length, length


def truss2d_local_stiffness(e: float, a: float, length: float) -> NDArray[np.float64]:
    """1-DOF-per-end axial stiffness along the member's own local axis."""
    k = e * a / length
    return np.array([[k, -k], [-k, k]], dtype=np.float64)


def truss2d_global_stiffness(
    e: float, a: float, x1: float, y1: float, x2: float, y2: float
) -> NDArray[np.float64]:
    """4x4 global stiffness, DOF order (u1, v1, u2, v2)."""
    c, s, length = truss2d_direction_cosines(x1, y1, x2, y2)
    k = e * a / length
    cc, ss, cs = c * c, s * s, c * s
    return k * np.array(
        [
            [cc, cs, -cc, -cs],
            [cs, ss, -cs, -ss],
            [-cc, -cs, cc, cs],
            [-cs, -ss, cs, ss],
        ],
        dtype=np.float64,
    )


def truss2d_axial_force(
    e: float,
    a: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    u_global: NDArray[np.float64],
) -> float:
    """Axial force (tension positive) from the 4-vector of global end displacements."""
    c, s, length = truss2d_direction_cosines(x1, y1, x2, y2)
    u1, v1, u2, v2 = u_global
    elongation = -c * u1 - s * v1 + c * u2 + s * v2
    return float(e * a / length * elongation)
