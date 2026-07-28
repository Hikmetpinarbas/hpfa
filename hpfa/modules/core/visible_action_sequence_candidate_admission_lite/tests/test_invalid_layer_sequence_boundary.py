from __future__ import annotations

import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
SRC = MODULE_ROOT / "src"
sys.path.insert(0, str(SRC))

from sequence_admission import admit_visible_sequences  # noqa: E402

BINDING = "msb_generic_surface"
TEAM = "teamc_a"


def _node(node_id: str, start: float) -> dict:
    return {
        "selected_action_node_id": node_id,
        "team_identity_candidate_id": TEAM,
        "actor_identity_candidate_id": f"actor_{node_id}",
        "action_family_candidates": ["PASS"],
        "terminal_outcome_support_visible": False,
        "period_candidate": "1",
        "start_candidate": str(start),
    }


def _event(node_id: str) -> dict:
    return {
        "anchor_selected_action_node_id": node_id,
        "consequence_class_candidate": "NEUTRAL_VISIBLE_CONSEQUENCE_CANDIDATE",
        "zone_delta_class": "NO_ZONE_CHANGE_CANDIDATE",
        "anchor_zone_rank_candidate": 1,
        "turnover_window_class": "NOT_APPLICABLE",
        "false_progression_candidate": "NOT_APPLICABLE_NO_VISIBLE_ZONE_GAIN",
    }


def _layer(layer_id: str, start: float, node_ids: list[str], teams: list[str]) -> dict:
    return {
        "visible_action_time_layer_candidate_id": layer_id,
        "layer_state": "SINGLE_TEAM_PRIMARY_LAYER",
        "period_candidate": "1",
        "start_candidate": start,
        "primary_team_identity_candidate_ids": teams,
        "primary_selected_action_node_ids": node_ids,
        "team_context_selected_action_node_ids": [],
    }


def _run(invalid_layer: dict):
    nodes = [_node("before", 10), _node("after", 18)]
    layers = [
        _layer("layer_before", 10, ["before"], [TEAM]),
        invalid_layer,
        _layer("layer_after", 18, ["after"], [TEAM]),
    ]
    event_by_node = {node["selected_action_node_id"]: _event(node["selected_action_node_id"]) for node in nodes}
    return admit_visible_sequences(layers, nodes, event_by_node, BINDING, 12.0)


def test_invalid_team_cardinality_breaks_sequence_and_preserves_review_layer():
    sequences, _, _, review_layers, blocks = _run(
        _layer("layer_invalid_team", 14, ["before"], [TEAM, "teamc_b"])
    )

    assert [sequence["time_layer_count"] for sequence in sequences] == [1, 1]
    assert sequences[1]["start_reason_candidate"] == "AFTER_INVALID_PRIMARY_LAYER"
    assert [layer["visible_action_time_layer_candidate_id"] for layer in review_layers] == [
        "layer_invalid_team"
    ]
    assert "single_team_layer_team_count_invalid:layer_invalid_team" in blocks


def test_missing_primary_node_reference_breaks_sequence_and_preserves_review_layer():
    sequences, _, _, review_layers, blocks = _run(
        _layer("layer_missing_node", 14, ["ghost"], [TEAM])
    )

    assert [sequence["time_layer_count"] for sequence in sequences] == [1, 1]
    assert sequences[1]["start_reason_candidate"] == "AFTER_INVALID_PRIMARY_LAYER"
    assert [layer["visible_action_time_layer_candidate_id"] for layer in review_layers] == [
        "layer_missing_node"
    ]
    assert "time_layer_primary_node_reference_missing:layer_missing_node" in blocks
