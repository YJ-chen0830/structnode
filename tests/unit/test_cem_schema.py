"""S0 schema-level tests: valid model + the required negative cases
(missing node, duplicate ID, zero length, missing units, invalid
modulus, unsupported feature)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from structnode.core.model import CEM


def test_valid_model_parses(valid_cem_dict: dict[str, Any]) -> None:
    cem = CEM.model_validate(valid_cem_dict)
    assert cem.model_id == "unit-test-model"
    assert len(cem.nodes) == 2
    assert cem.content_hash  # non-empty hex digest


def test_missing_node_reference_rejected(valid_cem_dict: dict[str, Any]) -> None:
    # Element referencing a node that doesn't exist in `nodes` is a
    # *topology* error, not a schema error -- schema only knows about
    # per-model shape, not cross-collection references. Covered in
    # test_topology.py. Here we check the schema-level analogue: an
    # element's own node_ids tuple must have two distinct entries.
    valid_cem_dict["elements"][0]["node_ids"] = ["N1", "N1"]
    with pytest.raises(ValidationError):
        CEM.model_validate(valid_cem_dict)


def test_duplicate_node_id_rejected(valid_cem_dict: dict[str, Any]) -> None:
    valid_cem_dict["nodes"].append({"id": "N1", "position": [2.0, 0.0, 0.0]})
    with pytest.raises(ValidationError, match="Duplicate node id"):
        CEM.model_validate(valid_cem_dict)


def test_duplicate_element_id_rejected(valid_cem_dict: dict[str, Any]) -> None:
    valid_cem_dict["elements"].append(dict(valid_cem_dict["elements"][0]))
    with pytest.raises(ValidationError, match="Duplicate element id"):
        CEM.model_validate(valid_cem_dict)


def test_missing_units_field_rejected(valid_cem_dict: dict[str, Any]) -> None:
    del valid_cem_dict["units"]
    with pytest.raises(ValidationError):
        CEM.model_validate(valid_cem_dict)


def test_invalid_unit_value_rejected(valid_cem_dict: dict[str, Any]) -> None:
    valid_cem_dict["units"]["length"] = "furlong"
    with pytest.raises(ValidationError):
        CEM.model_validate(valid_cem_dict)


def test_nonpositive_modulus_rejected(valid_cem_dict: dict[str, Any]) -> None:
    valid_cem_dict["materials"][0]["E"] = -1.0
    with pytest.raises(ValidationError):
        CEM.model_validate(valid_cem_dict)


def test_inconsistent_isotropic_material_rejected(valid_cem_dict: dict[str, Any]) -> None:
    # E, G, nu given but not mutually consistent (>0.1% relative error).
    valid_cem_dict["materials"][0]["G"] = 1e9
    valid_cem_dict["materials"][0]["nu"] = 0.3
    with pytest.raises(ValidationError, match="inconsistent"):
        CEM.model_validate(valid_cem_dict)


def test_unsupported_element_type_rejected(valid_cem_dict: dict[str, Any]) -> None:
    valid_cem_dict["elements"][0]["type"] = "shell"  # not in CEM v0.1 scope
    with pytest.raises(ValidationError):
        CEM.model_validate(valid_cem_dict)


def test_truss_element_cannot_declare_releases(valid_cem_dict: dict[str, Any]) -> None:
    valid_cem_dict["elements"][0]["type"] = "truss"
    valid_cem_dict["elements"][0]["releases"] = [False] * 12
    with pytest.raises(ValidationError, match="must not declare releases"):
        CEM.model_validate(valid_cem_dict)


def test_frame_releases_must_have_twelve_entries(valid_cem_dict: dict[str, Any]) -> None:
    valid_cem_dict["elements"][0]["releases"] = [False] * 6  # wrong length
    with pytest.raises(ValidationError, match="12 entries"):
        CEM.model_validate(valid_cem_dict)
