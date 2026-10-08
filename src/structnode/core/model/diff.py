"""Structured diff between two CEM revisions (`model.diff` in the public
tool contract, docs/MASTER_PLAN.md section 5).

Each collection is keyed by its natural identifier (`id` for most
collections; `node_id` for `constraints`, since `Support` has no `id`
field). Note: if a collection legitimately has two entries sharing that
key (e.g. two `Support` rows on the same `node_id`), they collapse under
this key-based diff -- acceptable for S1 scope, but a known limitation.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from structnode.core.model.cem import CEM


@dataclass
class CollectionDiff:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.removed or self.changed)

    def to_dict(self) -> dict[str, list[str]]:
        return {"added": self.added, "removed": self.removed, "changed": self.changed}


@dataclass
class ModelDiff:
    nodes: CollectionDiff
    materials: CollectionDiff
    sections: CollectionDiff
    elements: CollectionDiff
    constraints: CollectionDiff
    load_cases: CollectionDiff
    loads: CollectionDiff
    analysis_cases: CollectionDiff

    @property
    def is_empty(self) -> bool:
        return all(c.is_empty for c in self._collections())

    def _collections(self) -> tuple[CollectionDiff, ...]:
        return (
            self.nodes,
            self.materials,
            self.sections,
            self.elements,
            self.constraints,
            self.load_cases,
            self.loads,
            self.analysis_cases,
        )

    def to_dict(self) -> dict[str, dict[str, list[str]]]:
        return {
            "nodes": self.nodes.to_dict(),
            "materials": self.materials.to_dict(),
            "sections": self.sections.to_dict(),
            "elements": self.elements.to_dict(),
            "constraints": self.constraints.to_dict(),
            "load_cases": self.load_cases.to_dict(),
            "loads": self.loads.to_dict(),
            "analysis_cases": self.analysis_cases.to_dict(),
        }


def _diff_collection(
    old_items: Sequence[Any], new_items: Sequence[Any], key_fn: Callable[[Any], str]
) -> CollectionDiff:
    old_by_key = {key_fn(item): item for item in old_items}
    new_by_key = {key_fn(item): item for item in new_items}
    old_keys, new_keys = set(old_by_key), set(new_by_key)

    added = sorted(new_keys - old_keys)
    removed = sorted(old_keys - new_keys)
    changed = sorted(
        key
        for key in old_keys & new_keys
        if old_by_key[key].model_dump(mode="json") != new_by_key[key].model_dump(mode="json")
    )
    return CollectionDiff(added=added, removed=removed, changed=changed)


def diff_cem(old: CEM, new: CEM) -> ModelDiff:
    return ModelDiff(
        nodes=_diff_collection(old.nodes, new.nodes, lambda n: n.id),
        materials=_diff_collection(old.materials, new.materials, lambda m: m.id),
        sections=_diff_collection(old.sections, new.sections, lambda s: s.id),
        elements=_diff_collection(old.elements, new.elements, lambda e: e.id),
        constraints=_diff_collection(old.constraints, new.constraints, lambda s: s.node_id),
        load_cases=_diff_collection(old.load_cases, new.load_cases, lambda lc: lc.id),
        loads=_diff_collection(old.loads, new.loads, lambda load: load.id),
        analysis_cases=_diff_collection(old.analysis_cases, new.analysis_cases, lambda ac: ac.id),
    )
