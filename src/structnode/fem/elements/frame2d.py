"""2D Euler-Bernoulli frame element stiffness (no shear deformation).

DOF order per node: (u, v, theta) -- translation in global X, Y plus
in-plane rotation about the global Z axis (right-hand rule: positive
counterclockwise). In-plane bending uses `section.Iz` -- `Iy` is a 3D
property and is not used by this 2D solver; see
docs/MASTER_PLAN.md section 3 (CEM v0.1 exclusions carry forward: no
shear deformation).
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from structnode.fem.elements.truss2d import truss2d_direction_cosines


def frame2d_local_stiffness(e: float, a: float, iz: float, length: float) -> NDArray[np.float64]:
    """6x6 local stiffness, DOF order (u1, v1, t1, u2, v2, t2)."""
    ea_l = e * a / length
    ei_l3 = 12.0 * e * iz / length**3
    ei_l2 = 6.0 * e * iz / length**2
    ei_l = e * iz / length

    return np.array(
        [
            [ea_l, 0.0, 0.0, -ea_l, 0.0, 0.0],
            [0.0, ei_l3, ei_l2, 0.0, -ei_l3, ei_l2],
            [0.0, ei_l2, 4.0 * ei_l, 0.0, -ei_l2, 2.0 * ei_l],
            [-ea_l, 0.0, 0.0, ea_l, 0.0, 0.0],
            [0.0, -ei_l3, -ei_l2, 0.0, ei_l3, -ei_l2],
            [0.0, ei_l2, 2.0 * ei_l, 0.0, -ei_l2, 4.0 * ei_l],
        ],
        dtype=np.float64,
    )


def frame2d_transform_matrix(c: float, s: float) -> NDArray[np.float64]:
    """6x6 block-rotation matrix T such that u_local = T @ u_global."""
    block = np.array([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    t = np.zeros((6, 6), dtype=np.float64)
    t[:3, :3] = block
    t[3:, 3:] = block
    return t


def frame2d_global_stiffness(
    e: float, a: float, iz: float, x1: float, y1: float, x2: float, y2: float
) -> NDArray[np.float64]:
    """6x6 global stiffness, DOF order (u1, v1, t1, u2, v2, t2)."""
    c, s, length = truss2d_direction_cosines(x1, y1, x2, y2)
    k_local = frame2d_local_stiffness(e, a, iz, length)
    t = frame2d_transform_matrix(c, s)
    return t.T @ k_local @ t


def frame2d_local_end_forces(
    e: float,
    a: float,
    iz: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    u_global: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Local end forces (N1, V1, M1, N2, V2, M2) from global end displacements."""
    c, s, length = truss2d_direction_cosines(x1, y1, x2, y2)
    k_local = frame2d_local_stiffness(e, a, iz, length)
    t = frame2d_transform_matrix(c, s)
    u_local = t @ np.asarray(u_global, dtype=np.float64)
    return np.asarray(k_local @ u_local, dtype=np.float64)
