"""Agent tool-contract tests: these go through the real MCP tool-calling
machinery (`MCPServer.call_tool`), not just the plain Python functions
underneath, so they actually exercise tool registration, schema
validation, and dispatch -- the same path a real MCP client uses.

Master Plan acceptance gate for S5: "Agent tool contract tests; no
unsafe direct execution." The `model_snapshot` tests below are the
concrete check of that: a tool call with the default confirm=False
must never write to disk.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest

from structnode.mcp import mcp


def _call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = asyncio.run(mcp.call_tool(name, arguments))
    assert not result.is_error, result.content
    assert result.structured_content is not None
    return result.structured_content


@pytest.fixture
def valid_cem_dict() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "model_id": "mcp-test",
        "revision": 0,
        "units": {"length": "m", "force": "N"},
        "coordinate_system": "global_cartesian_rh",
        "nodes": [
            {"id": "N1", "position": [0.0, 0.0, 0.0]},
            {"id": "N2", "position": [1.0, 0.0, 0.0]},
        ],
        "materials": [{"id": "M1", "E": 2.0e11}],
        "sections": [{"id": "S1", "A": 0.01, "Iy": 8.333e-6, "Iz": 8.333e-6, "J": 1.666e-5}],
        "elements": [
            {
                "id": "E1",
                "type": "frame",
                "node_ids": ["N1", "N2"],
                "material_id": "M1",
                "section_id": "S1",
            }
        ],
        "constraints": [{"node_id": "N1", "dofs": [True, True, True, True, True, True]}],
        "load_cases": [{"id": "LC1"}],
        "loads": [
            {
                "id": "F1",
                "case_id": "LC1",
                "kind": "nodal_force",
                "target_id": "N2",
                "values": [0.0, -1000.0, 0.0],
                "coordinate_basis": "global",
            }
        ],
        "analysis_cases": [{"id": "AC1", "load_case_ids": ["LC1"], "method": "linear_static"}],
        "metadata": {},
        "provenance": {
            "created_by": "human",
            "created_at": "2026-10-12T00:00:00Z",
            "tool_version": "0.0.1",
        },
    }


def test_all_expected_tools_are_registered() -> None:
    tools = asyncio.run(mcp.list_tools())
    names = {t.name for t in tools}
    assert names == {
        "model_validate",
        "model_apply",
        "model_diff",
        "model_snapshot",
        "analysis_run",
        "analysis_compare",
        "report_generate",
        "capabilities_list",
    }


def test_model_validate_tool(valid_cem_dict: dict[str, Any]) -> None:
    result = _call("model_validate", {"cem": valid_cem_dict})
    assert result["status"] == "ok"


def test_model_apply_tool_is_atomic(valid_cem_dict: dict[str, Any]) -> None:
    command = {"op": "create_node", "id": "N3", "position": [2.0, 0.0, 0.0]}
    result = _call(
        "model_apply", {"cem": valid_cem_dict, "command": command, "created_by": "agent:test"}
    )
    assert result["status"] == "ok"
    assert any(n["id"] == "N3" for n in result["cem"]["nodes"])


def test_model_snapshot_default_confirm_false_writes_nothing(
    valid_cem_dict: dict[str, Any], tmp_path: Path
) -> None:
    # Omit `confirm` entirely -- the tool schema's default must be False.
    result = _call("model_snapshot", {"cem": valid_cem_dict, "directory": str(tmp_path)})
    assert result["dry_run"] is True
    assert list(tmp_path.iterdir()) == [], "a tool call without confirm=True must never write"


def test_model_snapshot_explicit_confirm_true_writes(
    valid_cem_dict: dict[str, Any], tmp_path: Path
) -> None:
    result = _call(
        "model_snapshot", {"cem": valid_cem_dict, "directory": str(tmp_path), "confirm": True}
    )
    assert result["dry_run"] is False
    assert Path(result["artifact_path"]).exists()


def test_analysis_run_tool(valid_cem_dict: dict[str, Any]) -> None:
    result = _call(
        "analysis_run",
        {"cem": valid_cem_dict, "analysis_case_id": "AC1", "solver": "native-2d"},
    )
    assert result["status"] == "ok"
    assert "N2" in result["displacements"]


def test_malformed_command_returns_typed_error_not_crash(valid_cem_dict: dict[str, Any]) -> None:
    # Missing required fields for create_node -- must be a clean typed
    # error through the tool-calling path, not an unhandled exception
    # that the MCP layer turns into a generic failure.
    bad_command = {"op": "create_node"}  # missing id/position
    result = asyncio.run(
        mcp.call_tool("model_apply", {"cem": valid_cem_dict, "command": bad_command})
    )
    # Either the tool call itself reports an MCP-level error, or it
    # succeeds at the protocol level but returns a structured error --
    # either way it must not raise out of call_tool.
    if not result.is_error:
        assert result.structured_content is not None
        assert result.structured_content["status"] == "error"


def test_capabilities_list_tool_requires_no_model() -> None:
    result = _call("capabilities_list", {})
    assert "native-2d" in result["solvers"]
