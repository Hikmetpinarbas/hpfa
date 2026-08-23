from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "visible_action_sequence_candidates_lite_v1"
TRACE_MODULE_ID = "trackable_action_trace_candidates_lite_v1"
CONSEQUENCE_MODULE_ID = "trackable_action_consequence_candidates_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
MAX_GAP_SECONDS = 12.0
CLAIM_CEILING = "VISIBLE_SEQUENCE_CANDIDATE_ONLY"
ALLOWED_TRACE_ROLES = {"PLAYER_SURFACE_CANDIDATE", "GOALKEEPER_SURFACE_CANDIDATE"}

OUTPUTS = {
    "json": "visible_action_sequence_candidates_lite_v1.json",
    "summary": "visible_action_sequence_candidates_lite_v1.txt",
    "analyst": "visible_action_sequence_candidates_analyst_audit_v1.txt",
}


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


def _period_sort_key(value: Any) -> tuple[int, Any]:
    text = _clean(value)
    try:
        return (0, int(float(text)))
    except (TypeError, ValueError):
        return (1, text)


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _validate_trace(trace: dict[str, Any], index: int, binding: str) -> list[str]:
    blocks: list[str] = []
    trace_id = _clean(trace.get("trackable_action_trace_candidate_id"))
    if not trace_id:
        blocks.append(f"trace_id_missing:{index}")
    if trace.get("match_surface_binding_id") != binding:
        blocks.append(f"trace_binding_mismatch:{index}")
    if trace.get("source_role") not in ALLOWED_TRACE_ROLES:
        blocks.append(f"trace_source_role_rejected:{index}")
    if not _clean(trace.get("team_identity_candidate_id")):
        blocks.append(f"trace_team_identity_candidate_missing:{index}")
    if not _clean(trace.get("actor_identity_candidate_id")):
        blocks.append(f"trace_actor_identity_candidate_missing:{index}")
    if _number(trace.get("start_candidate")) is None:
        blocks.append(f"trace_start_candidate_invalid:{index}")
    if trace.get("trackable_action_candidate_is_event_truth") is True:
        blocks.append(f"trace_event_truth_claimed:{index}")
    if trace.get("physical_action_identity_truth") is True:
        blocks.append(f"trace_physical_action_truth_claimed:{index}")
    if trace.get("sequence_link_allowed") is True:
        blocks.append(f"trace_sequence_link_already_admitted:{index}")
    if trace.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
        blocks.append(f"trace_canonical_event_count_claimed:{index}")
    return blocks


def _validate_consequence(record: dict[str, Any], index: int, binding: str) -> list[str]:
    blocks: list[str] = []
    consequence_id = _clean(record.get("trackable_action_consequence_candidate_id"))
    anchor_id = _clean(record.get("anchor_trackable_action_trace_candidate_id"))
    if not consequence_id:
        blocks.append(f"consequence_id_missing:{index}")
    if not anchor_id:
        blocks.append(f"consequence_anchor_trace_id_missing:{index}")
    if record.get("match_surface_binding_id") != binding:
        blocks.append(f"consequence_binding_mismatch:{index}")
    if record.get("record_status") not in {"PASS_CANDIDATE_CLASSIFICATION", "REVIEW_REQUIRED"}:
        blocks.append(f"consequence_status_rejected:{index}")
    for field in (
        "same_time_link_allowed",
        "negative_time_link_allowed",
        "cross_period_link_allowed",
        "window_is_sequence_truth",
        "continuation_is_possession_truth",
        "consequence_candidate_is_causal_truth",
        "event_instance_allowed",
        "validated_event_identity",
    ):
        if record.get(field) is True:
            blocks.append(f"consequence_claim_boundary_breached:{field}:{index}")
    if record.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
        blocks.append(f"consequence_canonical_event_count_claimed:{index}")
    return blocks


def _build_time_layers(
    traces: list[dict[str, Any]],
    consequence_by_trace: dict[str, dict[str, Any]],
    binding: str,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for trace in traces:
        grouped[(_clean(trace.get("period_candidate")), _number_key(trace.get("start_candidate")))].append(trace)

    layers: list[dict[str, Any]] = []
    for (period, start_key), members in grouped.items():
        members = sorted(members, key=lambda row: _clean(row.get("trackable_action_trace_candidate_id")))
        teams = sorted({_clean(row.get("team_identity_candidate_id")) for row in members if _clean(row.get("team_identity_candidate_id"))})
        missing_team_ids = [
            _clean(row.get("trackable_action_trace_candidate_id"))
            for row in members
            if not _clean(row.get("team_identity_candidate_id"))
        ]
        if missing_team_ids:
            state = "UNKNOWN_PRIMARY_LAYER_REVIEW_REQUIRED"
        elif len(teams) == 1:
            state = "SINGLE_TEAM_PRIMARY_LAYER"
        elif len(teams) > 1:
            state = "MIXED_TEAM_PRIMARY_LAYER_REVIEW_REQUIRED"
        else:
            state = "UNKNOWN_PRIMARY_LAYER_REVIEW_REQUIRED"

        trace_ids = [_clean(row.get("trackable_action_trace_candidate_id")) for row in members]
        consequence_rows = [consequence_by_trace[trace_id] for trace_id in trace_ids]
        action_family_counts = Counter(
            _clean(family)
            for row in members
            for family in (row.get("action_family_candidates") or [])
            if _clean(family)
        )
        consequence_counts = Counter(
            _clean(row.get("primary_consequence_candidate")) for row in consequence_rows
        )
        reflection_context_trace_count = sum(bool(row.get("reflection_context_action_bundle_candidate_ids")) for row in members)
        terminal_support_count = sum(bool(row.get("terminal_outcome_support_visible")) for row in consequence_rows)
        consequence_review_count = sum(row.get("record_status") == "REVIEW_REQUIRED" for row in consequence_rows)
        layer_id = "vasl_" + _digest(binding, period, start_key, trace_ids)[:24]
        layers.append(
            {
                "visible_action_time_layer_candidate_id": layer_id,
                "match_surface_binding_id": binding,
                "period_candidate": period,
                "start_candidate": float(start_key),
                "layer_state": state,
                "team_identity_candidate_ids": teams,
                "missing_team_identity_trace_ids": missing_team_ids,
                "trackable_action_trace_candidate_ids": trace_ids,
                "trace_candidate_count": len(trace_ids),
                "action_family_counts": dict(sorted(action_family_counts.items())),
                "consequence_candidate_counts": dict(sorted(consequence_counts.items())),
                "consequence_review_trace_count": consequence_review_count,
                "reflection_context_trace_count": reflection_context_trace_count,
                "terminal_outcome_support_trace_count": terminal_support_count,
                "same_timestamp_internal_ordering_allowed": False,
                "time_layer_is_event_group_truth": False,
                "time_layer_is_sequence_truth": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
            }
        )
    return sorted(
        layers,
        key=lambda row: (
            _period_sort_key(row.get("period_candidate")),
            row.get("start_candidate"),
            row.get("visible_action_time_layer_candidate_id"),
        ),
    )


def _build_sequence_record(
    binding: str,
    temp: dict[str, Any],
    layer_by_id: dict[str, dict[str, Any]],
    trace_by_id: dict[str, dict[str, Any]],
    consequence_by_trace: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    layer_ids = list(temp["time_layer_candidate_ids"])
    layers = [layer_by_id[layer_id] for layer_id in layer_ids]
    trace_ids = [trace_id for layer in layers for trace_id in layer.get("trackable_action_trace_candidate_ids") or []]
    traces = [trace_by_id[trace_id] for trace_id in trace_ids]
    consequences = [consequence_by_trace[trace_id] for trace_id in trace_ids]
    family_counts = Counter(
        _clean(family)
        for trace in traces
        for family in (trace.get("action_family_candidates") or [])
        if _clean(family)
    )
    consequence_counts = Counter(_clean(row.get("primary_consequence_candidate")) for row in consequences)
    consequence_review_count = sum(row.get("record_status") == "REVIEW_REQUIRED" for row in consequences)
    reflection_context_trace_count = sum(bool(trace.get("reflection_context_action_bundle_candidate_ids")) for trace in traces)
    start_time = layers[0]["start_candidate"]
    end_time = layers[-1]["start_candidate"]
    status = (
        "REVIEW_REQUIRED_CONTEXT"
        if consequence_review_count
        else (
            "PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE"
            if len(layer_ids) > 1
            else "PASS_SINGLE_LAYER_VISIBLE_TRACE_CANDIDATE"
        )
    )
    sequence_id = "vasq_" + _digest(binding, temp["team_identity_candidate_id"], temp["period_candidate"], layer_ids)[:24]
    return {
        "visible_action_sequence_candidate_id": sequence_id,
        "match_surface_binding_id": binding,
        "team_identity_candidate_id": temp["team_identity_candidate_id"],
        "period_candidate": temp["period_candidate"],
        "start_time_candidate": start_time,
        "end_time_candidate": end_time,
        "duration_candidate_seconds": round(end_time - start_time, 6),
        "time_layer_candidate_ids": layer_ids,
        "time_layer_count": len(layer_ids),
        "trackable_action_trace_candidate_ids": trace_ids,
        "trace_candidate_count": len(trace_ids),
        "action_family_counts": dict(sorted(family_counts.items())),
        "consequence_candidate_counts": dict(sorted(consequence_counts.items())),
        "consequence_review_trace_count": consequence_review_count,
        "reflection_context_trace_count": reflection_context_trace_count,
        "sequence_record_status": status,
        "start_reason_candidate": temp["start_reason_candidate"],
        "end_reason_candidate": temp["end_reason_candidate"],
        "end_boundary_time_candidate": temp.get("end_boundary_time_candidate"),
        "next_team_identity_candidate_id": temp.get("next_team_identity_candidate_id"),
        "visible_sequence_candidate_is_sequence_truth": False,
        "visible_sequence_candidate_is_possession_truth": False,
        "single_team_continuity_is_control_truth": False,
        "sequence_duration_is_physical_action_duration": False,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "claim_ceiling": CLAIM_CEILING,
    }


def build_visible_action_sequence_candidates(
    trace_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if trace_payload.get("module_id") != TRACE_MODULE_ID:
        blocks.append("trace_input_module_id_mismatch")
    if consequence_payload.get("module_id") != CONSEQUENCE_MODULE_ID:
        blocks.append("consequence_input_module_id_mismatch")
    for prefix, payload in (("trace", trace_payload), ("consequence", consequence_payload)):
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{prefix}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{prefix}_production_release_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{prefix}_hard_blocks_present")

    trace_binding = _clean(trace_payload.get("match_surface_binding_id"))
    consequence_binding = _clean(consequence_payload.get("match_surface_binding_id"))
    if not trace_binding or trace_binding != consequence_binding:
        blocks.append("match_surface_binding_mismatch")

    traces = trace_payload.get("trackable_action_trace_candidates") or []
    consequences = consequence_payload.get("trackable_action_consequence_candidates") or []
    if not isinstance(traces, list) or not traces:
        blocks.append("trackable_action_trace_candidates_empty_or_invalid")
        traces = []
    if not isinstance(consequences, list) or not consequences:
        blocks.append("trackable_action_consequence_candidates_empty_or_invalid")
        consequences = []
    if trace_payload.get("trackable_action_trace_candidate_count") != len(traces):
        blocks.append("trace_candidate_count_mismatch")
    if consequence_payload.get("trackable_action_consequence_candidate_count") != len(consequences):
        blocks.append("consequence_candidate_count_mismatch")

    trace_by_id: dict[str, dict[str, Any]] = {}
    for index, trace in enumerate(traces):
        if not isinstance(trace, dict):
            blocks.append(f"trace_record_invalid:{index}")
            continue
        blocks.extend(_validate_trace(trace, index, trace_binding))
        trace_id = _clean(trace.get("trackable_action_trace_candidate_id"))
        if trace_id in trace_by_id:
            blocks.append(f"duplicate_trace_candidate_id:{trace_id}")
        trace_by_id[trace_id] = trace

    consequence_by_trace: dict[str, dict[str, Any]] = {}
    consequence_ids: set[str] = set()
    for index, record in enumerate(consequences):
        if not isinstance(record, dict):
            blocks.append(f"consequence_record_invalid:{index}")
            continue
        blocks.extend(_validate_consequence(record, index, trace_binding))
        consequence_id = _clean(record.get("trackable_action_consequence_candidate_id"))
        anchor_id = _clean(record.get("anchor_trackable_action_trace_candidate_id"))
        if consequence_id in consequence_ids:
            blocks.append(f"duplicate_consequence_candidate_id:{consequence_id}")
        consequence_ids.add(consequence_id)
        if anchor_id in consequence_by_trace:
            blocks.append(f"duplicate_consequence_anchor_trace_id:{anchor_id}")
        consequence_by_trace[anchor_id] = record
    if set(consequence_by_trace) != set(trace_by_id):
        blocks.append("trace_consequence_anchor_coverage_mismatch")

    layers: list[dict[str, Any]] = []
    sequences: list[dict[str, Any]] = []
    review_layers: list[dict[str, Any]] = []
    assignments: list[dict[str, Any]] = []
    boundary_records: list[dict[str, Any]] = []

    if not blocks:
        layers = _build_time_layers(traces, consequence_by_trace, trace_binding)
        layer_by_id = {row["visible_action_time_layer_candidate_id"]: row for row in layers}
        temp_sequences: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        pending_start_reason = "PERIOD_START"
        previous_period: str | None = None

        def close_current(reason: str, boundary_time: float | None = None, next_team: str | None = None) -> None:
            nonlocal current
            if current is None:
                return
            current["end_reason_candidate"] = reason
            current["end_boundary_time_candidate"] = boundary_time
            current["next_team_identity_candidate_id"] = next_team
            temp_sequences.append(current)
            current = None

        for layer in layers:
            period = _clean(layer.get("period_candidate"))
            start_time = _number(layer.get("start_candidate"))
            layer_id = _clean(layer.get("visible_action_time_layer_candidate_id"))
            state = _clean(layer.get("layer_state"))
            if start_time is None:
                blocks.append(f"time_layer_start_invalid:{layer_id}")
                close_current("INVALID_TIME_LAYER_BOUNDARY")
                review_layers.append(layer)
                pending_start_reason = "AFTER_INVALID_TIME_LAYER"
                previous_period = period
                continue
            if previous_period is not None and period != previous_period:
                close_current("PERIOD_END", start_time)
                pending_start_reason = "PERIOD_START"

            if state == "MIXED_TEAM_PRIMARY_LAYER_REVIEW_REQUIRED":
                close_current("MIXED_TEAM_PRIMARY_LAYER_BOUNDARY", start_time)
                review_layers.append(layer)
                pending_start_reason = "AFTER_MIXED_TEAM_PRIMARY_LAYER"
                previous_period = period
                continue
            if state != "SINGLE_TEAM_PRIMARY_LAYER":
                close_current("UNKNOWN_PRIMARY_LAYER_BOUNDARY", start_time)
                review_layers.append(layer)
                pending_start_reason = "AFTER_UNKNOWN_PRIMARY_LAYER"
                previous_period = period
                continue

            teams = layer.get("team_identity_candidate_ids") or []
            if len(teams) != 1:
                blocks.append(f"single_team_layer_team_count_invalid:{layer_id}")
                review_layers.append(layer)
                previous_period = period
                continue
            team = _clean(teams[0])
            families = set((layer.get("action_family_counts") or {}).keys())

            if current is not None:
                gap = start_time - float(current["last_time_candidate"])
                if gap <= 0:
                    blocks.append(f"non_positive_inter_layer_time:{layer_id}")
                elif "RESTART" in families:
                    close_current("RESTART_PRIMARY_LAYER_BOUNDARY", start_time, team)
                    pending_start_reason = "RESTART_PRIMARY_LAYER_START"
                elif gap > MAX_GAP_SECONDS:
                    close_current("TIME_GAP_BOUNDARY", start_time, team)
                    pending_start_reason = "AFTER_TIME_GAP"
                elif team != current["team_identity_candidate_id"]:
                    previous_team = current["team_identity_candidate_id"]
                    close_current("TEAM_HANDOVER_BOUNDARY", start_time, team)
                    pending_start_reason = "AFTER_TEAM_HANDOVER"
                    boundary_records.append(
                        {
                            "visible_sequence_boundary_candidate_id": "vasb_"
                            + _digest(trace_binding, period, start_time, previous_team, team)[:24],
                            "boundary_type": "VISIBLE_TEAM_HANDOVER_CANDIDATE",
                            "period_candidate": period,
                            "boundary_time_candidate": start_time,
                            "from_team_identity_candidate_id": previous_team,
                            "to_team_identity_candidate_id": team,
                            "boundary_is_possession_change_truth": False,
                            "boundary_is_sequence_truth": False,
                            "canonical_event_count": CANONICAL_EVENT_COUNT,
                        }
                    )

            if current is None:
                current = {
                    "team_identity_candidate_id": team,
                    "period_candidate": period,
                    "start_reason_candidate": pending_start_reason,
                    "time_layer_candidate_ids": [],
                    "last_time_candidate": start_time,
                }
            current["time_layer_candidate_ids"].append(layer_id)
            current["last_time_candidate"] = start_time

            if int(layer.get("terminal_outcome_support_trace_count") or 0) > 0:
                close_current("TERMINAL_OUTCOME_SUPPORT_BOUNDARY", start_time)
                pending_start_reason = "AFTER_TERMINAL_OUTCOME_SUPPORT"
            else:
                pending_start_reason = "CONTINUATION"
            previous_period = period

        close_current("PERIOD_END")

        sequences = [
            _build_sequence_record(trace_binding, temp, layer_by_id, trace_by_id, consequence_by_trace)
            for temp in temp_sequences
        ]
        sequences.sort(
            key=lambda row: (
                _period_sort_key(row.get("period_candidate")),
                row.get("start_time_candidate"),
                row.get("visible_action_sequence_candidate_id"),
            )
        )

        assigned_trace_ids: set[str] = set()
        for sequence in sequences:
            seq_id = _clean(sequence.get("visible_action_sequence_candidate_id"))
            assignment_status = (
                "REVIEW_REQUIRED_CONTEXT"
                if sequence.get("sequence_record_status") == "REVIEW_REQUIRED_CONTEXT"
                else "PASS"
            )
            for trace_id in sequence.get("trackable_action_trace_candidate_ids") or []:
                if trace_id in assigned_trace_ids:
                    blocks.append(f"trace_assignment_duplicate:{trace_id}")
                assignments.append(
                    {
                        "trackable_action_trace_candidate_id": trace_id,
                        "assignment_type": "PRIMARY_SEQUENCE_MEMBER",
                        "target_candidate_id": seq_id,
                        "assignment_status": assignment_status,
                    }
                )
                assigned_trace_ids.add(trace_id)
        for layer in review_layers:
            layer_id = _clean(layer.get("visible_action_time_layer_candidate_id"))
            for trace_id in layer.get("trackable_action_trace_candidate_ids") or []:
                if trace_id in assigned_trace_ids:
                    blocks.append(f"trace_assignment_duplicate:{trace_id}")
                assignments.append(
                    {
                        "trackable_action_trace_candidate_id": trace_id,
                        "assignment_type": "REVIEW_LAYER_MEMBER",
                        "target_candidate_id": layer_id,
                        "assignment_status": "REVIEW_REQUIRED",
                    }
                )
                assigned_trace_ids.add(trace_id)
        if assigned_trace_ids != set(trace_by_id):
            blocks.append("trace_assignment_coverage_mismatch")

    layer_state_counts = Counter(row.get("layer_state") for row in layers)
    sequence_status_counts = Counter(row.get("sequence_record_status") for row in sequences)
    boundary_reason_counts = Counter(row.get("end_reason_candidate") for row in sequences)
    assignment_type_counts = Counter(row.get("assignment_type") for row in assignments)
    consequence_class_counts = Counter(
        consequence
        for sequence in sequences
        for consequence, count in (sequence.get("consequence_candidate_counts") or {}).items()
        for _ in range(int(count))
    )

    trace_status = str(trace_payload.get("module_status") or trace_payload.get("status") or "UNKNOWN")
    consequence_status = str(consequence_payload.get("module_status") or consequence_payload.get("status") or "UNKNOWN")
    for prefix, status in (("trace", trace_status), ("consequence", consequence_status)):
        if status == "FAIL_CLOSED":
            blocks.append(f"{prefix}_input_fail_closed")
        elif status == "REVIEW_REQUIRED":
            reviews.append(f"{prefix}_upstream_review_required")
        elif status != "PASS":
            reviews.append(f"{prefix}_upstream_status_review:{status}")
    if review_layers:
        reviews.append("mixed_or_unknown_time_layers_preserved")
    if sequence_status_counts.get("REVIEW_REQUIRED_CONTEXT", 0):
        reviews.append("sequence_consequence_context_review_required")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": trace_binding or None,
        "visible_action_time_layer_candidates": layers,
        "visible_action_sequence_candidates": sequences,
        "visible_sequence_boundary_candidates": boundary_records,
        "trace_assignments": assignments,
        "review_time_layer_candidates": review_layers,
        "source_trackable_action_trace_candidate_count": len(traces),
        "source_trackable_action_consequence_candidate_count": len(consequences),
        "visible_action_time_layer_candidate_count": len(layers),
        "single_team_primary_layer_count": layer_state_counts.get("SINGLE_TEAM_PRIMARY_LAYER", 0),
        "mixed_team_primary_layer_review_required_count": layer_state_counts.get("MIXED_TEAM_PRIMARY_LAYER_REVIEW_REQUIRED", 0),
        "unknown_primary_layer_review_required_count": layer_state_counts.get("UNKNOWN_PRIMARY_LAYER_REVIEW_REQUIRED", 0),
        "visible_action_sequence_candidate_count": len(sequences),
        "pass_multi_layer_visible_sequence_candidate_count": sequence_status_counts.get("PASS_MULTI_LAYER_VISIBLE_SEQUENCE_CANDIDATE", 0),
        "pass_single_layer_visible_trace_candidate_count": sequence_status_counts.get("PASS_SINGLE_LAYER_VISIBLE_TRACE_CANDIDATE", 0),
        "review_required_sequence_context_count": sequence_status_counts.get("REVIEW_REQUIRED_CONTEXT", 0),
        "review_time_layer_count": len(review_layers),
        "primary_sequence_member_trace_count": assignment_type_counts.get("PRIMARY_SEQUENCE_MEMBER", 0),
        "review_layer_member_trace_count": assignment_type_counts.get("REVIEW_LAYER_MEMBER", 0),
        "trace_assignment_count": len(assignments),
        "trace_assignment_complete": len(assignments) == len(traces) and not any(hit.startswith("trace_assignment_") for hit in blocks),
        "layer_state_counts": dict(sorted(layer_state_counts.items())),
        "sequence_status_counts": dict(sorted(sequence_status_counts.items())),
        "boundary_reason_counts": dict(sorted(boundary_reason_counts.items())),
        "sequence_consequence_candidate_counts": dict(sorted(consequence_class_counts.items())),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "max_inter_layer_gap_seconds": MAX_GAP_SECONDS,
        "strict_positive_inter_layer_time_required": True,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "visible_sequence_candidate_is_sequence_truth": False,
        "visible_sequence_candidate_is_possession_truth": False,
        "single_team_continuity_is_control_truth": False,
        "restart_trace_is_set_piece_design_truth": False,
        "shot_chain_is_chance_quality_truth": False,
        "sequence_duration_is_physical_action_duration": False,
        "consequence_context_is_causal_truth": False,
        "event_instance_count": 0,
        "claim_allowed": False,
        "phase_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def _summary(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA VISIBLE ACTION SEQUENCE CANDIDATES LITE V1",
        f"status={payload.get('status')}",
        f"source_trackable_action_trace_candidate_count={payload.get('source_trackable_action_trace_candidate_count')}",
        f"visible_action_time_layer_candidate_count={payload.get('visible_action_time_layer_candidate_count')}",
        f"single_team_primary_layer_count={payload.get('single_team_primary_layer_count')}",
        f"mixed_team_primary_layer_review_required_count={payload.get('mixed_team_primary_layer_review_required_count')}",
        f"visible_action_sequence_candidate_count={payload.get('visible_action_sequence_candidate_count')}",
        f"pass_multi_layer_visible_sequence_candidate_count={payload.get('pass_multi_layer_visible_sequence_candidate_count')}",
        f"pass_single_layer_visible_trace_candidate_count={payload.get('pass_single_layer_visible_trace_candidate_count')}",
        f"review_required_sequence_context_count={payload.get('review_required_sequence_context_count')}",
        f"primary_sequence_member_trace_count={payload.get('primary_sequence_member_trace_count')}",
        f"review_layer_member_trace_count={payload.get('review_layer_member_trace_count')}",
        f"boundary_reason_counts={payload.get('boundary_reason_counts')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        f"review_hits={payload.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def _analyst(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA ANALYST AUDIT — VISIBLE ACTION SEQUENCE CANDIDATES",
        f"Visible time-layer candidates: {payload.get('visible_action_time_layer_candidate_count', 0)}",
        f"Single-team layers: {payload.get('single_team_primary_layer_count', 0)}",
        f"Mixed-team review layers: {payload.get('mixed_team_primary_layer_review_required_count', 0)}",
        f"Visible sequence candidates: {payload.get('visible_action_sequence_candidate_count', 0)}",
        f"Multi-layer candidates: {payload.get('pass_multi_layer_visible_sequence_candidate_count', 0)}",
        f"Single-layer traces: {payload.get('pass_single_layer_visible_trace_candidate_count', 0)}",
        f"Sequence-context review candidates: {payload.get('review_required_sequence_context_count', 0)}",
        "Analyst-safe meaning: actor-bearing trace candidates are grouped into same-team, strictly later visible time layers with explicit gap, restart, team-handover, period and ambiguity boundaries.",
        "Same-timestamp traces are never internally ordered. Mixed-team same-time layers remain review-required.",
        "These are candidate sequence traces only; they do not establish possession, control, causal, tactical, physical-action or canonical-event truth.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out: str | Path) -> dict[str, Path]:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    paths = {key: output / name for key, name in OUTPUTS.items()}
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["summary"].write_text(_summary(payload), encoding="utf-8")
    paths["analyst"].write_text(_analyst(payload), encoding="utf-8")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", required=True)
    parser.add_argument("--consequence", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    trace_payload = json.loads(Path(args.trace).read_text(encoding="utf-8"))
    consequence_payload = json.loads(Path(args.consequence).read_text(encoding="utf-8"))
    payload = build_visible_action_sequence_candidates(trace_payload, consequence_payload)
    write_outputs(payload, args.out)
    print(json.dumps({
        "status": payload.get("status"),
        "visible_action_time_layer_candidate_count": payload.get("visible_action_time_layer_candidate_count"),
        "visible_action_sequence_candidate_count": payload.get("visible_action_sequence_candidate_count"),
        "review_required_sequence_context_count": payload.get("review_required_sequence_context_count"),
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
