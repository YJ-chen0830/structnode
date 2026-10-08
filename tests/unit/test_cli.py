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
