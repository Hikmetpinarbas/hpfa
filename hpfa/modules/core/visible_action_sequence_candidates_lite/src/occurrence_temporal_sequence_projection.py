from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "VISIBLE_SEQUENCE_CANDIDATE_ONLY"
PASS_RECORD_STATUS = "PASS_CANDIDATE_CLASSIFICATION"
SAME_TEAM_CONTINUATION = "SAME_TEAM_CONTINUATION_CANDIDATE"
RECOVERY_CONTINUATION = "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE"
ELIGIBLE_CONTINUATION_CONSEQUENCES = {
    SAME_TEAM_CONTINUATION,
    RECOVERY_CONTINUATION,
}
RECOVERY_OR_INTERCEPTION_FAMILIES = {"RECOVERY", "INTERCEPTION"}
AFTER_CONFIRMED = "AFTER_CONFIRMED"
SINGLE_ACTOR_TOPOLOGY = "SINGLE_ACTOR_ACTION"


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _number(value: Any) -> float | None:
    try:
        return float(_clean(value))
    except (TypeError, ValueError):
        return None


def _number_key(value: Any) -> str:
    number = _number(value)
    return f"{number:.6f}" if number is not None else _clean(value)


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _occurrence_topology(trace_payload: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in trace_payload.get("occurrence_trace_binding_records") or []:
        if not isinstance(row, dict):
            continue
        occurrence_id = _clean(row.get("action_occurrence_candidate_id"))
        topology = _clean(row.get("occurrence_topology"))
        if occurrence_id and topology:
            result[occurrence_id] = topology
    return result


def _trace_map(trace_payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    primary_surface = trace_payload.get("primary_occurrence_trace_candidates")
    trace_rows = (
        primary_surface
        if isinstance(primary_surface, list)
        else trace_payload.get("trackable_action_trace_candidates") or []
    )
    return {
        _clean(row.get("trackable_action_trace_candidate_id")): row
        for row in trace_rows
        if isinstance(row, dict) and _clean(row.get("trackable_action_trace_candidate_id"))
    }


def _confirmed_pairs(trace_payload: dict[str, Any]) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for row in trace_payload.get("temporal_relation_admission_records") or []:
        if not isinstance(row, dict) or _clean(row.get("relation_state")) != AFTER_CONFIRMED:
            continue
        anchor = _clean(row.get("anchor_trackable_action_trace_candidate_id"))
        follow = _clean(row.get("candidate_trackable_action_trace_candidate_id"))
        if anchor and follow:
            result.add((anchor, follow))
    return result


def _trace_occurrences(trace: dict[str, Any]) -> list[str]:
    return sorted({_clean(value) for value in trace.get("supporting_action_occurrence_candidate_ids") or [] if _clean(value)})


def _trace_families(trace: dict[str, Any]) -> set[str]:
    return {
        _clean(value)
        for value in trace.get("action_family_candidates") or []
        if _clean(value)
    }


def build_occurrence_temporal_sequence_projection(
    trace_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
) -> dict[str, Any]:
    """Build conservative two-layer sequence candidates from admitted occurrence-backed continuation evidence.

    This projection never creates possession, canonical-event, causal or tactical truth. A candidate requires:
    - a PASS same-team continuation consequence, including a recovery-origin same-team continuation;
    - an explicit AFTER_CONFIRMED temporal relation for the same trace pair;
    - occurrence backing on both trace endpoints;
    - SINGLE_ACTOR_ACTION topology on both endpoint occurrences;
    - same team and period.

    Recovery-origin continuation is admitted only when the anchor trace itself carries an
    admitted RECOVERY or INTERCEPTION action-family candidate. Same-time occurrence
    multiplicity is preserved as an unordered layer rather than internally ordered.
    """
    trace_by_id = _trace_map(trace_payload)
    topology_by_occurrence = _occurrence_topology(trace_payload)
    confirmed_pairs = _confirmed_pairs(trace_payload)

    binding = _clean(trace_payload.get("match_surface_binding_id"))
    if binding != _clean(consequence_payload.get("match_surface_binding_id")):
        return {
            "status": "FAIL_CLOSED",
            "hard_block_hits": ["match_surface_binding_mismatch"],
            "occurrence_temporal_sequence_candidates": [],
            "occurrence_temporal_sequence_candidate_count": 0,
            "occurrence_temporal_time_layer_candidates": [],
            "occurrence_temporal_time_layer_candidate_count": 0,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    edges: list[dict[str, Any]] = []
    rejected = Counter()
    seen_edge_keys: set[tuple[str, str, str, str, str]] = set()

    for record in consequence_payload.get("trackable_action_consequence_candidates") or []:
        if not isinstance(record, dict):
            continue
        if _clean(record.get("record_status")) != PASS_RECORD_STATUS:
            continue
        continuation_consequence = _clean(record.get("primary_consequence_candidate"))
        if continuation_consequence not in ELIGIBLE_CONTINUATION_CONSEQUENCES:
            continue
        anchor_trace_id = _clean(record.get("anchor_trackable_action_trace_candidate_id"))
        anchor_trace = trace_by_id.get(anchor_trace_id)
        if anchor_trace is None:
            rejected["anchor_trace_missing"] += 1
            continue
        anchor_families = _trace_families(anchor_trace)
        if (
            continuation_consequence == RECOVERY_CONTINUATION
            and not (anchor_families & RECOVERY_OR_INTERCEPTION_FAMILIES)
        ):
            rejected["recovery_continuation_anchor_family_mismatch"] += 1
            continue
        anchor_occurrences = _trace_occurrences(anchor_trace)
        if not anchor_occurrences:
            rejected["anchor_occurrence_missing"] += 1
            continue

        for raw_follow_id in record.get("admitted_after_follow_up_trace_ids") or []:
            follow_trace_id = _clean(raw_follow_id)
            if not follow_trace_id:
                continue
            if (anchor_trace_id, follow_trace_id) not in confirmed_pairs:
                rejected["after_confirmed_relation_missing"] += 1
                continue
            follow_trace = trace_by_id.get(follow_trace_id)
            if follow_trace is None:
                rejected["follow_trace_missing"] += 1
                continue
            follow_occurrences = _trace_occurrences(follow_trace)
            if not follow_occurrences:
                rejected["follow_occurrence_missing"] += 1
                continue

            anchor_team = _clean(anchor_trace.get("team_identity_candidate_id"))
            follow_team = _clean(follow_trace.get("team_identity_candidate_id"))
            anchor_period = _clean(anchor_trace.get("period_candidate"))
            follow_period = _clean(follow_trace.get("period_candidate"))
            if not anchor_team or anchor_team != follow_team:
                rejected["same_team_requirement_failed"] += 1
                continue
            if not anchor_period or anchor_period != follow_period:
                rejected["same_period_requirement_failed"] += 1
                continue
            anchor_start = _number(anchor_trace.get("start_candidate"))
            follow_start = _number(follow_trace.get("start_candidate"))
            if anchor_start is None or follow_start is None or follow_start <= anchor_start:
                rejected["strict_after_start_requirement_failed"] += 1
                continue

            for anchor_occurrence_id in anchor_occurrences:
                for follow_occurrence_id in follow_occurrences:
                    if anchor_occurrence_id == follow_occurrence_id:
                        rejected["same_occurrence_internal_relation"] += 1
                        continue
                    if topology_by_occurrence.get(anchor_occurrence_id) != SINGLE_ACTOR_TOPOLOGY:
                        rejected["anchor_topology_not_single_actor"] += 1
                        continue
                    if topology_by_occurrence.get(follow_occurrence_id) != SINGLE_ACTOR_TOPOLOGY:
                        rejected["follow_topology_not_single_actor"] += 1
                        continue
                    key = (
                        anchor_occurrence_id,
                        follow_occurrence_id,
                        anchor_trace_id,
                        follow_trace_id,
                        continuation_consequence,
                    )
                    if key in seen_edge_keys:
                        continue
                    seen_edge_keys.add(key)
                    edges.append(
                        {
                            "anchor_occurrence_id": anchor_occurrence_id,
                            "follow_occurrence_id": follow_occurrence_id,
                            "anchor_trace_id": anchor_trace_id,
                            "follow_trace_id": follow_trace_id,
                            "team_identity_candidate_id": anchor_team,
                            "period_candidate": anchor_period,
                            "anchor_start_candidate": anchor_start,
                            "follow_start_candidate": follow_start,
                            "anchor_action_family_candidates": sorted(anchor_families),
                            "continuation_consequence_candidate": continuation_consequence,
                            "recovery_origin_continuation_candidate": (
                                continuation_consequence == RECOVERY_CONTINUATION
                            ),
                            "consequence_candidate_id": _clean(record.get("trackable_action_consequence_candidate_id")),
                        }
                    )

    pair_groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        key = (
            edge["team_identity_candidate_id"],
            edge["period_candidate"],
            _number_key(edge["anchor_start_candidate"]),
            _number_key(edge["follow_start_candidate"]),
        )
        pair_groups[key].append(edge)

    layer_members: dict[tuple[str, str, str], dict[str, set[str]]] = defaultdict(lambda: {
        "occurrence_ids": set(),
        "trace_ids": set(),
    })
    for edge in edges:
        source_key = (
            edge["team_identity_candidate_id"],
            edge["period_candidate"],
            _number_key(edge["anchor_start_candidate"]),
        )
        target_key = (
            edge["team_identity_candidate_id"],
            edge["period_candidate"],
            _number_key(edge["follow_start_candidate"]),
        )
        layer_members[source_key]["occurrence_ids"].add(edge["anchor_occurrence_id"])
        layer_members[source_key]["trace_ids"].add(edge["anchor_trace_id"])
        layer_members[target_key]["occurrence_ids"].add(edge["follow_occurrence_id"])
        layer_members[target_key]["trace_ids"].add(edge["follow_trace_id"])

    layers: list[dict[str, Any]] = []
    layer_id_by_key: dict[tuple[str, str, str], str] = {}
    for key, members in sorted(layer_members.items()):
        team, period, start_key = key
        trace_ids = sorted(members["trace_ids"])
        occurrence_ids = sorted(members["occurrence_ids"])
        family_counts = Counter(
            _clean(family)
            for trace_id in trace_ids
            for family in (trace_by_id[trace_id].get("action_family_candidates") or [])
            if _clean(family)
        )
        reflection_context_trace_count = sum(
            bool(trace_by_id[trace_id].get("reflection_context_action_bundle_candidate_ids"))
            for trace_id in trace_ids
        )
        layer_id = "vasl_occ_" + _digest(binding, team, period, start_key, occurrence_ids)[:20]
        layer_id_by_key[key] = layer_id
        layers.append(
            {
                "visible_action_time_layer_candidate_id": layer_id,
                "match_surface_binding_id": binding,
                "period_candidate": period,
                "start_candidate": float(start_key),
                "layer_state": "SINGLE_TEAM_PRIMARY_LAYER",
                "team_identity_candidate_ids": [team],
                "missing_team_identity_trace_ids": [],
                "trackable_action_trace_candidate_ids": trace_ids,
                "supporting_action_occurrence_candidate_ids": occurrence_ids,
                "trace_candidate_count": len(trace_ids),
                "action_family_counts": dict(sorted(family_counts.items())),
                "consequence_candidate_counts": {},
                "consequence_review_trace_count": 0,
                "reflection_context_trace_count": reflection_context_trace_count,
                "terminal_outcome_support_trace_count": 0,
                "same_timestamp_internal_ordering_allowed": False,
                "time_layer_is_event_group_truth": False,
                "time_layer_is_sequence_truth": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
            }
        )

    sequences: list[dict[str, Any]] = []
    for key, group in sorted(pair_groups.items()):
        team, period, anchor_start_key, follow_start_key = key
        source_layer_key = (team, period, anchor_start_key)
        target_layer_key = (team, period, follow_start_key)
        source_layer_id = layer_id_by_key[source_layer_key]
        target_layer_id = layer_id_by_key[target_layer_key]
        occurrence_ids = sorted({
            edge["anchor_occurrence_id"] for edge in group
        } | {
            edge["follow_occurrence_id"] for edge in group
        })
        trace_ids = sorted({
            edge["anchor_trace_id"] for edge in group
        } | {
            edge["follow_trace_id"] for edge in group
        })
        consequence_ids = sorted({edge["consequence_candidate_id"] for edge in group if edge["consequence_candidate_id"]})
        family_counts = Counter(
            _clean(family)
            for trace_id in trace_ids
            for family in (trace_by_id[trace_id].get("action_family_candidates") or [])
            if _clean(family)
        )
        origin_family_counts = Counter(
            family
            for edge in group
            for family in edge.get("anchor_action_family_candidates") or []
        )
        continuation_consequence_counts = Counter(
            edge["continuation_consequence_candidate"] for edge in group
        )
        reflection_context_trace_count = sum(
            bool(trace_by_id[trace_id].get("reflection_context_action_bundle_candidate_ids"))
            for trace_id in trace_ids
        )
        anchor_start = float(anchor_start_key)
        follow_start = float(follow_start_key)
        sequence_id = "vasq_occ_" + _digest(binding, team, period, anchor_start_key, follow_start_key, occurrence_ids)[:20]
        sequences.append(
            {
                "visible_action_sequence_candidate_id": sequence_id,
                "match_surface_binding_id": binding,
                "team_identity_candidate_id": team,
                "period_candidate": period,
                "start_time_candidate": anchor_start,
                "end_time_candidate": follow_start,
                "duration_candidate_seconds": round(follow_start - anchor_start, 6),
                "time_layer_candidate_ids": [source_layer_id, target_layer_id],
                "time_layer_count": 2,
                "trackable_action_trace_candidate_ids": trace_ids,
                "supporting_action_occurrence_candidate_ids": occurrence_ids,
                "supporting_consequence_candidate_ids": consequence_ids,
                "supporting_after_confirmed_edge_count": len(group),
                "trace_candidate_count": len(trace_ids),
                "action_family_counts": dict(sorted(family_counts.items())),
                "origin_action_family_counts": dict(sorted(origin_family_counts.items())),
                "continuation_consequence_candidate_counts": dict(
                    sorted(continuation_consequence_counts.items())
                ),
                "consequence_candidate_counts": dict(
                    sorted(continuation_consequence_counts.items())
                ),
                "recovery_origin_continuation_candidate": any(
                    edge.get("recovery_origin_continuation_candidate") is True for edge in group
                ),
                "consequence_review_trace_count": 0,
                "reflection_context_trace_count": reflection_context_trace_count,
                "sequence_record_status": "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE",
                "start_reason_candidate": "OCCURRENCE_BACKED_AFTER_CONFIRMED_CONTINUATION_START",
                "end_reason_candidate": "AFTER_CONFIRMED_LAYER_PAIR_BOUNDARY",
                "end_boundary_time_candidate": follow_start,
                "next_team_identity_candidate_id": None,
                "visible_sequence_candidate_is_sequence_truth": False,
                "visible_sequence_candidate_is_possession_truth": False,
                "single_team_continuity_is_control_truth": False,
                "recovery_origin_continuation_is_successful_press_truth": False,
                "sequence_duration_is_physical_action_duration": False,
                "same_timestamp_internal_ordering_allowed": False,
                "source_row_order_is_temporal_truth": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
                "claim_ceiling": CLAIM_CEILING,
            }
        )

    return {
        "status": "PASS" if sequences else "REVIEW_REQUIRED",
        "hard_block_hits": [],
        "review_hits": [] if sequences else ["no_occurrence_backed_after_confirmed_same_team_continuation"],
        "occurrence_temporal_time_layer_candidates": layers,
        "occurrence_temporal_time_layer_candidate_count": len(layers),
        "occurrence_temporal_sequence_candidates": sequences,
        "occurrence_temporal_sequence_candidate_count": len(sequences),
        "eligible_occurrence_after_confirmed_edge_count": len(edges),
        "recovery_origin_continuation_edge_count": sum(
            1 for edge in edges if edge.get("recovery_origin_continuation_candidate") is True
        ),
        "rejected_edge_reason_counts": dict(sorted(rejected.items())),
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "sequence_truth": False,
        "possession_truth": False,
        "causal_truth": False,
        "tactical_truth": False,
        "successful_press_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
