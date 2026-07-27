from __future__ import annotations

from collections import Counter
from typing import Any

try:
    from .common import CANONICAL_EVENT_COUNT, UNRESOLVED_CONSEQUENCE, clean, digest, number
except ImportError:
    from common import CANONICAL_EVENT_COUNT, UNRESOLVED_CONSEQUENCE, clean, digest, number

RECOVERY_FAMILIES = {"RECOVERY", "INTERCEPTION"}


def _trace_signals(
    primary_nodes: list[dict[str, Any]],
    event_records: list[dict[str, Any]],
) -> list[str]:
    families = Counter(
        clean(family)
        for node in primary_nodes
        for family in (node.get("action_family_candidates") or [])
        if clean(family)
    )
    consequence_counts = Counter(clean(record.get("consequence_class_candidate")) for record in event_records)
    turnover_counts = Counter(clean(record.get("turnover_window_class")) for record in event_records)
    false_progression_counts = Counter(clean(record.get("false_progression_candidate")) for record in event_records)
    signals: list[str] = []

    first_families = set(primary_nodes[0].get("action_family_candidates") or []) if primary_nodes else set()
    if "RESTART" in first_families:
        signals.append("RESTART_TRACE_CANDIDATE")
    if first_families & RECOVERY_FAMILIES and len(primary_nodes) > 1:
        signals.append("REGAIN_TO_VISIBLE_CONTINUATION_CANDIDATE")
    if families.get("SHOT", 0) > 0:
        signals.append("SHOT_CHAIN_CANDIDATE")
    if families.get("CLEARANCE", 0) >= 2:
        signals.append("CLEARANCE_CLUSTER_CANDIDATE")
    if consequence_counts.get("CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE", 0):
        signals.append("CONSTRUCTIVE_VISIBLE_CONSEQUENCE_PRESENT")
    if consequence_counts.get("RISKY_CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE", 0):
        signals.append("RISKY_CONSTRUCTIVE_VISIBLE_CONSEQUENCE_PRESENT")
    if consequence_counts.get("FAILED_VISIBLE_CONSEQUENCE_CANDIDATE", 0):
        signals.append("FAILED_VISIBLE_CONSEQUENCE_PRESENT")
    if consequence_counts.get(UNRESOLVED_CONSEQUENCE, 0):
        signals.append("UNRESOLVED_CONSEQUENCE_CONTEXT_PRESENT")
    if turnover_counts.get("TURNOVER_TO_OPPONENT_SHOT_CANDIDATE", 0):
        signals.append("TURNOVER_TO_OPPONENT_SHOT_TRACE_CANDIDATE")
    if turnover_counts.get("TURNOVER_TO_OPPONENT_BOX_ACCESS_CANDIDATE", 0):
        signals.append("TURNOVER_TO_OPPONENT_BOX_ACCESS_TRACE_CANDIDATE")
    if false_progression_counts.get("FALSE_PROGRESSION_CANDIDATE", 0):
        signals.append("PROGRESSION_TO_HANDOVER_TRACE_CANDIDATE")
    if not signals:
        signals.append("OPEN_VISIBLE_CONTINUITY_CANDIDATE")
    return sorted(set(signals))


def _zone_span(event_records: list[dict[str, Any]]) -> str:
    if not event_records:
        return "UNRESOLVED_ZONE_SPAN_REVIEW_REQUIRED"
    first_rank = event_records[0].get("anchor_zone_rank_candidate")
    last_rank = event_records[-1].get("anchor_zone_rank_candidate")
    if not isinstance(first_rank, int) or not isinstance(last_rank, int):
        return "UNRESOLVED_ZONE_SPAN_REVIEW_REQUIRED"
    if last_rank > first_rank:
        return "NET_FORWARD_ZONE_SPAN_CANDIDATE"
    if last_rank < first_rank:
        return "NET_BACKWARD_ZONE_SPAN_CANDIDATE"
    return "NO_NET_ZONE_SPAN_CANDIDATE"


def _composition_state(event_records: list[dict[str, Any]]) -> str:
    counts = Counter(clean(record.get("consequence_class_candidate")) for record in event_records)
    if counts.get(UNRESOLVED_CONSEQUENCE, 0):
        return "VISIBLE_SEQUENCE_CONTEXT_REVIEW_REQUIRED"
    positive = counts.get("CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE", 0)
    risky = counts.get("RISKY_CONSTRUCTIVE_VISIBLE_CONSEQUENCE_CANDIDATE", 0)
    failed = counts.get("FAILED_VISIBLE_CONSEQUENCE_CANDIDATE", 0)
    if (positive or risky) and failed:
        return "MIXED_VISIBLE_CONSEQUENCE_COMPOSITION_CANDIDATE"
    if positive or risky:
        return "CONSTRUCTIVE_VISIBLE_CONSEQUENCE_COMPOSITION_CANDIDATE"
    if failed:
        return "FAILED_VISIBLE_CONSEQUENCE_COMPOSITION_CANDIDATE"
    return "NEUTRAL_VISIBLE_CONSEQUENCE_COMPOSITION_CANDIDATE"


def _sequence_record(
    binding: str,
    temp: dict[str, Any],
    layer_by_id: dict[str, dict[str, Any]],
    node_by_id: dict[str, dict[str, Any]],
    event_by_node: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    layer_ids = temp["time_layer_ids"]
    layers = [layer_by_id[layer_id] for layer_id in layer_ids]
    primary_ids = [
        node_id
        for layer in layers
        for node_id in layer.get("primary_selected_action_node_ids") or []
    ]
    context_ids = [
        node_id
        for layer in layers
        for node_id in layer.get("team_context_selected_action_node_ids") or []
    ]
    primary_nodes = [node_by_id[node_id] for node_id in primary_ids]
    event_records = [event_by_node[node_id] for node_id in primary_ids]
    start_time = number(layers[0].get("start_candidate"))
    end_time = number(layers[-1].get("start_candidate"))
    sequence_id = "vasc_" + digest(
        binding,
        temp["team_identity_candidate_id"],
        temp["period_candidate"],
        layer_ids,
        primary_ids,
    )[:24]
    family_counts = Counter(
        clean(family)
        for node in primary_nodes
        for family in (node.get("action_family_candidates") or [])
        if clean(family)
    )
    actor_ids = sorted(
        {
            clean(node.get("actor_identity_candidate_id"))
            for node in primary_nodes
            if clean(node.get("actor_identity_candidate_id"))
        }
    )
    consequence_counts = Counter(clean(record.get("consequence_class_candidate")) for record in event_records)
    zone_counts = Counter(clean(record.get("zone_delta_class")) for record in event_records)
    turnover_counts = Counter(
        clean(record.get("turnover_window_class"))
        for record in event_records
        if clean(record.get("turnover_window_class")) != "NOT_APPLICABLE"
    )
    false_progression_counts = Counter(
        clean(record.get("false_progression_candidate"))
        for record in event_records
        if clean(record.get("false_progression_candidate")) != "NOT_APPLICABLE_NO_VISIBLE_ZONE_GAIN"
    )
    cross_team_context_count = sum(
        clean(node_by_id[node_id].get("team_identity_candidate_id"))
        != temp["team_identity_candidate_id"]
        for node_id in context_ids
        if clean(node_by_id[node_id].get("team_identity_candidate_id"))
    )
    admission_status = (
        "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE"
        if len(layer_ids) >= 2
        else "PASS_SINGLE_LAYER_VISIBLE_TRACE_CANDIDATE"
    )
    context_status = (
        "REVIEW_REQUIRED"
        if consequence_counts.get(UNRESOLVED_CONSEQUENCE, 0) or cross_team_context_count
        else "PASS"
    )
    return {
        "visible_action_sequence_candidate_id": sequence_id,
        "match_surface_binding_id": binding,
        "sequence_admission_status": admission_status,
        "sequence_context_status": context_status,
        "team_identity_candidate_id": temp["team_identity_candidate_id"],
        "period_candidate": temp["period_candidate"],
        "start_time_candidate": start_time,
        "end_time_candidate": end_time,
        "duration_between_anchor_times_seconds_candidate": (
            None if start_time is None or end_time is None else round(end_time - start_time, 6)
        ),
        "source_interval_span_not_action_duration": True,
        "start_reason_candidate": temp["start_reason_candidate"],
        "end_reason_candidate": temp["end_reason_candidate"],
        "time_layer_candidate_ids": layer_ids,
        "time_layer_count": len(layer_ids),
        "primary_selected_action_node_ids": primary_ids,
        "primary_node_count": len(primary_ids),
        "team_context_support_node_ids": context_ids,
        "team_context_support_node_count": len(context_ids),
        "cross_team_context_support_review_count": cross_team_context_count,
        "actor_identity_candidate_ids": actor_ids,
        "action_family_counts": dict(sorted(family_counts.items())),
        "consequence_class_candidate_counts": dict(sorted(consequence_counts.items())),
        "zone_delta_class_counts": dict(sorted(zone_counts.items())),
        "turnover_window_class_counts": dict(sorted(turnover_counts.items())),
        "false_progression_candidate_counts": dict(sorted(false_progression_counts.items())),
        "trace_signal_candidates": _trace_signals(primary_nodes, event_records),
        "sequence_zone_span_candidate": _zone_span(event_records),
        "sequence_consequence_composition_candidate": _composition_state(event_records),
        "visible_sequence_candidate_is_sequence_truth": False,
        "visible_sequence_candidate_is_possession_truth": False,
        "single_team_continuity_is_control_truth": False,
        "sequence_duration_is_physical_action_duration": False,
        "event_instance_allowed": False,
        "claim_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
    }
