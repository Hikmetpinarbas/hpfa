from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

OUT_JSON = "match_reading_export_lite_v1.json"
OUT_TXT = "match_reading_export_lite_v1.txt"


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def num(value: Any) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def flt(value: Any) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def rows(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    full = payload.get("event_windows")
    if isinstance(full, list):
        return [x for x in full if isinstance(x, dict)], False
    sample = payload.get("event_windows_sample")
    sample_rows = [x for x in sample if isinstance(x, dict)] if isinstance(sample, list) else []
    return sample_rows, num(payload.get("event_window_count")) > len(sample_rows)


def add_counter(counter: Counter[str], value: Any) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            counter[str(k)] += num(v)


def top(counter: Counter[str], limit: int = 6) -> list[list[Any]]:
    total = sum(counter.values())
    return [[k, v, round((v / total) * 100, 1) if total else 0.0] for k, v in counter.most_common(limit)]


def win_range(w: dict[str, Any]) -> str:
    if w.get("start_minute") is not None or w.get("end_minute") is not None:
        return f"minute:{w.get('start_minute')}-{w.get('end_minute')}"
    if w.get("start_index") is not None or w.get("end_index") is not None:
        return f"index:{w.get('start_index')}-{w.get('end_index')}"
    return "unknown"


def card(w: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": w.get("window_id"),
        "axis": w.get("window_axis"),
        "range": win_range(w),
        "rows": w.get("surface_row_count"),
        "density": w.get("context_density"),
        "confidence": w.get("window_confidence"),
    }


def add_spine_path(repo_root: Path) -> None:
    p = repo_root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def validate_out(repo_root: Path, out_dir: Path) -> Path:
    add_spine_path(repo_root)
    import spine_runner  # type: ignore
    return spine_runner.validate_output_root(out_dir)


def artifact_ready(payload: dict[str, Any], keys: list[str]) -> bool:
    return bool(payload) and all(k in payload for k in keys)


def build(input_dir: Path) -> dict[str, Any]:
    full = load(input_dir / "active_match_full_run_lite_v1.json")
    ewb = load(input_dir / "event_window_builder_lite_v1.json")
    tsr = load(input_dir / "time_scale_router_lite_v1.json")
    axis = load(input_dir / "axis_integrity_tagger_lite_v1.json")
    windows, truncated = rows(ewb)
    valid = full.get("engineering_evidence", {}).get("valid_run") is True
    event_ready = artifact_ready(ewb, ["event_window_count", "input_context_count"])
    time_ready = artifact_ready(tsr, ["routed_window_count", "minute_axis_window_count"])
    axis_ready = artifact_ready(axis, ["axis_integrity_score", "axis_status"])
    loaded = len(windows)
    declared = num(ewb.get("event_window_count"))
    nonzero_windows = declared > 0 and loaded > 0

    status = "REVIEW_REQUIRED"
    decision = "MATCH_READING_EXPORTED"
    if not valid or not event_ready or not time_ready or not axis_ready or not nonzero_windows or truncated:
        status = "FAIL_CLOSED"
        decision = "UPSTREAM_EVIDENCE_NOT_READY"
        windows = []

    actions: Counter[str] = Counter()
    zones: Counter[str] = Counter()
    channels: Counter[str] = Counter()
    teams: Counter[str] = Counter()
    for w in windows:
        add_counter(actions, w.get("action_family_counts"))
        add_counter(zones, w.get("zone_counts"))
        add_counter(channels, w.get("channel_counts"))
        add_counter(teams, w.get("team_label_counts"))

    dense = sorted(windows, key=lambda x: flt(x.get("context_density")), reverse=True)[:6]
    terminal = [w for w in windows if bool(w.get("terminal_action_surface_present"))][:6]
    restart = [w for w in windows if bool(w.get("restart_surface_present"))][:6]

    return {
        "module_id": "match_reading_export_lite_v1",
        "status": status,
        "decision": decision,
        "claim_safety": "MATCH_READING_CANDIDATE_ONLY",
        "input_checks": {"full_run_valid": valid, "event_window_artifact_ready": event_ready, "time_scale_artifact_ready": time_ready, "axis_artifact_ready": axis_ready, "nonzero_windows": nonzero_windows, "window_sample_truncated": truncated, "loaded_windows": len(windows), "declared_event_window_count": ewb.get("event_window_count")},
        "runtime": {"input_context_count": ewb.get("input_context_count"), "minute_bearing_context_count": ewb.get("minute_bearing_context_count"), "event_window_count": ewb.get("event_window_count"), "routed_window_count": tsr.get("routed_window_count"), "minute_axis_window_count": tsr.get("minute_axis_window_count"), "axis_integrity_score": axis.get("axis_integrity_score")},
        "axis_status": axis.get("axis_status", {}),
        "permissions": axis.get("downstream_permissions", {}),
        "surfaces": {"actions": top(actions, 8), "zones": top(zones, 6), "channels": top(channels, 6), "teams": top(teams, 6)},
        "windows": {"high_density": [card(w) for w in dense], "final_action_surface": [card(w) for w in terminal], "restart_surface": [card(w) for w in restart]},
        "closed_claims": {"canonical_event_count": "UNKNOWN", "phase_truth": False, "possession_truth": False, "sequence_truth": False, "rhythm_truth": False, "tactical_truth": False, "dominance_truth": False},
    }


def render(report: dict[str, Any]) -> str:
    lines = ["HPFA MATCH READING EXPORT LITE V1", "==================================", f"status={report.get('status')}", f"decision={report.get('decision')}", f"claim_safety={report.get('claim_safety')}", "", "INPUT CHECKS", json.dumps(report.get("input_checks", {}), ensure_ascii=False, sort_keys=True)]
    if report.get("status") == "FAIL_CLOSED":
        lines += ["", "READING NOT WRITTEN", "Upstream evidence is not ready for an analyst reading."]
    else:
        r = report.get("runtime", {})
        lines += ["", "MATCH READABILITY", f"Context candidates: {r.get('input_context_count')}", f"Minute-bearing candidates: {r.get('minute_bearing_context_count')}", f"Windows: {r.get('event_window_count')}", f"Routed windows: {r.get('routed_window_count')}", f"Minute-axis windows: {r.get('minute_axis_window_count')}", f"Axis score: {r.get('axis_integrity_score')}", "", "AXES"]
        for k, v in report.get("axis_status", {}).items():
            lines.append(f"- {k}: {v}")
        lines += ["", "SURFACE MAP"]
        for title, key in [("Actions", "actions"), ("Zones", "zones"), ("Channels", "channels"), ("Teams", "teams")]:
            lines.append(f"[{title}]")
            for label, count, pct in report.get("surfaces", {}).get(key, []):
                lines.append(f"- {label}: {count} surface rows ({pct}%)")
        lines += ["", "WINDOW MAP"]
        for group, cards in report.get("windows", {}).items():
            lines.append(f"[{group}]")
            for item in cards:
                lines.append(f"- {item.get('range')} | axis={item.get('axis')} | rows={item.get('rows')} | density={item.get('density')} | confidence={item.get('confidence')}")
        lines += ["", "STAFF NOTE", "This is a candidate-level match reading. It shows surface concentration and window structure. It does not create final football truth."]
    lines += ["", "CLOSED CLAIMS"]
    for k, v in report.get("closed_claims", {}).items():
        lines.append(f"- {k}={v}")
    return "\n".join(lines) + "\n"


def write(input_dir: Path, out_dir: Path, repo_root: Path) -> dict[str, Any]:
    out = validate_out(repo_root, out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build(input_dir)
    report["outputs"] = {"json": str(out / OUT_JSON), "txt": str(out / OUT_TXT)}
    (out / OUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (out / OUT_TXT).write_text(render(report), encoding="utf-8")
    return report


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="runtime/outputs/active_match_current")
    parser.add_argument("--out-dir", default="runtime/outputs/active_match_current")
    args = parser.parse_args()
    input_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir)
    if not input_dir.is_absolute():
        input_dir = repo_root / input_dir
    if not out_dir.is_absolute():
        out_dir = repo_root / out_dir
    report = write(input_dir, out_dir, repo_root)
    print(json.dumps({"status": report.get("status"), "decision": report.get("decision"), "outputs": report.get("outputs"), "input_checks": report.get("input_checks")}, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("status") != "FAIL_CLOSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
