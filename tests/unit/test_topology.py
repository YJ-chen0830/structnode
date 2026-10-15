from __future__ import annotations

from typing import Any

from structnode.core.model import CEM
from structnode.core.validation import validate_topology


def test_valid_model_has_no_findings(valid_cem_dict: dict[str, Any]) -> None:
    cem = CEM.model_validate(valid_cem_dict)
    result = validate_topology(cem)
    assert result.ok
    assert result.errors == []


def test_dangling_support_reference_is_error(valid_cem_dict: dict[str, Any]) -> None:
    valid_cem_dict["constraints"].append({"node_id": "N404", "dofs": [True] * 6})
    cem = CEM.model_validate(valid_cem_dict)
    result = validate_topology(cem)
    assert not result.ok
    assert any(f.code == "CEM-REF-NODE" for f in result.errors)


def test_dangling_load_case_reference_is_error(valid_cem_dict: dict[str, Any]) -> None:
    valid_cem_dict["loads"][0]["case_id"] = "LC404"
    cem = CEM.model_validate(valid_cem_dict)
    result = validate_topology(cem)
    assert not result.ok
    assert any(f.code == "CEM-REF-LOADCASE" for f in result.errors)


def test_zero_length_element_is_error(valid_cem_dict: dict[str, Any]) -> None:
    valid_cem_dict["nodes"][1]["position"] = [0.0, 0.0, 0.0]  # coincide with N1
    cem = CEM.model_validate(valid_cem_dict)
    result = validate_topology(cem)
    assert not result.ok
    assert any(f.code == "CEM-GEOM-ZEROLEN" for f in result.errors)
    assert any(f.code == "CEM-GEOM-COINCIDENT" for f in result.warnings)


def test_unrestrained_model_is_unstable(valid_cem_dict: dict[str, Any]) -> None:
    valid_cem_dict["constraints"] = []
    cem = CEM.model_validate(valid_cem_dict)
    result = validate_topology(cem)
    assert not result.ok
    assert any(f.code == "CEM-STAB-NOSUPPORT" for f in result.errors)


def test_rotation_only_support_is_still_unstable(valid_cem_dict: dict[str, Any]) -> None:
    # Restraining only rotational DOFs leaves the body free to translate.
    valid_cem_dict["constraints"][0]["dofs"] = [False, False, False, True, True, True]
    cem = CEM.model_validate(valid_cem_dict)
    result = validate_topology(cem)
    assert not result.ok
    assert any(f.code == "CEM-STAB-NOSUPPORT" for f in result.errors)


def test_dangling_rebar_material_reference_is_error(valid_cem_dict: dict[str, Any]) -> None:
    valid_cem_dict["sections"][0]["rebar"] = {
        "material_id": "REBAR404",
        "bars": [{"y": 0.0, "z": 0.0, "diameter": 0.02}],
    }
    cem = CEM.model_validate(valid_cem_dict)
    result = validate_topology(cem)
    assert not result.ok
    assert any(f.code == "CEM-REF-REBAR-MATERIAL" for f in result.errors)


def test_rebar_modulus_not_greater_than_element_material_is_warning(
    valid_cem_dict: dict[str, Any],
) -> None:
    # M1's E is 2e11 (steel-range); give the "rebar" an even lower E so
    # n <= 1 -- almost certainly the wrong material was picked.
    valid_cem_dict["materials"].append({"id": "WEAK", "E": 1e10})
    valid_cem_dict["sections"][0]["rebar"] = {
        "material_id": "WEAK",
        "bars": [{"y": 0.0, "z": 0.0, "diameter": 0.02}],
    }
    cem = CEM.model_validate(valid_cem_dict)
    result = validate_topology(cem)
    assert result.ok  # a warning, not an error
    assert any(f.code == "CEM-REBAR-LOW-MODULUS" for f in result.warnings)


def _gravity_load(target_id: str) -> dict[str, Any]:
    return {
        "id": "SW",
        "case_id": "LC1",
        "kind": "gravity",
        "target_id": target_id,
        "values": [0.0, -9.81, 0.0],
        "coordinate_basis": "global",
    }


def test_gravity_unknown_element_target_is_error(valid_cem_dict: dict[str, Any]) -> None:
    valid_cem_dict["loads"].append(_gravity_load("NOPE"))
    result = validate_topology(CEM.model_validate(valid_cem_dict))
    assert any(f.code == "CEM-REF-ELEMENT" for f in result.errors)


def test_gravity_all_elements_target_is_valid(valid_cem_dict: dict[str, Any]) -> None:
    valid_cem_dict["loads"].append(_gravity_load("*"))
    result = validate_topology(CEM.model_validate(valid_cem_dict))
    assert not any(f.code == "CEM-REF-ELEMENT" for f in result.errors)
