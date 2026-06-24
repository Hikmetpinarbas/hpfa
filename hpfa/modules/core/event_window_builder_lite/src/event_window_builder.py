from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "event_window_builder_lite_v1"
CLAIM_SAFETY = "EVENT_WINDOW_CANDIDATE_ONLY"
OUTPUT_JSON = "event_window_builder_lite_v1.json"
OUTPUT_TXT = "event_window_builder_lite_v1.txt"
MIN_CONTEXT_JSON = "minimum_viable_context_lite_v1.json"
TERMINAL_FAMILIES = {"SHOT"}
LOSS_RECOVERY_FAMILIES = {"BALL_LOSS", "RECOVERY"}
RESTART_FAMILIES = {"RESTART", "DEAD_BALL"}
TIME_KEYS = ["minute_bucket", "minute", "time", "timestamp", "start", "end", "absolute_time_seconds", "match_time"]
DEFAULT_INDEX_WINDOW_ROWS = 100


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


def minimum_context_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "minimum_viable_context_lite" / "src"
    ensure_module_path(src)
    import minimum_viable_context  # type: ignore
    return minimum_viable_context


def safe_int(value: Any) -> int | None:
    if value in (None, "", "unknown"):
        return None
    try:
        return int(float(str(value)))
    except ValueError:
        return None


def parse_clock_minute(value: str) -> int | None:
    text = value.strip()
    if not text or text.lower() == "unknown":
        return None
    if ":" not in text:
        return None
    parts = text.split(":")
    try:
        nums = [float(part.replace(",", ".")) for part in parts]
    except ValueError:
        return None
    if len(nums) == 2:
        minutes, seconds = nums
        return int(minutes + seconds / 60.0)
    if len(nums) == 3:
        hours, minutes, seconds = nums
        return int(hours * 60.0 + minutes + seconds / 60.0)
    return None


def safe_minute_from_value(value: Any) -> int | None:
    if value in (None, "", "unknown"):
        return None
    text = str(value).strip()
    clock = parse_clock_minute(text)
    if clock is not None:
        return clock
    try:
        number = float(text.replace(",", "."))
    except ValueError:
        return None
    if number > 1000:
        return int(number / 60.0)
    return int(number)


def context_minute(row: dict[str, Any]) -> int | None:
    for key in TIME_KEYS:
        value = row.get(key)
        minute = safe_minute_from_value(value)
        if minute is not None:
            return minute
    return None


def minute_bearing_count(contexts: list[dict[str, Any]]) -> int:
    return sum(1 for item in contexts if context_minute(item) is not None)


def rebuild_full_context(input_root: Path, repo_root: Path) -> list[dict[str, Any]]:
    mvc = minimum_context_module(repo_root)
    if hasattr(mvc, "discover_rows") and hasattr(mvc, "build_context_candidates"):
        rows = mvc.discover_rows(input_root)
        contexts = list(mvc.build_context_candidates(rows))
        for ctx, raw in zip(contexts, rows):
            for key in TIME_KEYS:
                if key in raw and key not in ctx:
                    ctx[key] = raw.get(key)
        return contexts
    report = mvc.build_report(input_root, root=repo_root)
    return list(report.get("context_candidates_sample", []))


def read_minimum_context(input_dir: str | Path, root: str | Path | None = None) -> list[dict[str, Any]]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    input_root = Path(input_dir).expanduser().resolve(strict=False)
    context_path = input_root / MIN_CONTEXT_JSON
    if not context_path.exists():
        return rebuild_full_context(input_root, repo_root)

    data = json.loads(context_path.read_text(encoding="utf-8"))
    full_contexts = data.get("context_candidates")
    if isinstance(full_contexts, list):
        if minute_bearing_count(full_contexts) > 0:
            return full_contexts
        return rebuild_full_context(input_root, repo_root)

    sample = list(data.get("context_candidates_sample", []))
    total_count = int(data.get("context_candidate_count", len(sample)) or 0)
    if total_count > len(sample) or minute_bearing_count(sample) == 0:
        return rebuild_full_context(input_root, repo_root)
    return sample


def count_values(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        value = str(row.get(key, "unknown"))
        counts[value] += 1
    return dict(sorted(counts.items()))


def confidence_for_count(count: int) -> str:
    if count >= 25:
        return "high"
    if count >= 8:
        return "medium"
    return "low"


def window_from_rows(window_id: str, rows: list[dict[str, Any]], axis: str, start_value: int, end_value: int) -> dict[str, Any]:
    action_counts = count_values(rows, "action_family")
    families = set(action_counts)
    base = {
        "window_id": window_id,
        "window_axis": axis,
        "surface_row_count": len(rows),
        "action_family_counts": action_counts,
        "team_label_counts": count_values(rows, "team_label"),
        "zone_counts": count_values(rows, "zone_candidate"),
        "channel_counts": count_values(rows, "channel_candidate"),
        "terminal_action_surface_present": bool(families & TERMINAL_FAMILIES),
        "loss_recovery_surface_present": bool(families & LOSS_RECOVERY_FAMILIES),
        "restart_surface_present": bool(families & RESTART_FAMILIES),
        "window_confidence": confidence_for_count(len(rows)),
        "time_window_truth": False,
        "claim_allowed": False,
    }
    if axis == "minute":
        base["start_minute"] = start_value
        base["end_minute"] = end_value
        base["context_density"] = len(rows) / max(1, end_value - start_value)
    else:
        base["start_index"] = start_value
        base["end_index"] = end_value
        base["context_density"] = len(rows) / max(1, end_value - start_value)
    return base


def build_index_windows(contexts: list[dict[str, Any]], index_window_rows: int = DEFAULT_INDEX_WINDOW_ROWS) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    for start in range(0, len(contexts), index_window_rows):
        end = min(start + index_window_rows, len(contexts))
        rows = contexts[start:end]
        if not rows:
            continue
        windows.append(window_from_rows(f"idxwin_{len(windows):04d}", rows, "event_index", start, end))
    return windows


def build_minute_windows(
    contexts: list[dict[str, Any]],
    window_size_mins: int = 5,
    hop_mins: int = 5,
) -> list[dict[str, Any]]:
    minute_rows: list[tuple[int, dict[str, Any]]] = []
    for row in contexts:
        minute = context_minute(row)
        if minute is None:
            continue
        minute_rows.append((minute, row))
    if not minute_rows:
        return []
    min_minute = min(minute for minute, _ in minute_rows)
    max_minute = max(minute for minute, _ in minute_rows)
    start = (min_minute // hop_mins) * hop_mins
    windows: list[dict[str, Any]] = []
    while start <= max_minute:
        end = start + window_size_mins
        rows = [row for minute, row in minute_rows if start <= minute < end]
        if rows:
            windows.append(window_from_rows(f"win_{len(windows):04d}", rows, "minute", start, end))
        start += hop_mins
    return windows


def build_windows_from_context(
    contexts: list[dict[str, Any]],
    window_size_mins: int = 5,
    hop_mins: int = 5,
) -> list[dict[str, Any]]:
    minute_windows = build_minute_windows(contexts, window_size_mins=window_size_mins, hop_mins=hop_mins)
    if minute_windows:
        return minute_windows
    return build_index_windows(contexts)


def summarize_windows(windows: list[dict[str, Any]]) -> dict[str, Any]:
    confidence_counts: dict[str, int] = defaultdict(int)
    axis_counts: dict[str, int] = defaultdict(int)
    terminal = 0
    loss_recovery = 0
    restart = 0
    for win in windows:
        confidence_counts[str(win.get("window_confidence"))] += 1
        axis_counts[str(win.get("window_axis", "unknown"))] += 1
        terminal += int(bool(win.get("terminal_action_surface_present")))
        loss_recovery += int(bool(win.get("loss_recovery_surface_present")))
        restart += int(bool(win.get("restart_surface_present")))
    return {
        "window_confidence_counts": dict(sorted(confidence_counts.items())),
        "window_axis_counts": dict(sorted(axis_counts.items())),
        "terminal_action_window_count": terminal,
        "loss_recovery_window_count": loss_recovery,
        "restart_window_count": restart,
    }


def build_report(
    input_dir: str | Path,
    root: str | Path | None = None,
    window_size_mins: int = 5,
    hop_mins: int = 5,
) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    contexts = read_minimum_context(input_dir, root=repo_root)
    minute_context_count = minute_bearing_count(contexts)
    windows = build_windows_from_context(contexts, window_size_mins=window_size_mins, hop_mins=hop_mins)
    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED",
        "decision": "EVENT_WINDOWS_CANDIDATE_ONLY",
        "claim_safety": CLAIM_SAFETY,
        "window_size_mins": window_size_mins,
        "hop_mins": hop_mins,
        "index_window_rows": DEFAULT_INDEX_WINDOW_ROWS,
        "input_context_count": len(contexts),
        "minute_bearing_context_count": minute_context_count,
        "event_window_count": len(windows),
        "event_windows_sample": windows[:200],
        "window_summary": summarize_windows(windows),
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
        "repo_root": str(repo_root),
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA EVENT WINDOW BUILDER LITE V1",
        "==================================",
        f"status={report.get('status')}",
        f"decision={report.get('decision')}",
        f"claim_safety={report.get('claim_safety')}",
        f"input_context_count={report.get('input_context_count')}",
        f"minute_bearing_context_count={report.get('minute_bearing_context_count')}",
        f"event_window_count={report.get('event_window_count')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        f"phase_truth={report.get('phase_truth')}",
        f"possession_truth={report.get('possession_truth')}",
        f"sequence_truth={report.get('sequence_truth')}",
        f"rhythm_truth={report.get('rhythm_truth')}",
        f"time_window_truth={report.get('time_window_truth')}",
        "",
        "[window_summary]",
        json.dumps(report.get("window_summary", {}), ensure_ascii=False, sort_keys=True),
        "",
        "[sample]",
    ]
    for item in report.get("event_windows_sample", [])[:25]:
        lines.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
    lines.append("")
    return "\n".join(lines)


def write_outputs(
    input_dir: str | Path,
    out_dir: str | Path,
    root: str | Path | None = None,
    window_size_mins: int = 5,
    hop_mins: int = 5,
) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine = spine_runner_module(repo_root)
    output_root = spine.validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    report = build_report(input_dir, root=repo_root, window_size_mins=window_size_mins, hop_mins=hop_mins)
    json_out = output_root / OUTPUT_JSON
    txt_out = output_root / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
