from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "team_binding_lite_v1"
CLAIM_SAFETY = "IDENTITY_BINDING_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
DEDUPLICATED_EVENT_COUNT = "UNKNOWN"
PRIMARY_EVENT_SURFACE_CANDIDATE = "UNRESOLVED"
EVENT_COUNT_CLAIM_ALLOWED = False
OUTPUT_JSON = "team_binding_lite_v1.json"
AUDIT_JSON = "team_binding_lite_audit_v1.json"
AUDIT_TXT = "team_binding_lite_audit_v1.txt"


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


def load_rows(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict) and isinstance(data.get("rows"), list):
        return [row for row in data["rows"] if isinstance(row, dict)]
    return []


def clean_label(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def split_team_label(value: Any) -> tuple[str | None, str | None]:
    raw = clean_label(value)
    if not raw:
        return None, None
    match = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", raw)
    if match:
        label = clean_label(match.group(1))
        ext = clean_label(match.group(2))
        return label or raw, ext or None
    return raw, None


def entity_key(label: str | None, ext: str | None = None) -> str:
    base = clean_label(label).lower()
    base = re.sub(r"[^a-z0-9]+", "_", base)
    base = re.sub(r"_+", "_", base).strip("_")
    if not base and ext:
        base = f"id_{ext}"
    return base or "unknown_team"


def top_distribution(counter: Counter[str]) -> dict[str, int]:
    return {key: value for key, value in counter.most_common()}


def build_team_binding(rows: list[dict[str, Any]]) -> dict[str, Any]:
    teams: dict[str, dict[str, Any]] = {}
    unresolved_rows: list[dict[str, Any]] = []
    player_map: dict[str, dict[str, Any]] = {}

    for idx, row in enumerate(rows, start=1):
        team_raw = clean_label(row.get("team_normalized") or row.get("team_raw"))
        display, ext = split_team_label(team_raw)
        key = entity_key(display, ext) if display or ext else None
        if not key:
            unresolved_rows.append({
                "row_index": idx,
                "source_file": row.get("source_file"),
                "source_row_index": row.get("source_row_index"),
                "reason": "missing_team_label",
            })
        else:
            ent = teams.setdefault(key, {
                "team_entity_key": key,
                "display_label_candidate": display,
                "external_ids": set(),
                "aliases": Counter(),
                "visible_rows": 0,
                "source_files": Counter(),
                "source_formats": Counter(),
                "event_family_volume": Counter(),
                "zone_distribution": Counter(),
                "channel_distribution": Counter(),
                "unresolved_rows": 0,
                "claim_boundary": "identity_binding_only_no_quality_claim",
            })
            if ext:
                ent["external_ids"].add(ext)
            if team_raw:
                ent["aliases"][team_raw] += 1
            ent["visible_rows"] += 1
            ent["source_files"][clean_label(row.get("source_file"))] += 1
            ent["source_formats"][clean_label(row.get("source_format"))] += 1
            ent["event_family_volume"][clean_label(row.get("event_family")) or "UNKNOWN"] += 1
            ent["zone_distribution"][clean_label(row.get("zone")) or "UNKNOWN"] += 1
            ent["channel_distribution"][clean_label(row.get("channel")) or "UNKNOWN"] += 1

        player = clean_label(row.get("player_raw"))
        if player:
            pkey = entity_key(player)
            prec = player_map.setdefault(pkey, {
                "player_entity_key": pkey,
                "player_label_candidate": player,
                "team_entity_key_candidates": Counter(),
                "aliases": Counter(),
                "source_files": Counter(),
                "visible_rows": 0,
                "aggregate_support_available": False,
                "claim_boundary": "player_identity_binding_only_no_role_truth",
            })
            if key:
                prec["team_entity_key_candidates"][key] += 1
            prec["aliases"][player] += 1
            prec["source_files"][clean_label(row.get("source_file"))] += 1
            prec["visible_rows"] += 1
            if clean_label(row.get("source_format")) == "xlsx":
                prec["aggregate_support_available"] = True

    team_records = []
    for ent in teams.values():
        team_records.append({
            "team_entity_key": ent["team_entity_key"],
            "display_label_candidate": ent["display_label_candidate"],
            "external_ids": sorted(ent["external_ids"]),
            "aliases": top_distribution(ent["aliases"]),
            "visible_rows": ent["visible_rows"],
            "source_files": top_distribution(ent["source_files"]),
            "source_formats": top_distribution(ent["source_formats"]),
            "event_family_volume": top_distribution(ent["event_family_volume"]),
            "zone_distribution": top_distribution(ent["zone_distribution"]),
            "channel_distribution": top_distribution(ent["channel_distribution"]),
            "unresolved_rows": ent["unresolved_rows"],
            "claim_boundary": ent["claim_boundary"],
        })
    team_records.sort(key=lambda r: (-int(r["visible_rows"]), str(r["team_entity_key"])))

    player_records = []
    for prec in player_map.values():
        player_records.append({
            "player_entity_key": prec["player_entity_key"],
            "player_label_candidate": prec["player_label_candidate"],
            "team_entity_key_candidates": top_distribution(prec["team_entity_key_candidates"]),
            "aliases": top_distribution(prec["aliases"]),
            "source_files": top_distribution(prec["source_files"]),
            "visible_rows": prec["visible_rows"],
            "aggregate_support_available": prec["aggregate_support_available"],
            "claim_boundary": prec["claim_boundary"],
        })
    player_records.sort(key=lambda r: (-int(r["visible_rows"]), str(r["player_entity_key"])))

    surface_total = len(rows)
    return {
        "module_id": MODULE_ID,
        "status": "PASS",
        "claim_safety": CLAIM_SAFETY,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "deduplicated_event_count": DEDUPLICATED_EVENT_COUNT,
        "primary_event_surface_candidate": PRIMARY_EVENT_SURFACE_CANDIDATE,
        "event_count_claim_allowed": EVENT_COUNT_CLAIM_ALLOWED,
        "surface_row_inventory_total": surface_total,
        "canonical_lite_row_count_deprecated": surface_total,
        "team_entity_count": len(team_records),
        "player_entity_count": len(player_records),
        "unresolved_team_rows": len(unresolved_rows),
        "team_entities": team_records,
        "player_entities": player_records,
        "unresolved_rows_sample": unresolved_rows[:100],
        "blocked_claims": [
            "quality claim by identity",
            "possession claim by row count",
            "dominance claim",
            "tactical claim by label",
            "coach intention claim",
            "complete event truth",
            "multi-surface row inventory as event count",
        ],
    }


def render_audit_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA TEAM BINDING LITE V1 AUDIT",
        "=================================",
        f"status={report.get('status')}",
        f"claim_safety={report.get('claim_safety')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        f"deduplicated_event_count={report.get('deduplicated_event_count')}",
        f"primary_event_surface_candidate={report.get('primary_event_surface_candidate')}",
        f"event_count_claim_allowed={report.get('event_count_claim_allowed')}",
        f"surface_row_inventory_total={report.get('surface_row_inventory_total')}",
        f"canonical_lite_row_count_deprecated={report.get('canonical_lite_row_count_deprecated')}",
        f"team_entity_count={report.get('team_entity_count')}",
        f"player_entity_count={report.get('player_entity_count')}",
        f"unresolved_team_rows={report.get('unresolved_team_rows')}",
        "",
        "[team_entities]",
    ]
    for row in report.get("team_entities", []):
        lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
    lines.extend(["", "[blocked_claims]"])
    for item in report.get("blocked_claims", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(canonical_event_lite_json: str | Path, out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine_runner = _spine_runner_module(repo_root)
    out = spine_runner.validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    rows = load_rows(canonical_event_lite_json)
    report = build_team_binding(rows)
    json_out = out / OUTPUT_JSON
    audit_json_out = out / AUDIT_JSON
    audit_txt_out = out / AUDIT_TXT
    report["outputs"] = {
        "json": str(json_out),
        "audit_json": str(audit_json_out),
        "audit_txt": str(audit_txt_out),
    }
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    audit_json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    audit_txt_out.write_text(render_audit_txt(report), encoding="utf-8")
    return report
