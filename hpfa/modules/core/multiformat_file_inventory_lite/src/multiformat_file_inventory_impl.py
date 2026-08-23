from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
import posixpath
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

MODULE_ID = "multiformat_file_inventory_lite_v1"
SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls", ".xml", ".json", ".jsonl"}
TEXT_EXTENSIONS = {".csv", ".tsv", ".xml", ".json", ".jsonl"}
REFERENCE_REPORT_EXTENSIONS = {".pdf"}
GOVERNANCE_TEXT_EXTENSIONS = {".md", ".txt"}
FAIL_CLOSED_BLOCKS = {
    "input_root_missing",
    "file_unreadable",
    "unsupported_encoding",
    "encrypted_xlsx",
    "malformed_xml",
    "malformed_json",
    "empty_file",
    "duplicate_file_conflict",
    "external_entity_resolution_attempted",
    "runtime_authority_mismatch",
    "runtime_authority_path_invalid",
}
OUTPUT_NAMES = {
    "main": "multiformat_file_inventory_lite_v1.json",
    "inventory_json": "input_file_inventory.json",
    "inventory_tsv": "input_file_inventory.tsv",
    "unsupported": "unsupported_file_report.json",
    "duplicates": "duplicate_file_fingerprint_report.json",
    "decision_txt": "multiformat_ingest_decision_v1.txt",
}


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def _ensure_module_path(path: Path) -> None:
    text = str(path)
    if text not in sys.path:
        sys.path.insert(0, text)


def _spine_runner(root: Path):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    _ensure_module_path(src)
    import spine_runner  # type: ignore

    return spine_runner


def validate_output_root(out_dir: str | Path, root: str | Path | None = None) -> Path:
    output_root = Path(out_dir).expanduser().resolve(strict=False)
    if "HPFA" in output_root.parts and output_root.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    return _spine_runner(repo_root).validate_output_root(output_root)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_file_id(relative_path: str, sha256: str) -> str:
    seed = f"{relative_path}|{sha256}"
    return "file_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]


def normalized_field(value: str) -> str:
    text = str(value or "").strip().casefold()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def detect_text_encoding(path: Path) -> tuple[str, bool]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw.decode("utf-8-sig")
        return "utf-8-sig", True
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            raw.decode(encoding)
            return encoding, False
        except UnicodeDecodeError:
            continue
    raise UnicodeError("unsupported_encoding")


def first_nonblank_lines(text: str, limit: int = 20) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        if line.strip():
            lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def detect_delimiter(text: str, extension: str) -> str | None:
    sample_lines = first_nonblank_lines(text)
    if not sample_lines:
        return None
    sample = "\n".join(sample_lines)
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        if extension == ".tsv":
            return "\t"
        counts = {candidate: sample_lines[0].count(candidate) for candidate in (",", ";", "\t", "|")}
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else None


def sniff_quote_character(text: str, delimiter: str | None) -> str | None:
    if not delimiter:
        return None
    sample = "\n".join(first_nonblank_lines(text))
    try:
        return csv.Sniffer().sniff(sample, delimiters=delimiter).quotechar
    except csv.Error:
        return '"' if '"' in sample else None


def csv_metadata(path: Path, extension: str, encoding: str) -> dict[str, Any]:
    text = path.read_text(encoding=encoding)
    delimiter = detect_delimiter(text, extension)
    if not delimiter:
        return {
            "delimiter_candidate": None,
            "quote_character_candidate": None,
            "surface_row_count": 0,
            "visible_column_count": 0,
            "header_candidate": [],
            "schema_material": ["DELIMITER_UNRESOLVED"],
            "parse_status": "REVIEW_REQUIRED_DELIMITER_UNRESOLVED",
            "warnings": ["delimiter_unresolved"],
        }

    rows: list[list[str]] = []
    reader = csv.reader(text.splitlines(), delimiter=delimiter)
    for row in reader:
        if not any(str(cell).strip() for cell in row):
            continue
        rows.append(row)

    header = rows[0] if rows else []
    expected_width = len(header)
    malformed = bool(expected_width and any(len(row) != expected_width for row in rows[1:]))

    return {
        "delimiter_candidate": delimiter,
        "quote_character_candidate": sniff_quote_character(text, delimiter),
        "surface_row_count": max(len(rows) - 1, 0),
        "visible_column_count": expected_width,
        "header_candidate": header,
        "schema_material": [normalized_field(item) for item in header],
        "parse_status": "REVIEW_REQUIRED_ROW_WIDTH_MISMATCH" if malformed else "PARSED",
        "warnings": ["row_width_mismatch"] if malformed else [],
    }


def column_number(cell_reference: str) -> int:
    letters = "".join(char for char in cell_reference if char.isalpha())
    value = 0
    for char in letters.upper():
        value = value * 26 + (ord(char) - 64)
    return value


def xlsx_metadata(path: Path) -> dict[str, Any]:
    prefix = path.read_bytes()[:8]
    if prefix.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return {
            "sheet_names": [],
            "sheet_states": {},
            "surface_row_count": 0,
            "visible_column_count": 0,
            "schema_material": ["ENCRYPTED_OR_LEGACY_OLE_CONTAINER"],
            "parse_status": "FAIL_CLOSED_ENCRYPTED_XLSX",
            "warnings": ["encrypted_xlsx"],
            "signature_status": "OLE_CONTAINER_UNEXPECTED_FOR_XLSX",
        }
    if not prefix.startswith(b"PK"):
        return {
            "sheet_names": [],
            "sheet_states": {},
            "surface_row_count": 0,
            "visible_column_count": 0,
            "schema_material": ["XLSX_SIGNATURE_MISMATCH"],
            "parse_status": "FAIL_CLOSED_FILE_UNREADABLE",
            "warnings": ["file_unreadable"],
            "signature_status": "SIGNATURE_MISMATCH",
        }

    try:
        with zipfile.ZipFile(path) as archive:
            workbook_xml = archive.read("xl/workbook.xml")
            relationships_xml = archive.read("xl/_rels/workbook.xml.rels")
            workbook = ET.fromstring(workbook_xml)
            relationships = ET.fromstring(relationships_xml)

            rel_map: dict[str, str] = {}
            for rel in relationships:
                rel_id = rel.attrib.get("Id")
                target = rel.attrib.get("Target")
                if rel_id and target:
                    rel_map[rel_id] = target

            sheet_names: list[str] = []
            sheet_states: dict[str, str] = {}
            total_rows = 0
            max_columns = 0
            formula_count = 0

            for sheet in workbook.iter():
                if sheet.tag.split("}")[-1] != "sheet":
                    continue
                name = str(sheet.attrib.get("name") or "")
                state = str(sheet.attrib.get("state") or "visible")
                rel_id = (
                    sheet.attrib.get(
                        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                    )
                    or sheet.attrib.get("id")
                )
                sheet_names.append(name)
                sheet_states[name] = state

                target = rel_map.get(str(rel_id or ""))
                if not target:
                    continue
                worksheet_path = (
                    target.lstrip("/")
                    if target.startswith("/")
                    else posixpath.normpath(posixpath.join("xl", target))
                )
                try:
                    worksheet = ET.fromstring(archive.read(worksheet_path))
                except KeyError:
                    continue

                sheet_rows = 0
                sheet_max_columns = 0
                for node in worksheet.iter():
                    local = node.tag.split("}")[-1]
                    if local == "row":
                        sheet_rows += 1
                    elif local == "c":
                        ref = node.attrib.get("r")
                        if ref:
                            sheet_max_columns = max(sheet_max_columns, column_number(ref))
                    elif local == "f":
                        formula_count += 1
                total_rows += sheet_rows
                max_columns = max(max_columns, sheet_max_columns)

            schema_material = [f"{name}:{sheet_states.get(name, 'visible')}" for name in sheet_names]
            return {
                "sheet_names": sheet_names,
                "sheet_states": sheet_states,
                "surface_row_count": total_rows,
                "visible_column_count": max_columns,
                "formula_cell_count": formula_count,
                "schema_material": schema_material,
                "parse_status": "PARSED",
                "warnings": [],
                "signature_status": "ZIP_XLSX_CONFIRMED",
            }
    except (zipfile.BadZipFile, KeyError, ET.ParseError):
        return {
            "sheet_names": [],
            "sheet_states": {},
            "surface_row_count": 0,
            "visible_column_count": 0,
            "schema_material": ["MALFORMED_XLSX"],
            "parse_status": "FAIL_CLOSED_FILE_UNREADABLE",
            "warnings": ["file_unreadable"],
            "signature_status": "MALFORMED_XLSX",
        }


def xls_metadata(path: Path) -> dict[str, Any]:
    prefix = path.read_bytes()[:8]
    if not prefix.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return {
            "sheet_names": [],
            "sheet_states": {},
            "surface_row_count": 0,
            "visible_column_count": 0,
            "schema_material": ["XLS_SIGNATURE_MISMATCH"],
            "parse_status": "FAIL_CLOSED_FILE_UNREADABLE",
            "warnings": ["file_unreadable"],
            "signature_status": "SIGNATURE_MISMATCH",
        }
    try:
        import xlrd  # type: ignore
    except ImportError:
        return {
            "sheet_names": [],
            "sheet_states": {},
            "surface_row_count": 0,
            "visible_column_count": 0,
            "schema_material": ["LEGACY_XLS_READER_UNAVAILABLE"],
            "parse_status": "REVIEW_REQUIRED_LEGACY_XLS_READER_UNAVAILABLE",
            "warnings": ["legacy_xls_reader_unavailable"],
            "signature_status": "OLE_XLS_CONFIRMED",
        }

    try:
        workbook = xlrd.open_workbook(path, on_demand=True)
        sheet_names = workbook.sheet_names()
        total_rows = 0
        max_columns = 0
        for name in sheet_names:
            sheet = workbook.sheet_by_name(name)
            total_rows += sheet.nrows
            max_columns = max(max_columns, sheet.ncols)
        return {
            "sheet_names": sheet_names,
            "sheet_states": {name: "UNKNOWN_LEGACY_XLS" for name in sheet_names},
            "surface_row_count": total_rows,
            "visible_column_count": max_columns,
            "schema_material": sheet_names,
            "parse_status": "PARSED",
            "warnings": [],
            "signature_status": "OLE_XLS_CONFIRMED",
        }
    except Exception:
        return {
            "sheet_names": [],
            "sheet_states": {},
            "surface_row_count": 0,
            "visible_column_count": 0,
            "schema_material": ["MALFORMED_XLS"],
            "parse_status": "FAIL_CLOSED_FILE_UNREADABLE",
            "warnings": ["file_unreadable"],
            "signature_status": "MALFORMED_XLS",
        }


def xml_metadata(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    upper = raw.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        return {
            "xml_root_tag": None,
            "xml_namespace_map": {},
            "surface_row_count": 0,
            "visible_column_count": 0,
            "schema_material": ["EXTERNAL_ENTITY_OR_DTD_BLOCKED"],
            "parse_status": "FAIL_CLOSED_EXTERNAL_ENTITY_ATTEMPT",
            "warnings": ["external_entity_resolution_attempted"],
            "signature_status": "XML_DTD_OR_ENTITY_BLOCKED",
        }

    namespaces: dict[str, str] = {}
    try:
        for _, data in ET.iterparse(path, events=("start-ns",)):
            prefix, uri = data
            namespaces[prefix or "default"] = uri
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return {
            "xml_root_tag": None,
            "xml_namespace_map": namespaces,
            "surface_row_count": 0,
            "visible_column_count": 0,
            "schema_material": ["MALFORMED_XML"],
            "parse_status": "FAIL_CLOSED_MALFORMED_XML",
            "warnings": ["malformed_xml"],
            "signature_status": "MALFORMED_XML",
        }

    root_tag = root.tag.split("}")[-1]
    record_tags = {"instance", "event", "row", "code", "label"}
    record_count = 0
    field_names: set[str] = set()
    child_count = 0
    for node in root.iter():
        local = node.tag.split("}")[-1]
        if node is not root:
            child_count += 1
        if local.casefold() in record_tags:
            record_count += 1
        field_names.add(local)
        field_names.update(str(key).split("}")[-1] for key in node.attrib)

    return {
        "xml_root_tag": root_tag,
        "xml_namespace_map": namespaces,
        "surface_row_count": record_count if record_count else child_count,
        "visible_column_count": len(field_names),
        "schema_material": [root_tag, *sorted(namespaces.values()), *sorted(field_names)],
        "parse_status": "PARSED",
        "warnings": [],
        "signature_status": "XML_PARSED",
    }


def json_metadata(path: Path, extension: str, encoding: str) -> dict[str, Any]:
    text = path.read_text(encoding=encoding)
    if extension == ".jsonl":
        records: list[Any] = []
        keys: set[str] = set()
        try:
            for line in text.splitlines():
                if not line.strip():
                    continue
                item = json.loads(line)
                records.append(item)
                if isinstance(item, dict):
                    keys.update(str(key) for key in item)
        except json.JSONDecodeError:
            return {
                "surface_row_count": 0,
                "visible_column_count": 0,
                "schema_material": ["MALFORMED_JSONL"],
                "parse_status": "FAIL_CLOSED_MALFORMED_JSON",
                "warnings": ["malformed_json"],
                "signature_status": "MALFORMED_JSONL",
            }
        return {
            "surface_row_count": len(records),
            "visible_column_count": len(keys),
            "schema_material": sorted(keys),
            "parse_status": "PARSED",
            "warnings": [],
            "signature_status": "JSONL_PARSED",
        }

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {
            "surface_row_count": 0,
            "visible_column_count": 0,
            "schema_material": ["MALFORMED_JSON"],
            "parse_status": "FAIL_CLOSED_MALFORMED_JSON",
            "warnings": ["malformed_json"],
            "signature_status": "MALFORMED_JSON",
        }

    if isinstance(payload, list):
        keys = {str(key) for item in payload if isinstance(item, dict) for key in item}
        row_count = len(payload)
    elif isinstance(payload, dict):
        keys = set(str(key) for key in payload)
        row_count = 1
    else:
        keys = set()
        row_count = 1

    return {
        "surface_row_count": row_count,
        "visible_column_count": len(keys),
        "schema_material": sorted(keys) or [type(payload).__name__],
        "parse_status": "PARSED",
        "warnings": [],
        "signature_status": "JSON_PARSED",
    }


def mime_type_for(extension: str) -> str:
    custom = {
        ".csv": "text/csv",
        ".tsv": "text/tab-separated-values",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".xml": "application/xml",
        ".json": "application/json",
        ".jsonl": "application/x-ndjson",
    }
    return custom.get(extension) or mimetypes.types_map.get(extension, "application/octet-stream")


def infer_source_role(path: Path, extension: str, root: Path | None = None) -> str:
    relative_parts = ()
    if root is not None:
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            relative_parts = path.parts
    else:
        relative_parts = path.parts

    lowered_parts = tuple(part.casefold() for part in relative_parts)
    name = path.name.casefold()

    if lowered_parts and lowered_parts[0] == "manifest":
        return "MANIFEST_SURFACE_CANDIDATE"
    if "goalkeeper" in name or "keeper" in name:
        return "GOALKEEPER_SURFACE_CANDIDATE"
    if "player" in name:
        return "PLAYER_SURFACE_CANDIDATE"
    if "team" in name:
        return "TEAM_SURFACE_CANDIDATE"
    if any(token in name for token in ("lookup", "dictionary", "taxonomy", "ontology")):
        return "LOOKUP_OR_ONTOLOGY_SURFACE_CANDIDATE"
    if any(token in name for token in ("match", "summary")):
        return "MATCH_SUMMARY_SURFACE_CANDIDATE"
    if extension in {".csv", ".tsv"}:
        return "EVENT_ROW_OR_TABULAR_SURFACE_CANDIDATE"
    if extension == ".xml":
        return "SEMANTIC_HIERARCHY_OR_METADATA_SURFACE_CANDIDATE"
    if extension in {".xlsx", ".xls"}:
        return "AGGREGATE_OR_TABULAR_SURFACE_CANDIDATE"
    return "STRUCTURED_SUPPORT_SURFACE_CANDIDATE"


def schema_fingerprint(extension: str, material: Iterable[str]) -> str:
    normalized = [normalized_field(item) for item in material if str(item or "").strip()]
    seed = extension + "|" + "|".join(normalized)
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def inspect_supported_file(path: Path, root: Path) -> dict[str, Any]:
    relative_path = path.relative_to(root).as_posix()
    extension = path.suffix.casefold()
    hard_blocks: list[str] = []
    warnings: list[str] = []

    try:
        size_bytes = path.stat().st_size
        digest = sha256_file(path)
    except OSError:
        return {
            "file_id": stable_file_id(relative_path, "UNREADABLE"),
            "file_name": path.name,
            "relative_path": relative_path,
            "extension": extension,
            "mime_type": mime_type_for(extension),
            "size_bytes": None,
            "sha256": None,
            "encoding_candidate": None,
            "delimiter_candidate": None,
            "sheet_names": [],
            "sheet_states": {},
            "xml_root_tag": None,
            "xml_namespace_map": {},
            "surface_row_count": None,
            "visible_column_count": None,
            "source_role": infer_source_role(path, extension, root),
            "provider_candidate": "UNKNOWN",
            "match_identity_candidate": "UNKNOWN_MATCH_LOCAL_CANDIDATE",
            "readability_status": "UNREADABLE",
            "parse_status": "FAIL_CLOSED_FILE_UNREADABLE",
            "signature_status": "UNREADABLE",
            "schema_fingerprint": None,
            "hard_block_hits": ["file_unreadable"],
            "parse_warnings": [],
            "canonical_event_count": "UNKNOWN",
            "claim_ceiling": "FILE_DISCOVERY_ONLY",
        }

    if size_bytes == 0:
        hard_blocks.append("empty_file")

    encoding_candidate = None
    bom_present = False
    delimiter_candidate = None
    quote_character_candidate = None
    sheet_names: list[str] = []
    sheet_states: dict[str, str] = {}
    xml_root_tag = None
    xml_namespace_map: dict[str, str] = {}
    surface_row_count: int | None = 0
    visible_column_count: int | None = 0
    schema_material: list[str] = []
    parse_status = "PARSED"
    signature_status = "TEXT_OR_STRUCTURED_EXTENSION"

    if extension in TEXT_EXTENSIONS and size_bytes > 0:
        try:
            encoding_candidate, bom_present = detect_text_encoding(path)
        except (UnicodeError, OSError):
            hard_blocks.append("unsupported_encoding")
            parse_status = "FAIL_CLOSED_UNSUPPORTED_ENCODING"

    if size_bytes > 0 and not hard_blocks:
        if extension in {".csv", ".tsv"}:
            metadata = csv_metadata(path, extension, str(encoding_candidate))
            delimiter_candidate = metadata.get("delimiter_candidate")
            quote_character_candidate = metadata.get("quote_character_candidate")
            signature_status = "TEXT_TABULAR_PARSED"
        elif extension == ".xlsx":
            metadata = xlsx_metadata(path)
            sheet_names = metadata.get("sheet_names", [])
            sheet_states = metadata.get("sheet_states", {})
            signature_status = str(metadata.get("signature_status") or "UNKNOWN")
        elif extension == ".xls":
            metadata = xls_metadata(path)
            sheet_names = metadata.get("sheet_names", [])
            sheet_states = metadata.get("sheet_states", {})
            signature_status = str(metadata.get("signature_status") or "UNKNOWN")
        elif extension == ".xml":
            metadata = xml_metadata(path)
            xml_root_tag = metadata.get("xml_root_tag")
            xml_namespace_map = metadata.get("xml_namespace_map", {})
            signature_status = str(metadata.get("signature_status") or "UNKNOWN")
        else:
            metadata = json_metadata(path, extension, str(encoding_candidate))
            signature_status = str(metadata.get("signature_status") or "UNKNOWN")

        surface_row_count = metadata.get("surface_row_count")
        visible_column_count = metadata.get("visible_column_count")
        schema_material = list(metadata.get("schema_material") or [])
        parse_status = str(metadata.get("parse_status") or "UNKNOWN")
        warnings.extend(metadata.get("warnings") or [])
        for warning in warnings:
            if warning in FAIL_CLOSED_BLOCKS:
                hard_blocks.append(warning)

    hard_blocks = sorted(set(hard_blocks))
    warnings = sorted(set(warnings))
    if hard_blocks:
        parse_status = "FAIL_CLOSED"
    elif warnings and parse_status == "PARSED":
        parse_status = "REVIEW_REQUIRED"

    return {
        "file_id": stable_file_id(relative_path, digest),
        "file_name": path.name,
        "relative_path": relative_path,
        "extension": extension,
        "mime_type": mime_type_for(extension),
        "size_bytes": size_bytes,
        "sha256": digest,
        "encoding_candidate": encoding_candidate,
        "bom_present": bom_present,
        "delimiter_candidate": delimiter_candidate,
        "quote_character_candidate": quote_character_candidate,
        "sheet_names": sheet_names,
        "sheet_states": sheet_states,
        "xml_root_tag": xml_root_tag,
        "xml_namespace_map": xml_namespace_map,
        "surface_row_count": surface_row_count,
        "visible_column_count": visible_column_count,
        "source_role": infer_source_role(path, extension, root),
        "provider_candidate": "UNKNOWN",
        "match_identity_candidate": "UNKNOWN_MATCH_LOCAL_CANDIDATE",
        "readability_status": "READABLE" if "file_unreadable" not in hard_blocks else "UNREADABLE",
        "parse_status": parse_status,
        "signature_status": signature_status,
        "schema_fingerprint": schema_fingerprint(extension, schema_material),
        "hard_block_hits": hard_blocks,
        "parse_warnings": warnings,
        "canonical_event_count": "UNKNOWN",
        "claim_ceiling": "FILE_DISCOVERY_ONLY",
    }


def classify_unsupported_file(path: Path, root: Path) -> dict[str, Any]:
    relative_path = path.relative_to(root).as_posix()
    extension = path.suffix.casefold()
    parts = tuple(part.casefold() for part in path.relative_to(root).parts)

    if parts and parts[0] == "reference_reports" and extension in REFERENCE_REPORT_EXTENSIONS:
        source_role = "REFERENCE_REPORT_SURFACE"
        status = "REFERENCE_ONLY_UNSUPPORTED"
        disposition = "INVENTORY_ONLY_DO_NOT_INGEST"
        review_required = False
        claim_ceiling = "REFERENCE_ONLY"
    elif parts and parts[0] == "manifest" and extension in GOVERNANCE_TEXT_EXTENSIONS:
        source_role = "GOVERNANCE_MANIFEST_SURFACE"
        status = "GOVERNANCE_ONLY_UNSUPPORTED"
        disposition = "INVENTORY_ONLY_DO_NOT_INGEST"
        review_required = False
        claim_ceiling = "GOVERNANCE_ONLY"
    else:
        source_role = "UNRESOLVED_UNSUPPORTED_SURFACE"
        status = "REVIEW_REQUIRED_UNSUPPORTED_EXTENSION"
        disposition = "REVIEW_REQUIRED"
        review_required = True
        claim_ceiling = "FILE_DISCOVERY_ONLY"

    return {
        "file_name": path.name,
        "relative_path": relative_path,
        "extension": extension,
        "size_bytes": path.stat().st_size,
        "source_role": source_role,
        "status": status,
        "disposition": disposition,
        "review_required": review_required,
        "claim_ceiling": claim_ceiling,
        "canonical_event_count": "UNKNOWN",
    }


def duplicate_reports(files: list[dict[str, Any]]) -> dict[str, Any]:
    by_hash: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in files:
        digest = item.get("sha256")
        if digest:
            by_hash[str(digest)].append(item)
        by_name[str(item.get("file_name") or "").casefold()].append(item)

    exact_duplicate_groups: list[dict[str, Any]] = []
    exact_duplicate_reflection_count = 0
    representative_file_ids: list[str] = []
    for digest, group in sorted(by_hash.items()):
        ordered = sorted(
            group,
            key=lambda item: (
                len(Path(str(item.get("relative_path") or "")).parts),
                str(item.get("relative_path") or "").casefold(),
            ),
        )
        representative = ordered[0]
        representative_file_ids.append(str(representative["file_id"]))
        if len(group) > 1:
            exact_duplicate_reflection_count += len(group) - 1
            exact_duplicate_groups.append(
                {
                    "sha256": digest,
                    "file_ids": [item["file_id"] for item in ordered],
                    "relative_paths": [item["relative_path"] for item in ordered],
                    "representative_file_id": representative["file_id"],
                    "representative_relative_path": representative["relative_path"],
                    "representative_selection_rule": (
                        "shortest_relative_path_then_lexical_inventory_representative_not_source_truth"
                    ),
                    "status": "EXACT_DUPLICATE_REFLECTION",
                }
            )

    conflicting_logical_name_groups: list[dict[str, Any]] = []
    for name, group in sorted(by_name.items()):
        digests = sorted({str(item.get("sha256")) for item in group if item.get("sha256")})
        if len(group) > 1 and len(digests) > 1:
            conflicting_logical_name_groups.append(
                {
                    "logical_file_name": name,
                    "sha256_values": digests,
                    "file_ids": [item["file_id"] for item in group],
                    "relative_paths": [item["relative_path"] for item in group],
                    "status": "FAIL_CLOSED_DUPLICATE_FILE_CONFLICT",
                }
            )

    unique_hashes = {str(item.get("sha256")) for item in files if item.get("sha256")}
    return {
        "unique_content_file_count": len(unique_hashes),
        "representative_file_ids": representative_file_ids,
        "exact_duplicate_group_count": len(exact_duplicate_groups),
        "exact_duplicate_reflection_count": exact_duplicate_reflection_count,
        "exact_duplicate_groups": exact_duplicate_groups,
        "duplicate_file_conflict_count": len(conflicting_logical_name_groups),
        "conflicting_logical_name_groups": conflicting_logical_name_groups,
    }


def empty_inventory(root: Path, hard_block: str) -> dict[str, Any]:
    return {
        "module_id": MODULE_ID,
        "status": "FAIL_CLOSED",
        "input_root": str(root),
        "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
        "total_file_path_count": 0,
        "supported_file_count": 0,
        "file_count": 0,
        "file_count_semantics": "SUPPORTED_FILE_PATH_COUNT_LEGACY_ALIAS",
        "unique_content_file_count": 0,
        "unsupported_file_count": 0,
        "unresolved_unsupported_file_count": 0,
        "reference_only_unsupported_file_count": 0,
        "files": [],
        "unsupported_files": [],
        "duplicate_report": {
            "unique_content_file_count": 0,
            "representative_file_ids": [],
            "exact_duplicate_group_count": 0,
            "exact_duplicate_reflection_count": 0,
            "exact_duplicate_groups": [],
            "duplicate_file_conflict_count": 0,
            "conflicting_logical_name_groups": [],
        },
        "hard_block_hits": [hard_block],
        "canonical_event_count": "UNKNOWN",
        "active_match_evidence_pass": False,
        "production_release": False,
        "claim_ceiling": "FILE_DISCOVERY_ONLY",
    }


def build_inventory(input_root: str | Path) -> dict[str, Any]:
    root = Path(input_root).expanduser().resolve(strict=False)
    if not root.exists() or not root.is_dir():
        return empty_inventory(root, "input_root_missing")

    supported_paths: list[Path] = []
    unsupported_files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if not path.is_file():
            continue
        extension = path.suffix.casefold()
        if extension in SUPPORTED_EXTENSIONS:
            supported_paths.append(path)
        else:
            unsupported_files.append(classify_unsupported_file(path, root))

    files = [inspect_supported_file(path, root) for path in supported_paths]
    duplicates = duplicate_reports(files)

    hard_blocks = sorted(
        {
            block
            for item in files
            for block in item.get("hard_block_hits", [])
        }
    )
    if duplicates["duplicate_file_conflict_count"]:
        hard_blocks.append("duplicate_file_conflict")
    hard_blocks = sorted(set(hard_blocks))

    unresolved_unsupported = [item for item in unsupported_files if item.get("review_required")]
    reference_only_unsupported = [item for item in unsupported_files if not item.get("review_required")]
    review_required = bool(unresolved_unsupported) or any(
        str(item.get("parse_status", "")).startswith("REVIEW_REQUIRED")
        for item in files
    )
    status = (
        "FAIL_CLOSED"
        if any(block in FAIL_CLOSED_BLOCKS for block in hard_blocks)
        else ("REVIEW_REQUIRED" if review_required else "PASS")
    )
    total_file_path_count = len(files) + len(unsupported_files)

    return {
        "module_id": MODULE_ID,
        "status": status,
        "input_root": str(root),
        "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
        "total_file_path_count": total_file_path_count,
        "supported_file_count": len(files),
        "file_count": len(files),
        "file_count_semantics": "SUPPORTED_FILE_PATH_COUNT_LEGACY_ALIAS",
        "unique_content_file_count": duplicates["unique_content_file_count"],
        "unsupported_file_count": len(unsupported_files),
        "unresolved_unsupported_file_count": len(unresolved_unsupported),
        "reference_only_unsupported_file_count": len(reference_only_unsupported),
        "files": files,
        "unsupported_files": unsupported_files,
        "duplicate_report": duplicates,
        "hard_block_hits": hard_blocks,
        "canonical_event_count": "UNKNOWN",
        "active_match_evidence_pass": False,
        "production_release": False,
        "claim_ceiling": "FILE_DISCOVERY_ONLY",
        "analyst_evidence": {
            "total_file_paths_found": total_file_path_count,
            "supported_file_paths_found": len(files),
            "unsupported_file_paths_found": len(unsupported_files),
            "unique_supported_content_file_surfaces_found": duplicates["unique_content_file_count"],
            "supported_format_counts": {
                extension: sum(1 for item in files if item.get("extension") == extension)
                for extension in sorted(SUPPORTED_EXTENSIONS)
            },
            "safe_statement": (
                "Visible file surfaces were inventoried; exact duplicate reflections were "
                "preserved; semantic and event truth remain unresolved."
            ),
        },
    }


def apply_active_match_execution(
    payload: dict[str, Any],
    input_root: str | Path,
    runtime_authority: str | Path,
) -> dict[str, Any]:
    input_path = Path(input_root).expanduser().resolve(strict=False)
    authority_path = Path(runtime_authority).expanduser().resolve(strict=False)
    suffix_valid = tuple(authority_path.parts[-3:]) == (
        "runtime",
        "active_single_match",
        "current",
    )
    same_path = input_path == authority_path
    hard_blocks = list(payload.get("hard_block_hits") or [])

    if not suffix_valid:
        hard_blocks.append("runtime_authority_path_invalid")
    if not same_path:
        hard_blocks.append("runtime_authority_mismatch")

    hard_blocks = sorted(set(hard_blocks))
    payload["hard_block_hits"] = hard_blocks
    if any(block in FAIL_CLOSED_BLOCKS for block in hard_blocks):
        payload["status"] = "FAIL_CLOSED"

    passed = bool(
        suffix_valid
        and same_path
        and payload.get("status") != "FAIL_CLOSED"
        and not hard_blocks
    )
    payload["active_match_evidence_pass"] = passed
    payload["runtime_execution"] = {
        "requested": True,
        "input_root": str(input_path),
        "runtime_authority": str(authority_path),
        "authority_suffix_valid": suffix_valid,
        "input_matches_runtime_authority": same_path,
        "execution_status": "ACTIVE_MATCH_EVIDENCE_PASS" if passed else "FAIL_CLOSED",
    }
    return payload


def inventory_tsv(payload: dict[str, Any]) -> str:
    columns = [
        "file_id",
        "file_name",
        "relative_path",
        "extension",
        "mime_type",
        "size_bytes",
        "sha256",
        "encoding_candidate",
        "delimiter_candidate",
        "surface_row_count",
        "visible_column_count",
        "source_role",
        "provider_candidate",
        "match_identity_candidate",
        "readability_status",
        "parse_status",
        "signature_status",
        "schema_fingerprint",
        "hard_block_hits",
    ]
    rows = ["\t".join(columns)]
    for item in payload.get("files", []):
        values = []
        for column in columns:
            value = item.get(column)
            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False, sort_keys=True)
            values.append("" if value is None else str(value).replace("\t", " "))
        rows.append("\t".join(values))
    return "\n".join(rows) + "\n"


def write_outputs(
    input_root: str | Path,
    out_dir: str | Path,
    root: str | Path | None = None,
    runtime_authority: str | Path | None = None,
    active_match_execution: bool = False,
) -> dict[str, Any]:
    output_root = validate_output_root(out_dir, root=root)
    output_root.mkdir(parents=True, exist_ok=True)
    payload = build_inventory(input_root)

    if active_match_execution:
        if runtime_authority is None:
            payload["hard_block_hits"] = sorted(
                set(payload.get("hard_block_hits", [])) | {"runtime_authority_path_invalid"}
            )
            payload["status"] = "FAIL_CLOSED"
            payload["active_match_evidence_pass"] = False
        else:
            payload = apply_active_match_execution(payload, input_root, runtime_authority)

    paths = {name: output_root / filename for name, filename in OUTPUT_NAMES.items()}
    payload["outputs"] = {name: str(path) for name, path in paths.items()}

    paths["main"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    paths["inventory_json"].write_text(
        json.dumps(payload.get("files", []), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    paths["inventory_tsv"].write_text(inventory_tsv(payload), encoding="utf-8")
    paths["unsupported"].write_text(
        json.dumps(
            {
                "module_id": MODULE_ID,
                "unsupported_file_count": payload.get("unsupported_file_count", 0),
                "unresolved_unsupported_file_count": payload.get(
                    "unresolved_unsupported_file_count", 0
                ),
                "reference_only_unsupported_file_count": payload.get(
                    "reference_only_unsupported_file_count", 0
                ),
                "unsupported_files": payload.get("unsupported_files", []),
                "canonical_event_count": "UNKNOWN",
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    paths["duplicates"].write_text(
        json.dumps(
            {
                "module_id": MODULE_ID,
                **payload.get("duplicate_report", {}),
                "canonical_event_count": "UNKNOWN",
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    paths["decision_txt"].write_text(
        "\n".join(
            [
                "HPFA MULTIFORMAT INGEST DECISION V1",
                f"status={payload.get('status')}",
                f"total_file_path_count={payload.get('total_file_path_count')}",
                f"supported_file_count={payload.get('supported_file_count')}",
                f"unique_supported_content_file_count={payload.get('unique_content_file_count')}",
                f"unsupported_file_count={payload.get('unsupported_file_count')}",
                f"unresolved_unsupported_file_count={payload.get('unresolved_unsupported_file_count')}",
                f"reference_only_unsupported_file_count={payload.get('reference_only_unsupported_file_count')}",
                f"exact_duplicate_reflection_count={payload.get('duplicate_report', {}).get('exact_duplicate_reflection_count')}",
                f"hard_block_hits={payload.get('hard_block_hits')}",
                "canonical_event_count=UNKNOWN",
                f"active_match_evidence_pass={str(bool(payload.get('active_match_evidence_pass'))).lower()}",
                "production_release=false",
                "claim_ceiling=FILE_DISCOVERY_ONLY",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="HPFA multiformat file inventory lite v1")
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--runtime-authority")
    parser.add_argument("--active-match-execution", action="store_true")
    args = parser.parse_args()

    result = write_outputs(
        args.input_root,
        args.out,
        runtime_authority=args.runtime_authority,
        active_match_execution=args.active_match_execution,
    )
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "total_file_path_count": result.get("total_file_path_count"),
                "supported_file_count": result.get("supported_file_count"),
                "unique_supported_content_file_count": result.get("unique_content_file_count"),
                "unsupported_file_count": result.get("unsupported_file_count"),
                "unresolved_unsupported_file_count": result.get(
                    "unresolved_unsupported_file_count"
                ),
                "hard_block_hits": result.get("hard_block_hits"),
                "active_match_evidence_pass": result.get("active_match_evidence_pass"),
                "canonical_event_count": result.get("canonical_event_count"),
                "production_release": result.get("production_release"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result.get("status") != "FAIL_CLOSED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
