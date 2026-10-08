"""Immutable, content-addressed CEM snapshots.

Per docs/MASTER_PLAN.md section 3: "Immutable analysis snapshots
identified by SHA-256 of canonical serialized input." A snapshot's
filename *is* its content hash, so a snapshot can never silently drift
from what it claims to be -- `load_snapshot` re-derives the hash on load
and refuses to return a mismatched file.
"""

from __future__ import annotations

from pathlib import Path

from structnode.core.model import CEM


class SnapshotNotFoundError(Exception):
    pass


class SnapshotIntegrityError(Exception):
    pass


def _snapshot_path(directory: Path, content_hash: str) -> Path:
    return directory / f"{content_hash}.cem.json"


def save_snapshot(cem: CEM, directory: Path) -> Path:
    """Write `cem` to `directory/<content_hash>.cem.json`. Idempotent."""
    directory.mkdir(parents=True, exist_ok=True)
    path = _snapshot_path(directory, cem.content_hash)
    path.write_bytes(cem.canonical_json())
    return path


def load_snapshot(directory: Path, content_hash: str) -> CEM:
    path = _snapshot_path(directory, content_hash)
    if not path.exists():
        raise SnapshotNotFoundError(f"No snapshot for hash {content_hash!r} in {directory}")

    cem = CEM.model_validate_json(path.read_text(encoding="utf-8"))
    if cem.content_hash != content_hash:
        raise SnapshotIntegrityError(
            f"Snapshot at {path} hashes to {cem.content_hash!r}, "
            f"not the requested {content_hash!r} -- file may be corrupted or tampered with"
        )
    return cem
