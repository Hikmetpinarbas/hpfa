from __future__ import annotations

from copy import deepcopy
from typing import Any

try:
    from .common import clean, number
    from .sequence_engine import admit_visible_sequences as _admit_visible_sequences
    from .sequence_profiles import build_sequence_profiles
except ImportError:
    from common import clean, number
    from sequence_engine import admit_visible_sequences as _admit_visible_sequences
    from sequence_profiles import build_sequence_profiles


def admit_visible_sequences(
    layers: list[dict[str, Any]],
    nodes: list[dict[str, Any]],
    event_by_node: dict[str, dict[str, Any]],
    binding: str,
    max_gap_seconds: float,
):
    """Fail closed before the engine can bridge across structurally invalid layers."""
    known_node_ids = {
        clean(node.get("selected_action_node_id"))
        for node in nodes
        if clean(node.get("selected_action_node_id"))
    }
    prepared_layers: list[dict[str, Any]] = []
    pre_blocks: list[str] = []
    invalid_boundaries: list[tuple[str, float]] = []

    for source_layer in layers:
        layer = deepcopy(source_layer)
        if clean(layer.get("layer_state")) == "SINGLE_TEAM_PRIMARY_LAYER":
            layer_id = clean(layer.get("visible_action_time_layer_candidate_id"))
            teams = layer.get("primary_team_identity_candidate_ids") or []
            primary_ids = [
                clean(node_id)
                for node_id in (layer.get("primary_selected_action_node_ids") or [])
            ]
            reason: str | None = None
            if len(teams) != 1:
                reason = f"single_team_layer_team_count_invalid:{layer_id}"
            elif any(node_id not in known_node_ids for node_id in primary_ids):
                reason = f"time_layer_primary_node_reference_missing:{layer_id}"

            if reason is not None:
                pre_blocks.append(reason)
                layer["layer_state"] = "INVALID_PRIMARY_LAYER_REVIEW_REQUIRED"
                start_time = number(layer.get("start_candidate"))
                period = clean(layer.get("period_candidate"))
                if start_time is not None:
                    invalid_boundaries.append((period, start_time))
        prepared_layers.append(layer)

    sequences, boundaries, assignments, review_layers, engine_blocks = _admit_visible_sequences(
        prepared_layers,
        nodes,
        event_by_node,
        binding,
        max_gap_seconds,
    )

    for period, invalid_time in invalid_boundaries:
        candidates = [
            sequence
            for sequence in sequences
            if clean(sequence.get("period_candidate")) == period
            and number(sequence.get("start_time_candidate")) is not None
            and float(sequence["start_time_candidate"]) > invalid_time
            and sequence.get("start_reason_candidate") == "AFTER_UNKNOWN_PRIMARY_LAYER"
        ]
        if candidates:
            min(candidates, key=lambda item: float(item["start_time_candidate"]))[
                "start_reason_candidate"
            ] = "AFTER_INVALID_PRIMARY_LAYER"

    return (
        sequences,
        boundaries,
        assignments,
        review_layers,
        sorted(set(pre_blocks + engine_blocks)),
    )


__all__ = ["admit_visible_sequences", "build_sequence_profiles"]
