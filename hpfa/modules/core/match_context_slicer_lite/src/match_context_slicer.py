from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "match_context_slicer_lite_v1"
CLAIM_SAFETY = "CONTEXT_SLICE_CANDIDATE_ONLY"
OUTPUT_JSON = "match_context_slicer_lite_v1.json"
OUTPUT_TXT = "match_context_slicer_lite_v1.txt"
MIN_CONTEXT_JSON = "minimum_viable_context_lite_v1.json"
EVENT_WINDOWS_JSON = "event_window_builder_lite_v1.json"
REQUIRED_INPUTS = [MIN_CONTEXT_JSON, EVENT_WINDOWS_JSON]
RESTART_FAMILIES = {"RESTART", "DEAD_BALL"}


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
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def claim_boundary() -> dict[str, Any]:
    return {
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "event_count_claim_allowed": False,
        "production_binding_allowed": False,
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "time_window_truth": False,
        "score_state_truth": False,
        "card_state_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
    }


def as_int(value: Any) -> int | None:
    if value in (None, "", "unknown"):
        return None
    try:
        return int(float(str(value).replace(",", ".")))
    except ValueError:
        return None


def rows_from(data: dict[str, Any], full_key: str, sample_key: str) -> list[dict[str, Any]]:
    rows = data.get(full_key)
    if not isinstance(rows, list):
        rows = data.get(sample_key)
    return [row for row in rows or [] if isinstance(row, dict)]


def half_candidate(context: dict[str, Any]) -> str:
    period = str(context.get("period", "unknown")).strip().lower()
    if period in {"1", "1h", "first", "first_half", "first half"}:
        return "FIRST_HALF_CANDIDATE"
    if period in {"2", "2h", "second", "second_half", "second half"}:
        return "SECOND_HALF_CANDIDATE"
    minute = as_int(context.get("minute_bucket"))
    if minute is None:
        return "UNKNOWN_HALF"
    if 0 <= minute <= 45:
        return "FIRST_HALF_CANDIDATE"
    if 46 <= minute <= 120:
        return "SECOND_HALF_CANDIDATE"
    return "UNKNOWN_HALF"


def restart_open_play_candidate(action_family: str) -> str:
    if action_family in RESTART_FAMILIES:
        return "RESTART_OR_DEAD_BALL_CANDIDATE"
    if action_family == "UNKNOWN_OR_OTHER" or not action_family:
        return "UNKNOWN_RESTART_OPEN_PLAY"
    return "OPEN_PLAY_CANDIDATE"


def source_role(source_file: str) -> str:
    name = source_file.lower()
    if "goalkeeper" in name or "gk" in name:
        return "GOALKEEPER_SURFACE_CANDIDATE"
    if "player" in name:
        return "PLAYER_SURFACE_CANDIDATE"
    if "team" in name:
        return "TEAM_SURFACE_CANDIDATE"
    if "canonical_event" in name:
        return "CANONICAL_EVENT_LITE_SURFACE_CANDIDATE"
    return "UNKNOWN_SOURCE_ROLE"


def window_for_context(context: dict[str, Any], windows: list[dict[str, Any]]) -> tuple[str, str]:
    row_index = as_int(context.get("source_row_index"))
    minute = as_int(context.get("minute_bucket"))
    for window in windows:
        axis = str(window.get("window_axis", "UNKNOWN_WINDOW_AXIS"))
        if axis == "event_index" and row_index is not None:
            start = as_int(window.get("start_index"))
            end = as_int(window.get("end_index"))
            if start is not None and end is not None and start <= row_index < end:
                return str(window.get("window_id", "UNKNOWN_WINDOW")), axis
        if axis == "minute" and minute is not None:
            start = as_int(window.get("start_minute"))
            end = as_int(window.get("end_minute"))
            if start is not None and end is not None and start <= minute < end:
                return str(window.get("window_id", "UNKNOWN_WINDOW")), axis
    return "UNKNOWN_WINDOW", "UNKNOWN_WINDOW_AXIS"


def build_slice(context: dict[str, Any], windows: list[dict[str, Any]], idx: int) -> dict[str, Any]:
    action_family = str(context.get("action_family", "UNKNOWN_OR_OTHER"))
    source_file = str(context.get("source_file", "unknown"))
    window_id, window_axis = window_for_context(context, windows)
    return {
        "slice_id": f"slice_{idx:06d}",
        "context_id": context.get("context_id"),
        "source_file": source_file,
        "source_format": str(context.get("source_format", "unknown")),
        "source_row_index": context.get("source_row_index"),
        "source_role": source_role(source_file),
        "team_label": str(context.get("team_label", "unknown")),
        "action_family": action_family,
        "previous_action_family": str(context.get("previous_action_family", "UNKNOWN_PREVIOUS_ACTION")),
        "next_action_family": str(context.get("next_action_family", "UNKNOWN_NEXT_ACTION")),
        "zone_candidate": str(context.get("zone_candidate", "UNKNOWN_ZONE")),
        "channel_candidate": str(context.get("channel_candidate", "UNKNOWN_CHANNEL")),
        "window_id": window_id,
        "window_axis": window_axis,
        "half_candidate": half_candidate(context),
        "score_state_candidate": "UNKNOWN_SCORE_STATE",
        "card_state_candidate": "UNKNOWN_CARD_STATE",
        "restart_open_play_candidate": restart_open_play_candidate(action_family),
        "claim_level": "CONTEXT_SLICE_CANDIDATE_ONLY",
        "claim_allowed": False,
    }


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row.get(key, "unknown"))] += 1
    return dict(sorted(counts.items()))


def summarize(slices: list[dict[str, Any]]) -> dict[str, Any]:
    keys = [
        "team_label", "action_family", "half_candidate", "score_state_candidate",
        "card_state_candidate", "restart_open_play_candidate", "zone_candidate",
        "channel_candidate", "window_axis", "source_role", "claim_level",
    ]
    return {f"{key}_counts": count_by(slices, key) for key in keys}


def build_report(input_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    input_root = Path(input_dir).expanduser().resolve(strict=False)
    missing = [name for name in REQUIRED_INPUTS if not (input_root / name).exists()]
    boundary = claim_boundary()
    if missing:
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "decision": "FAIL_CLOSED_MISSING_REQUIRED_INPUTS",
            "claim_safety": CLAIM_SAFETY,
            "input_dir": str(input_root),
            "missing_required_inputs": missing,
            "blockers": ["missing_required_inputs"],
            "input_context_count": 0,
            "event_window_count": 0,
            "context_slice_count": 0,
            "context_slices_sample": [],
            "slice_summary": {},
            "claim_boundary": boundary,
            **boundary,
        }

    context_data = read_json(input_root / MIN_CONTEXT_JSON)
    window_data = read_json(input_root / EVENT_WINDOWS_JSON)
    contexts = rows_from(context_data, "context_candidates", "context_candidates_sample")
    windows = rows_from(window_data, "event_windows", "event_windows_sample")
    slices = [build_slice(context, windows, idx) for idx, context in enumerate(contexts)]
    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED",
        "decision": "CONTEXT_SLICES_CANDIDATE_ONLY",
        "claim_safety": CLAIM_SAFETY,
        "input_dir": str(input_root),
        "input_context_count": int(context_data.get("context_candidate_count", len(contexts)) or len(contexts)),
        "context_slice_count": len(slices),
        "event_window_count": int(window_data.get("event_window_count", len(windows)) or len(windows)),
        "context_slices_sample": slices[:200],
        "slice_summary": summarize(slices),
        "missing_required_inputs": [],
        "blockers": [
            "production_binding_blocked",
            "canonical_event_count_unknown",
            "score_state_candidate_unknown_without_goal_timeline",
            "card_state_candidate_unknown_without_card_timeline",
            "phase_possession_sequence_truth_blocked",
        ],
        "claim_boundary": boundary,
        **boundary,
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA MATCH CONTEXT SLICER LITE V1",
        "===================================",
        f"status={report.get('status')}",
        f"decision={report.get('decision')}",
        f"claim_safety={report.get('claim_safety')}",
        f"input_context_count={report.get('input_context_count')}",
        f"context_slice_count={report.get('context_slice_count')}",
        f"event_window_count={report.get('event_window_count')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        f"event_count_claim_allowed={report.get('event_count_claim_allowed')}",
        f"production_binding_allowed={report.get('production_binding_allowed')}",
        f"phase_truth={report.get('phase_truth')}",
        f"possession_truth={report.get('possession_truth')}",
        f"sequence_truth={report.get('sequence_truth')}",
        "",
        "[missing_required_inputs]",
        json.dumps(report.get("missing_required_inputs", []), ensure_ascii=False, sort_keys=True),
        "",
        "[blockers]",
        json.dumps(report.get("blockers", []), ensure_ascii=False, sort_keys=True),
        "",
        "[slice_summary]",
        json.dumps(report.get("slice_summary", {}), ensure_ascii=False, sort_keys=True),
        "",
        "[sample]",
    ]
    for item in report.get("context_slices_sample", [])[:25]:
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
