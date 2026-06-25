from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "time_scale_router_lite_v1"
CLAIM_SAFETY = "TIME_SCALE_CANDIDATE_ONLY"
INPUT_JSON = "event_window_builder_lite_v1.json"
OUTPUT_JSON = "time_scale_router_lite_v1.json"
OUTPUT_TXT = "time_scale_router_lite_v1.txt"

MIN_USABLE_DENSITY = 5.0
MIN_USABLE_ROWS = 25
MIN_LOW_DENSITY_ROWS = 8


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


def safe_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def safe_int(value: Any) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return 0


def read_event_windows(input_dir: str | Path) -> list[dict[str, Any]]:
    path = Path(input_dir).expanduser().resolve(strict=False) / INPUT_JSON
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    windows = data.get("event_windows_sample", [])
    if isinstance(windows, list):
        return list(windows)
    return []


def route_window(window: dict[str, Any]) -> dict[str, Any]:
    axis = str(window.get("window_axis", "unknown"))
    rows = safe_int(window.get("surface_row_count"))
    density = safe_float(window.get("context_density"))
    confidence = str(window.get("window_confidence", "unknown"))

    if axis == "minute":
        if rows >= MIN_USABLE_ROWS and density >= MIN_USABLE_DENSITY:
            decision = "MINUTE_AXIS_USABLE"
            density_candidate = "HIGH_SIGNAL_DENSITY"
            reason = "minute_axis_with_sufficient_surface_density"
        elif rows >= MIN_LOW_DENSITY_ROWS:
            decision = "MINUTE_AXIS_LOW_DENSITY"
            density_candidate = "LOW_SIGNAL_DENSITY"
            reason = "minute_axis_with_low_surface_density"
        else:
            decision = "TIME_SURFACE_INSUFFICIENT"
            density_candidate = "INSUFFICIENT_SIGNAL_DENSITY"
            reason = "minute_axis_but_insufficient_surface_rows"
    elif axis == "event_index":
        decision = "EVENT_INDEX_FALLBACK_ONLY"
        density_candidate = "EVENT_INDEX_DENSITY_ONLY"
        reason = "event_index_window_without_minute_axis_truth"
    else:
        decision = "REVIEW_REQUIRED"
        density_candidate = "UNKNOWN_SIGNAL_DENSITY"
        reason = "unknown_window_axis"

    return {
        "window_id": str(window.get("window_id", "unknown")),
        "window_axis": axis,
        "surface_row_count": rows,
        "context_density": density,
        "window_confidence": confidence,
        "time_scale_candidate": decision,
        "signal_density_candidate": density_candidate,
        "routing_decision": decision,
        "routing_reason": reason,
        "terminal_action_surface_present": bool(window.get("terminal_action_surface_present")),
        "loss_recovery_surface_present": bool(window.get("loss_recovery_surface_present")),
        "restart_surface_present": bool(window.get("restart_surface_present")),
        "claim_allowed": False,
    }


def route_windows(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [route_window(window) for window in windows]


def summarize_routes(routed: list[dict[str, Any]]) -> dict[str, Any]:
    decision_counts: dict[str, int] = defaultdict(int)
    axis_counts: dict[str, int] = defaultdict(int)
    density_counts: dict[str, int] = defaultdict(int)
    terminal = 0
    loss_recovery = 0
    restart = 0
    for item in routed:
        decision_counts[str(item.get("routing_decision", "unknown"))] += 1
        axis_counts[str(item.get("window_axis", "unknown"))] += 1
        density_counts[str(item.get("signal_density_candidate", "unknown"))] += 1
        terminal += int(bool(item.get("terminal_action_surface_present")))
        loss_recovery += int(bool(item.get("loss_recovery_surface_present")))
        restart += int(bool(item.get("restart_surface_present")))
    return {
        "routing_decision_counts": dict(sorted(decision_counts.items())),
        "window_axis_counts": dict(sorted(axis_counts.items())),
        "signal_density_candidate_counts": dict(sorted(density_counts.items())),
        "terminal_action_routed_count": terminal,
        "loss_recovery_routed_count": loss_recovery,
        "restart_routed_count": restart,
    }


def build_report(input_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    windows = read_event_windows(input_dir)
    routed = route_windows(windows)
    summary = summarize_routes(routed)
    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED",
        "decision": "TIME_SCALE_CANDIDATES_ONLY",
        "claim_safety": CLAIM_SAFETY,
        "input_window_count": len(windows),
        "routed_window_count": len(routed),
        "minute_axis_window_count": summary.get("window_axis_counts", {}).get("minute", 0),
        "event_index_window_count": summary.get("window_axis_counts", {}).get("event_index", 0),
        "routed_windows_sample": routed[:200],
        "routing_summary": summary,
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
        "input_dir": str(Path(input_dir).expanduser().resolve(strict=False)),
        "repo_root": str(repo_root),
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA TIME-SCALE ROUTER LITE V1",
        "================================",
        f"status={report.get('status')}",
        f"decision={report.get('decision')}",
        f"claim_safety={report.get('claim_safety')}",
        f"input_window_count={report.get('input_window_count')}",
        f"routed_window_count={report.get('routed_window_count')}",
        f"minute_axis_window_count={report.get('minute_axis_window_count')}",
        f"event_index_window_count={report.get('event_index_window_count')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        f"phase_truth={report.get('phase_truth')}",
        f"possession_truth={report.get('possession_truth')}",
        f"sequence_truth={report.get('sequence_truth')}",
        f"rhythm_truth={report.get('rhythm_truth')}",
        f"time_window_truth={report.get('time_window_truth')}",
        "",
        "[routing_summary]",
        json.dumps(report.get("routing_summary", {}), ensure_ascii=False, sort_keys=True),
        "",
        "[sample]",
    ]
    for item in report.get("routed_windows_sample", [])[:25]:
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
