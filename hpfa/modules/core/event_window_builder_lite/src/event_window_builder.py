from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

MODULE_ID = "event_window_builder_lite_v1"
CLAIM_SAFETY = "EVENT_WINDOW_CANDIDATE_ONLY"
OUTPUT_JSON = "event_window_builder_lite_v1.json"
OUTPUT_TXT = "event_window_builder_lite_v1.txt"
MIN_CONTEXT_JSON = "minimum_viable_context_lite_v1.json"
TERMINAL_FAMILIES = {"SHOT"}
LOSS_RECOVERY_FAMILIES = {"BALL_LOSS", "RECOVERY"}
RESTART_FAMILIES = {"RESTART", "DEAD_BALL"}
DEFAULT_INDEX_WINDOW_ROWS = 100
VISIBLE_TIME_ORDER_SCOPE = "VISIBLE_MINUTE_BUCKET_ONLY"
PROVENANCE_ORDER_SCOPE = "PROVENANCE_ORDER_ONLY"
ORDERING_AUTHORITY = "PARTIAL_ORDER_ONLY"
MAX_FOOTBALL_MINUTE_CANDIDATE = 180


def repo_root_from_file():
    return Path(__file__).resolve().parents[5]


def ensure_module_path(path):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def spine_runner_module(root):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    ensure_module_path(src)
    import spine_runner
    return spine_runner


def minimum_context_module(root):
    src = root / "hpfa" / "modules" / "core" / "minimum_viable_context_lite" / "src"
    ensure_module_path(src)
    import minimum_viable_context
    return minimum_viable_context


def _safe_int(value):
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return None


def _context_time_status(row):
    return str(row.get("time_admission_status") or row.get("time_field_admission_status") or "MISSING")


def context_minute(row):
    if _context_time_status(row) != "ADMITTED":
        return None
    value = row.get("football_minute_candidate")
    if value in (None, "", "unknown"):
        value = row.get("minute_bucket")
    minute = _safe_int(value)
    return minute if minute is not None and 0 <= minute <= MAX_FOOTBALL_MINUTE_CANDIDATE else None


def minute_bearing_count(contexts):
    return sum(1 for row in contexts if context_minute(row) is not None)


def rebuild_full_context(raw_root, repo_root):
    mvc = minimum_context_module(repo_root)
    rows = mvc.discover_rows(raw_root)
    return list(mvc.build_context_candidates(rows))


def _has_current_time_semantics(contexts):
    return bool(contexts) and all("time_admission_status" in row or "time_field_admission_status" in row for row in contexts)


def read_minimum_context_report(input_dir, root=None, raw_input_dir=None):
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    input_root = Path(input_dir).expanduser().resolve(strict=False)
    raw_root = Path(raw_input_dir).expanduser().resolve(strict=False) if raw_input_dir is not None else input_root
    path = input_root / MIN_CONTEXT_JSON
    if not path.exists():
        contexts = rebuild_full_context(raw_root, repo_root)
        return {"contexts": contexts, "context_input_scope": "rebuilt_full_context", "is_truncated_sample": False, "complete_context_available": True, "context_candidate_count_reported": len(contexts), "context_candidates_loaded": len(contexts)}
    data = json.loads(path.read_text(encoding="utf-8"))
    full = data.get("context_candidates")
    if isinstance(full, list):
        if _has_current_time_semantics(full):
            return {"contexts": full, "context_input_scope": "full_context", "is_truncated_sample": False, "complete_context_available": True, "context_candidate_count_reported": len(full), "context_candidates_loaded": len(full)}
        rebuilt = rebuild_full_context(raw_root, repo_root)
        if rebuilt:
            return {"contexts": rebuilt, "context_input_scope": "rebuilt_full_context", "is_truncated_sample": False, "complete_context_available": True, "context_candidate_count_reported": len(rebuilt), "context_candidates_loaded": len(rebuilt)}
        return {"contexts": full, "context_input_scope": "legacy_context_review_only", "is_truncated_sample": False, "complete_context_available": True, "context_candidate_count_reported": len(full), "context_candidates_loaded": len(full)}
    sample = list(data.get("context_candidates_sample", []))
    total = int(data.get("context_candidate_count", len(sample)) or 0)
    truncated = total > len(sample)
    if truncated or not _has_current_time_semantics(sample):
        rebuilt = rebuild_full_context(raw_root, repo_root)
        if rebuilt:
            return {"contexts": rebuilt, "context_input_scope": "rebuilt_full_context", "is_truncated_sample": False, "complete_context_available": True, "context_candidate_count_reported": len(rebuilt), "context_candidates_loaded": len(rebuilt)}
    return {"contexts": sample, "context_input_scope": "sample_only", "is_truncated_sample": truncated, "complete_context_available": not truncated, "context_candidate_count_reported": total, "context_candidates_loaded": len(sample)}


def read_minimum_context(input_dir, root=None, raw_input_dir=None):
    return list(read_minimum_context_report(input_dir, root=root, raw_input_dir=raw_input_dir).get("contexts", []))


def with_context_ordinals(contexts):
    out = []
    for ordinal, row in enumerate(contexts):
        item = dict(row)
        item["context_ordinal"] = ordinal
        out.append(item)
    return out


def count_values(rows, key):
    counts = defaultdict(int)
    for row in rows:
        counts[str(row.get(key, "unknown"))] += 1
    return dict(sorted(counts.items()))


def collect_preserved_unmapped(rows):
    keys = set()
    for row in rows:
        preserved = row.get("_preserved_unmapped")
        if isinstance(preserved, dict):
            keys.update(str(key) for key in preserved)
    return sorted(keys)


def confidence_for_count(count):
    return "high" if count >= 25 else "medium" if count >= 8 else "low"


def time_axis_status(contexts):
    bearing = minute_bearing_count(contexts)
    if not contexts or bearing == 0:
        return "MISSING"
    return "AVAILABLE" if bearing == len(contexts) else "PARTIAL"


def ordering_status(contexts):
    bearing = minute_bearing_count(contexts)
    if bearing == 0:
        return "ORDER_INDETERMINATE"
    return "VISIBLE_TIME_AVAILABLE" if bearing == len(contexts) else "REVIEW_REQUIRED"


def time_admission_status(contexts):
    if not contexts:
        return "MISSING"
    statuses = [_context_time_status(row) for row in contexts]
    minutes = [context_minute(row) for row in contexts]
    if all(status == "ADMITTED" for status in statuses) and all(minute is not None for minute in minutes):
        return "ADMITTED"
    if all(status == "MISSING" for status in statuses):
        return "MISSING"
    return "REVIEW_REQUIRED"


def temporal_gap_flags(contexts, gap_threshold_mins=15):
    by_period = defaultdict(set)
    for row in contexts:
        minute = context_minute(row)
        if minute is not None:
            by_period[str(row.get("period", "UNKNOWN"))].add(minute)
    flags = []
    for period, minutes in sorted(by_period.items()):
        ordered = sorted(minutes)
        for previous, current in zip(ordered, ordered[1:]):
            gap = current - previous
            if gap > gap_threshold_mins:
                flags.append({"period": period, "from_minute": previous, "to_minute": current, "gap_mins": gap, "evidence_scope": "VISIBLE_MINUTE_BUCKET_COVERAGE_ONLY", "sequence_continuity_truth": False, "admission_blocker": False})
    return flags


def duplicate_time_flags(contexts):
    return []


def same_time_multiplicity_summary(contexts):
    seen = defaultdict(int)
    for row in contexts:
        minute = context_minute(row)
        if minute is not None:
            seen[(str(row.get("period", "UNKNOWN")), minute)] += 1
    buckets = [{"period": period, "minute": minute, "surface_row_count": count, "state": "SAME_TIME_UNORDERED"} for (period, minute), count in sorted(seen.items()) if count > 1]
    return {"same_time_unordered_bucket_count": len(buckets), "max_surface_rows_in_same_time_bucket": max((bucket["surface_row_count"] for bucket in buckets), default=0), "same_time_unordered_buckets_sample": buckets[:200], "same_timestamp_internal_ordering_allowed": False, "minute_equality_is_duplicate_event_evidence": False, "duplicate_event_identity_requires_sha_or_reflection_lineage": True}


def tempo_regime(density):
    if density is None:
        return "UNKNOWN"
    return "HIGH" if density >= 5 else "MID" if density >= 2 else "LOW"


def sequence_readiness(rows, ordered=False, temporal_admission=False):
    teams = {str(row.get("team_label", row.get("team", "unknown"))).lower() for row in rows}
    teams.discard("unknown")
    families = set(count_values(rows, "action_family"))
    return {"has_ordered_context": False, "has_visible_time_context": bool(temporal_admission), "has_team_labels": bool(teams), "has_restart_signal": bool(families & RESTART_FAMILIES), "has_terminal_signal": bool(families & TERMINAL_FAMILIES), "ready_for_sequence_candidate": False, "sequence_truth": False, "ordering_truth_delegated_to_current_partial_order_spine": True}


def pattern_support_surface(rows):
    families = set(count_values(rows, "action_family"))
    return {"action_family_counts": count_values(rows, "action_family"), "zone_counts": count_values(rows, "zone_candidate"), "channel_counts": count_values(rows, "channel_candidate"), "terminal_action_surface_present": bool(families & TERMINAL_FAMILIES), "restart_surface_present": bool(families & RESTART_FAMILIES), "loss_recovery_surface_present": bool(families & LOSS_RECOVERY_FAMILIES), "pattern_truth": False}


def window_from_rows(window_id, rows, axis, start_value, end_value, ordered=False):
    action_counts = count_values(rows, "action_family")
    families = set(action_counts)
    temporal = axis == "minute"
    density = len(rows) / max(1, end_value - start_value)
    item = {"window_id": window_id, "window_axis": axis, "window_assignment_basis": "visible_minute_bucket" if temporal else "context_ordinal_provenance", "surface_row_count": len(rows), "action_family_counts": action_counts, "team_label_counts": count_values(rows, "team_label"), "zone_counts": count_values(rows, "zone_candidate"), "channel_counts": count_values(rows, "channel_candidate"), "terminal_action_surface_present": bool(families & TERMINAL_FAMILIES), "loss_recovery_surface_present": bool(families & LOSS_RECOVERY_FAMILIES), "restart_surface_present": bool(families & RESTART_FAMILIES), "window_confidence": confidence_for_count(len(rows)), "temporal_admission": temporal, "time_semantic_admission": temporal, "provenance_only": not temporal, "ordering_evidence_scope": VISIBLE_TIME_ORDER_SCOPE if temporal else PROVENANCE_ORDER_SCOPE, "ordering_authority": ORDERING_AUTHORITY, "same_timestamp_internal_ordering_allowed": False, "source_row_order_is_temporal_truth": False, "time_window_truth": False, "claim_allowed": False, "canonical_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "context_density": density, "density_delta_candidate": None, "events_per_min_candidate": density if temporal else None, "volatility_candidate": None, "tempo_regime_candidate": tempo_regime(density) if temporal else "UNKNOWN", "sequence_readiness": sequence_readiness(rows, ordered=False, temporal_admission=temporal), "pattern_support_surface": pattern_support_surface(rows), "claim_boundary": "event_window_candidate_only"}
    if temporal:
        item.update({"start_minute": start_value, "end_minute": end_value})
    else:
        item.update({"start_context_ordinal": start_value, "end_context_ordinal": end_value})
    return item


def build_windows_from_context(contexts, window_size_mins=5, hop_mins=5, index_window_rows=DEFAULT_INDEX_WINDOW_ROWS):
    prepared = with_context_ordinals(contexts)
    if time_admission_status(prepared) == "ADMITTED":
        numeric = [context_minute(row) for row in prepared if context_minute(row) is not None]
        if not numeric:
            return []
        current = (min(numeric) // hop_mins) * hop_mins
        stop = max(numeric)
        windows = []
        idx = 0
        while current <= stop:
            rows = [row for row in prepared if context_minute(row) is not None and current <= context_minute(row) < current + window_size_mins]
            if rows:
                windows.append(window_from_rows(f"win_{idx:04d}", rows, "minute", current, current + window_size_mins))
                idx += 1
            current += hop_mins
        return windows
    windows = []
    for idx, start in enumerate(range(0, len(prepared), max(1, index_window_rows))):
        rows = prepared[start:start + index_window_rows]
        if rows:
            windows.append(window_from_rows(f"win_{idx:04d}", rows, "context_ordinal", start, start + len(rows)))
    return windows


def summarize_windows(windows):
    axis = defaultdict(int)
    confidence = defaultdict(int)
    for window in windows:
        axis[str(window.get("window_axis", "unknown"))] += 1
        confidence[str(window.get("window_confidence", "unknown"))] += 1
    return {"window_axis_counts": dict(sorted(axis.items())), "window_confidence_counts": dict(sorted(confidence.items()))}


def window_integrity_summary(windows, context_complete, time_admitted):
    minute = sum(1 for window in windows if window.get("window_axis") == "minute" and window.get("temporal_admission") is True)
    provenance = sum(1 for window in windows if window.get("provenance_only") is True)
    return {"minute_temporal_window_count": minute, "provenance_only_window_count": provenance, "fail_closed_window_count": 0, "downstream_ready": bool(context_complete and time_admitted and minute > 0), "source_row_order_is_temporal_truth": False, "same_timestamp_internal_ordering_allowed": False}


def build_report(input_dir, root=None, raw_input_dir=None, window_size_mins=5, hop_mins=5, index_window_rows=DEFAULT_INDEX_WINDOW_ROWS):
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    loaded = read_minimum_context_report(input_dir, root=repo_root, raw_input_dir=raw_input_dir)
    contexts = list(loaded.get("contexts", []))
    complete = bool(loaded.get("complete_context_available")) and not bool(loaded.get("is_truncated_sample"))
    admission = time_admission_status(contexts)
    axis_status = time_axis_status(contexts)
    order = ordering_status(contexts)
    windows = build_windows_from_context(contexts, window_size_mins=window_size_mins, hop_mins=hop_mins, index_window_rows=index_window_rows) if complete else []
    multiplicity = same_time_multiplicity_summary(contexts)
    gaps = temporal_gap_flags(contexts)
    integrity = window_integrity_summary(windows, complete, admission == "ADMITTED")
    status = "PASS" if integrity["downstream_ready"] else "REVIEW_REQUIRED"
    summary = summarize_windows(windows)
    return {"module_id": MODULE_ID, "status": status, "decision": "EVENT_WINDOW_CANDIDATES_ONLY", "claim_safety": CLAIM_SAFETY, "input_context_count": len(contexts), "minute_bearing_context_count": minute_bearing_count(contexts), "event_window_count": len(windows), "event_windows": windows, "event_windows_sample": windows[:200], "window_summary": summary, "context_input_scope": loaded.get("context_input_scope"), "is_truncated_sample": bool(loaded.get("is_truncated_sample")), "complete_context_available": complete, "time_axis_status": axis_status, "time_admission_status": admission, "time_field_admission_status": admission, "ordering_status": order, "ordering_authority": ORDERING_AUTHORITY, "minute_window_enabled": integrity["minute_temporal_window_count"] > 0, "index_window_enabled": integrity["provenance_only_window_count"] > 0, "index_window_is_temporal_context": False, "same_time_multiplicity_summary": multiplicity, "same_time_unordered_bucket_count": multiplicity["same_time_unordered_bucket_count"], "duplicate_time_flags": [], "temporal_gap_flags": gaps, "temporal_gap_flags_are_admission_blockers": False, "window_integrity_summary": integrity, "preserved_unmapped_fields": collect_preserved_unmapped(contexts), "source_row_order_is_temporal_truth": False, "same_timestamp_internal_ordering_allowed": False, "canonical_action_id_present": False, "canonical_action_identity_status": "UNKNOWN", "canonical_action_identity_basis": "NO_ADMITTED_STABLE_ACTION_ID", "canonical_event_count": "UNKNOWN", "deduplicated_event_count": "UNKNOWN", "true_action_count": "UNKNOWN", "phase_truth": False, "possession_truth": False, "sequence_truth": False, "rhythm_truth": False, "time_window_truth": False, "momentum_truth": False, "tactical_truth": False, "dominance_truth": False, "claim_allowed": False, "production_release": False, "repo_root": str(repo_root), "input_dir": str(Path(input_dir).expanduser().resolve(strict=False))}


def render_txt(report):
    keys = ["status", "input_context_count", "minute_bearing_context_count", "event_window_count", "time_axis_status", "time_admission_status", "ordering_status"]
    return "\n".join(["HPFA EVENT WINDOW BUILDER LITE V1", "================================="] + [f"{key}={report.get(key)}" for key in keys] + ["source_row_order_is_temporal_truth=false", "same_timestamp_internal_ordering_allowed=false", "canonical_action_id_present=false", "canonical_event_count=UNKNOWN", "true_action_count=UNKNOWN", "production_release=false", ""])


def write_outputs(input_dir, out_dir, root=None, raw_input_dir=None, window_size_mins=5, hop_mins=5):
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
