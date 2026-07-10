from __future__ import annotations

from pathlib import Path
from typing import Any

import surface_manifest as legacy
from hpfa.security.safe_surface_io import (
    SurfaceSecurityError,
    reject_unsafe_xml_declarations,
    validate_regular_surface_file,
    validate_xlsx_archive,
)

ALLOWED_FORMATS = {"csv", "xml", "xlsx"}


def _format(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    return "xlsx" if suffix == "xlsm" else suffix


def _security_fail(match_dir: Path, reason: str, source_file: str | None = None) -> dict[str, Any]:
    failure = {"security_error": reason}
    if source_file is not None:
        failure["source_file"] = source_file
    return {
        "manifest_id": "canonical_ingest_surface_manifest_v1",
        "status": "FAIL_CLOSED",
        "reason": "surface_security_gate_failed",
        "match_dir": str(match_dir),
        "security_failures": [failure],
        "surfaces": [],
        "canonical_event_count": "UNKNOWN",
        "claim_safety": "EVIDENCE_ONLY",
        "report_language_allowed": False,
        "production_binding_allowed": False,
    }


def _validate_surface(path: Path) -> None:
    validate_regular_surface_file(path)
    fmt = _format(path)
    if fmt == "xml":
        reject_unsafe_xml_declarations(path)
    elif fmt == "xlsx":
        validate_xlsx_archive(path)


def build_manifest(match_dir: str) -> dict[str, Any]:
    root = Path(match_dir).expanduser().resolve(strict=False)
    if not root.exists() or not root.is_dir():
        return _security_fail(root, "match_directory_missing_or_invalid")

    for entry in root.iterdir():
        if _format(entry) not in ALLOWED_FORMATS:
            continue
        try:
            _validate_surface(entry)
        except (SurfaceSecurityError, OSError) as exc:
            return _security_fail(root, str(exc) or type(exc).__name__, entry.name)

    result = legacy.build_manifest(str(root))
    result.setdefault("security_failures", [])
    result["security_gate"] = "PASS"
    return result


def write_manifest(match_dir: str, out: str) -> dict[str, Any]:
    result = build_manifest(match_dir)
    from json import dumps

    output = Path(out).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return result
