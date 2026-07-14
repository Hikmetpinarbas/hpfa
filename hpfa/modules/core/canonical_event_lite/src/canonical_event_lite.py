from __future__ import annotations

import csv
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "canonical_event_lite_v1"
CLAIM_SAFETY = "EVIDENCE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
DEDUPLICATED_EVENT_COUNT = "UNKNOWN"
PRIMARY_EVENT_SURFACE_CANDIDATE = "UNRESOLVED"
EVENT_COUNT_CLAIM_ALLOWED = False

OUTPUT_JSON = "canonical_event_lite_v1.json"
OUTPUT_TSV = "canonical_event_lite_v1.tsv"
AUDIT_JSON = "canonical_event_lite_audit_v1.json"
AUDIT_TXT = "canonical_event_lite_audit_v1.txt"

SYNONYMS = {
    "source_event_id": ["id", "event_id", "event id", "source_event_id"],
    "event_type": ["action", "event", "event_type", "type", "name", "title", "action_name", "event name", "action type", "event type"],
    "team": ["team", "team_name", "squad", "club", "side", "participant", "team_id", "team id"],
    "player": ["player", "player_name", "athlete", "player id", "player_id"],
    "minute": ["minute", "min", "match_minute", "match minute"],
    "second": ["second", "sec", "match_second", "match second"],
    "timestamp": ["time", "timestamp", "match_time", "match time", "period_time"],
    "start": ["start", "start_time", "start time"],
    "end": ["end", "end_time", "end time"],
    "code": ["code"],
    "period": ["half", "period", "period_id", "period id"],
    "x": ["x", "start_x", "x1", "x_coord", "x coordinate", "x_coordinate", "location_x", "pos_x", "coord_x", "coordinate_x", "start x", "location x", "x start"],
    "y": ["y", "start_y", "y1", "y_coord", "y coordinate", "y_coordinate", "location_y", "pos_y", "coord_y", "coordinate_y", "start y", "location y", "y start"],
}

OUTPUT_FIELDS = [
    "source_file","source_format","source_role","source_sheet","source_row_index",
    "source_event_id_raw","event_type_raw","event_family","team_raw","team_normalized",
    "player_raw","minute_raw","second_raw","timestamp_raw","start_raw","end_raw",
    "duration_seconds_candidate","code_raw","period_raw","period_candidate",
    "x_raw","y_raw","x_meters","y_meters","coordinate_system_candidate",
    "coordinate_frame_status","attacking_direction_candidate","directional_features_allowed",
    "source_labels_raw","source_extra_fields","row_claim_safety","row_warnings",
]

def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]

def _ensure_module_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

def _spine_runner_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    _ensure_module_path(src)
    import spine_runner  # type: ignore
    return spine_runner

def normalize_header(value: str) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[\s\-\./]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")

def _synonym_index() -> dict[str, str]:
    idx: dict[str, str] = {}
    for canonical, values in SYNONYMS.items():
        for value in values:
            idx[normalize_header(value)] = canonical
    return idx

SYNONYM_INDEX = _synonym_index()

def source_format(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    return "xlsx" if suffix in {"xlsx", "xlsm"} else suffix

def source_role(path: Path) -> str:
    name = path.name.lower()
    if "goalkeeper" in name:
        return "goalkeepers"
    if "player" in name:
        return "players"
    if "team" in name:
        return "teams"
    return "unknown"

def detect_columns(headers: list[str]) -> dict[str, str | None]:
    detected: dict[str, str | None] = {key: None for key in SYNONYMS}
    for header in headers:
        canonical = SYNONYM_INDEX.get(normalize_header(header))
        if canonical and detected[canonical] is None:
            detected[canonical] = header
    return detected

def _detect_sep(path: Path) -> str:
    with path.open("r", encoding="utf-8-sig", errors="ignore") as f:
        first = f.readline()
    candidates = [",", ";", "\t", "|"]
    return max(candidates, key=lambda sep: first.count(sep))

def read_csv_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    sep = _detect_sep(path)
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        reader = csv.DictReader(f, delimiter=sep, restkey="__overflow__")
        rows = [dict(row) for row in reader]
        headers = list(reader.fieldnames or [])
    return rows, headers

def _local(tag: str) -> str:
    return str(tag).split("}")[-1]

def _label_record(node: ET.Element) -> dict[str, Any]:
    record: dict[str, Any] = {"attributes": dict(node.attrib)}
    direct = (node.text or "").strip()
    if direct:
        record["text"] = direct
    for child in list(node):
        key = _local(child.tag)
        value = (child.text or "").strip()
        if value:
            if key in record:
                current = record[key]
                record[key] = current + [value] if isinstance(current, list) else [current, value]
            else:
                record[key] = value
        if child.attrib:
            record[f"{key}_attributes"] = dict(child.attrib)
    return record

def read_xml_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return [], []
    instances = [n for n in root.iter() if _local(n.tag).lower() == "instance"]
    nodes = instances if instances else [
        n for n in root.iter() if _local(n.tag).lower() in {"event", "action"}
    ]
    rows: list[dict[str, Any]] = []
    for node in nodes:
        row: dict[str, Any] = {str(k): v for k, v in node.attrib.items()}
        labels: list[dict[str, Any]] = []
        extra_children: dict[str, Any] = {}
        for child in list(node):
            key = _local(child.tag)
            if key.lower() == "label":
                labels.append(_label_record(child))
                continue
            text = (child.text or "").strip()
            if text:
                if key in row:
                    current = row[key]
                    row[key] = current + [text] if isinstance(current, list) else [current, text]
                else:
                    row[key] = text
            if child.attrib:
                extra_children[f"{key}_attributes"] = dict(child.attrib)
        if labels:
            row["__labels__"] = labels
        if extra_children:
            row["__xml_child_attributes__"] = extra_children
        row["__xml_node__"] = _local(node.tag)
        rows.append(row)
    headers = sorted({str(k) for row in rows for k in row.keys()})
    return rows, headers

_CELL_RE = re.compile(r"([A-Z]+)(\d+)$")

def _col_index(cell_ref: str) -> int:
    match = _CELL_RE.match(cell_ref.upper())
    if not match:
        return 0
    letters = match.group(1)
    value = 0
    for char in letters:
        value = value * 26 + (ord(char) - 64)
    return value - 1

def _xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    shared: list[str] = []
    if "xl/sharedStrings.xml" not in zf.namelist():
        return shared
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    for si in root.iter():
        if _local(si.tag) == "si":
            texts = [t.text or "" for t in si.iter() if _local(t.tag) == "t"]
            shared.append("".join(texts))
    return shared

def _xlsx_cell_value(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(t.text or "" for t in cell.iter() if _local(t.tag) == "t")
    raw = ""
    for child in list(cell):
        if _local(child.tag) == "v":
            raw = child.text or ""
            break
    if cell_type == "s":
        try:
            return shared[int(raw)]
        except Exception:
            return raw
    if cell_type == "b":
        return "TRUE" if raw == "1" else "FALSE"
    return raw

def read_xlsx_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        with zipfile.ZipFile(path) as zf:
            shared = _xlsx_shared_strings(zf)
            sheets = sorted(
                n for n in zf.namelist()
                if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
            )
            all_rows: list[dict[str, Any]] = []
            all_headers: list[str] = []
            for sheet_name in sheets:
                root = ET.fromstring(zf.read(sheet_name))
                table: list[list[str]] = []
                for row_node in root.iter():
                    if _local(row_node.tag) != "row":
                        continue
                    indexed: dict[int, str] = {}
                    max_idx = -1
                    for cell in list(row_node):
                        if _local(cell.tag) != "c":
                            continue
                        idx = _col_index(cell.attrib.get("r", ""))
                        indexed[idx] = _xlsx_cell_value(cell, shared)
                        max_idx = max(max_idx, idx)
                    if max_idx >= 0:
                        table.append([indexed.get(i, "") for i in range(max_idx + 1)])
                if not table:
                    continue
                headers = [str(h).strip() or f"column_{i+1}" for i, h in enumerate(table[0])]
                if not all_headers:
                    all_headers = list(headers)
                for raw_row in table[1:]:
                    row = {headers[i]: raw_row[i] if i < len(raw_row) else "" for i in range(len(headers))}
                    row["__source_sheet__"] = sheet_name
                    all_rows.append(row)
                for header in headers:
                    if header not in all_headers:
                        all_headers.append(header)
            return all_rows, all_headers
    except Exception:
        return [], []

def read_surface(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    fmt = source_format(path)
    if fmt == "csv":
        return read_csv_rows(path)
    if fmt == "xml":
        return read_xml_rows(path)
    if fmt == "xlsx":
        return read_xlsx_rows(path)
    return [], []

def first_value(row: dict[str, Any], column: str | None) -> str | None:
    if not column:
        return None
    value = row.get(column)
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None

def to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None

def normalize_team(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", value).strip()

def normalize_event_family(raw: str | None) -> str:
    text = (raw or "").strip().upper().replace("-", " ").replace("_", " ")
    if not text:
        return "UNKNOWN_OR_OTHER"
    if "PASS" in text:
        return "PASS"
    if "SHOT" in text or "ATTEMPT" in text:
        return "SHOT"
    if any(token in text for token in ("DUEL","PRESS","CHALLENGE","TACKLE")):
        return "DUEL_PRESSURE"
    if any(token in text for token in ("CARRY","DRIB","RUN")):
        return "CARRY_DRIBBLE"
    if any(token in text for token in ("LOSS","LOST","TURNOVER")):
        return "BALL_LOSS"
    if any(token in text for token in ("RECOVER","INTERCEPTION","INTERCEPT")):
        return "RECOVERY"
    if "FOUL" in text:
        return "FOUL"
    if any(token in text for token in ("GOAL KICK","RESTART","THROW","CORNER","FREE KICK")):
        return "GOALKEEPER_RESTART"
    if any(token in text for token in ("POSITIONAL ATTACK","FINAL THIRD","PENALTY BOX")):
        return "POSITIONAL_ATTACK_SIGNAL"
    return "UNKNOWN_OR_OTHER"

def coordinate_with_warning(value: str | None, axis: str) -> tuple[float | None, list[str]]:
    number = to_float(value)
    if number is None:
        return None, [f"missing_{axis}"]
    max_val = 105.0 if axis == "x" else 68.0
    if 0.0 <= number <= max_val:
        return number, []
    return number, [f"{axis}_outside_expected_pitch_range"]

def zone_from_x(x: float | None) -> str:
    if x is None:
        return "UNKNOWN"
    if x <= 35.0:
        return "DEFENSIVE_THIRD"
    if x <= 70.0:
        return "MIDDLE_THIRD"
    return "FINAL_THIRD"

def channel_from_y(y: float | None) -> str:
    if y is None:
        return "UNKNOWN"
    if y < 68.0 / 3.0:
        return "LEFT_CHANNEL"
    if y < 2.0 * 68.0 / 3.0:
        return "CENTRAL_CHANNEL"
    return "RIGHT_CHANNEL"

def _period_candidate(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = normalize_header(raw)
    if text in {"1","first","first_half","1st_half"}:
        return "FIRST_HALF"
    if text in {"2","second","second_half","2nd_half"}:
        return "SECOND_HALF"
    return raw

def _duration(start_raw: str | None, end_raw: str | None) -> float | None:
    start = to_float(start_raw)
    end = to_float(end_raw)
    if start is None or end is None or end < start:
        return None
    return round(end - start, 6)

def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

def _surface_candidates(active_match_path: Path) -> tuple[list[Path], list[dict[str, str]]]:
    files = sorted(
        [p for p in active_match_path.rglob("*") if p.is_file() and source_format(p) in {"csv","xml","xlsx"}],
        key=lambda p: (len(p.relative_to(active_match_path).parts), str(p).lower()),
    )
    selected: list[Path] = []
    skipped: list[dict[str, str]] = []
    seen: dict[tuple[str, int], Path] = {}
    for path in files:
        key = (path.name.lower(), path.stat().st_size)
        if key in seen:
            skipped.append({"source_file": str(path.relative_to(active_match_path)), "duplicate_of": str(seen[key].relative_to(active_match_path))})
            continue
        seen[key] = path
        selected.append(path)
    return selected, skipped

def active_surfaces(active_match_path: Path) -> list[Path]:
    return _surface_candidates(active_match_path)[0]

def build_canonical_lite(active_match_dir: str | Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    active_match_path = Path(active_match_dir).expanduser().resolve(strict=False)
    rows_out: list[dict[str, Any]] = []
    files_audit: list[dict[str, Any]] = []
    family_counter: Counter[str] = Counter()
    zone_counter: Counter[str] = Counter()
    channel_counter: Counter[str] = Counter()
    team_counter: Counter[str] = Counter()
    surface_role_counter: Counter[str] = Counter()
    source_surface_counter: Counter[str] = Counter()
    coverage = Counter()
    surfaces, skipped_duplicates = _surface_candidates(active_match_path)

    for path in surfaces:
        fmt = source_format(path)
        role = source_role(path)
        rows, headers = read_surface(path)
        detected = detect_columns(headers)
        used_columns = {v for v in detected.values() if v}
        mapped_columns = sorted(used_columns)
        unmapped_columns = [h for h in headers if h not in used_columns and not h.startswith("__")]
        surface_role_counter[role] += len(rows)
        source_surface_counter[str(path.relative_to(active_match_path))] += len(rows)

        label_count = 0
        extra_kv_count = 0
        for idx, row in enumerate(rows, start=1):
            event_raw = first_value(row, detected.get("event_type"))
            team_raw = first_value(row, detected.get("team"))
            player_raw = first_value(row, detected.get("player"))
            x_raw = first_value(row, detected.get("x"))
            y_raw = first_value(row, detected.get("y"))
            x_m, x_warn = coordinate_with_warning(x_raw, "x")
            y_m, y_warn = coordinate_with_warning(y_raw, "y")
            warnings = x_warn + y_warn
            family = normalize_event_family(event_raw)
            zone = zone_from_x(x_m if not warnings else None)
            channel = channel_from_y(y_m if not warnings else None)
            team_norm = normalize_team(team_raw)
            source_labels = row.get("__labels__", [])
            label_count += len(source_labels) if isinstance(source_labels, list) else 0
            extras = {k: v for k, v in row.items() if k not in used_columns and not k.startswith("__")}
            if "__overflow__" in row and row["__overflow__"]:
                extras["__overflow__"] = row["__overflow__"]
            extra_kv_count += len(extras)

            start_raw = first_value(row, detected.get("start"))
            end_raw = first_value(row, detected.get("end"))
            period_raw = first_value(row, detected.get("period"))

            if event_raw:
                coverage["event_type_rows"] += 1
            if team_norm:
                coverage["team_rows"] += 1
                team_counter[team_norm] += 1
            if x_m is not None and y_m is not None and not warnings:
                coverage["coordinate_rows"] += 1
            if start_raw:
                coverage["start_rows"] += 1
            if period_raw:
                coverage["period_rows"] += 1

            family_counter[family] += 1
            zone_counter[zone] += 1
            channel_counter[channel] += 1

            rows_out.append({
                "source_file": str(path.relative_to(active_match_path)),
                "source_format": fmt,
                "source_role": role,
                "source_sheet": row.get("__source_sheet__"),
                "source_row_index": idx,
                "source_event_id_raw": first_value(row, detected.get("source_event_id")),
                "event_type_raw": event_raw,
                "event_family": family,
                "team_raw": team_raw,
                "team_normalized": team_norm,
                "player_raw": player_raw,
                "minute_raw": first_value(row, detected.get("minute")),
                "second_raw": first_value(row, detected.get("second")),
                "timestamp_raw": first_value(row, detected.get("timestamp")),
                "start_raw": start_raw,
                "end_raw": end_raw,
                "duration_seconds_candidate": _duration(start_raw, end_raw),
                "code_raw": first_value(row, detected.get("code")),
                "period_raw": period_raw,
                "period_candidate": _period_candidate(period_raw),
                "x_raw": x_raw,
                "y_raw": y_raw,
                "x_meters": x_m if not x_warn else None,
                "y_meters": y_m if not y_warn else None,
                "coordinate_system_candidate": "PITCH_105_X_68_CANDIDATE" if x_m is not None and y_m is not None and not warnings else "UNKNOWN",
                "coordinate_frame_status": "FIXED_PITCH_FRAME_UNPROVEN_DIRECTION",
                "attacking_direction_candidate": "UNKNOWN",
                "directional_features_allowed": False,
                "source_labels_raw": _json(source_labels),
                "source_extra_fields": _json(extras),
                "row_claim_safety": CLAIM_SAFETY,
                "row_warnings": ";".join(warnings),
            })

        files_audit.append({
            "source_file": str(path.relative_to(active_match_path)),
            "source_format": fmt,
            "source_role": role,
            "rows_read": len(rows),
            "raw_column_count": len(headers),
            "mapped_columns": mapped_columns,
            "unmapped_columns": unmapped_columns,
            "preserved_extra_key_value_count": extra_kv_count,
            "xml_label_count": label_count,
        })

    surface_total = len(rows_out)
    audit = {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if skipped_duplicates else "PASS",
        "claim_safety": CLAIM_SAFETY,
        "semantic_correction": "P2S_LOSSLESS_SURFACE_INTAKE",
        "active_match_dir": str(active_match_path),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "deduplicated_event_count": DEDUPLICATED_EVENT_COUNT,
        "primary_event_surface_candidate": PRIMARY_EVENT_SURFACE_CANDIDATE,
        "event_count_claim_allowed": EVENT_COUNT_CLAIM_ALLOWED,
        "surface_row_inventory_total": surface_total,
        "canonical_lite_row_count_deprecated": surface_total,
        "canonical_lite_row_count_deprecated_note": "Deprecated alias for surface_row_inventory_total; not a match event count.",
        "surface_role_row_counts": dict(surface_role_counter.most_common()),
        "source_surface_row_counts": dict(source_surface_counter.most_common()),
        "skipped_duplicate_surfaces": skipped_duplicates,
        "files_read": files_audit,
        "event_family_volume": dict(family_counter.most_common()),
        "zone_distribution": _distribution(zone_counter),
        "channel_distribution": _distribution(channel_counter),
        "team_row_volume": dict(team_counter.most_common()),
        "coverage": {
            "event_type_rows": coverage["event_type_rows"],
            "team_rows": coverage["team_rows"],
            "coordinate_rows": coverage["coordinate_rows"],
            "start_rows": coverage["start_rows"],
            "period_rows": coverage["period_rows"],
            "surface_row_inventory_total": surface_total,
            "total_rows_deprecated": surface_total,
            "event_type_pct_of_surface_inventory": _pct(coverage["event_type_rows"], surface_total),
            "team_pct_of_surface_inventory": _pct(coverage["team_rows"], surface_total),
            "coordinate_pct_of_surface_inventory": _pct(coverage["coordinate_rows"], surface_total),
        },
        "blocked_claims": [
            "multi_surface_rows_as_event_count","deduplicated event count without primary surface gate",
            "complete event truth","possession truth","phase truth","tactical truth","dominance truth",
            "attacking direction truth","direction-sensitive progression without direction evidence","validated xT",
        ],
        "technical_limits": [
            "All source fields are preserved, but preservation does not grant claim authority.",
            "XLSX rows remain aggregate validation surfaces, not event truth.",
            "Attacking direction remains UNKNOWN; direction-sensitive outputs are blocked.",
            "canonical_event_count remains UNKNOWN.",
        ],
    }
    return rows_out, audit

def _pct(value: int, total: int) -> float:
    return round((value / total) * 100, 1) if total else 0.0

def _distribution(counter: Counter[str]) -> dict[str, dict[str, float | int]]:
    total = sum(counter.values())
    return {key: {"visible_rows": value, "pct": _pct(value, total)} for key, value in counter.most_common()}

def render_audit_txt(audit: dict[str, Any]) -> str:
    lines = [
        "HPFA CANONICAL EVENT LITE V1 AUDIT","====================================",
        f"status={audit.get('status')}",f"claim_safety={audit.get('claim_safety')}",
        f"semantic_correction={audit.get('semantic_correction')}",
        f"active_match_dir={audit.get('active_match_dir')}",
        f"canonical_event_count={audit.get('canonical_event_count')}",
        f"deduplicated_event_count={audit.get('deduplicated_event_count')}",
        f"primary_event_surface_candidate={audit.get('primary_event_surface_candidate')}",
        f"event_count_claim_allowed={audit.get('event_count_claim_allowed')}",
        f"surface_row_inventory_total={audit.get('surface_row_inventory_total')}",
        "",
    ]
    for section in ("surface_role_row_counts","coverage","event_family_volume","zone_distribution","channel_distribution","team_row_volume"):
        lines.append(f"[{section}]")
        for key, value in audit.get(section, {}).items():
            lines.append(f"{key}={value}")
        lines.append("")
    lines.append("[files_read]")
    lines.extend(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in audit.get("files_read", []))
    lines.append("")
    lines.append("[skipped_duplicate_surfaces]")
    lines.extend(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in audit.get("skipped_duplicate_surfaces", []))
    lines.append("")
    lines.append("[blocked_claims]")
    lines.extend(f"- {item}" for item in audit.get("blocked_claims", []))
    lines.append("")
    lines.append("[technical_limits]")
    lines.extend(f"- {item}" for item in audit.get("technical_limits", []))
    lines.append("")
    return "\n".join(lines)

def write_tsv(rows: list[dict[str, Any]], out: Path) -> None:
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS, delimiter="\t", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

def write_outputs(active_match_dir: str | Path, out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine_runner = _spine_runner_module(repo_root)
    output_root = spine_runner.validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    rows, audit = build_canonical_lite(active_match_dir)
    json_out = output_root / OUTPUT_JSON
    tsv_out = output_root / OUTPUT_TSV
    audit_json_out = output_root / AUDIT_JSON
    audit_txt_out = output_root / AUDIT_TXT
    json_out.write_text(json.dumps({"rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    write_tsv(rows, tsv_out)
    audit["output_root"] = str(output_root)
    audit["outputs"] = {
        "canonical_event_lite_json": str(json_out),
        "canonical_event_lite_tsv": str(tsv_out),
        "audit_json": str(audit_json_out),
        "audit_txt": str(audit_txt_out),
    }
    audit_json_out.write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    audit_txt_out.write_text(render_audit_txt(audit), encoding="utf-8")
    return audit
