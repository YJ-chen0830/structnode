"""Markdown report rendering from an `analyze` results JSON payload
(docs/MASTER_PLAN.md section 5: `report.generate` /
`structnode report ... --format markdown`).

This module only formats numbers the solver already produced -- it
never recomputes, rounds for "nicer" values, or infers anything not
already in the results payload.
"""

from __future__ import annotations

from typing import Any

_DISCLAIMER = "> **EXPERIMENTAL -- NOT FOR ENGINEERING DESIGN WITHOUT INDEPENDENT REVIEW**"


def _ordered_components(table: dict[str, dict[str, float]]) -> list[str]:
    """Column order: first-seen order across rows, not sorted -- so it
    matches the solver's own DOF ordering (Ux,Uy,Uz,Rx,Ry,Rz, ...)."""
    seen: list[str] = []
    for row in table.values():
        for key in row:
            if key not in seen:
                seen.append(key)
    return seen


def _fmt(value: float | None) -> str:
    return "" if value is None else f"{value:.6g}"


def _render_table(title: str, row_label: str, table: dict[str, dict[str, float]]) -> list[str]:
    if not table:
        return []
    components = _ordered_components(table)
    lines = [f"## {title}", "", f"| {row_label} | " + " | ".join(components) + " |"]
    lines.append("|" + "---|" * (len(components) + 1))
    for key, row in table.items():
        cells = " | ".join(_fmt(row.get(c)) for c in components)
        lines.append(f"| {key} | {cells} |")
    lines.append("")
    return lines


def render_markdown_report(results: dict[str, Any]) -> str:
    solver_line = f"{results.get('solver_name', '?')} {results.get('solver_version', '')}".rstrip()
    lines: list[str] = [
        "# StructNode Analysis Report",
        "",
        _DISCLAIMER,
        "",
        "## Summary",
        "",
        f"- Analysis case: `{results.get('analysis_case_id', '?')}`",
        f"- Element kind: `{results.get('element_kind', '?')}`",
        f"- Solver: `{solver_line}`",
        f"- Model hash: `{results.get('model_hash', '?')}`",
        "",
    ]

    warnings = results.get("warnings") or []
    if warnings:
        lines += ["## Warnings", ""]
        lines += [f"- {w}" for w in warnings]
        lines.append("")

    lines += _render_table("Displacements", "Node", results.get("displacements", {}))
    lines += _render_table("Reactions", "Node", results.get("reactions", {}))
    lines += _render_table("Element end forces", "Element", results.get("element_forces", {}))

    return "\n".join(lines) + "\n"
