"""Shared exceptions for both the 2D and 3D native solvers, so callers
only ever need to catch one type regardless of which dimensionality
handled the model.
"""

from __future__ import annotations


class AnalysisCaseNotFoundError(Exception):
    pass


class SingularStiffnessError(Exception):
    """The free-DOF stiffness submatrix is singular/ill-conditioned --
    an unrestrained mechanism or rigid-body mode that the coarse
    topology check did not catch for this specific geometry."""
