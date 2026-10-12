"""3D Euler-Bernoulli frame element stiffness (no shear deformation).

DOF order per node: (u, v, w, theta_x, theta_y, theta_z) -- 3
translations + 3 rotations in the member's *local* axes once
transformed; globally, the usual 6 CEM DOFs.

Local-axis convention: local x runs node1->node2. The local y/z pair is
resolved from a reference vector (`FrameSection.local_axis_hint` when
given) via `local_y = normalize(ref x local_x)`, `local_z = local_x x
local_y` -- always a valid right-handed orthonormal basis as long as
`ref` isn't parallel to the member. When no hint is given we fall back
to global Z as the reference (global Y if the member is itself
near-parallel to global Z) and report that fallback as a warning, per
docs/MASTER_PLAN.md section 3 ("adapters/solvers fall back to a
default rule ... and MUST report that fallback as a warning").

Bending about local z uses `section.Iz` (deflection in local y);
bending about local y uses `section.Iy` (deflection in local z). The
two blocks' off-diagonal coupling terms have opposite sign patterns --
not a typo: (x, y, z) and (x, z, y) are opposite-handed orderings, so
the two bending planes' moment-rotation relationships mirror each
other. This is the standard 3D frame stiffness (e.g. Przemieniecki,
*Theory of Matrix Structural Analysis*).
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

_GLOBAL_Z = np.array([0.0, 0.0, 1.0])
_GLOBAL_Y = np.array([0.0, 1.0, 0.0])
_NEAR_PARALLEL_COS = 0.999
_MIN_CROSS_NORM = 1e-9


class DegenerateLocalAxisError(Exception):
    """`local_axis_hint` is parallel (or near-parallel) to the member axis."""


def frame3d_local_axes(
    x1: float,
    y1: float,
    z1: float,
    x2: float,
    y2: float,
    z2: float,
    local_axis_hint: tuple[float, float, float] | None,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], float, str | None]:
    """Returns (local_x, local_y, local_z, length, fallback_warning)."""
    dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    local_x = np.array([dx, dy, dz], dtype=np.float64) / length

    warning: str | None = None
    if local_axis_hint is not None:
        ref = np.asarray(local_axis_hint, dtype=np.float64)
        ref_norm = float(np.linalg.norm(ref))
        if ref_norm < _MIN_CROSS_NORM:
            raise DegenerateLocalAxisError("local_axis_hint must not be a zero vector")
        ref = ref / ref_norm
    elif abs(float(local_x @ _GLOBAL_Z)) > _NEAR_PARALLEL_COS:
        ref = _GLOBAL_Y
        warning = (
            "no local_axis_hint and member is near-parallel to global Z; "
            "defaulted local-axis reference to global Y"
        )
    else:
        ref = _GLOBAL_Z
        warning = "no local_axis_hint; defaulted local-axis reference to global Z"

    cross = np.cross(ref, local_x)
    cross_norm = float(np.linalg.norm(cross))
    if cross_norm < _MIN_CROSS_NORM:
        raise DegenerateLocalAxisError(
            "local_axis_hint is parallel to the member axis; cannot resolve orientation"
        )
    local_y = cross / cross_norm
    local_z = np.cross(local_x, local_y)

    return local_x, local_y, local_z, length, warning


def frame3d_local_stiffness(
    e: float, g: float, a: float, iy: float, iz: float, j: float, length: float
) -> NDArray[np.float64]:
    """12x12 local stiffness, DOF order (u1,v1,w1,tx1,ty1,tz1,u2,v2,w2,tx2,ty2,tz2)."""
    length_ = length
    ea_l = e * a / length_
    gj_l = g * j / length_

    bz1, bz2, bz3, bz4 = (
        12.0 * e * iz / length_**3,
        6.0 * e * iz / length_**2,
        4.0 * e * iz / length_,
        2.0 * e * iz / length_,
    )
    by1, by2, by3, by4 = (
        12.0 * e * iy / length_**3,
        6.0 * e * iy / length_**2,
        4.0 * e * iy / length_,
        2.0 * e * iy / length_,
    )

    k = np.zeros((12, 12), dtype=np.float64)

    k[0, 0] = k[6, 6] = ea_l
    k[0, 6] = k[6, 0] = -ea_l

    k[3, 3] = k[9, 9] = gj_l
    k[3, 9] = k[9, 3] = -gj_l

    # z-bending: v (1, 7), theta_z (5, 11)
    k[1, 1] = k[7, 7] = bz1
    k[1, 7] = k[7, 1] = -bz1
    k[1, 5] = k[5, 1] = bz2
    k[1, 11] = k[11, 1] = bz2
    k[7, 5] = k[5, 7] = -bz2
    k[7, 11] = k[11, 7] = -bz2
    k[5, 5] = k[11, 11] = bz3
    k[5, 11] = k[11, 5] = bz4

    # y-bending: w (2, 8), theta_y (4, 10) -- opposite coupling sign vs z-bending
    k[2, 2] = k[8, 8] = by1
    k[2, 8] = k[8, 2] = -by1
    k[2, 4] = k[4, 2] = -by2
    k[2, 10] = k[10, 2] = -by2
    k[8, 4] = k[4, 8] = by2
    k[8, 10] = k[10, 8] = by2
    k[4, 4] = k[10, 10] = by3
    k[4, 10] = k[10, 4] = by4

    return k


def frame3d_transform_matrix(
    local_x: NDArray[np.float64], local_y: NDArray[np.float64], local_z: NDArray[np.float64]
) -> NDArray[np.float64]:
    """12x12 block-rotation matrix T such that u_local = T @ u_global."""
    r = np.vstack([local_x, local_y, local_z])
    t = np.zeros((12, 12), dtype=np.float64)
    for block in range(4):
        t[3 * block : 3 * block + 3, 3 * block : 3 * block + 3] = r
    return t


def frame3d_global_stiffness(
    e: float,
    g: float,
    a: float,
    iy: float,
    iz: float,
    j: float,
    x1: float,
    y1: float,
    z1: float,
    x2: float,
    y2: float,
    z2: float,
    local_axis_hint: tuple[float, float, float] | None,
) -> tuple[NDArray[np.float64], str | None]:
    """Returns (12x12 global stiffness, fallback_warning_or_None)."""
    local_x, local_y, local_z, length, warning = frame3d_local_axes(
        x1, y1, z1, x2, y2, z2, local_axis_hint
    )
    k_local = frame3d_local_stiffness(e, g, a, iy, iz, j, length)
    t = frame3d_transform_matrix(local_x, local_y, local_z)
    return t.T @ k_local @ t, warning


def frame3d_local_end_forces(
    e: float,
    g: float,
    a: float,
    iy: float,
    iz: float,
    j: float,
    x1: float,
    y1: float,
    z1: float,
    x2: float,
    y2: float,
    z2: float,
    local_axis_hint: tuple[float, float, float] | None,
    u_global: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Local end forces (N1,Vy1,Vz1,T1,My1,Mz1, N2,Vy2,Vz2,T2,My2,Mz2)."""
    local_x, local_y, local_z, length, _ = frame3d_local_axes(
        x1, y1, z1, x2, y2, z2, local_axis_hint
    )
    k_local = frame3d_local_stiffness(e, g, a, iy, iz, j, length)
    t = frame3d_transform_matrix(local_x, local_y, local_z)
    u_local = t @ np.asarray(u_global, dtype=np.float64)
    return np.asarray(k_local @ u_local, dtype=np.float64)
