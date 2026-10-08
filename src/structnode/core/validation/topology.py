"""Cross-field topology/engineering-sanity checks for a CEM document.

These rules need whole-model context (references across collections),
which is why they live outside the per-model `@model_validator` hooks in
`structnode.core.model.cem` -- those only enforce invariants that are
never valid regardless of the rest of the document (duplicate IDs,
non-physical properties, self-referencing elements).

Scope note: the "no support restrains any translational DOF" check here
is a coarse necessary-but-not-sufficient stability heuristic meant to
reject obviously-unsupported models before they ever reach a solver.
Full rigid-body-mode detection (e.g. a mechanism that *is* restrained
enough to pass this check but still has an internal release mechanism)
is a solver-level responsibility (Master Plan S2+), not S0 scope.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum

from structnode.core.model import CEM

ZERO_LENGTH_EPS_M = 1e-9
COINCIDENT_GRID_M = 1e-9


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str
    path: str


@dataclass
class ValidationResult:
    errors: list[Finding] = field(default_factory=list)
    warnings: list[Finding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_topology(cem: CEM) -> ValidationResult:
    errors: list[Finding] = []
    warnings: list[Finding] = []

    node_ids = {n.id for n in cem.nodes}
    material_ids = {m.id for m in cem.materials}
    section_ids = {s.id for s in cem.sections}
    element_ids = {e.id for e in cem.elements}
    load_case_ids = {lc.id for lc in cem.load_cases}
    node_by_id = {n.id: n for n in cem.nodes}

    # --- Referential integrity -------------------------------------
    for i, el in enumerate(cem.elements):
        path = f"elements[{i}]"
        for nid in el.node_ids:
            if nid not in node_ids:
                errors.append(
                    Finding(
                        "CEM-REF-NODE",
                        Severity.ERROR,
                        f"Element {el.id!r} references unknown node {nid!r}",
                        path,
                    )
                )
        if el.material_id not in material_ids:
            errors.append(
                Finding(
                    "CEM-REF-MATERIAL",
                    Severity.ERROR,
                    f"Element {el.id!r} references unknown material {el.material_id!r}",
                    path,
                )
            )
        if el.section_id not in section_ids:
            errors.append(
                Finding(
                    "CEM-REF-SECTION",
                    Severity.ERROR,
                    f"Element {el.id!r} references unknown section {el.section_id!r}",
                    path,
                )
            )

    for i, sup in enumerate(cem.constraints):
        if sup.node_id not in node_ids:
            errors.append(
                Finding(
                    "CEM-REF-NODE",
                    Severity.ERROR,
                    f"Support references unknown node {sup.node_id!r}",
                    f"constraints[{i}]",
                )
            )

    for i, load in enumerate(cem.loads):
        path = f"loads[{i}]"
        if load.case_id not in load_case_ids:
            errors.append(
                Finding(
                    "CEM-REF-LOADCASE",
                    Severity.ERROR,
                    f"Load {load.id!r} references unknown load case {load.case_id!r}",
                    path,
                )
            )
        if load.kind in ("nodal_force", "nodal_moment") and load.target_id not in node_ids:
            errors.append(
                Finding(
                    "CEM-REF-NODE",
                    Severity.ERROR,
                    f"Load {load.id!r} targets unknown node {load.target_id!r}",
                    path,
                )
            )
        if load.kind == "member_distributed" and load.target_id not in element_ids:
            errors.append(
                Finding(
                    "CEM-REF-ELEMENT",
                    Severity.ERROR,
                    f"Load {load.id!r} targets unknown element {load.target_id!r}",
                    path,
                )
            )

    for i, ac in enumerate(cem.analysis_cases):
        path = f"analysis_cases[{i}]"
        for lc_id in ac.load_case_ids:
            if lc_id not in load_case_ids:
                errors.append(
                    Finding(
                        "CEM-REF-LOADCASE",
                        Severity.ERROR,
                        f"AnalysisCase {ac.id!r} references unknown load case {lc_id!r}",
                        path,
                    )
                )

    # --- Geometry -----------------------------------------------------
    for i, el in enumerate(cem.elements):
        n1 = node_by_id.get(el.node_ids[0])
        n2 = node_by_id.get(el.node_ids[1])
        if n1 is None or n2 is None:
            continue  # already reported above as CEM-REF-NODE
        length = math.dist(n1.position, n2.position)
        if length < ZERO_LENGTH_EPS_M:
            errors.append(
                Finding(
                    "CEM-GEOM-ZEROLEN",
                    Severity.ERROR,
                    f"Element {el.id!r} has zero (or near-zero) length: {length:.3e} m",
                    f"elements[{i}]",
                )
            )

    seen_positions: dict[tuple[int, int, int], str] = {}
    for i, node in enumerate(cem.nodes):
        key = (
            round(node.position[0] / COINCIDENT_GRID_M),
            round(node.position[1] / COINCIDENT_GRID_M),
            round(node.position[2] / COINCIDENT_GRID_M),
        )
        if key in seen_positions:
            warnings.append(
                Finding(
                    "CEM-GEOM-COINCIDENT",
                    Severity.WARNING,
                    f"Node {node.id!r} is coincident with node {seen_positions[key]!r}",
                    f"nodes[{i}]",
                )
            )
        else:
            seen_positions[key] = node.id

    # --- Coarse stability heuristic ------------------------------------
    any_translation_restrained = any(any(sup.dofs[:3]) for sup in cem.constraints)
    if not any_translation_restrained:
        errors.append(
            Finding(
                "CEM-STAB-NOSUPPORT",
                Severity.ERROR,
                "Model has no support restraining any translational DOF; "
                "this is an unrestrained rigid body and cannot be solved",
                "constraints",
            )
        )

    return ValidationResult(errors=errors, warnings=warnings)
