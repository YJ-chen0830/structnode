from __future__ import annotations

from structnode.reporting import render_markdown_report


def _sample_results() -> dict:
    return {
        "analysis_case_id": "AC1",
        "element_kind": "frame",
        "solver_name": "structnode-native-2d",
        "solver_version": "0.1.0",
        "model_hash": "abc123",
        "displacements": {"N2": {"Ux": 0.0, "Uy": -0.0002, "Rz": -0.0003}},
        "reactions": {"N1": {"Fx": 0.0, "Fy": 1000.0, "Mz": 1000.0}},
        "element_forces": {"E1": {"N1": 0.0, "V1": 1000.0, "M1": 1000.0}},
        "warnings": [],
    }


def test_report_includes_disclaimer_and_summary_fields() -> None:
    md = render_markdown_report(_sample_results())
    assert "EXPERIMENTAL" in md
    assert "AC1" in md
    assert "structnode-native-2d" in md
    assert "abc123" in md


def test_report_renders_tables_with_consistent_column_order() -> None:
    md = render_markdown_report(_sample_results())
    assert "## Displacements" in md
    assert "| Node | Ux | Uy | Rz |" in md
    assert "| N2 | 0 | -0.0002 | -0.0003 |" in md
    assert "## Reactions" in md
    assert "| N1 | 0 | 1000 | 1000 |" in md
    assert "## Element end forces" in md


def test_report_omits_empty_sections() -> None:
    results = _sample_results()
    results["reactions"] = {}
    md = render_markdown_report(results)
    assert "## Reactions" not in md


def test_report_lists_warnings() -> None:
    results = _sample_results()
    results["warnings"] = ["no local_axis_hint; defaulted to global Z"]
    md = render_markdown_report(results)
    assert "## Warnings" in md
    assert "defaulted to global Z" in md
