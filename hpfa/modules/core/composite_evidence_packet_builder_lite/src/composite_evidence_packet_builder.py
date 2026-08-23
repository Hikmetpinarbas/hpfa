from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "composite_evidence_packet_builder_lite_v1"
OUTPUT_JSON = "composite_evidence_packet_builder_lite_v1.json"
OUTPUT_TXT = "composite_evidence_packet_builder_lite_v1.txt"

DEFAULT_CLAIM_CEILING = "composite_candidate_only"
DEFAULT_MINIMUM_SIGNAL_COUNT = 2

DEFAULT_REPORT_CONSUMERS = [
    "multi_signal_evidence_fusion_lite",
    "composite_argument_builder_lite",
    "evidence_graph_engine_lite",
    "active_match_analyst_report_lite",
]

BLOCKED_LANGUAGE_FAMILIES = [
    "tactical_truth",
    "dominance_truth",
    "control_truth",
    "coach_intention",
    "off_ball_truth",
    "pitch_control_truth",
]

FORBIDDEN_OUTPUT_FIELDS = {
    "claim_text",
    "safe_sentence",
    "safe_sentence_candidate_tr",
    "tactical_truth",
    "dominance_truth",
    "control_truth",
    "coach_intention",
    "off_ball_truth",
    "pitch_control_truth",
}

ALLOWED_PACKET_FAMILIES = {
    "progression",
    "risk",
    "tempo",
    "restart",
    "sequence",
    "defensive",
    "goalkeeper",
    "source_integrity",
    "production_consequence",
    "weak_signal",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _validate_output_root(out_dir: str | Path) -> Path:
    spine_src = _repo_root() / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    if str(spine_src) not in sys.path:
        sys.path.insert(0, str(spine_src))
    from spine_runner import validate_output_root  # type: ignore

    return validate_output_root(out_dir)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _stable_packet_id(packet_family: str, refs: list[str]) -> str:
    seed = "__".join([packet_family] + sorted(refs)) or "empty"
    total = sum((idx + 1) * ord(ch) for idx, ch in enumerate(seed))
    return f"cep_{packet_family}_{total % 100000:05d}"


def _ref_from_item(item: Any, fallback_prefix: str, idx: int) -> str:
    if isinstance(item, dict):
        for key in ["ref_id", "id", "feature_id", "window_id", "sequence_id", "metric_id", "signal_id"]:
            if item.get(key) not in [None, ""]:
                return str(item[key])
    if item not in [None, ""]:
        return str(item)
    return f"{fallback_prefix}_{idx}"


def collect_input_refs(candidate: dict[str, Any]) -> dict[str, list[str]]:
    groups = {
        "input_features": _as_list(candidate.get("input_features")),
        "input_windows": _as_list(candidate.get("input_windows")),
        "input_sequences": _as_list(candidate.get("input_sequences")),
        "input_metrics": _as_list(candidate.get("input_metrics")),
        "supporting_signals": _as_list(candidate.get("supporting_signals")),
        "contradicting_signals": _as_list(candidate.get("contradicting_signals")),
    }
    refs: dict[str, list[str]] = {}
    for group_name, items in groups.items():
        refs[group_name] = [_ref_from_item(item, group_name, idx) for idx, item in enumerate(items)]
    return refs


def _all_refs(refs: dict[str, list[str]]) -> list[str]:
    values: list[str] = []
    for group_refs in refs.values():
        values.extend(group_refs)
    return values


def _source_surface_count(candidate: dict[str, Any]) -> int:
    surfaces = set()
    for group_name in ["input_features", "input_windows", "input_sequences", "input_metrics", "supporting_signals", "contradicting_signals"]:
        for item in _as_list(candidate.get(group_name)):
            if isinstance(item, dict):
                surface = item.get("source_surface") or item.get("source") or item.get("surface")
                if surface:
                    surfaces.add(str(surface))
    return len(surfaces)


def _is_forbidden_value(value: Any) -> bool:
    return value not in [None, "", False, []]


def _collect_forbidden_hits(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_OUTPUT_FIELDS and _is_forbidden_value(child):
                hits.append(child_path)
            hits.extend(_collect_forbidden_hits(child, child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            child_path = f"{path}[{idx}]" if path else f"[{idx}]"
            hits.extend(_collect_forbidden_hits(child, child_path))
    return hits


def _detect_forbidden_output_attempt(candidate: dict[str, Any]) -> list[str]:
    return sorted(set(_collect_forbidden_hits(candidate)))


def _normalized_blocked_language_families(candidate: dict[str, Any]) -> list[str]:
    requested = {str(item) for item in _as_list(candidate.get("blocked_language_families")) if item not in [None, ""]}
    required = set(BLOCKED_LANGUAGE_FAMILIES)
    return sorted(required | requested)


def _claim_ceiling(candidate: dict[str, Any]) -> str:
    return str(candidate.get("claim_ceiling") or "")


def _evidence_strength(signal_count: int, contradiction_count: int, surface_count: int) -> str:
    if signal_count < DEFAULT_MINIMUM_SIGNAL_COUNT:
        return "weak"
    if contradiction_count:
        return "medium"
    if signal_count >= 4 and surface_count >= 2:
        return "strong"
    return "medium"


def build_composite_packet(candidate: dict[str, Any]) -> dict[str, Any]:
    packet_family = str(candidate.get("packet_family") or "weak_signal")
    if packet_family not in ALLOWED_PACKET_FAMILIES:
        packet_family = "weak_signal"

    refs = collect_input_refs(candidate)
    all_refs = _all_refs(refs)
    unique_ref_count = len(set(all_refs))
    supporting_count = len(refs["supporting_signals"])
    contradicting_count = len(refs["contradicting_signals"])
    source_surface_count = _source_surface_count(candidate)
    forbidden_hits = _detect_forbidden_output_attempt(candidate)
    claim_ceiling = _claim_ceiling(candidate)

    hard_block_hits: list[str] = []
    if unique_ref_count < DEFAULT_MINIMUM_SIGNAL_COUNT:
        hard_block_hits.append("minimum_two_sources_required")
        hard_block_hits.append("single_signal_cannot_create_composite_argument")
    if not claim_ceiling:
        hard_block_hits.append("claim_ceiling_missing")
    elif claim_ceiling != DEFAULT_CLAIM_CEILING:
        hard_block_hits.append("non_candidate_claim_ceiling_rejected")
    if forbidden_hits:
        hard_block_hits.append("forbidden_output_attempted")

    status = "FAIL_CLOSED" if hard_block_hits else "SMOKE_PASS"
    decision = "BLOCK_PACKET" if hard_block_hits else "READY_FOR_FUSION_CONSUMER"

    packet = {
        "module_id": MODULE_ID,
        "packet_id": str(candidate.get("packet_id") or _stable_packet_id(packet_family, all_refs)),
        "packet_family": packet_family,
        "input_features": refs["input_features"],
        "input_windows": refs["input_windows"],
        "input_sequences": refs["input_sequences"],
        "input_metrics": refs["input_metrics"],
        "supporting_signals": refs["supporting_signals"],
        "contradicting_signals": refs["contradicting_signals"],
        "input_ref_count": unique_ref_count,
        "supporting_signal_count": supporting_count,
        "contradicting_signal_count": contradicting_count,
        "source_surface_count": source_surface_count,
        "evidence_strength": _evidence_strength(unique_ref_count, contradicting_count, source_surface_count),
        "minimum_signal_count": DEFAULT_MINIMUM_SIGNAL_COUNT,
        "claim_ceiling": claim_ceiling or DEFAULT_CLAIM_CEILING,
        "report_consumers": list(candidate.get("report_consumers") or DEFAULT_REPORT_CONSUMERS),
        "blocked_language_families": _normalized_blocked_language_families(candidate),
        "hard_block_hits": hard_block_hits,
        "forbidden_output_hits": forbidden_hits,
        "decision": decision,
        "status": status,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "control_truth": False,
        "coach_intention_truth": False,
        "off_ball_truth": False,
        "pitch_control_truth": False,
        "canonical_event_count": "UNKNOWN",
    }
    return packet


def build_report(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    packets = [build_composite_packet(candidate) for candidate in candidates]
    family_counts = Counter(packet["packet_family"] for packet in packets)
    hard_block_count = sum(1 for packet in packets if packet["hard_block_hits"])
    status = "FAIL_CLOSED" if hard_block_count else "SMOKE_PASS"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "packet_count": len(packets),
        "blocked_packet_count": hard_block_count,
        "family_counts": dict(sorted(family_counts.items())),
        "packets": packets,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "claim_boundary": "composite_evidence_packet_only_no_claim_text",
    }


def write_outputs(candidates: list[dict[str, Any]], out_dir: str | Path) -> dict[str, Any]:
    out = _validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_report(candidates)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA COMPOSITE EVIDENCE PACKET BUILDER LITE V1",
        "================================================",
        f"status={report['status']}",
        f"packet_count={report['packet_count']}",
        f"blocked_packet_count={report['blocked_packet_count']}",
        f"canonical_event_count={report['canonical_event_count']}",
        "",
        "[packets]",
    ]
    for packet in report["packets"][:50]:
        lines.append(
            f"- {packet['packet_id']} family={packet['packet_family']} refs={packet['input_ref_count']} "
            f"strength={packet['evidence_strength']} decision={packet['decision']}"
        )
    (out / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
