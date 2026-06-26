from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "axis_integrity_tagger_lite_v1"
CLAIM_SAFETY = "AXIS_INTEGRITY_CANDIDATE_ONLY"
OUTPUT_JSON = "axis_integrity_tagger_lite_v1.json"
OUTPUT_TXT = "axis_integrity_tagger_lite_v1.txt"
TIME_ROUTER_JSON = "time_scale_router_lite_v1.json"
EVENT_WINDOW_JSON = "event_window_builder_lite_v1.json"
MIN_CONTEXT_JSON = "minimum_viable_context_lite_v1.json"
AVAILABLE = "AXIS_AVAILABLE"
PARTIAL = "AXIS_PARTIAL"
MISSING = "AXIS_MISSING"
UNKNOWN = "AXIS_UNKNOWN"


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


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def safe_int(value: Any) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def status_score(status: str) -> float:
    if status == AVAILABLE:
        return 1.0
    if status == PARTIAL:
        return 0.5
    return 0.0


def rows_from(payload: dict[str, Any], full_key: str, sample_key: str) -> list[dict[str, Any]]:
    rows = payload.get(full_key)
    if not isinstance(rows, list):
        rows = payload.get(sample_key)
    return [x for x in rows if isinstance(x, dict)] if isinstance(rows, list) else []


def has_value(value: Any) -> bool:
    return value not in (None, "", "unknown", "UNKNOWN", "UNKNOWN_ZONE", "UNKNOWN_CHANNEL")


def count_rows_with_keys(rows: list[dict[str, Any]], keys: list[str]) -> int:
    return sum(1 for row in rows if any(has_value(row.get(key)) for key in keys))


def count_rows_with_count_dict(rows: list[dict[str, Any]], keys: list[str]) -> int:
    count = 0
    for row in rows:
        for key in keys:
            value = row.get(key)
            if isinstance(value, dict) and any(safe_int(v) > 0 for v in value.values()):
                count += 1
                break
    return count


def ratio_status(count: int, total: int, empty_status: str = UNKNOWN) -> str:
    if total <= 0:
        return empty_status
    ratio = count / total
    if ratio >= 0.75:
        return AVAILABLE
    if ratio > 0:
        return PARTIAL
    return MISSING


def axis_from_context_or_windows(contexts: list[dict[str, Any]], windows: list[dict[str, Any]], context_keys: list[str], window_count_keys: list[str]) -> str:
    context_status = ratio_status(count_rows_with_keys(contexts, context_keys), len(contexts))
    if context_status != UNKNOWN:
        return context_status
    return ratio_status(count_rows_with_count_dict(windows, window_count_keys), len(windows))


def build_axis_report(input_dir: str | Path) -> dict[str, Any]:
    root = Path(input_dir).expanduser().resolve(strict=False)
    tsr = read_json(root / TIME_ROUTER_JSON)
    ewb = read_json(root / EVENT_WINDOW_JSON)
    mvc = read_json(root / MIN_CONTEXT_JSON)
    contexts = rows_from(mvc, "context_candidates", "context_candidates_sample")
    windows = rows_from(ewb, "event_windows", "event_windows_sample")
    routed_count = safe_int(tsr.get("routed_window_count"))
    minute_axis_count = safe_int(tsr.get("minute_axis_window_count"))
    event_index_count = safe_int(tsr.get("event_index_window_count"))

    if routed_count > 0:
        minute_status = ratio_status(minute_axis_count, routed_count, empty_status=MISSING)
    else:
        minute_status = ratio_status(count_rows_with_keys(windows, ["start_minute", "end_minute"]), len(windows), empty_status=MISSING)

    event_index_status = AVAILABLE if event_index_count > 0 else MISSING
    second_status = ratio_status(count_rows_with_keys(contexts, ["second", "seconds", "second_raw", "timestamp", "timestamp_raw"]), len(contexts))
    space_status = axis_from_context_or_windows(contexts, windows, ["x_meters", "y_meters", "x_raw", "y_raw", "zone_candidate", "channel_candidate"], ["zone_counts", "channel_counts"])
    team_status = axis_from_context_or_windows(contexts, windows, ["team_label", "team_raw", "team_normalized"], ["team_label_counts"])
    action_status = axis_from_context_or_windows(contexts, windows, ["action_family", "event_family", "event_type_raw"], ["action_family_counts"])

    statuses = [minute_status, second_status, event_index_status, space_status, team_status, action_status]
    score = round(sum(status_score(s) for s in statuses) / len(statuses), 4)
    time_allowed = minute_status in {AVAILABLE, PARTIAL}
    phase_allowed = time_allowed and space_status in {AVAILABLE, PARTIAL} and action_status in {AVAILABLE, PARTIAL}
    sequence_allowed = time_allowed and team_status in {AVAILABLE, PARTIAL} and action_status in {AVAILABLE, PARTIAL}
    rhythm_allowed = time_allowed and routed_count > 0

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED",
        "decision": "AXIS_INTEGRITY_CANDIDATES_ONLY",
        "claim_safety": CLAIM_SAFETY,
        "input_dir": str(root),
        "input_counts": {"context_sample_count": len(contexts), "event_window_sample_count": len(windows), "routed_window_count": routed_count},
        "axis_status": {"minute_axis_status": minute_status, "second_axis_status": second_status, "event_index_axis_status": event_index_status, "space_axis_status": space_status, "team_axis_status": team_status, "action_family_axis_status": action_status},
        "axis_integrity_score": score,
        "downstream_permissions": {"downstream_time_allowed": time_allowed, "downstream_phase_candidate_allowed": phase_allowed, "downstream_sequence_candidate_allowed": sequence_allowed, "downstream_rhythm_candidate_allowed": rhythm_allowed},
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "rhythm_truth": False,
        "time_window_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "claim_allowed": False,
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = ["HPFA AXIS INTEGRITY TAGGER LITE V1", "==================================="]
    for key in ["status", "decision", "claim_safety", "axis_integrity_score"]:
        lines.append(f"{key}={report.get(key)}")
    lines += ["", "[input_counts]", json.dumps(report.get("input_counts", {}), ensure_ascii=False, sort_keys=True), "", "[axis_status]", json.dumps(report.get("axis_status", {}), ensure_ascii=False, sort_keys=True), "", "[downstream_permissions]", json.dumps(report.get("downstream_permissions", {}), ensure_ascii=False, sort_keys=True)]
    for key in ["canonical_event_count", "phase_truth", "possession_truth", "sequence_truth", "rhythm_truth", "time_window_truth"]:
        lines.append(f"{key}={report.get(key)}")
    return "\n".join(lines) + "\n"


def write_outputs(input_dir: str | Path, out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine = spine_runner_module(repo_root)
    output_root = spine.validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    report = build_axis_report(input_dir)
    json_out = output_root / OUTPUT_JSON
    txt_out = output_root / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
