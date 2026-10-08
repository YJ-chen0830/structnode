from __future__ import annotations

from typing import Any

from structnode.core.editing import CreateNode, apply_command
from structnode.core.model import CEM, diff_cem


def test_identical_models_have_empty_diff(valid_cem_dict: dict[str, Any]) -> None:
    cem = CEM.model_validate(valid_cem_dict)
    diff = diff_cem(cem, cem)
    assert diff.is_empty


def test_added_node_shows_up_as_added(valid_cem_dict: dict[str, Any]) -> None:
    old = CEM.model_validate(valid_cem_dict)
    new = apply_command(old, CreateNode(id="N3", position=(3.0, 0.0, 0.0)), created_by="human")

    diff = diff_cem(old, new)
    assert diff.nodes.added == ["N3"]
    assert diff.nodes.removed == []
    assert diff.nodes.changed == []
    assert not diff.is_empty


def test_changed_material_shows_up_as_changed(valid_cem_dict: dict[str, Any]) -> None:
    old = CEM.model_validate(valid_cem_dict)
    data = old.model_dump(mode="json")
    data["materials"][0]["E"] = old.materials[0].E * 2
    data["revision"] += 1
    new = CEM.model_validate(data)

    diff = diff_cem(old, new)
    assert diff.materials.changed == ["M1"]
    assert diff.materials.added == []


def test_removed_material_shows_up_as_removed(valid_cem_dict: dict[str, Any]) -> None:
    old = CEM.model_validate(valid_cem_dict)
    # Removing M1 outright would break element references, so this just
    # exercises the diff primitive directly rather than via apply_command.
    data = old.model_dump(mode="json")
    data["materials"] = [{"id": "M2", "E": 1e11}]
    data["elements"][0]["material_id"] = "M2"
    data["revision"] += 1
    new = CEM.model_validate(data)

    diff = diff_cem(old, new)
    assert diff.materials.removed == ["M1"]
    assert diff.materials.added == ["M2"]


def test_diff_to_dict_shape(valid_cem_dict: dict[str, Any]) -> None:
    old = CEM.model_validate(valid_cem_dict)
    new = apply_command(old, CreateNode(id="N3", position=(3.0, 0.0, 0.0)), created_by="human")
    as_dict = diff_cem(old, new).to_dict()
    assert set(as_dict) == {
        "nodes",
        "materials",
        "sections",
        "elements",
        "constraints",
        "load_cases",
        "loads",
        "analysis_cases",
    }
    assert as_dict["nodes"] == {"added": ["N3"], "removed": [], "changed": []}
