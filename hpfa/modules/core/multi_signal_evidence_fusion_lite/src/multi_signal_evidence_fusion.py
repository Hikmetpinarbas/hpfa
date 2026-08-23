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
MISSING_PACKET_ID = "MISSING_PACKET_ID"

RELATION_TYPES = {
    "SUPPORTS",
    "CONTRADICTS",
    "QUALIFIES",
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
    "causal_truth",
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


def _packet_id(packet: dict[str, Any]) -> str:
    return str(packet.get("packet_id") or "")


def _ref_from_item(item: Any, fallback_prefix: str, idx: int) -> str:
    if isinstance(item, dict):
        for key in ["signal_ref", "signal_id", "ref_id", "id", "feature_id", "window_id", "metric_id", "sequence_id"]:
            if item.get(key) not in [None, ""]:
                return str(item[key])
    if item not in [None, ""]:
        return str(item)
    return f"{fallback_prefix}_{idx}"


def _items(packet: dict[str, Any], key: str) -> list[Any]:
    return [item for item in _as_list(packet.get(key)) if item not in [None, ""]]


def _signal_items(packet: dict[str, Any], key: str) -> list[Any]:
    record_key = {
        "supporting_signals": "supporting_signal_records",
        "contradicting_signals": "contradicting_signal_records",
    }.get(key)
    if record_key:
        records = _items(packet, record_key)
        if records:
            return records
    return _items(packet, key)


def _refs(packet: dict[str, Any], key: str) -> list[str]:
    return [_ref_from_item(item, key, idx) for idx, item in enumerate(_items(packet, key))]


def _is_forbidden_value(value: Any) -> bool:
    return value not in [None, "", False, []]


def _collect_forbidden_hits(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_PACKET_FIELDS and _is_forbidden_value(child):
                hits.append(child_path)
            hits.extend(_collect_forbidden_hits(child, child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            child_path = f"{path}[{idx}]" if path else f"[{idx}]"
            hits.extend(_collect_forbidden_hits(child, child_path))
    return hits


def _forbidden_packet_hits(packet: dict[str, Any]) -> list[str]:
    return sorted(set(_collect_forbidden_hits(packet)))


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
    return [key for key in required if packet.get(key) in [None, ""]]


def _upstream_packet_failed(packet: dict[str, Any]) -> bool:
    if _as_list(packet.get("hard_block_hits")):
        return True
    if str(packet.get("decision") or "").upper().startswith("BLOCK"):
        return True
    if str(packet.get("status") or "").upper() in {"FAIL_CLOSED", "BLOCKED"}:
        return True
    return False


def _is_explicit_contradiction(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    relation_type = str(item.get("relation_type") or "").upper()
    if relation_type == "CONTRADICTS":
        return True
    if item.get("explicit_contradiction") is True:
        return True
    if item.get("contradiction_basis") not in [None, "", []]:
        return True
    return False


def _record(packet_id: str, signal_ref: str, relation_type: str, evidence_role: str, relation_basis: str = "") -> dict[str, Any]:
    record = {
        "packet_id": packet_id,
        "signal_ref": signal_ref,
        "relation_type": relation_type,
        "evidence_role": evidence_role,
        "claim_ceiling": FUSION_CLAIM_CEILING,
    }
    if relation_basis:
        record["relation_basis"] = relation_basis
    return record


def _signal_relation_records(packet: dict[str, Any]) -> list[dict[str, Any]]:
    packet_id = str(packet["packet_id"])
    records: list[dict[str, Any]] = []

    for idx, signal in enumerate(_signal_items(packet, "supporting_signals")):
        records.append(_record(packet_id, _ref_from_item(signal, "supporting_signals", idx), "SUPPORTS", "supporting_signal"))

    for idx, signal in enumerate(_signal_items(packet, "contradicting_signals")):
        signal_ref = _ref_from_item(signal, "contradicting_signals", idx)
        if _is_explicit_contradiction(signal):
            basis = str(signal.get("contradiction_basis") or signal.get("relation_basis") or "") if isinstance(signal, dict) else ""
            records.append(_record(packet_id, signal_ref, "CONTRADICTS", "explicit_contradiction_signal", basis))
        else:
            records.append(_record(packet_id, signal_ref, "QUALIFIES", "qualifying_or_tension_signal"))

    for feature in _refs(packet, "input_features"):
        records.append(_record(packet_id, feature, "COMPLEMENTS", "input_feature_ref"))

    for window in _refs(packet, "input_windows"):
        records.append(_record(packet_id, window, "CONTEXTUALIZES", "input_window_ref"))

    if not records:
        records.append(_record(packet_id, packet_id, "ABSTAINS", "insufficient_signal_surface"))

    return records


def fuse_packet(packet: dict[str, Any], idx: int = 0) -> dict[str, Any]:
    normalized_packet = dict(packet)
    original_packet_id = _packet_id(normalized_packet)

    missing_fields = _required_packet_missing(normalized_packet)
    packet_id = original_packet_id or MISSING_PACKET_ID
    if original_packet_id:
        normalized_packet["packet_id"] = original_packet_id
    else:
        normalized_packet["packet_id"] = packet_id

    forbidden_hits = _forbidden_packet_hits(normalized_packet)
    upstream_hard_block_hits = [str(item) for item in _as_list(normalized_packet.get("hard_block_hits")) if item not in [None, ""]]
    hard_block_hits: list[str] = []

    if missing_fields:
        hard_block_hits.append("composite_packet_required_fields_missing")
    if _upstream_packet_failed(normalized_packet):
        hard_block_hits.append("upstream_packet_failed_closed")
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
    has_qualifier = relation_counts.get("QUALIFIES", 0) > 0

    if hard_block_hits:
        fusion_status = "BLOCKED"
        decision = "BLOCK_FUSION"
    elif has_support and has_contradiction:
        fusion_status = "MIXED_WITH_EXPLICIT_CONTRADICTION"
        decision = "READY_FOR_ARGUMENT_WITH_CONTRADICTION"
    elif has_support and has_qualifier:
        fusion_status = "SUPPORTED_WITH_QUALIFIER"
        decision = "READY_FOR_ARGUMENT_WITH_QUALIFIER"
    elif has_support:
        fusion_status = "SUPPORTED"
        decision = "READY_FOR_ARGUMENT_SUPPORT"
    elif has_contradiction:
        fusion_status = "EXPLICITLY_CONTRADICTED"
        decision = "REVIEW_REQUIRED"
    elif has_qualifier:
        fusion_status = "QUALIFIED_ONLY"
        decision = "REVIEW_REQUIRED"
    else:
        fusion_status = "ABSTAINS"
        decision = "INSUFFICIENT_FOR_ARGUMENT"

    return {
        "module_id": MODULE_ID,
        "fusion_id": f"fusion_{packet_id}",
        "packet_id": packet_id,
        "packet_family": normalized_packet.get("packet_family", "unknown"),
        "relation_records": relation_records,
        "relation_counts": dict(sorted(relation_counts.items())),
        "support_signal_count": relation_counts.get("SUPPORTS", 0),
        "contradiction_signal_count": relation_counts.get("CONTRADICTS", 0),
        "qualifier_signal_count": relation_counts.get("QUALIFIES", 0),
        "context_signal_count": relation_counts.get("CONTEXTUALIZES", 0),
        "complement_signal_count": relation_counts.get("COMPLEMENTS", 0),
        "fusion_status": fusion_status,
        "decision": decision,
        "claim_ceiling": FUSION_CLAIM_CEILING,
        "upstream_claim_ceiling": normalized_packet.get("claim_ceiling"),
        "upstream_status": normalized_packet.get("status"),
        "upstream_decision": normalized_packet.get("decision"),
        "upstream_hard_block_hits": upstream_hard_block_hits,
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
            f"qualifies={record['qualifier_signal_count']} contradicts={record['contradiction_signal_count']}"
        )
    (out / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
