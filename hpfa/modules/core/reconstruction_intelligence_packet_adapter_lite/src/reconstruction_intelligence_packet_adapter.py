from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "reconstruction_intelligence_packet_adapter_lite_v1"
UPSTREAM_MODULE_ID = "visible_action_sequence_candidates_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
SOURCE_CLAIM_CEILING = "VISIBLE_SEQUENCE_CANDIDATE_ONLY"
TARGET_CLAIM_CEILING = "composite_candidate_only"
OUTPUT_JSON = "reconstruction_intelligence_packet_adapter_lite_v1.json"
OUTPUT_TXT = "reconstruction_intelligence_packet_adapter_lite_v1.txt"

PASS_SEQUENCE_STATES = {
    "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
    "PASS_SINGLE_LAYER_VISIBLE_TRACE_CANDIDATE",
}
REVIEW_SEQUENCE_STATES = {"REVIEW_REQUIRED_CONTEXT"}
TOP_LEVEL_FALSE_LOCKS = (
    "same_timestamp_internal_ordering_allowed",
    "source_row_order_is_temporal_truth",
    "visible_sequence_candidate_is_sequence_truth",
    "visible_sequence_candidate_is_possession_truth",
    "single_team_continuity_is_control_truth",
    "sequence_duration_is_physical_action_duration",
    "sequence_truth",
    "possession_truth",
    "phase_truth",
    "tactical_truth",
)
SEQUENCE_FALSE_LOCKS = (
    "visible_sequence_candidate_is_sequence_truth",
    "visible_sequence_candidate_is_possession_truth",
    "single_team_continuity_is_control_truth",
    "sequence_duration_is_physical_action_duration",
    "same_timestamp_internal_ordering_allowed",
    "source_row_order_is_temporal_truth",
)
LAYER_FALSE_LOCKS = (
    "same_timestamp_internal_ordering_allowed",
    "time_layer_is_event_group_truth",
    "time_layer_is_sequence_truth",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def validate_out(out_dir: str | Path) -> Path:
    spine_src = _repo_root() / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    if str(spine_src) not in sys.path:
        sys.path.insert(0, str(spine_src))
    from spine_runner import validate_output_root  # type: ignore

    return validate_output_root(out_dir)


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _count(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _validate_false_locks(record: dict[str, Any], fields: tuple[str, ...], prefix: str) -> list[str]:
    return [f"{prefix}_claim_boundary_breached:{field}" for field in fields if record.get(field) is True]


def _sequence_review_reasons(sequence: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    state = _clean(sequence.get("sequence_record_status"))
    if state in REVIEW_SEQUENCE_STATES:
        reasons.append(f"sequence_record_status:{state}")
    review_count = _count(sequence.get("consequence_review_trace_count")) or 0
    if review_count > 0:
        reasons.append(f"consequence_review_trace_count:{review_count}")
    return reasons


def _validate_upstream(payload: dict[str, Any]) -> tuple[list[str], list[str], dict[str, dict[str, Any]]]:
    blocks: list[str] = []
    reviews: list[str] = []

    if payload.get("module_id") != UPSTREAM_MODULE_ID:
        blocks.append("upstream_module_id_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("upstream_canonical_event_count_claimed")
    if payload.get("production_release") is True:
        blocks.append("upstream_production_release_claimed")
    if _as_list(payload.get("hard_block_hits")):
        blocks.append("upstream_hard_blocks_present")

    upstream_status = _clean(payload.get("module_status") or payload.get("status"))
    if upstream_status == "FAIL_CLOSED":
        blocks.append("upstream_fail_closed")
    elif upstream_status not in {"PASS", "REVIEW_REQUIRED"}:
        blocks.append(f"upstream_status_not_admitted:{upstream_status or 'UNKNOWN'}")
    elif upstream_status == "REVIEW_REQUIRED":
        reviews.append("upstream_visible_sequence_review_required")

    binding = _clean(payload.get("match_surface_binding_id"))
    if not binding:
        blocks.append("match_surface_binding_missing")

    blocks.extend(_validate_false_locks(payload, TOP_LEVEL_FALSE_LOCKS, "upstream"))

    layers_raw = payload.get("visible_action_time_layer_candidates")
    if not isinstance(layers_raw, list):
        blocks.append("visible_action_time_layer_inventory_invalid")
        layers_raw = []
    layer_count = _count(payload.get("visible_action_time_layer_candidate_count"))
    if layer_count is not None and layer_count != len(layers_raw):
        blocks.append("visible_action_time_layer_candidate_count_mismatch")

    layer_by_id: dict[str, dict[str, Any]] = {}
    for idx, raw in enumerate(layers_raw):
        if not isinstance(raw, dict):
            blocks.append(f"time_layer_record_invalid:{idx}")
            continue
        layer_id = _clean(raw.get("visible_action_time_layer_candidate_id"))
        if not layer_id or layer_id in layer_by_id:
            blocks.append(f"time_layer_id_invalid_or_duplicate:{idx}")
            continue
        if binding and _clean(raw.get("match_surface_binding_id")) != binding:
            blocks.append(f"time_layer_binding_mismatch:{layer_id}")
        if raw.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
            blocks.append(f"time_layer_canonical_event_count_claimed:{layer_id}")
        blocks.extend(_validate_false_locks(raw, LAYER_FALSE_LOCKS, f"time_layer:{layer_id}"))
        layer_by_id[layer_id] = raw

    sequences_raw = payload.get("visible_action_sequence_candidates")
    if not isinstance(sequences_raw, list) or not sequences_raw:
        blocks.append("visible_action_sequence_inventory_empty_or_invalid")
        sequences_raw = []
    sequence_count = _count(payload.get("visible_action_sequence_candidate_count"))
    if sequence_count is not None and sequence_count != len(sequences_raw):
        blocks.append("visible_action_sequence_candidate_count_mismatch")

    seen_sequence_ids: set[str] = set()
    for idx, raw in enumerate(sequences_raw):
        if not isinstance(raw, dict):
            blocks.append(f"sequence_record_invalid:{idx}")
            continue
        sequence_id = _clean(raw.get("visible_action_sequence_candidate_id"))
        if not sequence_id or sequence_id in seen_sequence_ids:
            blocks.append(f"sequence_id_invalid_or_duplicate:{idx}")
            continue
        seen_sequence_ids.add(sequence_id)
        if binding and _clean(raw.get("match_surface_binding_id")) != binding:
            blocks.append(f"sequence_binding_mismatch:{sequence_id}")
        if raw.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
            blocks.append(f"sequence_canonical_event_count_claimed:{sequence_id}")
        if _clean(raw.get("claim_ceiling")) != SOURCE_CLAIM_CEILING:
            blocks.append(f"sequence_claim_ceiling_not_visible_candidate_only:{sequence_id}")
        blocks.extend(_validate_false_locks(raw, SEQUENCE_FALSE_LOCKS, f"sequence:{sequence_id}"))

        state = _clean(raw.get("sequence_record_status"))
        if state not in PASS_SEQUENCE_STATES | REVIEW_SEQUENCE_STATES:
            blocks.append(f"sequence_record_status_not_admitted:{sequence_id}:{state or 'UNKNOWN'}")

        layer_ids = [_clean(item) for item in _as_list(raw.get("time_layer_candidate_ids")) if _clean(item)]
        if not layer_ids:
            blocks.append(f"sequence_time_layer_refs_missing:{sequence_id}")
        if len(set(layer_ids)) != len(layer_ids):
            blocks.append(f"sequence_time_layer_refs_duplicate:{sequence_id}")
        expected_layer_count = _count(raw.get("time_layer_count"))
        if expected_layer_count is not None and expected_layer_count != len(layer_ids):
            blocks.append(f"sequence_time_layer_count_mismatch:{sequence_id}")
        for layer_id in layer_ids:
            if layer_id not in layer_by_id:
                blocks.append(f"sequence_time_layer_ref_missing:{sequence_id}:{layer_id}")

        reasons = _sequence_review_reasons(raw)
        if reasons:
            reviews.extend(f"{sequence_id}:{reason}" for reason in reasons)

    for item in _as_list(payload.get("review_hits")):
        text = _clean(item)
        if text:
            reviews.append(f"upstream_review_hit:{text}")

    return sorted(set(blocks)), sorted(set(reviews)), layer_by_id


def _packet_candidate(sequence: dict[str, Any], layer_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    sequence_id = _clean(sequence.get("visible_action_sequence_candidate_id"))
    binding = _clean(sequence.get("match_surface_binding_id"))
    layer_ids = [_clean(item) for item in _as_list(sequence.get("time_layer_candidate_ids")) if _clean(item)]
    review_reasons = _sequence_review_reasons(sequence)

    sequence_ref = {
        "sequence_id": sequence_id,
        "source_surface": "CURRENT_RECONSTRUCTION",
        "match_surface_binding_id": binding,
        "period_candidate": sequence.get("period_candidate"),
        "independent_support_vote": False,
        "sequence_truth": False,
        "possession_truth": False,
    }
    windows = [
        {
            "window_id": layer_id,
            "source_surface": "CURRENT_RECONSTRUCTION",
            "match_surface_binding_id": binding,
            "period_candidate": layer_by_id[layer_id].get("period_candidate"),
            "start_candidate": layer_by_id[layer_id].get("start_candidate"),
            "layer_state": layer_by_id[layer_id].get("layer_state"),
            "independent_support_vote": False,
            "same_timestamp_internal_ordering_allowed": False,
        }
        for layer_id in layer_ids
    ]

    support_id = "ris_" + _digest(sequence_id, "visible_sequence_structure")[:24]
    supporting_signal = {
        "signal_id": support_id,
        "source_surface": "CURRENT_RECONSTRUCTION",
        "evidence_derivation_role": "DERIVED_FROM_VISIBLE_SEQUENCE_CANDIDATE",
        "evidence_role": "visible_sequence_structure_candidate",
        "relation_type": "SUPPORTS",
        "match_surface_binding_id": binding,
        "sequence_candidate_id": sequence_id,
        "action_family_counts": dict(sequence.get("action_family_counts") or {}),
        "consequence_candidate_counts": dict(sequence.get("consequence_candidate_counts") or {}),
        "trace_candidate_count": sequence.get("trace_candidate_count"),
        "time_layer_count": sequence.get("time_layer_count"),
        "independent_support_vote": False,
        "sequence_truth": False,
        "possession_truth": False,
        "causal_truth": False,
        "tactical_truth_candidate_admitted": False,
    }

    qualifiers: list[dict[str, Any]] = []
    if review_reasons:
        qualifier_id = "riq_" + _digest(sequence_id, review_reasons)[:24]
        qualifiers.append(
            {
                "signal_id": qualifier_id,
                "source_surface": "CURRENT_RECONSTRUCTION",
                "evidence_derivation_role": "DERIVED_FROM_VISIBLE_SEQUENCE_REVIEW_STATE",
                "evidence_role": "upstream_review_qualifier",
                "relation_type": "QUALIFIES",
                "match_surface_binding_id": binding,
                "sequence_candidate_id": sequence_id,
                "review_required": True,
                "review_reasons": review_reasons,
                "independent_support_vote": False,
                "explicit_contradiction": False,
                "sequence_truth": False,
                "possession_truth": False,
            }
        )

    packet_id = "rip_" + _digest(binding, sequence_id, layer_ids)[:24]
    return {
        "packet_id": packet_id,
        "packet_family": "sequence",
        "input_features": [],
        "input_windows": windows,
        "input_sequences": [sequence_ref],
        "input_metrics": [],
        "supporting_signals": [supporting_signal],
        "contradicting_signals": qualifiers,
        "claim_ceiling": TARGET_CLAIM_CEILING,
        "source_adapter_module_id": MODULE_ID,
        "source_sequence_candidate_id": sequence_id,
        "source_match_surface_binding_id": binding,
        "review_required": bool(review_reasons),
        "review_reasons": review_reasons,
        "derived_reconstruction_refs_are_independent_sources": False,
        "independent_support_vote_allowed": False,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
    }


def build_packet_input_candidates(payload: dict[str, Any]) -> dict[str, Any]:
    blocks, reviews, layer_by_id = _validate_upstream(payload)
    sequences = payload.get("visible_action_sequence_candidates") if isinstance(payload.get("visible_action_sequence_candidates"), list) else []

    packet_candidates: list[dict[str, Any]] = []
    if not blocks:
        packet_candidates = [_packet_candidate(sequence, layer_by_id) for sequence in sequences if isinstance(sequence, dict)]

    if blocks:
        status = "FAIL_CLOSED"
        decision = "BLOCK_RECONSTRUCTION_INTELLIGENCE_BRIDGE"
    elif reviews:
        status = "REVIEW_REQUIRED"
        decision = "ROUTE_PACKETS_WITH_REVIEW_QUALIFIERS"
    else:
        status = "SMOKE_PASS"
        decision = "READY_FOR_COMPOSITE_PACKET_BUILDER"

    review_packet_count = sum(bool(row.get("review_required")) for row in packet_candidates)
    binding = _clean(payload.get("match_surface_binding_id"))
    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "decision": decision,
        "source_module_id": payload.get("module_id"),
        "match_surface_binding_id": binding or None,
        "source_visible_action_sequence_candidate_count": len(sequences),
        "packet_input_candidate_count": len(packet_candidates),
        "review_required_packet_input_candidate_count": review_packet_count,
        "packet_input_assignment_complete": (not blocks and len(packet_candidates) == len(sequences)),
        "composite_packet_input_candidates": packet_candidates,
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "source_claim_ceiling": SOURCE_CLAIM_CEILING,
        "target_claim_ceiling": TARGET_CLAIM_CEILING,
        "packet_input_ref_count_is_independent_source_count": False,
        "derived_reconstruction_refs_are_independent_sources": False,
        "independent_support_vote_allowed": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "visible_sequence_candidate_is_sequence_truth": False,
        "visible_sequence_candidate_is_possession_truth": False,
        "sequence_truth": False,
        "possession_truth": False,
        "causal_truth": False,
        "tactical_truth": False,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA RECONSTRUCTION -> INTELLIGENCE PACKET ADAPTER LITE V1",
        "===========================================================",
        f"status={report.get('status')}",
        f"decision={report.get('decision')}",
        f"source_visible_action_sequence_candidate_count={report.get('source_visible_action_sequence_candidate_count')}",
        f"packet_input_candidate_count={report.get('packet_input_candidate_count')}",
        f"review_required_packet_input_candidate_count={report.get('review_required_packet_input_candidate_count')}",
        f"packet_input_assignment_complete={report.get('packet_input_assignment_complete')}",
        f"hard_block_hits={report.get('hard_block_hits') or []}",
        f"review_hits={report.get('review_hits') or []}",
        "derived_reconstruction_refs_are_independent_sources=false",
        "independent_support_vote_allowed=false",
        "same_timestamp_internal_ordering_allowed=false",
        "source_row_order_is_temporal_truth=false",
        "visible_sequence_candidate_is_sequence_truth=false",
        "visible_sequence_candidate_is_possession_truth=false",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
        "",
    ]
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Any]:
    output = validate_out(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    report = build_packet_input_candidates(payload)
    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    report["outputs"] = {"adapter_json": str(json_path), "adapter_txt": str(txt_path)}
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text(render_txt(report), encoding="utf-8")
    return report
