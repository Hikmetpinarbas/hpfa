from __future__ import annotations

import re
import sys
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
    _ORIGINAL_READ_XML = reflection.read_xml

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

        team_raw = str(first("team", "team_name", "team_raw")).strip()
        if not team_raw and code_raw and action_raw:
            suffix = f" - {action_raw}"
            if code_raw.casefold().endswith(suffix.casefold()):
                team_raw = code_raw[: -len(suffix)].strip()

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

    def _read_xml_compat(path: Path) -> list[dict[str, Any]]:
        return [_canonicalize_row(row) for row in _ORIGINAL_READ_XML(path)]

    reflection.read_csv_or_tsv = _read_csv_or_tsv_compat
    reflection.read_xml = _read_xml_compat
