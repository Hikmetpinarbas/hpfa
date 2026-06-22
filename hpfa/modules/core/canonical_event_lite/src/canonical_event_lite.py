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

EVENT_FAMILIES = (
    "PASS",
    "SHOT",
    "DUEL_PRESSURE",
    "CARRY_DRIBBLE",
    "BALL_LOSS",
    "RECOVERY",
    "FOUL",
    "GOALKEEPER_RESTART",
    "POSITIONAL_ATTACK_SIGNAL",
    "UNKNOWN_OR_OTHER",
)

SYNONYMS = {
    "event_type": [
        "action", "event", "event_type", "type", "name", "title", "label", "action_name",
        "event name", "action type", "event type",
    ],
    "team": [
        "team", "team_name", "squad", "club", "side", "participant", "team_id", "team id",
    ],
    "player": [
        "player", "player_name", "athlete", "player id", "player_id",
    ],
    "minute": ["minute", "min", "match_minute", "match minute"],
    "second": ["second", "sec", "match_second", "match second"],
    "timestamp": ["time", "timestamp", "match_time", "match time", "period_time"],
    "x": [
        "x", "start_x", "x1", "x_coord", "x coordinate", "x_coordinate", "location_x",
        "pos_x", "coord_x", "coordinate_x", "start x", "location x", "x start",
    ],
    "y": [
        "y", "start_y", "y1", "y_coord", "y coordinate", "y_coordinate", "location_y",
        "pos_y", "coord_y", "coordinate_y", "start y", "location y", "y start",
    ],
}

OUTPUT_FIELDS = [
    "source_file",
    "source_format",
    "source_role",
    "source_row_index",
    "event_type_raw",
    "event_family",
    "team_raw",
    "team_normalized",
    "player_raw",
    "minute_raw",
    "second_raw",
    "timestamp_raw",
    "x_raw",
    "y_raw",
    "x_meters",
    "y_meters",
    "zone",
    "channel",
    "row_claim_safety",
    "row_warnings",
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
        if canonical and detected.get(canonical) is None:
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
        reader = csv.DictReader(f, delimiter=sep)
        rows = [dict(row) for row in reader]
        headers = list(reader.fieldnames or [])
    return rows, headers


def _local(tag: str) -> str:
    return str(tag).split("}")[-1]


def read_xml_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return [], []
    rows: list[dict[str, Any]] = []
    node_names = {"instance", "event", "row", "action"}
    for node in root.iter():
        if _local(node.tag).lower() not in node_names:
            continue
        row: dict[str, Any] = {str(k): v for k, v in node.attrib.items()}
        for child in list(node):
            key = _local(child.tag)
            text = (child.text or "").strip()
            if text:
                row[key] = text
            for attr_key, attr_val in child.attrib.items():
                row[f"{key}_{attr_key}"] = attr_val
        if row:
            rows.append(row)
        else:
            rows.append({"xml_node": _local(node.tag)})
    headers = sorted({str(k) for row in rows for k in row.keys()})
    return rows, headers


def read_xlsx_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    # Lightweight XLSX reader: extracts shared strings and first worksheet rows.
    try:
        with zipfile.ZipFile(path) as zf:
            shared: list[str] = []
            if "xl/sharedStrings.xml" in zf.namelist():
                shared_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                for si in shared_root.iter():
                    if _local(si.tag) == "si":
                        texts = [t.text or "" for t in si.iter() if _local(t.tag) == "t"]
                        shared.append("".join(texts))
            sheets = [n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
            if not sheets:
                return [], []
            root = ET.fromstring(zf.read(sorted(sheets)[0]))
    except Exception:
        return [], []

    table: list[list[str]] = []
    for row_node in root.iter():
        if _local(row_node.tag) != "row":
            continue
        values: list[str] = []
        for cell in list(row_node):
            if _local(cell.tag) != "c":
                continue
            cell_type = cell.attrib.get("t")
            raw = ""
            for child in list(cell):
                if _local(child.tag) == "v":
                    raw = child.text or ""
                    break
            if cell_type == "s":
                try:
                    raw = shared[int(raw)]
                except Exception:
                    pass
            values.append(raw)
        if values:
            table.append(values)
    if not table:
        return [], []
    headers = [str(h).strip() or f"column_{i+1}" for i, h in enumerate(table[0])]
    rows = []
    for raw_row in table[1:]:
        row = {headers[i]: raw_row[i] if i < len(raw_row) else "" for i in range(len(headers))}
        rows.append(row)
    return rows, headers


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
    if "DUEL" in text or "PRESS" in text or "CHALLENGE" in text or "TACKLE" in text:
        return "DUEL_PRESSURE"
    if "CARRY" in text or "DRIB" in text or "RUN" in text:
        return "CARRY_DRIBBLE"
    if "LOSS" in text or "LOST" in text or "TURNOVER" in text:
        return "BALL_LOSS"
    if "RECOVER" in text or "INTERCEPTION" in text or "INTERCEPT" in text:
        return "RECOVERY"
    if "FOUL" in text:
        return "FOUL"
    if "GOAL KICK" in text or "RESTART" in text or "THROW" in text or "CORNER" in text or "FREE KICK" in text:
        return "GOALKEEPER_RESTART"
    if "POSITIONAL ATTACK" in text or "FINAL THIRD" in text or "PENALTY BOX" in text:
        return "POSITIONAL_ATTACK_SIGNAL"
    return "UNKNOWN_OR_OTHER"


def coordinate_with_warning(value: str | None, axis: str) -> tuple[float | None, list[str]]:
    warnings: list[str] = []
    number = to_float(value)
    if number is None:
        return None, [f"missing_{axis}"]
    max_val = 105.0 if axis == "x" else 68.0
    if 0.0 <= number <= max_val:
        return number, warnings
    if 0.0 <= number <= 100.0:
        warnings.append(f"{axis}_possibly_0_100_scale_unconverted")
        return number, warnings
    warnings.append(f"{axis}_outside_expected_pitch_range")
    return number, warnings


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


def active_surfaces(active_match_path: Path) -> list[Path]:
    return sorted(
        [p for p in active_match_path.iterdir() if p.is_file() and source_format(p) in {"csv", "xml", "xlsx"}],
        key=lambda p: p.name.lower(),
    )


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

    for path in active_surfaces(active_match_path):
        fmt = source_format(path)
        role = source_role(path)
        rows, headers = read_surface(path)
        detected = detect_columns(headers)
        missing_families = [k for k, v in detected.items() if v is None]
        coordinate_rows = 0
        team_rows = 0
        event_rows = 0
        surface_role_counter[role] += len(rows)
        source_surface_counter[path.name] += len(rows)

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
            zone = zone_from_x(x_m if not x_warn else None)
            channel = channel_from_y(y_m if not y_warn else None)
            team_norm = normalize_team(team_raw)

            if event_raw:
                event_rows += 1
                coverage["event_type_rows"] += 1
            if team_norm:
                team_rows += 1
                coverage["team_rows"] += 1
                team_counter[team_norm] += 1
            if x_m is not None and y_m is not None and not x_warn and not y_warn:
                coordinate_rows += 1
                coverage["coordinate_rows"] += 1

            family_counter[family] += 1
            zone_counter[zone] += 1
            channel_counter[channel] += 1

            rows_out.append({
                "source_file": path.name,
                "source_format": fmt,
                "source_role": role,
                "source_row_index": idx,
                "event_type_raw": event_raw,
                "event_family": family,
                "team_raw": team_raw,
                "team_normalized": team_norm,
                "player_raw": player_raw,
                "minute_raw": first_value(row, detected.get("minute")),
                "second_raw": first_value(row, detected.get("second")),
                "timestamp_raw": first_value(row, detected.get("timestamp")),
                "x_raw": x_raw,
                "y_raw": y_raw,
                "x_meters": x_m if not x_warn else None,
                "y_meters": y_m if not y_warn else None,
                "zone": zone,
                "channel": channel,
                "row_claim_safety": CLAIM_SAFETY,
                "row_warnings": ";".join(warnings),
            })

        files_audit.append({
            "source_file": path.name,
            "source_format": fmt,
            "source_role": role,
            "rows_read": len(rows),
            "columns": headers[:80],
            "detected_columns": detected,
            "missing_column_families": missing_families,
            "event_type_coverage_rows": event_rows,
            "team_coverage_rows": team_rows,
            "coordinate_coverage_rows": coordinate_rows,
        })

    surface_total = len(rows_out)
    audit = {
        "module_id": MODULE_ID,
        "status": "PASS",
        "claim_safety": CLAIM_SAFETY,
        "semantic_correction": "P2S_CANONICAL_LITE_SURFACE_COUNT_CORRECTION",
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
        "files_read": files_audit,
        "event_family_volume": dict(family_counter.most_common()),
        "zone_distribution": _distribution(zone_counter),
        "channel_distribution": _distribution(channel_counter),
        "team_row_volume": dict(team_counter.most_common()),
        "coverage": {
            "event_type_rows": coverage["event_type_rows"],
            "team_rows": coverage["team_rows"],
            "coordinate_rows": coverage["coordinate_rows"],
            "surface_row_inventory_total": surface_total,
            "total_rows_deprecated": surface_total,
            "event_type_pct_of_surface_inventory": _pct(coverage["event_type_rows"], surface_total),
            "team_pct_of_surface_inventory": _pct(coverage["team_rows"], surface_total),
            "coordinate_pct_of_surface_inventory": _pct(coverage["coordinate_rows"], surface_total),
        },
        "blocked_claims": [
            "multi_surface_rows_as_event_count",
            "deduplicated event count without primary surface gate",
            "complete event truth",
            "possession truth",
            "phase truth",
            "tactical truth",
            "dominance truth",
        ],
        "technical_limits": [
            "Canonical Event Lite is a normalized multi-surface row inventory, not complete event truth.",
            "surface_row_inventory_total must not be read as match event count.",
            "Players, Teams and Goalkeepers surfaces may represent overlapping or aggregate views.",
            "primary_event_surface_candidate remains UNRESOLVED until a dedicated gate selects it.",
            "deduplicated_event_count remains UNKNOWN.",
            "canonical_event_count remains UNKNOWN.",
            "XLSX aggregate rows are not treated as event truth.",
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
        "HPFA CANONICAL EVENT LITE V1 AUDIT",
        "====================================",
        f"status={audit.get('status')}",
        f"claim_safety={audit.get('claim_safety')}",
        f"semantic_correction={audit.get('semantic_correction')}",
        f"active_match_dir={audit.get('active_match_dir')}",
        f"canonical_event_count={audit.get('canonical_event_count')}",
        f"deduplicated_event_count={audit.get('deduplicated_event_count')}",
        f"primary_event_surface_candidate={audit.get('primary_event_surface_candidate')}",
        f"event_count_claim_allowed={audit.get('event_count_claim_allowed')}",
        f"surface_row_inventory_total={audit.get('surface_row_inventory_total')}",
        f"canonical_lite_row_count_deprecated={audit.get('canonical_lite_row_count_deprecated')}",
        "",
        "[surface_role_row_counts]",
    ]
    for key, value in audit.get("surface_role_row_counts", {}).items():
        lines.append(f"{key}={value}")
    lines.extend(["", "[coverage]"])
    for key, value in audit.get("coverage", {}).items():
        lines.append(f"{key}={value}")
    lines.extend(["", "[event_family_volume]"])
    for key, value in audit.get("event_family_volume", {}).items():
        lines.append(f"{key}={value}")
    lines.extend(["", "[zone_distribution]"])
    for key, value in audit.get("zone_distribution", {}).items():
        lines.append(f"{key}={value}")
    lines.extend(["", "[channel_distribution]"])
    for key, value in audit.get("channel_distribution", {}).items():
        lines.append(f"{key}={value}")
    lines.extend(["", "[team_row_volume]"])
    for key, value in audit.get("team_row_volume", {}).items():
        lines.append(f"{key}={value}")
    lines.extend(["", "[files_read]"])
    for row in audit.get("files_read", []):
        lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
    lines.extend(["", "[blocked_claims]"])
    for item in audit.get("blocked_claims", []):
        lines.append(f"- {item}")
    lines.extend(["", "[technical_limits]"])
    for item in audit.get("technical_limits", []):
        lines.append(f"- {item}")
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
