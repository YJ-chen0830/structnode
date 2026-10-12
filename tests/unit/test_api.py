from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from structnode.api import app

client = TestClient(app)


@pytest.fixture
def valid_cem_dict() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "model_id": "api-test",
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


def test_models_validate_ok(valid_cem_dict: dict[str, Any]) -> None:
    resp = client.post("/models/validate", json={"cem": valid_cem_dict})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_models_apply(valid_cem_dict: dict[str, Any]) -> None:
    command = {"op": "create_node", "id": "N3", "position": [2.0, 0.0, 0.0]}
    resp = client.post(
        "/models/apply", json={"cem": valid_cem_dict, "command": command, "created_by": "api"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert any(n["id"] == "N3" for n in body["cem"]["nodes"])


def test_models_snapshot_default_confirm_false_writes_nothing(
    valid_cem_dict: dict[str, Any], tmp_path: Path
) -> None:
    resp = client.post("/models/snapshot", json={"cem": valid_cem_dict, "directory": str(tmp_path)})
    assert resp.status_code == 200
    body = resp.json()
    assert body["dry_run"] is True
    assert list(tmp_path.iterdir()) == []


def test_models_snapshot_confirm_true_writes(
    valid_cem_dict: dict[str, Any], tmp_path: Path
) -> None:
    resp = client.post(
        "/models/snapshot",
        json={"cem": valid_cem_dict, "directory": str(tmp_path), "confirm": True},
    )
    body = resp.json()
    assert body["dry_run"] is False
    assert Path(body["artifact_path"]).exists()


def test_analysis_run(valid_cem_dict: dict[str, Any]) -> None:
    resp = client.post(
        "/analysis/run",
        json={"cem": valid_cem_dict, "analysis_case_id": "AC1", "solver": "native-2d"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "N2" in body["displacements"]


def test_analysis_run_opensees_reports_unavailable(valid_cem_dict: dict[str, Any]) -> None:
    resp = client.post(
        "/analysis/run",
        json={"cem": valid_cem_dict, "analysis_case_id": "AC1", "solver": "opensees"},
    )
    body = resp.json()
    assert body["status"] == "error"
    assert body["errors"][0]["code"] == "CEM-SOLVER-OPENSEESUNAVAILABLEERROR"


def test_reports_generate(valid_cem_dict: dict[str, Any]) -> None:
    run_resp = client.post(
        "/analysis/run",
        json={"cem": valid_cem_dict, "analysis_case_id": "AC1", "solver": "native-2d"},
    )
    report_resp = client.post("/reports/generate", json={"results": run_resp.json()})
    assert report_resp.status_code == 200
    assert "EXPERIMENTAL" in report_resp.json()["content"]


def test_capabilities() -> None:
    resp = client.get("/capabilities")
    assert resp.status_code == 200
    assert "native-2d" in resp.json()["solvers"]


def test_malformed_request_body_is_422_not_500() -> None:
    resp = client.post("/models/validate", json={"not_cem": True})
    assert resp.status_code == 422
