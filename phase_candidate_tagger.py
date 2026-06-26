from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

OUT_JSON = "phase_candidate_tagger_lite_v1.json"
OUT_TXT = "phase_candidate_tagger_lite_v1.txt"
MAX_PHASE_MINUTE = 130


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


def rows(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], bool]:
    full = payload.get("event_windows")
    if isinstance(full, list):
        return [x for x in full if isinstance(x, dict)], False
    sample = payload.get("event_windows_sample")
    out = [x for x in sample if isinstance(x, dict)] if isinstance(sample, list) else []
    return out, num(payload.get("event_window_count")) > len(out)


def add_spine_path(repo_root: Path) -> None:
    p = repo_root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


def validate_out(repo_root: Path, out_dir: Path) -> Path:
    add_spine_path(repo_root)
    import spine_runner  # type: ignore
    return spine_runner.validate_output_root(out_dir)


def top_key(counts: dict[str, Any]) -> str:
    if not isinstance(counts, dict) or not counts:
        return "UNKNOWN"
    return max(counts.items(), key=lambda kv: num(kv[1]))[0]


def end_minute(w: dict[str, Any]) -> int | None:
    if w.get("end_minute") is None:
        return None
    return num(w.get("end_minute"))


def window_range(w: dict[str, Any]) -> str:
    if w.get("start_minute") is not None or w.get("end_minute") is not None:
        return f"minute:{w.get('start_minute')}-{w.get('end_minute')}"
    if w.get("start_index") is not None or w.get("end_index") is not None:
        return f"index:{w.get('start_index')}-{w.get('end_index')}"
    return "unknown"


def classify(w: dict[str, Any]) -> tuple[str, list[str]]:
    actions = w.get("action_family_counts", {}) if isinstance(w.get("action_family_counts"), dict) else {}
    zones = w.get("zone_counts", {}) if isinstance(w.get("zone_counts"), dict) else {}
    reasons: list[str] = []
    rows_count = num(w.get("surface_row_count"))
    top_zone = top_key(zones)
    pass_count = num(actions.get("PASS"))
    shot_count = num(actions.get("SHOT"))
    duel_count = num(actions.get("DUEL_PRESSURE"))
    restart_count = num(actions.get("RESTART")) + num(actions.get("DEAD_BALL"))
    final_zone = num(zones.get("FINAL_THIRD"))
    middle_zone = num(zones.get("MIDDLE_THIRD"))
    defensive_zone = num(zones.get("DEFENSIVE_THIRD"))
    minute_end = end_minute(w)

    if minute_end is not None and minute_end > MAX_PHASE_MINUTE:
        return "TIME_AXIS_REVIEW_REQUIRED_CANDIDATE", ["minute_range_exceeds_phase_gate"]
    if rows_count <= 0:
        return "LOW_SIGNAL_SURFACE_CANDIDATE", ["no_surface_rows"]

    restart_share = restart_count / max(rows_count, 1)
    shot_share = shot_count / max(rows_count, 1)
    duel_share = duel_count / max(rows_count, 1)
    final_zone_share = final_zone / max(rows_count, 1)

    if restart_count >= 3 and restart_share >= 0.03:
        return "RESTART_SURFACE_CANDIDATE", ["restart_dead_ball_share_gate"]
    if shot_count >= 3 and (shot_share >= 0.10 or bool(w.get("terminal_action_surface_present"))):
        return "FINAL_ACTION_SURFACE_CANDIDATE", ["shot_terminal_share_gate"]
    if duel_count >= 3 and duel_share >= 0.15:
        return "DUEL_PRESSURE_SURFACE_CANDIDATE", ["duel_pressure_share_gate"]
    if final_zone >= 3 and (top_zone == "FINAL_THIRD" or final_zone_share >= 0.18):
        return "FINAL_ACTION_SURFACE_CANDIDATE", ["final_third_share_gate"]
    if top_zone == "DEFENSIVE_THIRD" and defensive_zone >= middle_zone:
        return "BUILDUP_SURFACE_CANDIDATE", ["defensive_third_surface_gate"]
    if top_zone == "MIDDLE_THIRD" or middle_zone >= defensive_zone:
        return "PROGRESSION_SURFACE_CANDIDATE", ["middle_third_progression_surface_gate"]
    if pass_count > 0:
        return "PROGRESSION_SURFACE_CANDIDATE", ["pass_surface_without_zone_resolution"]
    return "LOW_SIGNAL_SURFACE_CANDIDATE", ["insufficient_phase_surface"]


def build(input_dir: Path) -> dict[str, Any]:
    ewb = load(input_dir / "event_window_builder_lite_v1.json")
    tsr = load(input_dir / "time_scale_router_lite_v1.json")
    axis = load(input_dir / "axis_integrity_tagger_lite_v1.json")
    windows, truncated = rows(ewb)
    axis_permissions = axis.get("downstream_permissions", {}) if isinstance(axis.get("downstream_permissions"), dict) else {}
    allowed = axis_permissions.get("downstream_phase_candidate_allowed") is True
    ready = allowed and bool(ewb) and bool(tsr) and bool(axis) and not truncated and len(windows) > 0
    status = "REVIEW_REQUIRED" if ready else "FAIL_CLOSED"
    decision = "PHASE_CANDIDATES_EXPORTED" if ready else "PHASE_CANDIDATES_NOT_READY"
    candidates = []
    counts: Counter[str] = Counter()
    if ready:
        for w in windows:
            label, reasons = classify(w)
            counts[label] += 1
            candidates.append({"window_id": w.get("window_id"), "range": window_range(w), "window_axis": w.get("window_axis"), "phase_candidate": label, "reasons": reasons, "surface_row_count": w.get("surface_row_count"), "window_confidence": w.get("window_confidence")})
    return {
        "module_id": "phase_candidate_tagger_lite_v1",
        "status": status,
        "decision": decision,
        "claim_safety": "PHASE_CANDIDATE_ONLY",
        "donor_evidence": {"source_repo": "HP-Motor", "adapted_from": ["hp_motor/segmentation/phase_tagger.py", "STEP12_PHASE_TAGGER_MVP.py"], "adaptation": "candidate_only_window_surface_labels"},
        "input_checks": {"phase_candidate_allowed": allowed, "window_sample_truncated": truncated, "loaded_windows": len(windows), "max_phase_minute": MAX_PHASE_MINUTE},
        "summary": {"phase_candidate_count": len(candidates), "phase_candidate_counts": dict(counts.most_common())},
        "phase_candidates_sample": candidates[:40],
        "claim_boundary": {"canonical_event_count": "UNKNOWN", "phase_truth": False, "possession_truth": False, "sequence_truth": False, "rhythm_truth": False, "tactical_truth": False, "dominance_truth": False},
    }


def render(report: dict[str, Any]) -> str:
    lines = ["HPFA PHASE CANDIDATE TAGGER LITE V1", "=======================================", f"status={report.get('status')}", f"decision={report.get('decision')}", f"claim_safety={report.get('claim_safety')}", "", "DONOR EVIDENCE", json.dumps(report.get("donor_evidence", {}), ensure_ascii=False, sort_keys=True), "", "INPUT CHECKS", json.dumps(report.get("input_checks", {}), ensure_ascii=False, sort_keys=True), "", "SUMMARY", json.dumps(report.get("summary", {}), ensure_ascii=False, sort_keys=True), "", "SAMPLE"]
    for row in report.get("phase_candidates_sample", []):
        lines.append(f"- {row.get('range')} | {row.get('phase_candidate')} | rows={row.get('surface_row_count')} | confidence={row.get('window_confidence')} | reasons={row.get('reasons')}")
    lines += ["", "CLAIM BOUNDARY"]
    for k, v in report.get("claim_boundary", {}).items():
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
    print(json.dumps({"status": report.get("status"), "decision": report.get("decision"), "summary": report.get("summary"), "input_checks": report.get("input_checks"), "outputs": report.get("outputs")}, ensure_ascii=False, sort_keys=True))
    return 0 if report.get("status") != "FAIL_CLOSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
