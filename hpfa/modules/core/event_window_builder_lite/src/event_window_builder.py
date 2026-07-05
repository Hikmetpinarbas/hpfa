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
TIME_KEYS = [
    "minute_bucket",
    "minute",
    "minutes",
    "minute_raw",
    "time",
    "timestamp",
    "timestamp_raw",
    "start",
    "end",
    "start_time",
    "end_time",
    "time_start",
    "time_end",
    "absolute_time_seconds",
    "match_time",
    "game_time",
    "match_clock",
    "period_time",
    "second",
    "seconds",
    "second_raw",
    "tc",
    "t",
]
TIME_KEY_ALIASES = {key.lower(): key for key in TIME_KEYS}
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


def get_case_insensitive(row: dict[str, Any], key: str) -> Any:
    if key in row:
        return row.get(key)
    wanted = key.lower()
    for raw_key, value in row.items():
        if str(raw_key).lower() == wanted:
            return value
    return None


def context_minute(row: dict[str, Any]) -> int | None:
    for key in TIME_KEYS:
        value = get_case_insensitive(row, key)
        minute = safe_minute_from_value(value)
        if minute is not None:
            return minute
    return None


def minute_bearing_count(contexts: list[dict[str, Any]]) -> int:
    return sum(1 for item in contexts if context_minute(item) is not None)


def attach_raw_time_fields(contexts: list[dict[str, Any]], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for ctx, raw in zip(contexts, rows):
        for raw_key, raw_value in raw.items():
            canonical = TIME_KEY_ALIASES.get(str(raw_key).lower())
            if canonical and raw_value not in (None, ""):
                ctx.setdefault(canonical, raw_value)
    return contexts


def rebuild_full_context(raw_root: Path, repo_root: Path) -> list[dict[str, Any]]:
    mvc = minimum_context_module(repo_root)
    if hasattr(mvc, "discover_rows") and hasattr(mvc, "build_context_candidates"):
        rows = mvc.discover_rows(raw_root)
        contexts = list(mvc.build_context_candidates(rows))
        return attach_raw_time_fields(contexts, rows)
    report = mvc.build_report(raw_root, root=repo_root)
    return list(report.get("context_candidates_sample", []))


def read_minimum_context_report(
    input_dir: str | Path,
    root: str | Path | None = None,
    raw_input_dir: str | Path | None = None,
) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    input_root = Path(input_dir).expanduser().resolve(strict=False)
    raw_root = Path(raw_input_dir).expanduser().resolve(strict=False) if raw_input_dir is not None else input_root
    context_path = input_root / MIN_CONTEXT_JSON
    if not context_path.exists():
        contexts = rebuild_full_context(raw_root, repo_root)
        return {
            "contexts": contexts,
            "context_input_scope": "rebuilt_full_context",
            "is_truncated_sample": False,
            "complete_context_available": True,
            "context_candidate_count_reported": len(contexts),
            "context_candidates_loaded": len(contexts),
        }

    data = json.loads(context_path.read_text(encoding="utf-8"))
    full_contexts = data.get("context_candidates")
    if isinstance(full_contexts, list):
        if minute_bearing_count(full_contexts) > 0:
            return {
                "contexts": full_contexts,
                "context_input_scope": "full_context",
                "is_truncated_sample": False,
                "complete_context_available": True,
                "context_candidate_count_reported": len(full_contexts),
                "context_candidates_loaded": len(full_contexts),
            }
        rebuilt = rebuild_full_context(raw_root, repo_root)
        return {
            "contexts": rebuilt,
            "context_input_scope": "rebuilt_full_context",
            "is_truncated_sample": False,
            "complete_context_available": True,
            "context_candidate_count_reported": len(rebuilt),
            "context_candidates_loaded": len(rebuilt),
        }

    sample = list(data.get("context_candidates_sample", []))
    total_count = int(data.get("context_candidate_count", len(sample)) or 0)
    if total_count > len(sample) or minute_bearing_count(sample) == 0:
        rebuilt = rebuild_full_context(raw_root, repo_root)
        if rebuilt:
            return {
                "contexts": rebuilt,
                "context_input_scope": "rebuilt_full_context",
                "is_truncated_sample": False,
                "complete_context_available": True,
                "context_candidate_count_reported": len(rebuilt),
                "context_candidates_loaded": len(rebuilt),
            }
        return {
            "contexts": sample,
            "context_input_scope": "sample_only",
            "is_truncated_sample": total_count > len(sample),
            "complete_context_available": False,
            "context_candidate_count_reported": total_count,
            "context_candidates_loaded": len(sample),
        }
    return {
        "contexts": sample,
        "context_input_scope": "sample_only",
        "is_truncated_sample": False,
        "complete_context_available": True,
        "context_candidate_count_reported": total_count,
        "context_candidates_loaded": len(sample),
    }


def read_minimum_context(
    input_dir: str | Path,
    root: str | Path | None = None,
    raw_input_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    return list(read_minimum_context_report(input_dir, root=root, raw_input_dir=raw_input_dir).get("contexts", []))


def with_context_ordinals(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for ordinal, row in enumerate(contexts):
        item = dict(row)
        item["context_ordinal"] = ordinal
        prepared.append(item)
    return prepared


def count_values(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        value = str(row.get(key, "unknown"))
        counts[value] += 1
    return dict(sorted(counts.items()))


def collect_preserved_unmapped(rows: list[dict[str, Any]]) -> list[str]:
    keys: set[str] = set()
    for row in rows:
        preserved = row.get("_preserved_unmapped")
        if isinstance(preserved, dict):
            keys.update(str(key) for key in preserved.keys())
    return sorted(keys)


def confidence_for_count(count: int) -> str:
    if count >= 25:
        return "high"
    if count >= 8:
        return "medium"
    return "low"


def time_axis_status(contexts: list[dict[str, Any]]) -> str:
    bearing = minute_bearing_count(contexts)
    if not contexts or bearing == 0:
        return "MISSING"
    if bearing == len(contexts):
        return "AVAILABLE"
    return "PARTIAL"


def ordering_status(contexts: list[dict[str, Any]]) -> str:
    last: tuple[str, int] | None = None
    disorder = 0
    for row in contexts:
        minute = context_minute(row)
        if minute is None:
            continue
        period = str(row.get("period", "UNKNOWN"))
        current = (period, minute)
        if last is not None and current < last:
            disorder += 1
        last = current
    if disorder == 0:
        return "PASS"
    if disorder <= 2:
        return "REVIEW_REQUIRED"
    return "FAIL_CLOSED"


def temporal_gap_flags(contexts: list[dict[str, Any]], gap_threshold_mins: int = 15) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    minute_rows = [(idx, context_minute(row)) for idx, row in enumerate(contexts)]
    minute_rows = [(idx, minute) for idx, minute in minute_rows if minute is not None]
    for (prev_idx, prev_minute), (idx, minute) in zip(minute_rows, minute_rows[1:]):
        if minute - prev_minute > gap_threshold_mins:
            flags.append({"from_context_ordinal": prev_idx, "to_context_ordinal": idx, "gap_mins": minute - prev_minute})
    return flags


def duplicate_time_flags(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[tuple[str, int], int] = defaultdict(int)
    for row in contexts:
        minute = context_minute(row)
        if minute is None:
            continue
        seen[(str(row.get("period", "UNKNOWN")), minute)] += 1
    return [
        {"period": period, "minute": minute, "duplicate_count": count}
        for (period, minute), count in sorted(seen.items())
        if count > 1
    ]


def tempo_regime(density: float | None) -> str:
    if density is None:
        return "UNKNOWN"
    if density >= 5:
        return "HIGH"
    if density >= 2:
        return "MID"
    return "LOW"


def sequence_readiness(rows: list[dict[str, Any]], ordered: bool) -> dict[str, Any]:
    teams = {str(row.get("team_label", row.get("team", "unknown"))).lower() for row in rows}
    teams.discard("unknown")
    families = set(count_values(rows, "action_family"))
    return {
        "has_ordered_context": ordered,
        "has_team_labels": bool(teams),
        "has_restart_signal": bool(families & RESTART_FAMILIES),
        "has_terminal_signal": bool(families & TERMINAL_FAMILIES),
        "ready_for_sequence_candidate": bool(ordered and teams and (families & (RESTART_FAMILIES | TERMINAL_FAMILIES | LOSS_RECOVERY_FAMILIES))),
        "sequence_truth": False,
    }


def pattern_support_surface(rows: list[dict[str, Any]]) -> dict[str, Any]:
    families = set(count_values(rows, "action_family"))
    return {
        "action_family_counts": count_values(rows, "action_family"),
        "zone_counts": count_values(rows, "zone_candidate"),
        "channel_counts": count_values(rows, "channel_candidate"),
        "terminal_action_surface_present": bool(families & TERMINAL_FAMILIES),
        "restart_surface_present": bool(families & RESTART_FAMILIES),
        "loss_recovery_surface_present": bool(families & LOSS_RECOVERY_FAMILIES),
        "pattern_truth": False,
    }


def window_from_rows(window_id: str, rows: list[dict[str, Any]], axis: str, start_value: int, end_value: int, ordered: bool = True) -> dict[str, Any]:
    action_counts = count_values(rows, "action_family")
    families = set(action_counts)
    density = len(rows) / max(1, end_value - start_value)
    base = {
        "window_id": window_id,
        "window_axis": axis,
        "window_assignment_basis": "context_ordinal" if axis == "context_ordinal" else axis,
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
        "canonical_event_count": "UNKNOWN",
        "context_density": density,
        "density_delta_candidate": None,
        "events_per_min_candidate": density if axis == "minute" else None,
        "volatility_candidate": None,
        "tempo_regime_candidate": tempo_regime(density if axis == "minute" else None),
        "sequence_readiness": sequence_readiness(rows, ordered=ordered),
        "pattern_support_surface": pattern_support_surface(rows),
        "preserved_unmapped": collect_preserved_unmapped(rows),
        "claim_boundary": "event_window_candidate_only",
    }
    if axis == "minute":
        base["start_minute"] = start_value
        base["end_minute"] = end_value
    else:
        base["start_context_ordinal"] = start_value
        base["end_context_ordinal"] = end_value
        base["start_index"] = start_value
        base["end_index"] = end_value
    return base


def attach_density_deltas(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous_density: float | None = None
    for window in windows:
        density = float(window.get("context_density", 0.0))
        if previous_density is not None:
            delta = density - previous_density
            window["density_delta_candidate"] = delta
            window["volatility_candidate"] = abs(delta)
        previous_density = density
    return windows


def build_index_windows(contexts: list[dict[str, Any]], index_window_rows: int = DEFAULT_INDEX_WINDOW_ROWS, ordered: bool = True) -> list[dict[str, Any]]:
    contexts = with_context_ordinals(contexts)
    windows: list[dict[str, Any]] = []
    for start in range(0, len(contexts), index_window_rows):
        end = min(start + index_window_rows, len(contexts))
        rows = contexts[start:end]
        if not rows:
            continue
        windows.append(window_from_rows(f"idxwin_{len(windows):04d}", rows, "context_ordinal", start, end, ordered=ordered))
    return attach_density_deltas(windows)


def build_minute_windows(
    contexts: list[dict[str, Any]],
    window_size_mins: int = 5,
    hop_mins: int = 5,
    ordered: bool = True,
) -> list[dict[str, Any]]:
    minute_rows: list[tuple[int, dict[str, Any]]] = []
    for row in with_context_ordinals(contexts):
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
            windows.append(window_from_rows(f"win_{len(windows):04d}", rows, "minute", start, end, ordered=ordered))
        start += hop_mins
    return attach_density_deltas(windows)


def build_windows_from_context(
    contexts: list[dict[str, Any]],
    window_size_mins: int = 5,
    hop_mins: int = 5,
) -> list[dict[str, Any]]:
    order_status = ordering_status(contexts)
    ordered = order_status != "FAIL_CLOSED"
    if time_axis_status(contexts) != "MISSING":
        minute_windows = build_minute_windows(contexts, window_size_mins=window_size_mins, hop_mins=hop_mins, ordered=ordered)
        if minute_windows:
            return minute_windows
    return build_index_windows(contexts, ordered=ordered)


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
    raw_input_dir: str | Path | None = None,
    window_size_mins: int = 5,
    hop_mins: int = 5,
) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    context_payload = read_minimum_context_report(input_dir, root=repo_root, raw_input_dir=raw_input_dir)
    contexts = list(context_payload.get("contexts", []))
    minute_context_count = minute_bearing_count(contexts)
    t_axis = time_axis_status(contexts)
    order_status = ordering_status(contexts)
    gap_flags = temporal_gap_flags(contexts)
    dup_flags = duplicate_time_flags(contexts)
    truncated = bool(context_payload.get("is_truncated_sample")) and not bool(context_payload.get("complete_context_available"))
    windows = [] if truncated else build_windows_from_context(contexts, window_size_mins=window_size_mins, hop_mins=hop_mins)
    raw_root = str(Path(raw_input_dir).expanduser().resolve(strict=False)) if raw_input_dir is not None else str(Path(input_dir).expanduser().resolve(strict=False))
    downstream_ready = bool(windows and t_axis != "MISSING" and order_status != "FAIL_CLOSED")
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
        "window_integrity_summary": {
            "surface_row_count": len(contexts),
            "window_count": len(windows),
            "valid_window_count": len(windows),
            "review_required_window_count": 1 if gap_flags or dup_flags or order_status == "REVIEW_REQUIRED" or truncated else 0,
            "fail_closed_window_count": 1 if t_axis == "MISSING" or order_status == "FAIL_CLOSED" else 0,
            "time_field_status": t_axis,
            "ordering_status": order_status,
            "continuity_status": "REVIEW_REQUIRED" if gap_flags else "PASS",
            "downstream_ready": downstream_ready,
        },
        "context_input_scope": context_payload.get("context_input_scope"),
        "is_truncated_sample": bool(context_payload.get("is_truncated_sample")),
        "complete_context_available": bool(context_payload.get("complete_context_available")),
        "context_candidate_count_reported": int(context_payload.get("context_candidate_count_reported", len(contexts)) or 0),
        "context_candidates_loaded": int(context_payload.get("context_candidates_loaded", len(contexts)) or 0),
        "time_axis_status": t_axis,
        "minute_window_enabled": bool(t_axis != "MISSING" and not truncated),
        "index_window_enabled": True,
        "ordering_status": order_status,
        "temporal_gap_flags": gap_flags,
        "duplicate_time_flags": dup_flags,
        "preserved_unmapped": collect_preserved_unmapped(contexts),
        "input_dir": str(Path(input_dir).expanduser().resolve(strict=False)),
        "raw_input_dir": raw_root,
        "canonical_event_count": "UNKNOWN",
        "deduplicated_event_count": "UNKNOWN",
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "rhythm_truth": False,
        "time_window_truth": False,
        "momentum_truth": False,
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
        f"context_input_scope={report.get('context_input_scope')}",
        f"time_axis_status={report.get('time_axis_status')}",
        f"ordering_status={report.get('ordering_status')}",
        f"raw_input_dir={report.get('raw_input_dir')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        f"phase_truth={report.get('phase_truth')}",
        f"possession_truth={report.get('possession_truth')}",
        f"sequence_truth={report.get('sequence_truth')}",
        f"rhythm_truth={report.get('rhythm_truth')}",
        f"time_window_truth={report.get('time_window_truth')}",
        "",
        "[window_integrity_summary]",
        json.dumps(report.get("window_integrity_summary", {}), ensure_ascii=False, sort_keys=True),
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
    raw_input_dir: str | Path | None = None,
    window_size_mins: int = 5,
    hop_mins: int = 5,
) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine = spine_runner_module(repo_root)
    output_root = spine.validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    report = build_report(input_dir, root=repo_root, raw_input_dir=raw_input_dir, window_size_mins=window_size_mins, hop_mins=hop_mins)
    json_out = output_root / OUTPUT_JSON
    txt_out = output_root / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
