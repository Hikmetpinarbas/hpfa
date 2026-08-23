from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "csv_surface_reader_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "CSV_SURFACE_AUDIT_ONLY"
OUT = {
    "main": "csv_surface_audit_lite_v1.json",
    "summary": "csv_surface_audit_lite_v1.txt",
    "analyst": "csv_surface_analyst_audit_lite_v1.txt",
}

ALIASES = {
    "team": {"team", "team_id", "team_name", "side", "home_away", "homeaway"},
    "action": {"type", "event", "event_type", "action", "action_type", "name", "label"},
    "subtype": {"subtype", "sub_type", "qualifier", "outcome", "result"},
    "period": {"period", "half", "period_id", "match_period"},
    "start": {"start_time_s", "start_time", "start_s", "start", "timestamp", "time", "period_time"},
    "end": {"end_time_s", "end_time", "end_s", "end"},
    "start_frame": {"start_frame", "frame_start"},
    "end_frame": {"end_frame", "frame_end"},
    "start_x": {"start_x", "x", "x1", "pos_x", "location_x"},
    "start_y": {"start_y", "y", "y1", "pos_y", "location_y"},
    "end_x": {"end_x", "x2", "to_x", "dest_x"},
    "end_y": {"end_y", "y2", "to_y", "dest_y"},
}

ACTION_MAP = {
    "PASS": "pass",
    "RECOVERY": "recovery",
    "BALL LOST": "loss",
    "CHALLENGE": "duel_candidate",
    "SHOT": "shot",
    "CARD": "card",
    "BALL OUT": "ball_out",
    "FAULT RECEIVED": "foul_received",
    "FOUL": "foul",
}
RESTART_MAP = {
    "KICK OFF": "kick_off",
    "FREE KICK": "free_kick",
    "THROW IN": "throw_in",
    "GOAL KICK": "goal_kick",
    "CORNER KICK": "corner",
    "CORNER": "corner",
}
NON_EVENT_SOURCE_ROLES = {
    "MANIFEST_SURFACE_CANDIDATE",
    "GOVERNANCE_MANIFEST_SURFACE",
}
TEAM_SURFACE_ROLE = "TEAM_SURFACE_CANDIDATE"


def norm(value: Any) -> str:
    text = str(value or "").strip().casefold()
    text = re.sub(r"\[\s*([^\]]+)\s*\]", r"_\1", text)
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", text)).strip("_")


def to_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text or text.casefold() in {"na", "nan", "null", "none", "n/a", "-"}:
        return None
    if "," in text and "." not in text:
        text = text.replace(" ", "").replace(",", ".")
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def encoding(path: Path) -> tuple[str, bool]:
    raw = path.read_bytes()
    bom_candidates = (
        (b"\x00\x00\xfe\xff", "utf-32"),
        (b"\xff\xfe\x00\x00", "utf-32"),
        (b"\xfe\xff", "utf-16"),
        (b"\xff\xfe", "utf-16"),
        (b"\xef\xbb\xbf", "utf-8-sig"),
    )
    for marker, candidate in bom_candidates:
        if raw.startswith(marker):
            raw.decode(candidate)
            return candidate, True
    for candidate in ("utf-8", "cp1252", "latin-1"):
        try:
            raw.decode(candidate)
            return candidate, False
        except UnicodeDecodeError:
            continue
    raise UnicodeError("encoding_unresolved")


def _candidate_widths(text: str, candidate: str, limit: int = 40) -> list[int]:
    widths: list[int] = []
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=candidate)
    try:
        for row in reader:
            if not any(value.strip() for value in row):
                continue
            widths.append(len(row))
            if len(widths) >= limit:
                break
    except csv.Error:
        return []
    return widths


def delimiter(text: str) -> str | None:
    if not text.strip():
        return None
    sample = text[:65536]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        best: tuple[float, str] | None = None
        for candidate in ",;\t|":
            widths = _candidate_widths(sample, candidate)
            if not widths or max(widths) <= 1:
                continue
            mode, count = Counter(widths).most_common(1)[0]
            score = count / len(widths) + mode / 1000
            if best is None or score > best[0]:
                best = (score, candidate)
        return best[1] if best else None


def _parse_records(text: str, detected_delimiter: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=detected_delimiter)
    previous_end_line = 0
    try:
        for row in reader:
            end_line = reader.line_num
            records.append(
                {
                    "start_line": previous_end_line + 1,
                    "end_line": end_line,
                    "row": row,
                }
            )
            previous_end_line = end_line
    except csv.Error as exc:
        raise ValueError("malformed_csv") from exc
    return records


def header_index(rows: list[list[str]]) -> int | None:
    for index, row in enumerate(rows[:25]):
        values = [value.strip() for value in row if value.strip()]
        if len(values) >= 2 and len({norm(value) for value in values}) >= 2:
            return index
    return None


def find(headers: list[str], key: str) -> int | None:
    for index, header in enumerate(headers):
        if norm(header) in ALIASES[key]:
            return index
    return None


def find_named_column(headers: list[str], names: set[str]) -> int | None:
    for index, header in enumerate(headers):
        if norm(header) in names:
            return index
    return None


def infer(values: list[str]) -> str:
    present = [value.strip() for value in values if value.strip()]
    if not present:
        return "unknown"
    if all(to_float(value) is not None for value in present):
        return "number"
    if all(
        value.casefold() in {"true", "false", "yes", "no", "evet", "hayir", "hayır"}
        for value in present
    ):
        return "boolean"
    return "string"


def semantic(normalized: str) -> tuple[str, str | None, str]:
    for key, aliases in ALIASES.items():
        if normalized not in aliases:
            continue
        if key.endswith(("_x", "_y")):
            family = "space"
        elif key in {"period", "start", "end", "start_frame", "end_frame"}:
            family = "time"
        elif key == "action":
            family = "action"
        elif key == "team":
            family = "actor"
        else:
            family = "outcome_or_qualifier"
        return family, f"event.{key}_candidate", "CANDIDATE_ALIAS"
    return "unknown", None, "UNKNOWN_ALIAS"


def profile(
    header: str,
    values: list[str],
    duplicate: bool,
    unnamed: bool,
) -> dict[str, Any]:
    normalized = norm(header)
    family, key, alias_status = semantic(normalized)
    present = [value.strip() for value in values if value.strip()]
    inferred = infer(values)
    numbers = [
        number
        for number in (to_float(value) for value in present)
        if number is not None
    ]
    warnings: list[str] = []
    if duplicate:
        warnings.append("duplicate_column_name")
    if unnamed:
        warnings.append("unnamed_column")
    return {
        "raw_column": header,
        "normalized_column": normalized,
        "raw_value_type": (
            "all_null"
            if not present
            else ("numeric_text" if inferred == "number" else "string_or_mixed_text")
        ),
        "inferred_type": inferred,
        "null_count": len(values) - len(present),
        "null_ratio": (len(values) - len(present)) / len(values) if values else 0.0,
        "unique_count": len(set(present)),
        "example_values": list(dict.fromkeys(present))[:5],
        "minimum": min(numbers) if inferred == "number" and numbers else None,
        "maximum": max(numbers) if inferred == "number" and numbers else None,
        "semantic_family_candidate": family,
        "canonical_key_candidate": key,
        "provider_alias_status": alias_status,
        "required_status": (
            "BUNDLE_CANDIDATE"
            if normalized in ALIASES["team"] | ALIASES["action"] | ALIASES["start"]
            else "OPTIONAL"
        ),
        "claim_ceiling": "FIELD_SURFACE_ONLY",
        "parse_warning": warnings,
    }


def action_record(raw_type: str, raw_subtype: str, count: int) -> dict[str, Any]:
    event_type = re.sub(r"\s+", " ", raw_type.strip().upper().replace("_", " "))
    subtype = re.sub(r"\s+", " ", raw_subtype.strip().upper().replace("_", " "))
    mapped = RESTART_MAP.get(subtype) if event_type == "SET PIECE" else ACTION_MAP.get(event_type)
    return {
        "raw_type": raw_type,
        "raw_subtype": raw_subtype,
        "canonical_action_family_candidate": mapped,
        "mapping_status": (
            "KNOWN_ALIAS"
            if mapped
            else (
                "AMBIGUOUS_ALIAS"
                if event_type == "SET PIECE" or not event_type
                else "UNKNOWN_ACTION"
            )
        ),
        "surface_row_volume": count,
        "claim_ceiling": "ACTION_FAMILY_CANDIDATE_ONLY",
    }


def coord_audit(
    rows: list[list[str]],
    indexes: dict[str, int | None],
) -> dict[str, Any]:
    values: defaultdict[str, list[float]] = defaultdict(list)
    missing: dict[str, int] = {}
    for key, index in indexes.items():
        if index is None:
            missing[key] = len(rows)
            continue
        for row in rows:
            number = to_float(row[index])
            if number is None:
                missing[key] = missing.get(key, 0) + 1
            else:
                values[key].append(number)

    all_values = [number for group in values.values() for number in group]
    if not all_values:
        return {
            "coordinate_scale_candidate": "UNKNOWN",
            "observed_min_max": {},
            "out_of_range_count": 0,
            "raw_coordinates_preserved": True,
            "clamp_applied": False,
            "team_direction_candidate": "UNKNOWN",
            "missing_coordinate_counts": missing,
            "missing_coordinates_action_family_aware": True,
        }

    minimum = min(all_values)
    x_values = values["start_x"] + values["end_x"]
    y_values = values["start_y"] + values["end_y"]
    x_max = max(x_values) if x_values else max(all_values)
    y_max = max(y_values) if y_values else max(all_values)
    if minimum >= -0.25 and x_max <= 1.25 and y_max <= 1.25:
        scale, upper_x, upper_y = "0_TO_1_CANDIDATE", 1, 1
    elif minimum >= -0.5 and x_max <= 100.5 and y_max <= 100.5:
        scale, upper_x, upper_y = "0_TO_100_CANDIDATE", 100, 100
    elif minimum >= -0.5 and x_max <= 105.5 and y_max <= 68.5:
        scale, upper_x, upper_y = "105_BY_68_CANDIDATE", 105, 68
    elif minimum >= -0.5 and x_max <= 120.5 and y_max <= 80.5:
        scale, upper_x, upper_y = "120_BY_80_CANDIDATE", 120, 80
    else:
        scale, upper_x, upper_y = "PROVIDER_SPECIFIC_OR_UNKNOWN", None, None

    out_of_range = 0
    if upper_x is not None:
        for key, group in values.items():
            upper = upper_x if key.endswith("x") else upper_y
            out_of_range += sum(
                1 for number in group if number < 0 or number > upper
            )

    return {
        "coordinate_scale_candidate": scale,
        "observed_min_max": {
            key: {"minimum": min(group), "maximum": max(group)}
            for key, group in values.items()
            if group
        },
        "out_of_range_count": out_of_range,
        "raw_coordinates_preserved": True,
        "clamp_applied": False,
        "team_direction_candidate": "UNKNOWN",
        "missing_coordinate_counts": missing,
        "missing_coordinates_action_family_aware": True,
    }


def _provider_id_candidate(team_token: str) -> str | None:
    match = re.search(r"\(([^()]*)\)\s*$", team_token)
    return match.group(1).strip() if match and match.group(1).strip() else None


def team_binding_audit(
    rows: list[list[str]],
    headers: list[str],
    indexes: dict[str, int | None],
    source_role: str,
) -> dict[str, Any]:
    team_index = indexes["team"]
    if team_index is not None:
        teams = sorted(
            {row[team_index].strip() for row in rows if row[team_index].strip()}
        )
        if not teams:
            return {
                "raw_team_values": [],
                "provider_team_id_candidates": [],
                "binding_status": "UNRESOLVED",
                "binding_evidence": {
                    "method": "DIRECT_TEAM_COLUMN_EMPTY",
                    "source_column": headers[team_index],
                },
                "home_away_used_as_final_identity": False,
            }
        home_away = {value.casefold() for value in teams} <= {"home", "away"}
        return {
            "raw_team_values": teams,
            "provider_team_id_candidates": sorted(
                {
                    value
                    for value in (_provider_id_candidate(team) for team in teams)
                    if value
                }
            ),
            "binding_status": (
                "HOME_AWAY_LABEL_NOT_FINAL_IDENTITY"
                if home_away
                else "CANDIDATE_ONLY"
            ),
            "binding_evidence": {
                "method": "DIRECT_TEAM_COLUMN",
                "source_column": headers[team_index],
            },
            "home_away_used_as_final_identity": False,
        }

    if source_role != TEAM_SURFACE_ROLE:
        return {
            "raw_team_values": [],
            "provider_team_id_candidates": [],
            "binding_status": "UNRESOLVED",
            "binding_evidence": {
                "method": "NO_DIRECT_TEAM_COLUMN",
                "source_column": None,
            },
            "home_away_used_as_final_identity": False,
        }

    code_index = find_named_column(headers, {"code"})
    action_index = indexes["action"]
    candidates: set[str] = set()
    matched_rows = 0
    if code_index is not None and action_index is not None:
        for row in rows:
            code = row[code_index].strip()
            action = row[action_index].strip()
            if not code or not action:
                continue
            exact_suffix = f" - {action}"
            if not code.endswith(exact_suffix):
                continue
            prefix = code[: -len(exact_suffix)].strip()
            if not prefix:
                continue
            candidates.add(prefix)
            matched_rows += 1

    if candidates:
        return {
            "raw_team_values": sorted(candidates),
            "provider_team_id_candidates": sorted(
                {
                    value
                    for value in (
                        _provider_id_candidate(team) for team in candidates
                    )
                    if value
                }
            ),
            "binding_status": "EMBEDDED_CODE_TEAM_CANDIDATE",
            "binding_evidence": {
                "method": "CODE_PREFIX_BEFORE_EXACT_ACTION_SUFFIX",
                "source_column": headers[code_index] if code_index is not None else None,
                "action_column": (
                    headers[action_index] if action_index is not None else None
                ),
                "matched_surface_row_count": matched_rows,
                "candidate_only": True,
            },
            "home_away_used_as_final_identity": False,
        }

    return {
        "raw_team_values": [],
        "provider_team_id_candidates": [],
        "binding_status": "UNRESOLVED",
        "binding_evidence": {
            "method": "EMBEDDED_TEAM_CANDIDATE_NOT_FOUND",
            "source_column": headers[code_index] if code_index is not None else None,
            "action_column": headers[action_index] if action_index is not None else None,
        },
        "home_away_used_as_final_identity": False,
    }


def inspect_csv_file(
    path: str | Path,
    source_role: str = "EVENT_ROW_OR_TABULAR_SURFACE_CANDIDATE",
) -> dict[str, Any]:
    csv_path = Path(path)
    base = {
        "file_name": csv_path.name,
        "path": str(csv_path),
        "source_role": source_role,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
    hard_blocks: list[str] = []
    warnings: list[str] = []

    try:
        detected_encoding, bom_present = encoding(csv_path)
        text = csv_path.read_text(encoding=detected_encoding)
    except (OSError, UnicodeError):
        return base | {
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["file_unreadable_or_encoding_unresolved"],
            "parse_warnings": [],
        }

    detected_delimiter = delimiter(text)
    if not detected_delimiter:
        return base | {
            "status": "FAIL_CLOSED",
            "encoding_candidate": detected_encoding,
            "bom_present": bom_present,
            "delimiter_candidate": None,
            "hard_block_hits": ["delimiter_unresolved"],
            "parse_warnings": [],
        }

    try:
        records = _parse_records(text, detected_delimiter)
    except ValueError:
        return base | {
            "status": "FAIL_CLOSED",
            "encoding_candidate": detected_encoding,
            "bom_present": bom_present,
            "delimiter_candidate": detected_delimiter,
            "hard_block_hits": ["malformed_csv"],
            "parse_warnings": [],
        }

    all_rows = [record["row"] for record in records]
    header_record_index = header_index(all_rows)
    if header_record_index is None:
        return base | {
            "status": "FAIL_CLOSED",
            "encoding_candidate": detected_encoding,
            "bom_present": bom_present,
            "delimiter_candidate": detected_delimiter,
            "hard_block_hits": ["header_not_found"],
            "parse_warnings": [],
        }

    header_record = records[header_record_index]
    headers = [str(value) for value in header_record["row"]]
    body_records = [
        record
        for record in records[header_record_index + 1 :]
        if any(value.strip() for value in record["row"])
    ]
    width = len(headers)
    malformed = [
        record["start_line"]
        for record in body_records
        if len(record["row"]) != width
    ]
    if malformed:
        hard_blocks.append("row_width_mismatch")

    normalized_headers = [norm(value) for value in headers]
    repeated = [
        record["start_line"]
        for record in body_records
        if [norm(value) for value in record["row"]] == normalized_headers
    ]
    repeated_set = set(repeated)
    clean_records = [
        record
        for record in body_records
        if record["start_line"] not in repeated_set
        and len(record["row"]) == width
    ]
    clean = [record["row"] for record in clean_records]

    duplicate_names = {
        name
        for name, count in Counter(normalized_headers).items()
        if name and count > 1
    }
    unnamed = [
        index
        for index, value in enumerate(headers)
        if not value.strip() or norm(value).startswith("unnamed")
    ]
    if duplicate_names:
        warnings.append("duplicate_column_names")
    if unnamed:
        warnings.append("unnamed_columns")

    columns = [[row[index] for row in clean] for index in range(width)]
    profiles = [
        profile(
            headers[index],
            columns[index],
            normalized_headers[index] in duplicate_names,
            index in unnamed,
        )
        for index in range(width)
    ]
    indexes = {key: find(headers, key) for key in ALIASES}
    event_surface = source_role not in NON_EVENT_SOURCE_ROLES
    binding = team_binding_audit(clean, headers, indexes, source_role)
    if event_surface and binding["binding_status"] == "UNRESOLVED":
        hard_blocks.append("team_field_unusable")
    if event_surface and indexes["action"] is None:
        hard_blocks.append("action_field_unusable")
    if event_surface and indexes["start"] is None:
        hard_blocks.append("time_field_unusable")

    periods: set[str] = set()
    previous_by_period: dict[str, float] = {}
    monotonic_violations: list[int] = []
    negative_duration_rows: list[int] = []
    zero_duration_rows: list[int] = []
    timestamp_groups: defaultdict[tuple[str, float], list[int]] = defaultdict(list)

    for record in clean_records:
        row_number = int(record["start_line"])
        row = record["row"]
        period = (
            row[indexes["period"]].strip()
            if indexes["period"] is not None
            else "UNKNOWN"
        )
        periods.add(period)
        start = (
            to_float(row[indexes["start"]])
            if indexes["start"] is not None
            else None
        )
        end = (
            to_float(row[indexes["end"]])
            if indexes["end"] is not None
            else None
        )
        if start is not None:
            if period in previous_by_period and start < previous_by_period[period]:
                monotonic_violations.append(row_number)
            previous_by_period[period] = start
            timestamp_groups[(period, start)].append(row_number)
        if start is not None and end is not None:
            duration = end - start
            if duration < 0:
                negative_duration_rows.append(row_number)
            if abs(duration) < 1e-12:
                zero_duration_rows.append(row_number)

    if negative_duration_rows:
        hard_blocks.append("negative_duration_unreviewed")
    if monotonic_violations:
        warnings.append("period_time_non_monotonic")

    action_counts = (
        Counter(
            (
                row[indexes["action"]].strip(),
                (
                    row[indexes["subtype"]].strip()
                    if indexes["subtype"] is not None
                    else ""
                ),
            )
            for row in clean
        )
        if indexes["action"] is not None
        else Counter()
    )
    exact_duplicates = sum(
        count - 1
        for count in Counter(tuple(row) for row in clean).values()
        if count > 1
    )
    flattened = [value for column in columns for value in column]
    dot_count = sum(
        bool(re.fullmatch(r"[-+]?\d+\.\d+", value.strip()))
        for value in flattened
    )
    comma_count = sum(
        bool(re.fullmatch(r"[-+]?\d+,\d+", value.strip()))
        for value in flattened
    )
    status = "REVIEW_REQUIRED" if hard_blocks or warnings else "PASS"

    return base | {
        "status": status,
        "encoding_candidate": detected_encoding,
        "bom_present": bom_present,
        "delimiter_candidate": detected_delimiter,
        "decimal_style_candidate": (
            "MIXED"
            if dot_count and comma_count
            else ("DOT" if dot_count else ("COMMA" if comma_count else "UNKNOWN"))
        ),
        "quote_character_candidate": '"' if '"' in text else None,
        "header_row_index": header_record["start_line"],
        "blank_leading_row_count": sum(
            1
            for record in records[:header_record_index]
            if not any(value.strip() for value in record["row"])
        ),
        "raw_columns": headers,
        "normalized_columns": normalized_headers,
        "visible_column_count": width,
        "surface_row_count": len(body_records),
        "profiled_row_count": len(clean_records),
        "repeated_header_row_indices": repeated,
        "malformed_row_indices": malformed,
        "variable_column_count_detected": bool(malformed),
        "trailing_separator_candidate": bool(headers and not headers[-1].strip()),
        "unnamed_column_indices": unnamed,
        "duplicate_column_names": sorted(duplicate_names),
        "column_profiles": profiles,
        "field_bundle": {
            key: (headers[index] if index is not None else None)
            for key, index in indexes.items()
        },
        "time_audit": {
            "raw_time_preserved": True,
            "time_base_assumed_zero": False,
            "half_threshold_hardcoded": False,
            "period_values": sorted(periods),
            "period_time_monotonic": not monotonic_violations,
            "monotonic_violation_rows": monotonic_violations,
            "negative_duration_count": len(negative_duration_rows),
            "negative_duration_rows": negative_duration_rows,
            "zero_duration_count": len(zero_duration_rows),
            "zero_duration_automatically_invalid": False,
            "duplicate_timestamp_group_count": sum(
                1 for rows in timestamp_groups.values() if len(rows) > 1
            ),
            "multi_event_timestamp_automatic_duplicate": False,
            "extra_time_candidate": any(
                value not in {"", "UNKNOWN", "1", "2", "1.0", "2.0"}
                for value in periods
            ),
            "frame_rate_assumed": False,
        },
        "coordinate_audit": coord_audit(
            clean,
            {
                key: indexes[key]
                for key in ("start_x", "start_y", "end_x", "end_y")
            },
        ),
        "team_binding": binding,
        "action_taxonomy": [
            action_record(raw_type, raw_subtype, count)
            for (raw_type, raw_subtype), count in action_counts.most_common()
        ],
        "exact_duplicate_row_count": exact_duplicates,
        "duplicate_primary_surface_key": "NOT_EVALUATED_IDENTITY_REQUIRED",
        "hard_block_hits": sorted(set(hard_blocks)),
        "parse_warnings": sorted(set(warnings)),
        "does_not_measure": [
            "canonical_event_truth",
            "validated_team_identity",
            "validated_player_identity",
            "sequence_truth",
            "phase_truth",
            "tactical_truth",
        ],
    }


def representatives(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {
        str(item.get("file_id")): item
        for item in inventory.get("files", [])
    }
    configured = inventory.get("inventory_representatives") or []
    if configured:
        return [
            item
            for item in (
                by_id.get(str(record.get("representative_file_id")))
                for record in configured
            )
            if item
            and item.get("extension") in {".csv", ".tsv"}
            and item.get("source_role") != "MANIFEST_SURFACE_CANDIDATE"
        ]

    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in inventory.get("files", []):
        if (
            item.get("extension") not in {".csv", ".tsv"}
            or item.get("source_role") == "MANIFEST_SURFACE_CANDIDATE"
        ):
            continue
        key = item.get("sha256") or item.get("relative_path")
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def build_csv_surface_audit(
    input_root: str | Path,
    inventory: dict[str, Any],
) -> dict[str, Any]:
    root = Path(input_root).expanduser().resolve(strict=False)
    if not root.is_dir():
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["input_root_missing"],
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "active_match_evidence_pass": False,
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    files: list[dict[str, Any]] = []
    for item in representatives(inventory):
        result = inspect_csv_file(
            root / str(item.get("relative_path")),
            str(item.get("source_role") or "UNKNOWN"),
        )
        result.update(
            {
                "file_id": item.get("file_id"),
                "relative_path": item.get("relative_path"),
                "sha256": item.get("sha256"),
            }
        )
        files.append(result)

    hard_blocks = sorted(
        {
            block
            for result in files
            for block in result.get("hard_block_hits", [])
        }
    )
    if not files or all(result.get("status") == "FAIL_CLOSED" for result in files):
        status = "FAIL_CLOSED"
    elif hard_blocks or any(
        result.get("status") == "REVIEW_REQUIRED" for result in files
    ):
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return {
        "module_id": MODULE_ID,
        "status": status,
        "input_root": str(root),
        "csv_file_count": len(files),
        "files": files,
        "hard_block_hits": hard_blocks or ([] if files else ["csv_surface_missing"]),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "active_match_evidence_pass": False,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
        "analyst_evidence": {
            "visible_csv_surfaces": len(files),
            "safe_statement": (
                "Visible CSV surfaces were profiled; event identity and tactical "
                "truth remain unresolved."
            ),
        },
    }


def validate_out(out_dir: str | Path) -> Path:
    path = Path(out_dir).expanduser().resolve(strict=False)
    if "HPFA" in path.parts and path.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return path


def is_active(path: Path) -> bool:
    return path.as_posix().rstrip("/").endswith(
        "runtime/active_single_match/current"
    )


def write_outputs(
    input_root: str | Path,
    inventory_path: str | Path,
    out_dir: str | Path,
) -> dict[str, Any]:
    output_root = validate_out(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    payload = build_csv_surface_audit(
        input_root,
        json.loads(Path(inventory_path).read_text(encoding="utf-8")),
    )
    payload["active_match_evidence_pass"] = (
        payload.get("status") != "FAIL_CLOSED"
        and not payload.get("hard_block_hits")
        and is_active(Path(input_root).resolve(strict=False))
    )
    paths = {key: output_root / value for key, value in OUT.items()}
    payload["outputs"] = {key: str(value) for key, value in paths.items()}
    paths["main"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    paths["summary"].write_text(render_summary(payload), encoding="utf-8")
    paths["analyst"].write_text(render_analyst(payload), encoding="utf-8")
    return payload


def render_summary(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "HPFA CSV SURFACE READER LITE V1",
            f"status={payload.get('status')}",
            f"csv_file_count={payload.get('csv_file_count')}",
            f"hard_block_hits={payload.get('hard_block_hits')}",
            f"active_match_evidence_pass={payload.get('active_match_evidence_pass')}",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
            "claim_ceiling=CSV_SURFACE_AUDIT_ONLY",
            "",
        ]
    )


def render_analyst(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA CSV SURFACE ANALYST AUDIT LITE V1",
        f"status={payload.get('status')}",
        f"visible_csv_surfaces={payload.get('csv_file_count')}",
    ]
    for result in payload.get("files", []):
        lines += [
            "",
            f"file={result.get('relative_path')}",
            f"source_role={result.get('source_role')}",
            f"surface_rows={result.get('surface_row_count')}",
            f"columns={result.get('visible_column_count')}",
            f"time_audit={result.get('time_audit')}",
            f"coordinate_audit={result.get('coordinate_audit')}",
            f"team_binding={result.get('team_binding')}",
            f"hard_block_hits={result.get('hard_block_hits')}",
        ]
    return "\n".join(
        lines
        + [
            "",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
            (
                "safe_statement=visible CSV surface contains row-level evidence; "
                "canonical event truth remains unresolved."
            ),
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = write_outputs(args.input_root, args.inventory, args.out)
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "csv_file_count",
                    "hard_block_hits",
                    "active_match_evidence_pass",
                    "canonical_event_count",
                    "production_release",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
