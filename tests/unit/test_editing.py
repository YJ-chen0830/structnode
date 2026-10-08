from __future__ import annotations

from typing import Any

import pytest

from structnode.core.editing import (
    ApplyLoad,
    AssignSupport,
    CommandRejected,
    CreateElement,
    CreateFrameSection,
    CreateLoadCase,
    CreateMaterial,
    CreateNode,
    apply_command,
)
from structnode.core.model import CEM


def test_create_node_bumps_revision_and_provenance(valid_cem_dict: dict[str, Any]) -> None:
    cem = CEM.model_validate(valid_cem_dict)
    original_hash = cem.content_hash

    new_cem = apply_command(
        cem, CreateNode(id="N3", position=(2.0, 0.0, 0.0)), created_by="agent:test"
    )

    assert len(new_cem.nodes) == 3
    assert new_cem.revision == cem.revision + 1
    assert new_cem.provenance.created_by == "agent:test"
    assert new_cem.provenance.parent_revision == original_hash
    # original untouched
    assert len(cem.nodes) == 2
    assert cem.content_hash == original_hash


def test_create_material_and_section(valid_cem_dict: dict[str, Any]) -> None:
    cem = CEM.model_validate(valid_cem_dict)
    cem = apply_command(cem, CreateMaterial(id="M2", E=1e11), created_by="human")
    cem = apply_command(
        cem,
        CreateFrameSection(id="S2", A=0.02, Iy=1e-5, Iz=1e-5, J=2e-5),
        created_by="human",
    )
    assert {m.id for m in cem.materials} == {"M1", "M2"}
    assert {s.id for s in cem.sections} == {"S1", "S2"}


def test_create_element_referencing_new_nodes(valid_cem_dict: dict[str, Any]) -> None:
    cem = CEM.model_validate(valid_cem_dict)
    cem = apply_command(cem, CreateNode(id="N3", position=(2.0, 0.0, 0.0)), created_by="human")
    cem = apply_command(
        cem,
        CreateElement(
            id="E2", type="truss", node_ids=("N2", "N3"), material_id="M1", section_id="S1"
        ),
        created_by="human",
    )
    assert any(e.id == "E2" for e in cem.elements)


def test_assign_support_and_apply_load(valid_cem_dict: dict[str, Any]) -> None:
    cem = CEM.model_validate(valid_cem_dict)
    cem = apply_command(
        cem,
        AssignSupport(node_id="N2", dofs=(True, True, True, False, False, False)),
        created_by="human",
    )
    cem = apply_command(
        cem, CreateLoadCase(id="LC2", description="second case"), created_by="human"
    )
    cem = apply_command(
        cem,
        ApplyLoad(
            id="F2",
            case_id="LC2",
            kind="nodal_force",
            target_id="N1",
            values=(10.0, 0.0, 0.0),
            coordinate_basis="global",
        ),
        created_by="human",
    )
    assert len(cem.constraints) == 2
    assert any(lc.id == "LC2" for lc in cem.load_cases)
    assert any(load.id == "F2" for load in cem.loads)


def test_command_referencing_unknown_node_is_rejected(valid_cem_dict: dict[str, Any]) -> None:
    cem = CEM.model_validate(valid_cem_dict)
    original_hash = cem.content_hash

    with pytest.raises(CommandRejected) as exc_info:
        apply_command(
            cem,
            CreateElement(
                id="E2", type="truss", node_ids=("N1", "N404"), material_id="M1", section_id="S1"
            ),
            created_by="human",
        )

    assert any(f["code"] == "CEM-REF-NODE" for f in exc_info.value.findings)
    # rejected command must not mutate the input model
    assert cem.content_hash == original_hash
    assert len(cem.elements) == 1


def test_schema_level_rejection_is_normalized_to_dicts(valid_cem_dict: dict[str, Any]) -> None:
    cem = CEM.model_validate(valid_cem_dict)
    with pytest.raises(CommandRejected) as exc_info:
        apply_command(cem, CreateMaterial(id="M1", E=1e11), created_by="human")  # dup id

    finding = exc_info.value.findings[0]
    assert set(finding) == {"code", "severity", "message", "path"}
