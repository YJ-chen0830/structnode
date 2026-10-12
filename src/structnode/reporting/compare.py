"""Compare two `analyze` results payloads (docs/MASTER_PLAN.md section
5: `analysis.compare_solvers`). Purely descriptive -- it never decides
which result is "right", only how far apart they are, per quantity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_CATEGORIES = ("displacements", "reactions", "element_forces")


@dataclass
class QuantityDiff:
    category: str
    key: str
    component: str
    value_a: float
    value_b: float
    abs_diff: float
    rel_diff: float | None  # None when both values are ~0 (relative diff undefined)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "key": self.key,
            "component": self.component,
            "value_a": self.value_a,
            "value_b": self.value_b,
            "abs_diff": self.abs_diff,
            "rel_diff": self.rel_diff,
        }


@dataclass
class ComparisonResult:
    tolerance: float
    diffs: list[QuantityDiff] = field(default_factory=list)
    missing_in_a: list[str] = field(default_factory=list)
    missing_in_b: list[str] = field(default_factory=list)

    @property
    def max_relative_diff(self) -> float:
        rels = [d.rel_diff for d in self.diffs if d.rel_diff is not None]
        return max(rels) if rels else 0.0

    @property
    def ok(self) -> bool:
        if self.missing_in_a or self.missing_in_b:
            return False
        return all(d.rel_diff is None or d.rel_diff <= self.tolerance for d in self.diffs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "tolerance": self.tolerance,
            "max_relative_diff": self.max_relative_diff,
            "missing_in_a": self.missing_in_a,
            "missing_in_b": self.missing_in_b,
            "diffs": [d.to_dict() for d in self.diffs],
        }


def compare_results(
    a: dict[str, Any], b: dict[str, Any], tolerance: float = 1e-6, abs_floor: float = 1e-9
) -> ComparisonResult:
    """Compares two results payloads by shared (category, key, component).

    `abs_floor` guards the relative-difference division: when both
    values are smaller than it in magnitude, the quantity is
    effectively zero in both and `rel_diff` is left `None` rather than
    reporting a meaningless (or divide-by-zero) ratio.
    """
    diffs: list[QuantityDiff] = []
    missing_in_a: list[str] = []
    missing_in_b: list[str] = []

    for category in _CATEGORIES:
        table_a: dict[str, dict[str, float]] = a.get(category, {})
        table_b: dict[str, dict[str, float]] = b.get(category, {})
        for key in sorted(set(table_a) | set(table_b)):
            row_a, row_b = table_a.get(key), table_b.get(key)
            if row_a is None:
                missing_in_a.append(f"{category}.{key}")
                continue
            if row_b is None:
                missing_in_b.append(f"{category}.{key}")
                continue
            for component in sorted(set(row_a) | set(row_b)):
                va, vb = row_a.get(component), row_b.get(component)
                if va is None:
                    missing_in_a.append(f"{category}.{key}.{component}")
                    continue
                if vb is None:
                    missing_in_b.append(f"{category}.{key}.{component}")
                    continue
                abs_diff = abs(va - vb)
                denom = max(abs(va), abs(vb))
                rel_diff = None if denom < abs_floor else abs_diff / denom
                diffs.append(
                    QuantityDiff(
                        category=category,
                        key=key,
                        component=component,
                        value_a=va,
                        value_b=vb,
                        abs_diff=abs_diff,
                        rel_diff=rel_diff,
                    )
                )

    return ComparisonResult(
        tolerance=tolerance, diffs=diffs, missing_in_a=missing_in_a, missing_in_b=missing_in_b
    )
