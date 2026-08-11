from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("runtime_source_guard_input_unreadable_or_malformed") from exc
    if not isinstance(payload, dict):
        raise ValueError("runtime_source_guard_input_not_object")
    return payload


def _active_match_path(path: Path) -> bool:
    parts = path.resolve(strict=False).parts
    return len(parts) >= 3 and tuple(parts[-3:]) == (
        "runtime",
        "active_single_match",
        "current",
    )


def _verify_one(root: Path, relative_path: Any, expected_sha: Any, cache: dict[str, str]) -> None:
    relative = str(relative_path or "").strip()
    expected = str(expected_sha or "").strip().casefold()
    if not relative or len(expected) != 64:
        raise ValueError("prerequisite_source_lineage_missing")
    candidate = (root / relative).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"prerequisite_source_path_escape:{relative}") from exc
    if not candidate.is_file():
        raise ValueError(f"prerequisite_source_missing:{relative}")
    actual = cache.setdefault(str(candidate), sha256_file(candidate).casefold())
    if actual != expected:
        raise ValueError(f"prerequisite_source_sha_mismatch:{relative}")


def verify_runtime_sources(
    runtime_authority: str | Path,
    xlsx_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
) -> dict[str, Any]:
    root = Path(runtime_authority).expanduser().resolve(strict=False)
    if not _active_match_path(root):
        raise ValueError("active_match_runtime_authority_mismatch")
    cache: dict[str, str] = {}
    checked: set[tuple[str, str]] = set()

    for file_row in xlsx_payload.get("files", []) or []:
        for sheet in file_row.get("sheets", []) or []:
            for row in sheet.get("rows", []) or []:
                relative = row.get("relative_path")
                expected = row.get("source_sha256")
                key = (str(relative or ""), str(expected or "").casefold())
                if key in checked:
                    continue
                _verify_one(root, relative, expected, cache)
                checked.add(key)

    for atom in evidence_payload.get("evidence_atoms", []) or []:
        paths = atom.get("source_relative_paths") or []
        shas = atom.get("source_sha256_lineage") or []
        if not isinstance(paths, list) or not isinstance(shas, list) or len(paths) != len(shas) or not paths:
            raise ValueError("prerequisite_evidence_source_lineage_invalid")
        for relative, expected in zip(paths, shas):
            key = (str(relative or ""), str(expected or "").casefold())
            if key in checked:
                continue
            _verify_one(root, relative, expected, cache)
            checked.add(key)

    if not checked:
        raise ValueError("prerequisite_runtime_source_lineage_empty")
    return {
        "runtime_source_rehash_status": "PASS",
        "runtime_source_reference_count": len(checked),
        "runtime_source_file_count": len(cache),
    }


def preflight_from_paths(
    runtime_authority: str | Path,
    xlsx_path: str | Path,
    evidence_path: str | Path,
) -> dict[str, Any]:
    return verify_runtime_sources(runtime_authority, _load(xlsx_path), _load(evidence_path))
