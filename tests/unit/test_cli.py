from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from structnode.cli.main import app

runner = CliRunner()
EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "cantilever.cem.json"


def test_model_validate_example_fixture_ok() -> None:
    result = runner.invoke(app, ["model", "validate", str(EXAMPLE), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["errors"] == []
    assert payload["model_hash"]


def test_model_validate_rejects_bad_json(tmp_path: Path) -> None:
    bad = tmp_path / "broken.cem.json"
    bad.write_text("{ not valid json", encoding="utf-8")
    result = runner.invoke(app, ["model", "validate", str(bad), "--json"])
    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert payload["errors"][0]["code"] == "CEM-SCHEMA-INVALID_JSON"


def test_model_validate_reports_topology_error(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["constraints"] = []  # now an unrestrained mechanism
    broken = tmp_path / "unstable.cem.json"
    broken.write_text(json.dumps(data), encoding="utf-8")

    result = runner.invoke(app, ["model", "validate", str(broken), "--json"])
    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert any(e["code"] == "CEM-STAB-NOSUPPORT" for e in payload["errors"])


def test_model_apply_writes_new_revision(tmp_path: Path) -> None:
    command_path = tmp_path / "command.json"
    command_path.write_text(
        json.dumps({"op": "create_node", "id": "N3", "position": [3.0, 0.0, 0.0]}),
        encoding="utf-8",
    )
    out = tmp_path / "out.cem.json"

    result = runner.invoke(
        app,
        ["model", "apply", str(EXAMPLE), str(command_path), "--out", str(out), "--json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["artifact_paths"] == [str(out)]
    assert out.exists()

    new_data = json.loads(out.read_text(encoding="utf-8"))
    assert any(n["id"] == "N3" for n in new_data["nodes"])
    original_revision = json.loads(EXAMPLE.read_text(encoding="utf-8"))["revision"]
    assert new_data["revision"] == original_revision + 1


def test_model_apply_rejects_bad_command_leaves_out_untouched(tmp_path: Path) -> None:
    command_path = tmp_path / "command.json"
    command_path.write_text(
        json.dumps(
            {
                "op": "create_element",
                "id": "E404",
                "type": "truss",
                "node_ids": ["N1", "N404"],
                "material_id": "M1",
                "section_id": "S1",
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out.cem.json"

    result = runner.invoke(
        app,
        ["model", "apply", str(EXAMPLE), str(command_path), "--out", str(out), "--json"],
    )
    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["status"] == "error"
    assert any(e["code"] == "CEM-REF-NODE" for e in payload["errors"])
    assert not out.exists()


def test_model_diff_detects_added_node(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["nodes"].append({"id": "N3", "position": [3.0, 0.0, 0.0]})
    data["revision"] += 1
    other = tmp_path / "other.cem.json"
    other.write_text(json.dumps(data), encoding="utf-8")

    result = runner.invoke(app, ["model", "diff", str(EXAMPLE), str(other), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["diff"]["nodes"]["added"] == ["N3"]


def test_model_snapshot_writes_content_addressed_file(tmp_path: Path) -> None:
    snap_dir = tmp_path / "snapshots"
    result = runner.invoke(
        app, ["model", "snapshot", str(EXAMPLE), "--dir", str(snap_dir), "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    snapshot_path = Path(payload["artifact_paths"][0])
    assert snapshot_path.exists()
    assert snapshot_path.name == f"{payload['model_hash']}.cem.json"


def test_analyze_native_solver_writes_results(tmp_path: Path) -> None:
    out_dir = tmp_path / "out"
    result = runner.invoke(
        app, ["analyze", str(EXAMPLE), "--solver", "native", "--output", str(out_dir), "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["artifact_paths"] == [str(out_dir / "results_AC1.json")]

    results = json.loads((out_dir / "results_AC1.json").read_text(encoding="utf-8"))
    assert results["solver_name"] == "structnode-native-2d"
    assert "N2" in results["displacements"]
    assert "N1" in results["reactions"]
    assert "E1" in results["element_forces"]


def test_analyze_unimplemented_solver_rejected(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["analyze", str(EXAMPLE), "--solver", "opensees", "--output", str(tmp_path), "--json"],
    )
    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["errors"][0]["code"] == "CEM-SOLVER-UNIMPLEMENTED"


def test_analyze_rejects_mixed_element_model(tmp_path: Path) -> None:
    data = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    data["elements"].append(
        {
            "id": "E2",
            "type": "truss",
            "node_ids": ["N1", "N2"],
            "material_id": "M1",
            "section_id": "S1",
        }
    )
    mixed = tmp_path / "mixed.cem.json"
    mixed.write_text(json.dumps(data), encoding="utf-8")

    result = runner.invoke(
        app, ["analyze", str(mixed), "--solver", "native", "--output", str(tmp_path), "--json"]
    )
    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["errors"][0]["code"] == "CEM-SOLVER-UNSUPPORTEDMODELERROR"
