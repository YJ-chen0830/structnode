"""3D truss (pin-jointed, axial-only) element stiffness.

DOF order per node: (u, v, w) -- translation in global X, Y, Z. No
rotational DOF, same reasoning as the 2D truss element.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray


def truss3d_direction_cosines(
    x1: float, y1: float, z1: float, x2: float, y2: float, z2: float
) -> tuple[float, float, float, float]:
    """Returns (cx, cy, cz, length) of the member's local x-axis."""
    dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    return dx / length, dy / length, dz / length, length


def truss3d_global_stiffness(
    e: float, a: float, x1: float, y1: float, z1: float, x2: float, y2: float, z2: float
) -> NDArray[np.float64]:
    """6x6 global stiffness, DOF order (u1, v1, w1, u2, v2, w2)."""
    cx, cy, cz, length = truss3d_direction_cosines(x1, y1, z1, x2, y2, z2)
    n = np.array([cx, cy, cz], dtype=np.float64)
    nnt = np.outer(n, n)
    k = e * a / length
    top = np.hstack([nnt, -nnt])
    bottom = np.hstack([-nnt, nnt])
    return k * np.vstack([top, bottom])


def truss3d_axial_force(
    e: float,
    a: float,
    x1: float,
    y1: float,
    z1: float,
    x2: float,
    y2: float,
    z2: float,
    u_global: NDArray[np.float64],
) -> float:
    """Axial force (tension positive) from the 6-vector of global end displacements."""
    cx, cy, cz, length = truss3d_direction_cosines(x1, y1, z1, x2, y2, z2)
    n = np.array([cx, cy, cz], dtype=np.float64)
    u1, u2 = np.asarray(u_global[:3]), np.asarray(u_global[3:])
    elongation = float(n @ (u2 - u1))
    return e * a / length * elongation
