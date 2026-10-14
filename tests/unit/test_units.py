from __future__ import annotations

import pytest

from structnode.core.units import Units, force_to_si, length_to_si


def test_kgf_converts_at_standard_gravity() -> None:
    assert force_to_si(1.0, "kgf") == pytest.approx(9.80665)


def test_lbf_and_kip_still_convert() -> None:
    assert force_to_si(1.0, "lbf") == pytest.approx(4.4482216152605)
    assert force_to_si(1.0, "kip") == pytest.approx(4448.2216152605)


def test_length_units_unaffected() -> None:
    assert length_to_si(1.0, "mm") == pytest.approx(1e-3)


def test_units_accepts_kgf() -> None:
    Units.model_validate({"length": "m", "force": "kgf"})
