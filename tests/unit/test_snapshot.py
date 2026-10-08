from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from structnode.core.model import CEM
from structnode.core.snapshot import (
    SnapshotIntegrityError,
    SnapshotNotFoundError,
    load_snapshot,
    save_snapshot,
)


def test_save_and_load_roundtrip(valid_cem_dict: dict[str, Any], tmp_path: Path) -> None:
    cem = CEM.model_validate(valid_cem_dict)
    path = save_snapshot(cem, tmp_path)

    assert path.name == f"{cem.content_hash}.cem.json"
    loaded = load_snapshot(tmp_path, cem.content_hash)
    assert loaded.content_hash == cem.content_hash
    assert loaded.model_id == cem.model_id


def test_save_is_idempotent(valid_cem_dict: dict[str, Any], tmp_path: Path) -> None:
    cem = CEM.model_validate(valid_cem_dict)
    path1 = save_snapshot(cem, tmp_path)
    path2 = save_snapshot(cem, tmp_path)
    assert path1 == path2
    assert list(tmp_path.glob("*.cem.json")) == [path1]


def test_load_missing_snapshot_raises(tmp_path: Path) -> None:
    with pytest.raises(SnapshotNotFoundError):
        load_snapshot(tmp_path, "0" * 64)


def test_tampered_snapshot_is_detected(valid_cem_dict: dict[str, Any], tmp_path: Path) -> None:
    cem = CEM.model_validate(valid_cem_dict)
    path = save_snapshot(cem, tmp_path)

    # Overwrite the file's contents without renaming it -- the filename
    # (the claimed hash) no longer matches the actual content.
    tampered = cem.model_dump(mode="json")
    tampered["model_id"] = "tampered"
    path.write_text(json.dumps(tampered), encoding="utf-8")

    with pytest.raises(SnapshotIntegrityError):
        load_snapshot(tmp_path, cem.content_hash)
