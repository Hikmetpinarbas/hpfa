from __future__ import annotations

import csv
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

MODULE_ID = "minimum_viable_context_lite_v1"
CLAIM_SAFETY = "CONTEXT_CANDIDATE_ONLY"
OUTPUT_JSON = "minimum_viable_context_lite_v1.json"
OUTPUT_TXT = "minimum_viable_context_lite_v1.txt"
SUPPORTED_SUFFIXES = {".csv", ".tsv", ".xml"}

ACTION_KEYS = ["action_family", "event_family", "event_type", "type", "action", "subtype", "code", "label", "text", "name"]
TEAM_KEYS = ["team", "team_name", "team_raw", "team_entity_key", "squad", "side"]
TIME_KEYS = ["minute", "time", "timestamp", "start", "absolute_time_seconds", "match_time"]
PERIOD_KEYS = ["period", "half", "match_period"]
X_KEYS = ["x", "x_meters", "start_x", "pos_x"]
Y_KEYS = ["y", "y_meters", "start_y", "pos_y"]
XML_ACTION_TAGS = {"code", "label", "text", "action", "event", "event_type", "type", "subtype"}
XML_EVENT_TAGS = {"instance", "event", "row", "action"}


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def ensure_module_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def spine_runner_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    ensure_module_path(src)
    import spine_runner  # type: ignore
    return spine_runner


def text_value(row: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return "unknown"


def numeric_value(row: dict[str, Any], keys: list[str]) -> float | None:
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            return float(str(value).replace(",", "."))
        except ValueError:
            continue
    return None


def normalize_action(text: str) -> str:
    value = text.lower()
    if "pass" in value:
        return "PASS"
    if any(token in value for token in ["shot", "goal", "save"]):
        return "SHOT"
    if any(token in value for token in ["carry", "dribble"]):
        return "CARRY_DRIBBLE"
    if any(token in value for token in ["loss", "turnover", "dispossessed"]):
        return "BALL_LOSS"
    if any(token in value for token in ["recovery", "interception"]):
        return "RECOVERY"
    if any(token in value for token in ["duel", "challenge", "pressure"]):
        return "DUEL_PRESSURE"
    if any(token in value for token in ["corner", "throw", "free kick", "goal kick", "restart", "kick off"]):
        return "RESTART"
    if "foul" in value or "offside" in value:
        return "DEAD_BALL"
    return "UNKNOWN_OR_OTHER"


def minute_bucket(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value > 1000:
        value = value / 60.0
    return str(int(value))


def zone_candidate(x: float | None) -> str:
    if x is None:
        return "UNKNOWN_ZONE"
    if x < 35:
        return "DEFENSIVE_THIRD"
    if x < 70:
        return "MIDDLE_THIRD"
    return "FINAL_THIRD"


def channel_candidate(y: float | None) -> str:
    if y is None:
        return "UNKNOWN_CHANNEL"
    if y < 22.67:
        return "LEFT_CHANNEL"
    if y < 45.34:
        return "CENTRAL_CHANNEL"
    return "RIGHT_CHANNEL"


def context_completeness(row: dict[str, Any]) -> str:
    has_time = row["minute_bucket"] != "unknown"
    has_team = row["team_label"] != "unknown"
    has_action = row["action_family"] != "UNKNOWN_OR_OTHER"
    has_space = row["zone_candidate"] != "UNKNOWN_ZONE" and row["channel_candidate"] != "UNKNOWN_CHANNEL"
    score = sum([has_time, has_team, has_action, has_space])
    return "high" if score == 4 else "medium" if score >= 2 else "low"


def detect_delimiter(path: Path) -> str:
    sample = path.read_text(encoding="utf-8", errors="ignore")[:4096]
    first_line = sample.splitlines()[0] if sample.splitlines() else ""
    if first_line.count(";") > first_line.count(",") and first_line.count(";") >= first_line.count("\t"):
        return ";"
    if first_line.count("\t") > first_line.count(","):
        return "\t"
    return ","


def read_csv_or_tsv(path: Path, delimiter: str | None = None) -> list[dict[str, Any]]:
    delim = delimiter if delimiter is not None else detect_delimiter(path)
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delim)
        for idx, row in enumerate(reader):
            payload = dict(row)
            payload["_source_file"] = path.name
            payload["_source_format"] = path.suffix.lower().lstrip(".")
            payload["_source_row_index"] = idx
            rows.append(payload)
    return rows


def child_text(elem: ET.Element, tags: set[str]) -> str | None:
    for child in elem.iter():
        if child is elem:
            continue
        text = (child.text or "").strip()
        if child.tag.lower() in tags and text:
            return text
        for key, value in child.attrib.items():
            if key.lower() in tags and value:
                return str(value).strip()
    return None


def is_xml_event_node(elem: ET.Element) -> bool:
    tag = elem.tag.lower()
    if tag in XML_EVENT_TAGS and (dict(elem.attrib) or list(elem)):
        return True
    return child_text(elem, XML_ACTION_TAGS) is not None and tag not in {"file", "all_instances", "sort_info", "label"}


def flatten_xml_event(elem: ET.Element, path: Path, idx: int) -> dict[str, Any]:
    payload = dict(elem.attrib)
    action_text = child_text(elem, XML_ACTION_TAGS)
    if action_text:
        payload.setdefault("event_type", action_text)
        payload.setdefault("code", action_text)
    for child in elem.iter():
        if child is elem:
            continue
        text = (child.text or "").strip()
        if text:
            payload.setdefault(child.tag, text)
        for key, value in child.attrib.items():
            if value:
                payload.setdefault(key, value)
    payload["_source_file"] = path.name
    payload["_source_format"] = "xml"
    payload["_source_row_index"] = idx
    return payload


def read_xml(path: Path) -> list[dict[str, Any]]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []
    events = [elem for elem in root.iter() if elem is not root and is_xml_event_node(elem)]
    return [flatten_xml_event(elem, path, idx) for idx, elem in enumerate(events)]


def discover_rows(input_dir: str | Path) -> list[dict[str, Any]]:
    root = Path(input_dir).expanduser().resolve(strict=False)
    rows: list[dict[str, Any]] = []
    for path in sorted(root.iterdir() if root.exists() else []):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if path.suffix.lower() == ".csv":
            rows.extend(read_csv_or_tsv(path))
        elif path.suffix.lower() == ".tsv":
            rows.extend(read_csv_or_tsv(path, "\t"))
        elif path.suffix.lower() == ".xml":
            rows.extend(read_xml(path))
    return rows


def build_context_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        minute = numeric_value(row, TIME_KEYS)
        x = numeric_value(row, X_KEYS)
        y = numeric_value(row, Y_KEYS)
        action = normalize_action(text_value(row, ACTION_KEYS))
        candidate = {
            "context_id": f"ctx_{idx:06d}",
            "source_file": str(row.get("_source_file", "unknown")),
            "source_format": str(row.get("_source_format", "unknown")),
            "source_row_index": row.get("_source_row_index", idx),
            "period": text_value(row, PERIOD_KEYS),
            "minute_bucket": minute_bucket(minute),
            "team_label": text_value(row, TEAM_KEYS).lower(),
            "action_family": action,
            "zone_candidate": zone_candidate(x),
            "channel_candidate": channel_candidate(y),
            "previous_action_family": "UNKNOWN_PREVIOUS_ACTION",
            "next_action_family": "UNKNOWN_NEXT_ACTION",
            "source_confidence": "medium",
            "claim_allowed": False,
        }
        candidate["context_completeness"] = context_completeness(candidate)
        candidates.append(candidate)

    def sort_key(item: dict[str, Any]) -> tuple[int, int]:
        minute = item.get("minute_bucket")
        minute_int = 99999 if minute == "unknown" else int(str(minute))
        return minute_int, int(item.get("source_row_index", 0))

    ordered = sorted(candidates, key=sort_key)
    for pos, item in enumerate(ordered):
        if pos > 0:
            item["previous_action_family"] = ordered[pos - 1]["action_family"]
        if pos + 1 < len(ordered):
            item["next_action_family"] = ordered[pos + 1]["action_family"]
    return ordered


def summarize(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    completeness: dict[str, int] = {}
    action_families: dict[str, int] = {}
    for item in candidates:
        completeness[item["context_completeness"]] = completeness.get(item["context_completeness"], 0) + 1
        action_families[item["action_family"]] = action_families.get(item["action_family"], 0) + 1
    return {"context_completeness_counts": completeness, "action_family_counts": action_families}


def build_report(input_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    rows = discover_rows(input_dir)
    candidates = build_context_candidates(rows)
    summary = summarize(candidates)
    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED",
        "decision": "CONTEXT_CANDIDATES_ONLY",
        "claim_safety": CLAIM_SAFETY,
        "surface_row_count": len(rows),
        "context_candidate_count": len(candidates),
        "context_candidates_sample": candidates[:200],
        "context_summary": summary,
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "analyst_sentence_allowed": False,
        "claim_allowed": False,
        "repo_root": str(repo_root),
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA MINIMUM VIABLE CONTEXT LITE V1",
        "====================================",
        f"status={report.get('status')}",
        f"decision={report.get('decision')}",
        f"claim_safety={report.get('claim_safety')}",
        f"surface_row_count={report.get('surface_row_count')}",
        f"context_candidate_count={report.get('context_candidate_count')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        f"phase_truth={report.get('phase_truth')}",
        f"possession_truth={report.get('possession_truth')}",
        f"sequence_truth={report.get('sequence_truth')}",
        "",
        "[context_summary]",
        json.dumps(report.get("context_summary", {}), ensure_ascii=False, sort_keys=True),
        "",
        "[sample]",
    ]
    for item in report.get("context_candidates_sample", [])[:25]:
        lines.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
    lines.append("")
    return "\n".join(lines)


def write_outputs(input_dir: str | Path, out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine = spine_runner_module(repo_root)
    output_root = spine.validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    report = build_report(input_dir, root=repo_root)
    json_out = output_root / OUTPUT_JSON
    txt_out = output_root / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
