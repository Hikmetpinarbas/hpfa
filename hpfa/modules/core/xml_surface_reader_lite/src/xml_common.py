from __future__ import annotations

import codecs
import json
import re
from pathlib import Path
from typing import Any

MODULE_ID = "xml_surface_reader_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "XML_SURFACE_AUDIT_ONLY"
MAX_XML_FILE_BYTES = 64 * 1024 * 1024
MAX_XML_ELEMENTS = 1_000_000
MAX_XML_DEPTH = 128
MAX_XML_ATTRIBUTES_PER_ELEMENT = 256
MAX_XML_TEXT_CHARS = 1_000_000
MAX_XML_ROW_CANDIDATES = 500_000
MAX_FIELD_PATHS = 5_000
OUT = {
    "main": "xml_surface_audit_lite_v1.json",
    "summary": "xml_surface_audit_lite_v1.txt",
    "analyst": "xml_surface_analyst_audit_lite_v1.txt",
}
PREFERRED_ROW_TAGS = {"instance", "event", "row", "record", "entry", "item", "action"}
ROLE_ALIASES = {
    "player": {"player", "player_name", "player_id", "athlete", "athlete_id"},
    "team": {"team", "team_name", "team_id", "club", "side"},
    "action": {"action", "event", "event_type", "type", "subtype", "label"},
    "code": {"code", "event_code", "action_code"},
    "period": {"period", "half"},
    "time": {"time", "timestamp", "minute", "second", "start_time", "end_time"},
    "x_coordinate": {"x", "x_coordinate", "start_x", "end_x"},
    "y_coordinate": {"y", "y_coordinate", "start_y", "end_y"},
}


class XmlSurfaceError(ValueError):
    pass


def local_name(tag: Any) -> str:
    text = str(tag or "")
    return text.split("}", 1)[-1] if "}" in text else text


def namespace_uri(tag: Any) -> str | None:
    text = str(tag or "")
    return text[1:].split("}", 1)[0] if text.startswith("{") and "}" in text else None


def norm(value: Any) -> str:
    text = str(value or "").strip().casefold().replace("%", " percent ")
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w]+", "_", text, flags=re.UNICODE)
    return re.sub(r"_+", "_", text).strip("_")


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def xml_text_candidates(raw: bytes) -> list[str]:
    encodings: list[str] = []
    if raw.startswith(codecs.BOM_UTF32_LE) or raw.startswith(codecs.BOM_UTF32_BE):
        encodings.append("utf-32")
    elif raw.startswith(codecs.BOM_UTF16_LE) or raw.startswith(codecs.BOM_UTF16_BE):
        encodings.append("utf-16")
    elif raw.startswith(codecs.BOM_UTF8):
        encodings.append("utf-8-sig")
    prefix = raw[:4]
    if prefix == b"\x00\x00\x00<":
        encodings.append("utf-32-be")
    elif prefix == b"<\x00\x00\x00":
        encodings.append("utf-32-le")
    elif raw[:2] == b"\x00<":
        encodings.append("utf-16-be")
    elif raw[:2] == b"<\x00":
        encodings.append("utf-16-le")
    encodings.extend(["utf-8", "utf-16-le", "utf-16-be", "utf-32-le", "utf-32-be"])
    result: list[str] = []
    seen: set[str] = set()
    for encoding in encodings:
        if encoding in seen:
            continue
        seen.add(encoding)
        try:
            result.append(raw.decode(encoding))
        except UnicodeDecodeError:
            pass
    return result


def security_guard(path: Path) -> dict[str, Any]:
    try:
        size = path.stat().st_size
        raw = path.read_bytes()
    except OSError as exc:
        raise XmlSurfaceError("xml_file_unreadable") from exc
    if size == 0:
        raise XmlSurfaceError("empty_xml_file")
    if size > MAX_XML_FILE_BYTES:
        raise XmlSurfaceError("xml_file_size_budget_exceeded")
    forbidden = (("<!" + "DOCTYPE"), ("<!" + "ENTITY"))
    if any(token in text.upper() for text in xml_text_candidates(raw) for token in forbidden):
        raise XmlSurfaceError("external_entity_resolution_attempted")
    return {
        "file_size_bytes": size,
        "dtd_or_entity_declaration_present": False,
        "external_entity_resolution_performed": False,
        "status": "PASS",
    }


def resolve_inventory_path(root: Path, relative_path: Any) -> Path:
    raw = str(relative_path or "").strip()
    if not raw:
        raise XmlSurfaceError("inventory_relative_path_missing")
    relative = Path(raw)
    if relative.is_absolute():
        raise XmlSurfaceError("inventory_relative_path_absolute_rejected")
    candidate = (root / relative).resolve(strict=False)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise XmlSurfaceError("inventory_relative_path_outside_input_root") from exc
    return candidate


def representatives(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    files = inventory.get("files", [])
    by_id = {str(item.get("file_id")): item for item in files}
    configured = inventory.get("inventory_representatives") or []
    if configured:
        chosen = [by_id.get(str(row.get("representative_file_id"))) for row in configured]
        return [item for item in chosen if item and str(item.get("extension")).casefold() == ".xml"]
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in files:
        if str(item.get("extension")).casefold() != ".xml":
            continue
        key = str(item.get("sha256") or item.get("relative_path"))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def role_for_field(field_path: str) -> str | None:
    token = norm(field_path.rsplit(".", 1)[-1].lstrip("@"))
    return next((role for role, aliases in ROLE_ALIASES.items() if token in aliases), None)


def validate_out(out_dir: str | Path) -> Path:
    path = Path(out_dir).expanduser().resolve(strict=False)
    if "HPFA" in path.parts and path.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return path


def is_active(path: Path) -> bool:
    return path.as_posix().rstrip("/").endswith("runtime/active_single_match/current")
