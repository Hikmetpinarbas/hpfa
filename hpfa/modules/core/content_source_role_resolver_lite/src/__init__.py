from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

CORE_ROOT = Path(__file__).resolve().parents[2]
XML_SRC = CORE_ROOT / "xml_surface_reader_lite" / "src"
if str(XML_SRC) not in sys.path:
    sys.path.insert(0, str(XML_SRC))

from hpfa.modules.core.triangulated_event_reflection_resolver_lite.src import (
    triangulated_event_reflection_resolver as reflection,
)

# Controlled compatibility adapter for the older reflection API present on the
# #181 line. It preserves candidate-only semantics and does not promote a
# fingerprint to physical-event identity.
if not hasattr(reflection, "FINGERPRINT_FIELDS"):
    reflection.FINGERPRINT_FIELDS = (
        "provider_row_id",
        "start",
        "end",
        "code",
        "team",
        "action",
        "half",
        "pos_x",
        "pos_y",
    )

    _ORIGINAL_READ_CSV_OR_TSV = reflection.read_csv_or_tsv

    def _text(value: Any) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    def _number(value: Any) -> str:
        text = str(value or "").strip().replace(",", ".")
        if not text:
            return ""
        try:
            number = Decimal(text)
        except InvalidOperation:
            return _text(text)
        normalized = format(number.normalize(), "f")
        if "." in normalized:
            normalized = normalized.rstrip("0").rstrip(".")
        return normalized or "0"

    def _canonicalize_row(row: dict[str, Any]) -> dict[str, Any]:
        lower = {str(key).strip().casefold(): value for key, value in row.items()}

        def first(*keys: str) -> Any:
            for key in keys:
                value = lower.get(key.casefold())
                if value not in (None, ""):
                    return value
            return ""

        code_raw = str(first("code")).strip()
        action_raw = str(
            first("action", "event_type", "label", "type", "subtype")
        ).strip()
        if code_raw and " - " in code_raw:
            suffix = code_raw.rsplit(" - ", 1)[-1].strip()
            if not action_raw or action_raw.casefold() == code_raw.casefold():
                action_raw = suffix

        # IMPORTANT: do not synthesize a direct `team` field from `code`.
        # SportsBase TEAM surfaces intentionally omit the Team column/label and
        # encode a team candidate in `code=<team> - <action>`.  Promoting that
        # embedded candidate into `team` destroys the structural distinction
        # used by the content source-role resolver and can misroute TEAM rows
        # into the PLAYER/GOALKEEPER structural pool.
        team_raw = str(first("team", "team_name", "team_raw")).strip()

        result = dict(row)
        result.update(
            {
                "provider_row_id": _text(first("provider_row_id", "id")),
                "start": _number(first("start", "start_time", "timestamp", "time")),
                "end": _number(first("end", "end_time")),
                "code": _text(code_raw),
                "team": _text(team_raw),
                "action": _text(action_raw),
                "half": _text(first("half", "period", "period_id")),
                "pos_x": _number(first("pos_x", "start_x", "x")),
                "pos_y": _number(first("pos_y", "start_y", "y")),
            }
        )
        return result

    def _read_csv_or_tsv_compat(
        path: Path,
        delimiter: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            _canonicalize_row(row)
            for row in _ORIGINAL_READ_CSV_OR_TSV(path, delimiter)
        ]

    def _local_name(tag: Any) -> str:
        return str(tag).rsplit("}", 1)[-1].rsplit(":", 1)[-1]

    def _label_group_text_compat(label: ET.Element) -> tuple[str, str] | None:
        group = ""
        text = ""
        for child in list(label):
            tag = _local_name(child.tag).casefold()
            value = (child.text or "").strip()
            if tag == "group":
                group = value
            elif tag == "text":
                text = value
        if not group or not text:
            return None
        return _text(group), text

    def _flatten_xml_instance_compat(instance: ET.Element) -> dict[str, Any]:
        raw: dict[str, Any] = {}
        labels: dict[str, str] = {}
        for child in list(instance):
            tag = _local_name(child.tag).casefold()
            value = (child.text or "").strip()
            if tag == "label":
                pair = _label_group_text_compat(child)
                if pair is not None:
                    labels.setdefault(pair[0], pair[1])
                continue
            if value:
                raw.setdefault(tag, value)
        for group, value in labels.items():
            raw.setdefault(group, value)
        return raw

    def _read_xml_compat(path: Path) -> list[dict[str, Any]]:
        try:
            root = ET.parse(path).getroot()
        except (OSError, ET.ParseError):
            return []
        rows: list[dict[str, Any]] = []
        for idx, instance in enumerate(root.iter()):
            if _local_name(instance.tag).casefold() != "instance":
                continue
            raw = _flatten_xml_instance_compat(instance)
            raw["_source_file"] = path.name
            raw["_source_format"] = "xml"
            raw["_source_row_index"] = idx
            rows.append(_canonicalize_row(raw))
        return rows

    reflection.read_csv_or_tsv = _read_csv_or_tsv_compat
    reflection.read_xml = _read_xml_compat
