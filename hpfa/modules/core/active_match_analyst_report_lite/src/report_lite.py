from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "active_match_analyst_report_lite_v1"
CLAIM_SAFETY = "EVIDENCE_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"

OUTPUT_JSON = "active_match_analyst_report_lite_v1.json"
OUTPUT_TXT = "active_match_analyst_report_lite_v1.txt"

ACTION_COLUMNS = ("action", "Action", "event", "Event", "event_type", "Event Type", "type", "Type", "name", "Name")
TEAM_COLUMNS = ("team", "Team", "team_name", "Team Name", "squad", "Squad")
X_COLUMNS = ("x", "X", "start_x", "Start X", "x1", "X1")
Y_COLUMNS = ("y", "Y", "start_y", "Start Y", "y1", "Y1")

REPORT_GROUPS = (
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


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def _ensure_module_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _surface_manifest_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "canonical_ingest_surface_manifest" / "src"
    _ensure_module_path(src)
    import surface_manifest  # type: ignore

    return surface_manifest


def _spine_runner_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    _ensure_module_path(src)
    import spine_runner  # type: ignore

    return spine_runner


def _sniff_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        return [dict(row) for row in csv.DictReader(f, dialect=dialect)]


def _first_value(row: dict[str, str], candidates: tuple[str, ...]) -> str | None:
    for key in candidates:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return None


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def normalize_action_family(raw: str | None) -> str:
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


def zone_from_x(value: float | None) -> str:
    if value is None:
        return "UNKNOWN"
    if value <= 35.0:
        return "DEFENSIVE_THIRD"
    if value <= 70.0:
        return "MIDDLE_THIRD"
    return "FINAL_THIRD"


def channel_from_y(value: float | None) -> str:
    if value is None:
        return "UNKNOWN"
    if value < 68.0 / 3.0:
        return "LEFT_CHANNEL"
    if value < 2.0 * 68.0 / 3.0:
        return "CENTRAL_CHANNEL"
    return "RIGHT_CHANNEL"


def _percent(counter: Counter[str]) -> dict[str, dict[str, float | int]]:
    total = sum(counter.values())
    result: dict[str, dict[str, float | int]] = {}
    for key, value in counter.most_common():
        pct = round((value / total) * 100, 1) if total else 0.0
        result[key] = {"visible_rows": value, "pct": pct}
    return result


def _csv_paths(active_match_path: Path) -> list[Path]:
    return sorted([p for p in active_match_path.iterdir() if p.is_file() and p.suffix.lower() == ".csv"], key=lambda p: p.name.lower())


def build_report(active_match_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    active_match_path = Path(active_match_dir).expanduser().resolve(strict=False)

    spine_runner = _spine_runner_module(repo_root)
    role_resolver = spine_runner._content_source_role_resolver_module(repo_root)
    role_report = role_resolver.build_report(str(active_match_path), root=repo_root)
    surface_manifest = spine_runner._surface_manifest_module(repo_root)
    manifest = surface_manifest.build_manifest(
        str(active_match_path),
        role_report=role_report,
    )

    action_counter: Counter[str] = Counter()
    zone_counter: Counter[str] = Counter()
    channel_counter: Counter[str] = Counter()
    team_counter: Counter[str] = Counter()
    restart_counter: Counter[str] = Counter()
    missing_columns: list[dict[str, Any]] = []
    csv_row_total = 0

    for path in _csv_paths(active_match_path):
        rows = _sniff_csv(path)
        csv_row_total += len(rows)
        headers = set(rows[0].keys()) if rows else set()
        missing = {
            "action": not any(c in headers for c in ACTION_COLUMNS),
            "team": not any(c in headers for c in TEAM_COLUMNS),
            "x": not any(c in headers for c in X_COLUMNS),
            "y": not any(c in headers for c in Y_COLUMNS),
        }
        if any(missing.values()):
            missing_columns.append({"source_file": path.name, "missing_column_family": [k for k, v in missing.items() if v]})
        for row in rows:
            family = normalize_action_family(_first_value(row, ACTION_COLUMNS))
            action_counter[family] += 1
            if family == "GOALKEEPER_RESTART" or "goalkeeper" in path.name.lower():
                restart_counter[family] += 1
            zone_counter[zone_from_x(_to_float(_first_value(row, X_COLUMNS)))] += 1
            channel_counter[channel_from_y(_to_float(_first_value(row, Y_COLUMNS)))] += 1
            if "player" in path.name.lower():
                team_value = _first_value(row, TEAM_COLUMNS)
                if team_value:
                    team_counter[team_value] += 1

    key_blocks = {group: action_counter.get(group, 0) for group in REPORT_GROUPS}

    analyst_reading = [
        "Visible surface evidence indicates a readable ACTIVE_MATCH Lite surface when expected files are present.",
        "Action-family volume gives the analyst a first map of which event-like row families are most frequent.",
        "Zone and channel buckets show where coordinate evidence is concentrated on the visible surface.",
        "Team row-volume is a row-level relationship only; it is not possession, quality or tactical proof.",
        "Restart and goalkeeper-linked rows are reported as signal volume and require later validation.",
    ]

    result = {
        "module_id": MODULE_ID,
        "status": manifest.get("status", "UNKNOWN"),
        "claim_safety": CLAIM_SAFETY,
        "active_match_dir": str(active_match_path),
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "match_snapshot": {
            "match_dir": str(active_match_path),
            "surface_file_count": manifest.get("surface_file_count", 0),
            "expected_surface_count": manifest.get("expected_surface_count"),
            "canonical_event_count": CANONICAL_EVENT_COUNT,
        },
        "surface_inventory": manifest.get("surfaces", []),
        "action_family_volume": dict(action_counter.most_common()),
        "zone_distribution": _percent(zone_counter),
        "channel_distribution": _percent(channel_counter),
        "team_row_volume": dict(team_counter.most_common()),
        "goalkeeper_restart_signal": dict(restart_counter.most_common()),
        "key_action_blocks": key_blocks,
        "analyst_reading": analyst_reading,
        "missing_column_report": missing_columns,
        "technical_limits": [
            "This Lite report uses visible row-level evidence only.",
            "Canonical Event Lite is required before validated event-stream claims.",
            "Team Binding Lite is required before player-quality or role-quality judgement.",
            "Phase, possession, sequence and rhythm outputs require later upstream gates.",
        ],
        "engineering_evidence": {
            "csv_visible_rows_scanned": csv_row_total,
            "source_role_resolution_status": role_report.get("status"),
            "role_candidate_admitted_file_count": role_report.get(
                "role_candidate_admitted_file_count"
            ),
            "unresolved_role_file_count": role_report.get("unresolved_role_file_count"),
            "surface_manifest_status": manifest.get("status"),
            "missing_expected_surfaces": manifest.get("missing_expected_surfaces", []),
            "unexpected_surfaces": manifest.get("unexpected_surfaces", []),
            "output_contract": [OUTPUT_JSON, OUTPUT_TXT],
        },
    }
    return result


def render_txt(report: dict[str, Any]) -> str:
    lines: list[str] = [
        "HPFA ACTIVE_MATCH ANALYST REPORT LITE V1",
        "===========================================",
        f"status={report.get('status')}",
        f"claim_safety={report.get('claim_safety')}",
        f"active_match_dir={report.get('active_match_dir')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        "",
        "[match_snapshot]",
    ]
    snapshot = report.get("match_snapshot", {})
    for key in ["surface_file_count", "expected_surface_count", "canonical_event_count"]:
        lines.append(f"{key}={snapshot.get(key)}")

    lines.extend(["", "[action_family_volume]"])
    for key, value in report.get("action_family_volume", {}).items():
        lines.append(f"{key}={value}")

    lines.extend(["", "[zone_distribution]"])
    for key, value in report.get("zone_distribution", {}).items():
        lines.append(f"{key}={value}")

    lines.extend(["", "[channel_distribution]"])
    for key, value in report.get("channel_distribution", {}).items():
        lines.append(f"{key}={value}")

    lines.extend(["", "[team_row_volume]"])
    for key, value in report.get("team_row_volume", {}).items():
        lines.append(f"{key}={value}")

    lines.extend(["", "[goalkeeper_restart_signal]"])
    for key, value in report.get("goalkeeper_restart_signal", {}).items():
        lines.append(f"{key}={value}")

    lines.extend(["", "[key_action_blocks]"])
    for key, value in report.get("key_action_blocks", {}).items():
        lines.append(f"{key}={value}")

    lines.extend(["", "[analyst_reading]"])
    for item in report.get("analyst_reading", []):
        lines.append(f"- {item}")

    lines.extend(["", "[missing_column_report]"])
    for row in report.get("missing_column_report", []):
        lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))

    lines.extend(["", "[technical_limits]"])
    for item in report.get("technical_limits", []):
        lines.append(f"- {item}")

    lines.extend(["", "[engineering_evidence]"])
    for key, value in report.get("engineering_evidence", {}).items():
        lines.append(f"{key}={value}")

    lines.append("")
    return "\n".join(lines)


def write_report(active_match_dir: str | Path, out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine_runner = _spine_runner_module(repo_root)
    output_root = spine_runner.validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    report = build_report(active_match_dir, root=repo_root)
    json_out = output_root / OUTPUT_JSON
    txt_out = output_root / OUTPUT_TXT
    report["engineering_evidence"]["output_root"] = str(output_root)
    report["engineering_evidence"]["out_json"] = str(json_out)
    report["engineering_evidence"]["out_txt"] = str(txt_out)
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
