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
    ensure_path(root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src")
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
    return 0.0 if whole in (0, 0.0) else round((part / whole) * 100.0, 2)


def ratio(a: float, b: float) -> float | str:
    return "NA" if b in (0, 0.0) else round(a / b, 3)


def team_display_label(item: dict[str, Any]) -> str:
    for key in ("display_label_candidate", "team_entity_key", "team_name", "team_raw", "name", "team", "entity_name"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return "UNKNOWN_TEAM"


def team_rows(team_binding: dict[str, Any]) -> list[dict[str, Any]]:
    teams = team_binding.get("team_entities") or team_binding.get("teams") or []
    if isinstance(teams, dict):
        teams = list(teams.values())
    clean: list[dict[str, Any]] = []
    for item in teams if isinstance(teams, list) else []:
        if not isinstance(item, dict):
            continue
        visible = item.get("visible_rows") or item.get("row_count") or item.get("rows") or item.get("surface_rows") or 0
        clean.append({
            "team": team_display_label(item),
            "visible_rows": int(visible or 0),
            "event_family_volume": item.get("event_family_volume") or item.get("action_family_volume") or {},
            "zone_distribution": item.get("zone_distribution") or item.get("zone_volume") or {},
            "channel_distribution": item.get("channel_distribution") or item.get("channel_volume") or {},
        })
    clean.sort(key=lambda x: x["visible_rows"], reverse=True)
    return clean


def compare_dicts(left: dict[str, Any], right: dict[str, Any], left_total: int, right_total: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(set(left.keys()) | set(right.keys())):
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


def row_by_metric(rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    for row in rows:
        if row.get("metric") == metric:
            return row
    return {"left": 0, "right": 0, "diff_left_minus_right": 0, "ratio_left_to_right": "NA", "left_share_pct": 0, "right_share_pct": 0, "share_gap_pp": 0}


def analyst_translation(team_comparison: dict[str, Any], action: list[dict[str, Any]], zones: list[dict[str, Any]], channels: list[dict[str, Any]]) -> list[str]:
    left = str(team_comparison.get("left_team"))
    right = str(team_comparison.get("right_team"))
    lines = [
        f"{left}, bound visible row-volume içinde {team_comparison.get('left_row_share_pct')}% pay aldı; {right} {team_comparison.get('right_row_share_pct')}% seviyesinde kaldı. Bu, {left} tarafında daha yüksek görünür aksiyon hacmi olduğunu gösterir; canonical event count değildir.",
        f"Toplam bound visible row farkı {team_comparison.get('row_diff_left_minus_right')}; oran {team_comparison.get('row_ratio_left_to_right')}. Yani {left} yüzeyi {right} yüzeyinin yaklaşık {team_comparison.get('row_ratio_left_to_right')} katı hacim üretti.",
    ]
    for metric, label in [
        ("PASS", "pas hacmi"),
        ("POSITIONAL_ATTACK_SIGNAL", "pozisyonel hücum sinyali"),
        ("SHOT", "şut yüzeyi"),
        ("CARRY_DRIBBLE", "taşıma/dribbling yüzeyi"),
        ("GOALKEEPER_RESTART", "kaleci restart yüzeyi"),
        ("DUEL_PRESSURE", "duel/pressure yüzeyi"),
    ]:
        row = row_by_metric(action, metric)
        lines.append(f"{label}: {left} {row.get('left')}, {right} {row.get('right')}; fark {row.get('diff_left_minus_right')}, oran {row.get('ratio_left_to_right')}. Pay farkı {row.get('share_gap_pp')} puan.")
    final_third = row_by_metric(zones, "FINAL_THIRD")
    middle = row_by_metric(zones, "MIDDLE_THIRD")
    defensive = row_by_metric(zones, "DEFENSIVE_THIRD")
    right_ch = row_by_metric(channels, "RIGHT_CHANNEL")
    central = row_by_metric(channels, "CENTRAL_CHANNEL")
    left_ch = row_by_metric(channels, "LEFT_CHANNEL")
    lines.append(f"Bölge okuması: {left} final third'de {final_third.get('left')} row, {right} {final_third.get('right')} row; fark {final_third.get('diff_left_minus_right')} ve share gap {final_third.get('share_gap_pp')} puan.")
    lines.append(f"Orta bölge: {left} {middle.get('left')}, {right} {middle.get('right')}; fark {middle.get('diff_left_minus_right')}. Bu, {left} event-coordinate evidence'ının orta/ileri hatta yoğunlaştığını gösterir.")
    lines.append(f"Savunma bölgesi: {left} {defensive.get('left')}, {right} {defensive.get('right')}; {right} lehine {abs(int(defensive.get('diff_left_minus_right', 0)))} row farkı ve {abs(float(defensive.get('share_gap_pp', 0)))} puan share gap var.")
    lines.append(f"Kanal okuması: sağ kanalda {left} {right_ch.get('left')}, {right} {right_ch.get('right')}; fark {right_ch.get('diff_left_minus_right')}, oran {right_ch.get('ratio_left_to_right')}. Bu maç yüzeyinde {left} sağ kanal yoğunluğu belirgin.")
    lines.append(f"Merkez kanal payı {right} lehine: {left} {central.get('left_share_pct')}%, {right} {central.get('right_share_pct')}%, gap {central.get('share_gap_pp')} puan.")
    lines.append(f"Sol kanal payı da {right} lehine: {left} {left_ch.get('left_share_pct')}%, {right} {left_ch.get('right_share_pct')}%, gap {left_ch.get('share_gap_pp')} puan.")
    lines.append("Analyst conclusion: row-level evidence yüksek hacimli Türkiye yüzeyi ve daha düşük hacimli Avustralya yüzeyi gösteriyor. Bu, skor/verimlilik yorumuna adaydır; efficiency truth değildir ve Action Value Cost Fusion gerektirir.")
    return lines


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
    action = compare_dicts(left.get("event_family_volume", {}), right.get("event_family_volume", {}), left_total, right_total)
    zones = compare_dicts(left.get("zone_distribution", {}), right.get("zone_distribution", {}), left_total, right_total)
    channels = compare_dicts(left.get("channel_distribution", {}), right.get("channel_distribution", {}), left_total, right_total)
    team_comparison = {
        "left_team": left.get("team"),
        "right_team": right.get("team"),
        "left_visible_rows": left_total,
        "right_visible_rows": right_total,
        "total_bound_visible_rows": total,
        "left_row_share_pct": pct(left_total, total),
        "right_row_share_pct": pct(right_total, total),
        "row_diff_left_minus_right": left_total - right_total,
        "row_ratio_left_to_right": ratio(left_total, right_total),
    }
    return {
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
        "team_comparison": team_comparison,
        "action_family_comparison": action,
        "zone_comparison": zones,
        "channel_comparison": channels,
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
        "canonical_surface_summary": {"available": bool(canonical), "surface_row_inventory_total": canonical.get("surface_row_inventory_total")},
        "analyst_numeric_findings": numeric_findings(left, right, action, zones, channels),
        "analyst_translation": analyst_translation(team_comparison, action, zones, channels),
        "blocked_claims": ["validated event count", "primary event truth", "possession truth", "phase truth", "sequence truth", "metric truth", "efficiency truth"],
    }


def numeric_findings(left: dict[str, Any], right: dict[str, Any], action_rows: list[dict[str, Any]], zone_rows: list[dict[str, Any]], channel_rows: list[dict[str, Any]]) -> list[str]:
    left_name = str(left.get("team"))
    right_name = str(right.get("team"))
    findings = [f"{left_name} visible row-volume {left.get('visible_rows')}; {right_name} visible row-volume {right.get('visible_rows')}; ratio {ratio(int(left.get('visible_rows', 0)), int(right.get('visible_rows', 0)))}."]
    for row in action_rows[:5]:
        findings.append(f"Action family {row['metric']}: {left_name} {row['left']} ({row['left_share_pct']}%), {right_name} {row['right']} ({row['right_share_pct']}%), diff {row['diff_left_minus_right']}, ratio {row['ratio_left_to_right']}.")
    for row in zone_rows[:3]:
        findings.append(f"Zone {row['metric']}: {left_name} {row['left']} ({row['left_share_pct']}%), {right_name} {row['right']} ({row['right_share_pct']}%), share gap {row['share_gap_pp']}pp.")
    for row in channel_rows[:3]:
        findings.append(f"Channel {row['metric']}: {left_name} {row['left']} ({row['left_share_pct']}%), {right_name} {row['right']} ({row['right_share_pct']}%), share gap {row['share_gap_pp']}pp.")
    return findings


def render_table(rows: list[dict[str, Any]], title: str, left_name: str, right_name: str, limit: int = 10) -> list[str]:
    lines = [title, "-" * len(title), f"Metric | {left_name} | {right_name} | Diff | Ratio | {left_name}% | {right_name}% | Gap pp"]
    for row in rows[:limit]:
        lines.append(f"{row['metric']} | {row['left']} | {row['right']} | {row['diff_left_minus_right']} | {row['ratio_left_to_right']} | {row['left_share_pct']} | {row['right_share_pct']} | {row['share_gap_pp']}")
    return lines


def render_txt(report: dict[str, Any]) -> str:
    tc = report.get("team_comparison", {})
    left_name = str(tc.get("left_team"))
    right_name = str(tc.get("right_team"))
    lines = ["HPFA POSTMATCH ANALYST REPORT LITE V1", "======================================", f"status={report.get('status')}", f"claim_safety={report.get('claim_safety')}", "", "[surface_status]"]
    for key, value in report.get("surface_status", {}).items():
        lines.append(f"{key}={value}")
    lines += ["", "[team_row_volume]", f"{left_name}_visible_rows={tc.get('left_visible_rows')}", f"{right_name}_visible_rows={tc.get('right_visible_rows')}", f"row_diff_left_minus_right={tc.get('row_diff_left_minus_right')}", f"row_ratio_left_to_right={tc.get('row_ratio_left_to_right')}", f"{left_name}_row_share_pct={tc.get('left_row_share_pct')}", f"{right_name}_row_share_pct={tc.get('right_row_share_pct')}", ""]
    lines += render_table(report.get("action_family_comparison", []), "[action_family_comparison]", left_name, right_name, 12) + [""]
    lines += render_table(report.get("zone_comparison", []), "[zone_comparison]", left_name, right_name, 8) + [""]
    lines += render_table(report.get("channel_comparison", []), "[channel_comparison]", left_name, right_name, 8)
    lines += ["", "[analyst_translation]"] + [f"- {x}" for x in report.get("analyst_translation", [])]
    for block in ("physical_report_summary", "metric_registry_summary", "identity_summary"):
        lines += ["", f"[{block}]", json.dumps(report.get(block, {}), ensure_ascii=False, sort_keys=True)]
    lines += ["", "[analyst_numeric_findings]"] + [f"- {x}" for x in report.get("analyst_numeric_findings", [])]
    lines += ["", "[blocked_claims]"] + [f"- {x}" for x in report.get("blocked_claims", [])]
    lines.append("")
    return "\n".join(lines)


def write_outputs(out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    out = spine_runner_module(repo_root).validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_report(out)
    json_out = out / OUTPUT_JSON
    txt_out = out / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
