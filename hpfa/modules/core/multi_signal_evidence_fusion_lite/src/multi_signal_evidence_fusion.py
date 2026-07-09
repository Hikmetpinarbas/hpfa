from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "multi_signal_evidence_fusion_lite_v1"
OUTPUT_JSON = "multi_signal_evidence_fusion_lite_v1.json"
OUTPUT_TXT = "multi_signal_evidence_fusion_lite_v1.txt"

CANDIDATE_ONLY_CLAIM_CEILING = "composite_candidate_only"
FUSION_CLAIM_CEILING = "fusion_relation_candidate_only"

RELATION_TYPES = {
    "SUPPORTS",
    "CONTRADICTS",
    "COMPLEMENTS",
    "CONTEXTUALIZES",
    "ABSTAINS",
}

BLOCKED_LANGUAGE_FAMILIES = [
    "tactical_truth",
    "dominance_truth",
    "control_truth",
    "coach_intention",
    "off_ball_truth",
    "pitch_control_truth",
    "causal_truth",
]

FORBIDDEN_PACKET_FIELDS = {
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


def _packet_id(packet: dict[str, Any], idx: int) -> str:
    return str(packet.get("packet_id") or f"packet_{idx:03d}")


def _refs(packet: dict[str, Any], key: str) -> list[str]:
    return [str(item) for item in _as_list(packet.get(key)) if item not in [None, ""]]


def _forbidden_packet_hits(packet: dict[str, Any]) -> list[str]:
    hits = []
    for field in FORBIDDEN_PACKET_FIELDS:
        if field in packet and packet.get(field) not in [None, "", False, []]:
            hits.append(field)
    return sorted(hits)


def _required_packet_missing(packet: dict[str, Any]) -> list[str]:
    required = [
        "packet_id",
        "packet_family",
        "input_features",
        "input_windows",
        "input_metrics",
        "supporting_signals",
        "contradicting_signals",
        "claim_ceiling",
    ]
    return [key for key in required if key not in packet]


def _signal_relation_records(packet: dict[str, Any]) -> list[dict[str, Any]]:
    packet_id = str(packet["packet_id"])
    records: list[dict[str, Any]] = []

    for signal in _refs(packet, "supporting_signals"):
        records.append({
            "packet_id": packet_id,
            "signal_ref": signal,
            "relation_type": "SUPPORTS",
            "evidence_role": "supporting_signal",
            "claim_ceiling": FUSION_CLAIM_CEILING,
        })

    for signal in _refs(packet, "contradicting_signals"):
        records.append({
            "packet_id": packet_id,
            "signal_ref": signal,
            "relation_type": "CONTRADICTS",
            "evidence_role": "contradicting_signal",
            "claim_ceiling": FUSION_CLAIM_CEILING,
        })

    for feature in _refs(packet, "input_features"):
        records.append({
            "packet_id": packet_id,
            "signal_ref": feature,
            "relation_type": "COMPLEMENTS",
            "evidence_role": "input_feature_ref",
            "claim_ceiling": FUSION_CLAIM_CEILING,
        })

    for window in _refs(packet, "input_windows"):
        records.append({
            "packet_id": packet_id,
            "signal_ref": window,
            "relation_type": "CONTEXTUALIZES",
            "evidence_role": "input_window_ref",
            "claim_ceiling": FUSION_CLAIM_CEILING,
        })

    if not records:
        records.append({
            "packet_id": packet_id,
            "signal_ref": packet_id,
            "relation_type": "ABSTAINS",
            "evidence_role": "insufficient_signal_surface",
            "claim_ceiling": FUSION_CLAIM_CEILING,
        })

    return records


def fuse_packet(packet: dict[str, Any], idx: int = 0) -> dict[str, Any]:
    normalized_packet = dict(packet)
    normalized_packet["packet_id"] = _packet_id(normalized_packet, idx)

    missing_fields = _required_packet_missing(normalized_packet)
    forbidden_hits = _forbidden_packet_hits(normalized_packet)
    hard_block_hits: list[str] = []

    if missing_fields:
        hard_block_hits.append("composite_packet_required_fields_missing")
    if normalized_packet.get("claim_ceiling") != CANDIDATE_ONLY_CLAIM_CEILING:
        hard_block_hits.append("upstream_packet_claim_ceiling_not_candidate_only")
    if forbidden_hits:
        hard_block_hits.append("upstream_packet_forbidden_output_attempted")
    if normalized_packet.get("claim_output_allowed") not in [False, None]:
        hard_block_hits.append("upstream_packet_claim_output_allowed")
    if normalized_packet.get("report_language_allowed") not in [False, None]:
        hard_block_hits.append("upstream_packet_report_language_allowed")

    relation_records = _signal_relation_records(normalized_packet) if not missing_fields else []
    relation_counts = Counter(row["relation_type"] for row in relation_records)
    has_support = relation_counts.get("SUPPORTS", 0) > 0
    has_contradiction = relation_counts.get("CONTRADICTS", 0) > 0

    if hard_block_hits:
        fusion_status = "BLOCKED"
        decision = "BLOCK_FUSION"
    elif has_support and has_contradiction:
        fusion_status = "MIXED_WITH_CONTRADICTION"
        decision = "READY_FOR_ARGUMENT_WITH_CONTRADICTION"
    elif has_support:
        fusion_status = "SUPPORTED"
        decision = "READY_FOR_ARGUMENT_SUPPORT"
    elif has_contradiction:
        fusion_status = "CONTRADICTED"
        decision = "REVIEW_REQUIRED"
    else:
        fusion_status = "ABSTAINS"
        decision = "INSUFFICIENT_FOR_ARGUMENT"

    return {
        "module_id": MODULE_ID,
        "fusion_id": f"fusion_{normalized_packet['packet_id']}",
        "packet_id": normalized_packet["packet_id"],
        "packet_family": normalized_packet.get("packet_family", "unknown"),
        "relation_records": relation_records,
        "relation_counts": dict(sorted(relation_counts.items())),
        "support_signal_count": relation_counts.get("SUPPORTS", 0),
        "contradiction_signal_count": relation_counts.get("CONTRADICTS", 0),
        "context_signal_count": relation_counts.get("CONTEXTUALIZES", 0),
        "complement_signal_count": relation_counts.get("COMPLEMENTS", 0),
        "fusion_status": fusion_status,
        "decision": decision,
        "claim_ceiling": FUSION_CLAIM_CEILING,
        "upstream_claim_ceiling": normalized_packet.get("claim_ceiling"),
        "hard_block_hits": hard_block_hits,
        "missing_fields": missing_fields,
        "forbidden_output_hits": forbidden_hits,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "control_truth": False,
        "coach_intention_truth": False,
        "off_ball_truth": False,
        "pitch_control_truth": False,
        "causal_truth": False,
        "blocked_language_families": list(BLOCKED_LANGUAGE_FAMILIES),
        "canonical_event_count": "UNKNOWN",
    }


def build_fusion_report(packets: list[dict[str, Any]]) -> dict[str, Any]:
    fusion_records = [fuse_packet(packet, idx) for idx, packet in enumerate(packets)]
    blocked_count = sum(1 for record in fusion_records if record["hard_block_hits"])
    status = "FAIL_CLOSED" if blocked_count else "SMOKE_PASS"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "fusion_record_count": len(fusion_records),
        "blocked_fusion_count": blocked_count,
        "fusion_records": fusion_records,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "claim_ceiling": FUSION_CLAIM_CEILING,
        "canonical_event_count": "UNKNOWN",
        "claim_boundary": "fusion_relation_candidate_only_no_claim_text",
    }


def write_outputs(packets: list[dict[str, Any]], out_dir: str | Path) -> dict[str, Any]:
    out = _validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_fusion_report(packets)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA MULTI SIGNAL EVIDENCE FUSION LITE V1",
        "===========================================",
        f"status={report['status']}",
        f"fusion_record_count={report['fusion_record_count']}",
        f"blocked_fusion_count={report['blocked_fusion_count']}",
        f"canonical_event_count={report['canonical_event_count']}",
        "",
        "[fusion_records]",
    ]
    for record in report["fusion_records"][:50]:
        lines.append(
            f"- {record['fusion_id']} packet={record['packet_id']} status={record['fusion_status']} "
            f"decision={record['decision']} supports={record['support_signal_count']} "
            f"contradicts={record['contradiction_signal_count']}"
        )
    (out / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
