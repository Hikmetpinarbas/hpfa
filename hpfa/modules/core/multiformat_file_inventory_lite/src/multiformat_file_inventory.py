from __future__ import annotations

import codecs
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

_IMPLEMENTATION_PATH = Path(__file__).with_name("multiformat_file_inventory_impl.py")
_IMPLEMENTATION_MODULE_NAME = "_hpfa_multiformat_file_inventory_core"
_FORBIDDEN_XML_DECLARATIONS = ("<!DOCTYPE", "<!ENTITY")


def _load_implementation() -> ModuleType:
    existing = sys.modules.get(_IMPLEMENTATION_MODULE_NAME)
    if existing is not None:
        return existing

    spec = importlib.util.spec_from_file_location(
        _IMPLEMENTATION_MODULE_NAME,
        _IMPLEMENTATION_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(
            f"unable_to_load_multiformat_file_inventory_core:{_IMPLEMENTATION_PATH}"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[_IMPLEMENTATION_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(_IMPLEMENTATION_MODULE_NAME, None)
        raise
    return module


def _xml_text_candidates(raw: bytes) -> list[str]:
    encodings: list[str] = []

    # BOM order matters because the UTF-32 LE BOM begins with the UTF-16 LE BOM.
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

    encodings.extend(
        (
            "utf-8",
            "utf-16-le",
            "utf-16-be",
            "utf-32-le",
            "utf-32-be",
        )
    )

    candidates: list[str] = []
    seen: set[str] = set()
    for encoding in encodings:
        if encoding in seen:
            continue
        seen.add(encoding)
        try:
            candidates.append(raw.decode(encoding))
        except (UnicodeDecodeError, UnicodeError):
            continue
    return candidates


def _contains_forbidden_xml_declaration(raw: bytes) -> bool:
    # Preserve the original fast path for ASCII-compatible XML.
    upper_raw = raw.upper()
    if any(marker.encode("ascii") in upper_raw for marker in _FORBIDDEN_XML_DECLARATIONS):
        return True

    # UTF-16/32 encodings interleave NUL bytes around ASCII markup. This
    # normalized byte view is a defense-in-depth check before decoding.
    compact_upper = raw.replace(b"\x00", b"").upper()
    if any(marker.encode("ascii") in compact_upper for marker in _FORBIDDEN_XML_DECLARATIONS):
        return True

    for text in _xml_text_candidates(raw):
        upper_text = text.upper()
        if any(marker in upper_text for marker in _FORBIDDEN_XML_DECLARATIONS):
            return True
    return False


def _blocked_xml_metadata() -> dict[str, Any]:
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


_impl = _load_implementation()
_original_xml_metadata = _impl.xml_metadata


def xml_metadata(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if _contains_forbidden_xml_declaration(raw):
        return _blocked_xml_metadata()
    return _original_xml_metadata(path)


# Patch the implementation module itself so functions defined there, including
# build_inventory(), resolve this hardened XML gate through their own globals.
_impl.xml_metadata = xml_metadata

for _name in dir(_impl):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_impl, _name)


if __name__ == "__main__":
    raise SystemExit(_impl.main())
