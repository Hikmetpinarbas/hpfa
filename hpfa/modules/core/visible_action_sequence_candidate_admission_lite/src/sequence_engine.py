from __future__ import annotations

from typing import Any

try:
    from .common import CANONICAL_EVENT_COUNT, MAX_GAP_SECONDS, clean, digest, number, period_sort_key
    from .sequence_record import _sequence_record
except ImportError:
    from common import CANONICAL_EVENT_COUNT, MAX_GAP_SECONDS, clean, digest, number, period_sort_key
    from sequence_record import _sequence_record


def admit_visible_sequences(
    layers: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    event_by_node: dict[str, dict[str, Any]],
    binding: str,
    max_gap_seconds: float = MAX_GAP_SECONDS,
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[str],
]:
    blocks: list[str] = []
    node_by_id = {clean(node.get("selected_action_node_id")): node for node in nodes}
    layer_by_id = {
        clean(layer.get("visible_action_time_layer_candidate_id")): layer for layer in layers
    }
    temp_sequences: list[dict[str, Any]] = []
    review_layers: list[dict[str, Any]] = []
    context_only_layers: list[dict[str, Any]] = []
    boundary_specs: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    pending_start_reason = "PERIOD_START"
    previous_period: str | None = None

    def close_current(
        reason: str,
        boundary_time: float | None = None,
        next_team: str | None = None,
    ) -> None:
        nonlocal current
        if current is None:
            return
        current["end_reason_candidate"] = reason
        current["end_boundary_time_candidate"] = boundary_time
        current["next_team_identity_candidate_id"] = next_team
        temp_sequences.append(current)
        current = None

    for layer in layers:
        period = clean(layer.get("period_candidate"))
        start_time = number(layer.get("start_candidate"))
        state = clean(layer.get("layer_state"))
        layer_id = clean(layer.get("visible_action_time_layer_candidate_id"))
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
        if state == "TEAM_CONTEXT_ONLY_LAYER":
            close_current("TEAM_CONTEXT_ONLY_LAYER_BOUNDARY", start_time)
            context_only_layers.append(layer)
            pending_start_reason = "AFTER_TEAM_CONTEXT_ONLY_LAYER"
            previous_period = period
            continue
        if state != "SINGLE_TEAM_PRIMARY_LAYER":
            close_current("UNKNOWN_PRIMARY_LAYER_BOUNDARY", start_time)
            review_layers.append(layer)
            pending_start_reason = "AFTER_UNKNOWN_PRIMARY_LAYER"
            previous_period = period
            continue

        teams = layer.get("primary_team_identity_candidate_ids") or []
        if len(teams) != 1:
            blocks.append(f"single_team_layer_team_count_invalid:{layer_id}")
            previous_period = period
            continue
        team = clean(teams[0])
        primary_ids = layer.get("primary_selected_action_node_ids") or []
        primary_nodes = [node_by_id.get(clean(node_id)) for node_id in primary_ids]
        if any(node is None for node in primary_nodes):
            blocks.append(f"time_layer_primary_node_reference_missing:{layer_id}")
            previous_period = period
            continue
        primary_nodes = [node for node in primary_nodes if node is not None]
        families = {
            clean(family)
            for node in primary_nodes
            for family in (node.get("action_family_candidates") or [])
            if clean(family)
        }

        if current is not None:
            gap = start_time - float(current["last_time_candidate"])
            if gap <= 0:
                blocks.append(f"non_positive_inter_layer_time:{layer_id}")
            elif "RESTART" in families:
                close_current("RESTART_PRIMARY_LAYER_BOUNDARY", start_time, team)
                pending_start_reason = "RESTART_PRIMARY_LAYER_START"
            elif gap > max_gap_seconds:
                close_current("TIME_GAP_BOUNDARY", start_time, team)
                pending_start_reason = "AFTER_TIME_GAP"
            elif team != current["team_identity_candidate_id"]:
                previous_team = current["team_identity_candidate_id"]
                close_current("TEAM_HANDOVER_BOUNDARY", start_time, team)
                boundary_specs.append(
                    {
                        "boundary_type": "VISIBLE_TEAM_HANDOVER_CANDIDATE",
                        "period_candidate": period,
                        "boundary_time_candidate": start_time,
                        "from_team_identity_candidate_id": previous_team,
                        "to_team_identity_candidate_id": team,
                    }
                )
                pending_start_reason = "AFTER_TEAM_HANDOVER"

        if current is None:
            current = {
                "team_identity_candidate_id": team,
                "period_candidate": period,
                "start_reason_candidate": pending_start_reason,
                "time_layer_ids": [],
                "last_time_candidate": start_time,
            }
        current["time_layer_ids"].append(layer_id)
        current["last_time_candidate"] = start_time

        terminal = any(bool(node.get("terminal_outcome_support_visible")) for node in primary_nodes)
        if terminal:
            close_current("TERMINAL_OUTCOME_SUPPORT_BOUNDARY", start_time)
            pending_start_reason = "AFTER_TERMINAL_OUTCOME_SUPPORT"
        else:
            pending_start_reason = "CONTINUATION"
        previous_period = period

    close_current("PERIOD_END")

    sequences = [
        _sequence_record(binding, temp, layer_by_id, node_by_id, event_by_node)
        for temp in temp_sequences
    ]
    sequences.sort(
        key=lambda record: (
            period_sort_key(record.get("period_candidate")),
            record.get("start_time_candidate"),
            record.get("visible_action_sequence_candidate_id"),
        )
    )

    seq_by_layer: dict[str, str] = {}
    for sequence in sequences:
        for layer_id in sequence.get("time_layer_candidate_ids") or []:
            if layer_id in seq_by_layer:
                blocks.append(f"time_layer_sequence_reuse:{layer_id}")
            seq_by_layer[layer_id] = clean(sequence.get("visible_action_sequence_candidate_id"))

    boundary_records: list[dict[str, Any]] = []
    for spec in boundary_specs:
        before = [
            sequence
            for sequence in sequences
            if sequence.get("period_candidate") == spec["period_candidate"]
            and sequence.get("end_time_candidate") is not None
            and sequence.get("end_time_candidate") < spec["boundary_time_candidate"]
            and sequence.get("team_identity_candidate_id")
            == spec["from_team_identity_candidate_id"]
        ]
        after = [
            sequence
            for sequence in sequences
            if sequence.get("period_candidate") == spec["period_candidate"]
            and sequence.get("start_time_candidate") == spec["boundary_time_candidate"]
            and sequence.get("team_identity_candidate_id")
            == spec["to_team_identity_candidate_id"]
        ]
        from_id = (
            max(before, key=lambda item: item.get("end_time_candidate"))[
                "visible_action_sequence_candidate_id"
            ]
            if before
            else None
        )
        to_id = after[0]["visible_action_sequence_candidate_id"] if after else None
        boundary_records.append(
            {
                "visible_sequence_boundary_candidate_id": "vasb_"
                + digest(binding, spec, from_id, to_id)[:24],
                **spec,
                "from_visible_action_sequence_candidate_id": from_id,
                "to_visible_action_sequence_candidate_id": to_id,
                "boundary_is_possession_change_truth": False,
                "boundary_is_sequence_truth": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
            }
        )

    assignments: list[dict[str, Any]] = []
    assigned_nodes: set[str] = set()

    for sequence in sequences:
        sequence_id = clean(sequence.get("visible_action_sequence_candidate_id"))
        sequence_team = clean(sequence.get("team_identity_candidate_id"))
        for node_id in sequence.get("primary_selected_action_node_ids") or []:
            node_id = clean(node_id)
            assignments.append(
                {
                    "selected_action_node_id": node_id,
                    "assignment_type": "PRIMARY_SEQUENCE_MEMBER",
                    "target_candidate_id": sequence_id,
                    "assignment_status": "PASS",
                }
            )
            assigned_nodes.add(node_id)
        for node_id in sequence.get("team_context_support_node_ids") or []:
            node_id = clean(node_id)
            node_team = clean(node_by_id[node_id].get("team_identity_candidate_id"))
            status = (
                "PASS_SAME_TEAM_CONTEXT_SUPPORT"
                if node_team == sequence_team
                else "REVIEW_REQUIRED_CROSS_TEAM_CONTEXT_SUPPORT"
            )
            assignments.append(
                {
                    "selected_action_node_id": node_id,
                    "assignment_type": "TEAM_CONTEXT_SUPPORT_ATTACHED_TO_SEQUENCE",
                    "target_candidate_id": sequence_id,
                    "assignment_status": status,
                }
            )
            assigned_nodes.add(node_id)

    for layer in review_layers:
        layer_id = clean(layer.get("visible_action_time_layer_candidate_id"))
        for node_id in (
            (layer.get("primary_selected_action_node_ids") or [])
            + (layer.get("team_context_selected_action_node_ids") or [])
        ):
            node_id = clean(node_id)
            assignments.append(
                {
                    "selected_action_node_id": node_id,
                    "assignment_type": "REVIEW_LAYER_MEMBER",
                    "target_candidate_id": layer_id,
                    "assignment_status": "REVIEW_REQUIRED",
                }
            )
            assigned_nodes.add(node_id)

    for layer in context_only_layers:
        layer_id = clean(layer.get("visible_action_time_layer_candidate_id"))
        for node_id in layer.get("team_context_selected_action_node_ids") or []:
            node_id = clean(node_id)
            assignments.append(
                {
                    "selected_action_node_id": node_id,
                    "assignment_type": "TEAM_CONTEXT_ONLY_LAYER_SUPPORT",
                    "target_candidate_id": layer_id,
                    "assignment_status": "REVIEW_REQUIRED_CONTEXT_ONLY",
                }
            )
            assigned_nodes.add(node_id)

    all_node_ids = {clean(node.get("selected_action_node_id")) for node in nodes}
    assignment_ids = [clean(item.get("selected_action_node_id")) for item in assignments]
    if len(assignment_ids) != len(set(assignment_ids)):
        blocks.append("node_assignment_duplicate")
    if assigned_nodes != all_node_ids:
        blocks.append("node_assignment_coverage_mismatch")

    return (
        sequences,
        boundary_records,
        assignments,
        sorted(
            review_layers + context_only_layers,
            key=lambda layer: (
                period_sort_key(layer.get("period_candidate")),
                number(layer.get("start_candidate")) is None,
                number(layer.get("start_candidate"))
                if number(layer.get("start_candidate")) is not None
                else 0.0,
                layer.get("visible_action_time_layer_candidate_id"),
            ),
        ),
        sorted(set(blocks)),
    )
