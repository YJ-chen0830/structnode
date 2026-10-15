"""Scope guards shared by the 2D and 3D assemblers."""

from __future__ import annotations

from structnode.core.model import CEM
from structnode.fem.assembly.errors import UnsupportedModelError


def require_no_end_releases(cem: CEM, solver_label: str) -> None:
    """Frame end releases are part of the CEM schema but no native solver
    condenses them out yet. Assembling a released element as fully rigid
    would silently produce wrong moments, so reject instead. An all-False
    releases tuple is equivalent to no releases and is accepted."""
    offenders = [el.id for el in cem.elements if el.releases is not None and any(el.releases)]
    if offenders:
        raise UnsupportedModelError(
            f"{solver_label} does not support frame end releases yet; "
            f"elements with releases: {offenders}"
        )
