"""Shared exception for both the 2D and 3D native assembly/solver
scope guards, so callers (CLI, future REST/MCP) only ever need to
catch one type regardless of which dimensionality handled the model.
"""

from __future__ import annotations


class UnsupportedModelError(Exception):
    """Raised when a CEM model is outside a native solver's scope."""
