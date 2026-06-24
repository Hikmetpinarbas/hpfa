from __future__ import annotations

import csv
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "triangulated_event_reflection_resolver_lite_v1"
CLAIM_SAFETY = "REFLECTION_RESOLUTION_CANDIDATE_ONLY"
OUTPUT_JSON = "triangulated_event_reflection_resolver_lite_v1.json"
OUTPUT_TXT = "triangulated_event_reflection_resolver_lite_v1.txt"
SUPPORTED_SUFFIXES = {".csv", ".tsv", ".xml"}

ACTION_KEYS = ["action_family", "event_family", "event_type", "type", "action", "name", "subtype", "code", "label", "text"]
TEAM_KEYS = ["team", "team_name", "team_raw", "team_entity_key", "squad", "side"]
PLAYER_KEYS = ["player", "player_name", "player_raw", "athlete", "name"]
TIME_KEYS = ["minute", "time", "timestamp", "start", "absolute_time_seconds", "match_time"]
X_KEYS = ["x", "x_meters", "start_x"]
Y_KEYS = ["y", "y_meters", "start_y"]

BLOCKED_CLAIMS = [
    "true event count",
    "validated action count",
    "deduplicated event truth",
    "complete event stream",
    "possession truth",
    "sequence truth",
]


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
            return str(value).strip().lower()
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


def bucket(value: float | None, size: float, unknown: str = "unknown") -> str:
    if value is None:
        return unknown
    return str(int(value // size))


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
    return "UNKNOWN_OR_OTHER"


def reflection_key(row: dict[str, Any]) -> tuple[str, ...]:
    action_text = text_value(row, ACTION_KEYS)
    action = normalize_action(action_text)
    team = text_value(row, TEAM_KEYS)
    player = text_value(row, PLAYER_KEYS)
    minute = numeric_value(row, TIME_KEYS)
    x = numeric_value(row, X_KEYS)
    y = numeric_value(row, Y_KEYS)
    return (
        action,
        team,
        player,
        bucket(minute, 1.0),
        bucket(x, 5.0),
        bucket(y, 5.0),
    )


def read_csv_or_tsv(path: Path, delimiter: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for idx, row in enumerate(reader):
            payload = dict(row)
            payload["_source_file"] = path.name
            payload["_source_format"] = path.suffix.lower().lstrip(".")
            payload["_source_row_index"] = idx
            rows.append(payload)
    return rows


def flatten_xml_event(elem: ET.Element) -> dict[str, Any]:
    payload = dict(elem.attrib)
    payload.setdefault("name", elem.tag)
    for child in elem.iter():
        if child is elem:
            continue
        text = (child.text or "").strip()
        if text:
            payload.setdefault(child.tag, text)
        for key, value in child.attrib.items():
            payload.setdefault(key, value)
    return payload


def read_xml(path: Path) -> list[dict[str, Any]]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError:
        return []
    elements = [elem for elem in root.iter() if elem is not root and (dict(elem.attrib) or list(elem) or (elem.text or "").strip())]
    containers = [elem for elem in elements if list(elem)]
    source = containers if containers else elements
    rows: list[dict[str, Any]] = []
    for idx, elem in enumerate(source):
        payload = flatten_xml_event(elem)
        payload["_source_file"] = path.name
        payload["_source_format"] = "xml"
        payload["_source_row_index"] = idx
        rows.append(payload)
    return rows


def discover_surface_rows(input_dir: str | Path) -> list[dict[str, Any]]:
    root = Path(input_dir).expanduser().resolve(strict=False)
    rows: list[dict[str, Any]] = []
    for path in sorted(root.iterdir() if root.exists() else []):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if path.suffix.lower() == ".csv":
            rows.extend(read_csv_or_tsv(path, ","))
        elif path.suffix.lower() == ".tsv":
            rows.extend(read_csv_or_tsv(path, "\t"))
        elif path.suffix.lower() == ".xml":
            rows.extend(read_xml(path))
    return rows


def build_report(input_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    rows = discover_surface_rows(input_dir)
    groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[reflection_key(row)].append(row)

    examples: list[dict[str, Any]] = []
    family_volume: dict[str, int] = defaultdict(int)
    multi = 0
    for key, members in groups.items():
        action = key[0]
        family_volume[action] += 1
        source_files = sorted({str(item.get("_source_file")) for item in members})
        if len(source_files) > 1:
            multi += 1
        if len(examples) < 25:
            examples.append({
                "reflection_key": list(key),
                "candidate_action_family": action,
                "surface_row_count": len(members),
                "source_files": source_files,
                "claim_allowed": False,
            })

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED",
        "decision": "REFLECTION_GROUPS_CANDIDATE_ONLY",
        "claim_safety": CLAIM_SAFETY,
        "surface_row_count": len(rows),
        "reflection_group_count": len(groups),
        "single_surface_group_count": len(groups) - multi,
        "multi_surface_group_count": multi,
        "unresolved_reflection_count": len(groups),
        "candidate_action_family_volume": dict(sorted(family_volume.items())),
        "reflection_group_examples": examples,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "reflection_group_truth": False,
        "action_count_claim_allowed": False,
        "blocked_claims": BLOCKED_CLAIMS,
        "repo_root": str(repo_root),
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA TRIANGULATED EVENT REFLECTION RESOLVER LITE V1",
        "====================================================",
        f"status={report.get('status')}",
        f"decision={report.get('decision')}",
        f"claim_safety={report.get('claim_safety')}",
        f"surface_row_count={report.get('surface_row_count')}",
        f"reflection_group_count={report.get('reflection_group_count')}",
        f"multi_surface_group_count={report.get('multi_surface_group_count')}",
        f"true_action_count={report.get('true_action_count')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        "",
        "[candidate_action_family_volume]",
        json.dumps(report.get("candidate_action_family_volume", {}), ensure_ascii=False, sort_keys=True),
        "",
        "[reflection_group_examples]",
    ]
    for item in report.get("reflection_group_examples", []):
        lines.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
    lines.extend(["", "[blocked_claims]"])
    for item in report.get("blocked_claims", []):
        lines.append(f"- {item}")
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
