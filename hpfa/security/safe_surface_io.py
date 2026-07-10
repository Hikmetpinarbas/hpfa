from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import BinaryIO

MAX_SURFACE_BYTES = 512 * 1024 * 1024
MAX_XML_BYTES = 256 * 1024 * 1024
MAX_XLSX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_ZIP_ENTRY_BYTES = 256 * 1024 * 1024
MAX_ZIP_ENTRIES = 4096
MAX_COMPRESSION_RATIO = 100.0
XML_PROBE_BYTES = 65536


class SurfaceSecurityError(ValueError):
    pass


def validate_regular_surface_file(path: Path) -> None:
    if path.is_symlink():
        raise SurfaceSecurityError("surface_symlink_rejected")
    if not path.exists() or not path.is_file():
        raise SurfaceSecurityError("surface_not_regular_file")
    size = path.stat().st_size
    if size <= 0:
        raise SurfaceSecurityError("surface_empty_file")
    if size > MAX_SURFACE_BYTES:
        raise SurfaceSecurityError("surface_file_too_large")


def reject_unsafe_xml_declarations(path: Path) -> None:
    validate_regular_surface_file(path)
    if path.stat().st_size > MAX_XML_BYTES:
        raise SurfaceSecurityError("xml_file_too_large")
    with path.open("rb") as handle:
        probe = handle.read(XML_PROBE_BYTES).upper()
    if b"<!DOCTYPE" in probe:
        raise SurfaceSecurityError("xml_doctype_rejected")
    if b"<!ENTITY" in probe:
        raise SurfaceSecurityError("xml_entity_rejected")


def validate_xlsx_archive(path: Path) -> None:
    validate_regular_surface_file(path)
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ZIP_ENTRIES:
                raise SurfaceSecurityError("xlsx_too_many_zip_entries")
            total_uncompressed = 0
            for info in infos:
                if info.is_dir():
                    continue
                total_uncompressed += info.file_size
                if info.file_size > MAX_ZIP_ENTRY_BYTES:
                    raise SurfaceSecurityError("xlsx_zip_entry_too_large")
                if total_uncompressed > MAX_XLSX_UNCOMPRESSED_BYTES:
                    raise SurfaceSecurityError("xlsx_uncompressed_size_limit_exceeded")
                if info.file_size > 0:
                    ratio = info.file_size / max(1, info.compress_size)
                    if ratio > MAX_COMPRESSION_RATIO:
                        raise SurfaceSecurityError("xlsx_compression_ratio_exceeded")
    except zipfile.BadZipFile as exc:
        raise SurfaceSecurityError("xlsx_invalid_zip") from exc


def bounded_zip_member(archive: zipfile.ZipFile, member: str) -> BinaryIO:
    info = archive.getinfo(member)
    if info.file_size > MAX_ZIP_ENTRY_BYTES:
        raise SurfaceSecurityError("xlsx_zip_entry_too_large")
    return archive.open(info, "r")
