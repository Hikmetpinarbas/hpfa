from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path
from typing import Any

MAX_XLSX_FILE_BYTES = 64 * 1024 * 1024
MAX_XLSX_ARCHIVE_ENTRIES = 20_000
MAX_XLSX_ARCHIVE_UNCOMPRESSED_BYTES = 128 * 1024 * 1024
MAX_XLSX_ARCHIVE_COMPRESSION_RATIO = 250.0
MIN_RATIO_CHECK_BYTES = 8 * 1024 * 1024
REQUIRED_XLSX_MEMBERS = {"[Content_Types].xml", "xl/workbook.xml"}


class XlsxRuntimeGuardError(ValueError):
    """Fail-closed error raised before workbook parsing begins."""


def _fail(code: str) -> None:
    raise XlsxRuntimeGuardError(code)


def _representatives(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    files = inventory.get("files", [])
    by_id = {str(item.get("file_id")): item for item in files}
    configured = inventory.get("inventory_representatives") or []
    if configured:
        selected = [
            by_id.get(str(record.get("representative_file_id")))
            for record in configured
        ]
        return [
            item
            for item in selected
            if item and str(item.get("extension")).casefold() == ".xlsx"
        ]

    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in files:
        if str(item.get("extension")).casefold() != ".xlsx":
            continue
        key = str(item.get("sha256") or item.get("relative_path"))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def resolve_inventory_path(root: Path, relative_path: Any) -> Path:
    raw = str(relative_path or "").strip()
    if not raw:
        _fail("inventory_relative_path_missing")
    relative = Path(raw)
    if relative.is_absolute():
        _fail("inventory_relative_path_absolute_rejected")
    candidate = (root / relative).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError:
        _fail("inventory_relative_path_outside_input_root")
    return candidate


def inspect_xlsx_archive(path: Path) -> dict[str, Any]:
    try:
        file_size = path.stat().st_size
    except OSError:
        _fail("xlsx_file_unreadable")
    if file_size > MAX_XLSX_FILE_BYTES:
        _fail("xlsx_file_size_budget_exceeded")
    if not zipfile.is_zipfile(path):
        _fail("malformed_xlsx_container")

    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            names = {info.filename for info in infos}
            if not REQUIRED_XLSX_MEMBERS.issubset(names):
                _fail("xlsx_required_members_missing")
            if len(infos) > MAX_XLSX_ARCHIVE_ENTRIES:
                _fail("xlsx_archive_entry_budget_exceeded")
            if any(info.flag_bits & 0x1 for info in infos):
                _fail("encrypted_xlsx")

            total_uncompressed = sum(info.file_size for info in infos)
            total_compressed = sum(max(info.compress_size, 1) for info in infos)
            if total_uncompressed > MAX_XLSX_ARCHIVE_UNCOMPRESSED_BYTES:
                _fail("xlsx_archive_uncompressed_budget_exceeded")
            compression_ratio = total_uncompressed / total_compressed
            if (
                total_uncompressed >= MIN_RATIO_CHECK_BYTES
                and compression_ratio > MAX_XLSX_ARCHIVE_COMPRESSION_RATIO
            ):
                _fail("xlsx_archive_compression_ratio_exceeded")
    except zipfile.BadZipFile:
        _fail("malformed_xlsx_container")
    except OSError:
        _fail("xlsx_file_unreadable")

    return {
        "file_size_bytes": file_size,
        "archive_entry_count": len(infos),
        "archive_uncompressed_bytes": total_uncompressed,
        "archive_compression_ratio": round(compression_ratio, 6),
        "required_members_present": True,
        "encrypted": False,
        "status": "PASS",
    }


def guard_runtime_inputs(
    input_root: str | Path,
    inventory_path: str | Path,
) -> dict[str, Any]:
    root = Path(input_root).expanduser().resolve(strict=False)
    if not root.is_dir():
        _fail("input_root_missing")

    inventory_file = Path(inventory_path).expanduser().resolve(strict=False)
    try:
        inventory = json.loads(inventory_file.read_text(encoding="utf-8"))
    except OSError:
        _fail("inventory_file_unreadable")
    except json.JSONDecodeError:
        _fail("inventory_json_malformed")
    if not isinstance(inventory, dict):
        _fail("inventory_payload_not_object")

    representatives = _representatives(inventory)
    if not representatives:
        _fail("xlsx_surface_missing")

    files: list[dict[str, Any]] = []
    for item in representatives:
        candidate = resolve_inventory_path(root, item.get("relative_path"))
        if not candidate.is_file():
            _fail("xlsx_file_missing")
        files.append(
            {
                "relative_path": item.get("relative_path"),
                "sha256": item.get("sha256"),
                "archive_guard": inspect_xlsx_archive(candidate),
            }
        )

    return {
        "status": "PASS",
        "input_root": str(root),
        "xlsx_file_count": len(files),
        "files": files,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }


def guard_cli_arguments(argv: list[str] | None = None) -> dict[str, Any] | None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--input-root")
    parser.add_argument("--inventory")
    args, _ = parser.parse_known_args(argv)
    if not args.input_root or not args.inventory:
        return None
    return guard_runtime_inputs(args.input_root, args.inventory)
