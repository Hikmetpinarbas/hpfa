from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def surface_snapshot(root_like: str | Path) -> dict[str, Any]:
    """Canonical recursive ACTIVE_MATCH content snapshot.

    Contract matches the reconstruction and episode authority binding:
    relative path + size + SHA256 for every regular file, stable JSON encoding.
    """
    root = Path(root_like).expanduser().resolve(strict=False)
    records: list[dict[str, Any]] = []
    if root.is_dir():
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
            if not path.is_file():
                continue
            records.append({
                "relative_path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": _hash_file(path),
            })
    stable_payload = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "snapshot_id": hashlib.sha256(stable_payload.encode("utf-8")).hexdigest(),
        "surface_file_count": len(records),
        "records": records,
    }


def surface_snapshot_id(root_like: str | Path) -> str:
    return str(surface_snapshot(root_like)["snapshot_id"])
