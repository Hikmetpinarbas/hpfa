from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "postmatch_analyst_report_lite_v1"
CLAIM_SAFETY = "CLAIM_SAFE_NUMERIC_POSTMATCH_REPORT"
OUTPUT_JSON = "postmatch_analyst_report_lite_v1.json"
OUTPUT_TXT = "postmatch_analyst_report_lite_v1.txt"


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def ensure_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def spine_runner_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    ensure_path(src)
    import spine_runner  # type: ignore

    return spine_runner


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def pct(part: float, whole: float) -> float:
    if whole in (0, 0.0):
        return 0.0
    return round((part / whole) * 100.0, 2)


def ratio(a: float, b: float) -> float | str:
    if b in (0, 0.0):
        return "NA"
    return round(a / b, 3)


def diff(a: float, b: float) -> float:
    return round(a - b, 3)


def team_rows(team_binding: dict[str, Any]) -> list[dict[str, Any]]:
    teams = team_binding.get("team_entities") or team_binding.get("teams") or []
    if isinstance(teams, dict):
        teams = list(teams.values())
    clean: list[dict[str, Any]] = []
    for item in teams if isinstance(teams, list) else []:
        if not isinstance(item, dict):
            continue
        name = item.get("team_name") or item.get("team_raw") or item.get("name") or item.get("team") or item.get("entity_name")
        visible = item.get("visible_rows") or item.get("row_count") or item.get("rows") or item.get("surface_rows") or 0
        clean.append({
            "team": str(name) if name else "UNKNOWN_TEAM",
            "visible_rows": int(visible or 0),
            "event_family_volume": item.get("event_family_volume") or item.get("action_family_volume") or {},
            "zone_distribution": item.get("zone_distribution") or item.get("zone_volume") or {},
            "channel_distribution": item.get("channel_distribution") or item.get("channel_volume") or {},
        })
    clean.sort(key=lambda x: x["visible_rows"], reverse=True)
    return clean


def compare_dicts(left: dict[str, Any], right: dict[str, Any], left_total: int, right_total: int) -> list[dict[str, Any]]:
    keys = sorted(set(left.keys()) | set(right.keys()))
    rows = []
    for key in keys:
        lv = int(left.get(key, 0) or 0)
        rv = int(right.get(key, 0) or 0)
        rows.append({
            "metric": key,
            "left": lv,
            "right": rv,
            "diff_left_minus_right": lv - rv,
            "ratio_left_to_right": ratio(lv, rv),
            "left_share_pct": pct(lv, left_total),
            "right_share_pct": pct(rv, right_total),
            "share_gap_pp": round(pct(lv, left_total) - pct(rv, right_total), 2),
        })
    rows.sort(key=lambda r: abs(int(r["diff_left_minus_right"])), reverse=True)
    return rows


def top_items(rows: list[dict[str, Any]], n: int = 8) -> list[dict[str, Any]]:
    return rows[:n]


def build_report(out_dir: str | Path) -> dict[str, Any]:
    root = Path(out_dir).expanduser().resolve(strict=False)
    team_binding = read_json(root / "team_binding_lite_audit_v1.json")
    primary = read_json(root / "primary_event_surface_gate_lite_v1.json")
    metric_registry = read_json(root / "metric_family_registry_lite_v1.json")
    physical = read_json(root / "physical_cost_surface_audit_v1.json")
    identity = read_json(root / "event_identity_resolution_gate_lite_v1.json")
    canonical = read_json(root / "canonical_event_lite_audit_v1.json")

    teams = team_rows(team_binding)
    left = teams[0] if teams else {"team": "TEAM_A", "visible_rows": 0, "event_family_volume": {}, "zone_distribution": {}, "channel_distribution": {}}
    right = teams[1] if len(teams) > 1 else {"team": "TEAM_B", "visible_rows": 0, "event_family_volume": {}, "zone_distribution": {}, "channel_distribution": {}}

    left_total = int(left.get("visible_rows", 0) or 0)
    right_total = int(right.get("visible_rows", 0) or 0)
    total = left_total + right_total

    action_family_comparison = compare_dicts(left.get("event_family_volume", {}), right.get("event_family_volume", {}), left_total, right_total)
    zone_comparison = compare_dicts(left.get("zone_distribution", {}), right.get("zone_distribution", {}), left_total, right_total)
    channel_comparison = compare_dicts(left.get("channel_distribution", {}), right.get("channel_distribution", {}), left_total, right_total)

    report = {
        "module_id": MODULE_ID,
        "status": "PASS",
        "claim_safety": CLAIM_SAFETY,
        "surface_status": {
            "canonical_event_count": "UNKNOWN",
            "deduplicated_event_count": "UNKNOWN",
            "primary_surface_decision": primary.get("decision"),
            "primary_event_surface_candidate": primary.get("primary_event_surface_candidate"),
            "event_count_claim_allowed": False,
            "metric_count_allowed": False,
        },
        "team_comparison": {
            "left_team": left.get("team"),
            "right_team": right.get("team"),
            "left_visible_rows": left_total,
            "right_visible_rows": right_total,
            "total_bound_visible_rows": total,
            "left_row_share_pct": pct(left_total, total),
            "right_row_share_pct": pct(right_total, total),
            "row_diff_left_minus_right": left_total - right_total,
            "row_ratio_left_to_right": ratio(left_total, right_total),
        },
        "action_family_comparison": action_family_comparison,
        "zone_comparison": zone_comparison,
        "channel_comparison": channel_comparison,
        "physical_report_summary": {
            "physical_available": bool(physical),
            "record_count": physical.get("record_count"),
            "surface_counts": physical.get("surface_counts"),
            "metric_family_counts": physical.get("metric_family_counts"),
        },
        "metric_registry_summary": {
            "available": bool(metric_registry),
            "registry_record_count": metric_registry.get("registry_record_count"),
            "family_counts": metric_registry.get("family_counts"),
            "metric_value_output_allowed": metric_registry.get("metric_value_output_allowed"),
            "efficiency_calculation_allowed": metric_registry.get("efficiency_calculation_allowed"),
        },
        "identity_summary": {
            "available": bool(identity),
            "candidate_cluster_count": identity.get("candidate_cluster_count"),
            "duplicate_risk_candidate_count": identity.get("duplicate_risk_candidate_count"),
            "metric_count_allowed": identity.get("metric_count_allowed"),
        },
        "canonical_surface_summary": {
            "available": bool(canonical),
            "surface_row_inventory_total": canonical.get("surface_row_inventory_total"),
            "event_family_volume": canonical.get("event_family_volume") or canonical.get("action_family_volume"),
            "zone_distribution": canonical.get("zone_distribution"),
            "channel_distribution": canonical.get("channel_distribution"),
        },
        "analyst_numeric_findings": numeric_findings(left, right, action_family_comparison, zone_comparison, channel_comparison),
        "blocked_claims": [
            "validated event count",
            "primary event truth",
            "possession truth",
            "phase truth",
            "sequence truth",
            "tactical dominance truth",
            "fatigue causality",
            "efficiency truth",
        ],
    }
    return report


def numeric_findings(left: dict[str, Any], right: dict[str, Any], action_rows: list[dict[str, Any]], zone_rows: list[dict[str, Any]], channel_rows: list[dict[str, Any]]) -> list[str]:
    findings: list[str] = []
    left_name = str(left.get("team"))
    right_name = str(right.get("team"))
    left_total = int(left.get("visible_rows", 0) or 0)
    right_total = int(right.get("visible_rows", 0) or 0)
    findings.append(f"{left_name} visible row-volume {left_total}; {right_name} visible row-volume {right_total}; ratio {ratio(left_total, right_total)}.")
    for row in top_items(action_rows, 5):
        findings.append(f"Action family {row['metric']}: {left_name} {row['left']} ({row['left_share_pct']}%), {right_name} {row['right']} ({row['right_share_pct']}%), diff {row['diff_left_minus_right']}, ratio {row['ratio_left_to_right']}.")
    for row in top_items(zone_rows, 3):
        findings.append(f"Zone {row['metric']}: {left_name} {row['left']} ({row['left_share_pct']}%), {right_name} {row['right']} ({row['right_share_pct']}%), share gap {row['share_gap_pp']}pp.")
    for row in top_items(channel_rows, 3):
        findings.append(f"Channel {row['metric']}: {left_name} {row['left']} ({row['left_share_pct']}%), {right_name} {row['right']} ({row['right_share_pct']}%), share gap {row['share_gap_pp']}pp.")
    return findings


def render_table(rows: list[dict[str, Any]], title: str, left_name: str, right_name: str, limit: int = 10) -> list[str]:
    lines = [title, "-" * len(title)]
    lines.append(f"Metric | {left_name} | {right_name} | Diff | Ratio | {left_name}% | {right_name}% | Gap pp")
    for row in rows[:limit]:
        lines.append(
            f"{row['metric']} | {row['left']} | {row['right']} | {row['diff_left_minus_right']} | {row['ratio_left_to_right']} | {row['left_share_pct']} | {row['right_share_pct']} | {row['share_gap_pp']}"
        )
    return lines


def render_txt(report: dict[str, Any]) -> str:
    tc = report.get("team_comparison", {})
    left_name = str(tc.get("left_team"))
    right_name = str(tc.get("right_team"))
    lines = [
        "HPFA POSTMATCH ANALYST REPORT LITE V1",
        "======================================",
        f"status={report.get('status')}",
        f"claim_safety={report.get('claim_safety')}",
        "",
        "[surface_status]",
    ]
    for key, value in report.get("surface_status", {}).items():
        lines.append(f"{key}={value}")
    lines.extend([
        "",
        "[team_row_volume]",
        f"{left_name}_visible_rows={tc.get('left_visible_rows')}",
        f"{right_name}_visible_rows={tc.get('right_visible_rows')}",
        f"row_diff_left_minus_right={tc.get('row_diff_left_minus_right')}",
        f"row_ratio_left_to_right={tc.get('row_ratio_left_to_right')}",
        f"{left_name}_row_share_pct={tc.get('left_row_share_pct')}",
        f"{right_name}_row_share_pct={tc.get('right_row_share_pct')}",
        "",
    ])
    lines.extend(render_table(report.get("action_family_comparison", []), "[action_family_comparison]", left_name, right_name, 12))
    lines.append("")
    lines.extend(render_table(report.get("zone_comparison", []), "[zone_comparison]", left_name, right_name, 8))
    lines.append("")
    lines.extend(render_table(report.get("channel_comparison", []), "[channel_comparison]", left_name, right_name, 8))
    lines.extend(["", "[physical_report_summary]", json.dumps(report.get("physical_report_summary", {}), ensure_ascii=False, sort_keys=True)])
    lines.extend(["", "[metric_registry_summary]", json.dumps(report.get("metric_registry_summary", {}), ensure_ascii=False, sort_keys=True)])
    lines.extend(["", "[identity_summary]", json.dumps(report.get("identity_summary", {}), ensure_ascii=False, sort_keys=True)])
    lines.extend(["", "[analyst_numeric_findings]"])
    for item in report.get("analyst_numeric_findings", []):
        lines.append(f"- {item}")
    lines.extend(["", "[blocked_claims]"])
    for item in report.get("blocked_claims", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine_runner = spine_runner_module(repo_root)
    out = spine_runner.validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_report(out)
    json_out = out / OUTPUT_JSON
    txt_out = out / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
