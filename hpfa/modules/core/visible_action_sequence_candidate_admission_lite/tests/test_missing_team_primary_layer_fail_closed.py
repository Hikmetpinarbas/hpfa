from __future__ import annotations

import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
SRC = MODULE_ROOT / "src"
sys.path.insert(0, str(SRC))

from visible_action_sequence_candidate_admission import (  # noqa: E402
    build_visible_action_sequence_candidate_admission,
)

BINDING = "msb_generic_surface"
TEAM_A = "teamc_a"
ACTOR_A = "actorc_a"
ACTOR_B = "actorc_b"


def node(node_id: str, *, team: str | None, actor: str, start: float = 10.0) -> dict:
    return {
        "selected_action_node_id": node_id,
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "actor_identity_applicability": "APPLICABLE_BOUND_CANDIDATE",
        "period_candidate": "1",
        "start_candidate": str(start),
        "end_candidate": str(start + 12.0),
        "pos_x_candidate": "10",
        "pos_y_candidate": "20",
        "action_family_candidates": ["PASS"],
        "terminal_outcome_support_visible": False,
        "selected_surface_is_canonical_event": False,
        "event_instance_allowed": False,
        "canonical_event_count": "UNKNOWN",
    }


def payloads(nodes: list[dict]) -> tuple[dict, dict]:
    action_records = [
        {
            "selected_action_consequence_candidate_id": f"sacc_{item['selected_action_node_id']}",
            "anchor_selected_action_node_id": item["selected_action_node_id"],
            "match_surface_binding_id": BINDING,
            "primary_consequence_candidate": "SAME_TEAM_CONTINUATION_CANDIDATE",
            "canonical_event_count": "UNKNOWN",
        }
        for item in nodes
    ]
    event_records = [
        {
            "selected_event_consequence_candidate_id": f"secs_{item['selected_action_node_id']}",
            "source_selected_action_consequence_candidate_id": f"sacc_{item['selected_action_node_id']}",
            "anchor_selected_action_node_id": item["selected_action_node_id"],
            "match_surface_binding_id": BINDING,
            "team_identity_candidate_id": item["team_identity_candidate_id"],
            "actor_identity_candidate_id": item["actor_identity_candidate_id"],
            "source_role": item["source_role"],
            "period_candidate": item["period_candidate"],
            "anchor_action_family_candidates": item["action_family_candidates"],
            "anchor_zone_candidate": "MIDDLE_THIRD_CANDIDATE",
            "anchor_zone_rank_candidate": 1,
            "zone_delta_class": "NO_ZONE_CHANGE_CANDIDATE",
            "turnover_window_class": "NOT_APPLICABLE",
            "false_progression_candidate": "NOT_APPLICABLE_NO_VISIBLE_ZONE_GAIN",
            "consequence_class_candidate": "NEUTRAL_VISIBLE_CONSEQUENCE_CANDIDATE",
            "canonical_event_count": "UNKNOWN",
        }
        for item in nodes
    ]
    return (
        {
            "module_id": "selected_action_consequence_surface_lite_v1",
            "status": "PASS",
            "module_status": "PASS",
            "match_surface_binding_id": BINDING,
            "selected_action_nodes": nodes,
            "selected_action_node_count": len(nodes),
            "selected_action_consequence_candidates": action_records,
            "selected_action_consequence_candidate_count": len(action_records),
            "hard_block_hits": [],
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        },
        {
            "module_id": "selected_event_consequence_surface_lite_v1",
            "status": "PASS",
            "module_status": "PASS",
            "match_surface_binding_id": BINDING,
            "source_module_id": "selected_action_consequence_surface_lite_v1",
            "selected_event_consequence_candidates": event_records,
            "selected_event_consequence_candidate_count": len(event_records),
            "hard_block_hits": [],
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        },
    )


def build(nodes: list[dict]) -> dict:
    return build_visible_action_sequence_candidate_admission(*payloads(nodes))


def test_known_and_missing_team_primary_nodes_are_review_only():
    rows = [
        node("known", team=TEAM_A, actor=ACTOR_A),
        node("missing", team=None, actor=ACTOR_B),
    ]
    result = build(rows)
    assert result["visible_action_sequence_candidate_count"] == 0
    assert result["time_layer_state_counts"]["UNKNOWN_PRIMARY_LAYER_REVIEW_REQUIRED"] == 1
    layer = result["review_or_context_only_time_layers"][0]
    assert layer["primary_team_identity_candidate_ids"] == [TEAM_A]
    assert layer["missing_primary_team_identity_node_ids"] == ["missing"]
    assert layer["missing_primary_team_identity_count"] == 1
    assert {item["assignment_type"] for item in result["node_assignment_records"]} == {
        "REVIEW_LAYER_MEMBER"
    }


def test_single_missing_team_primary_node_is_review_only():
    result = build([node("missing", team=None, actor=ACTOR_A)])
    assert result["visible_action_sequence_candidate_count"] == 0
    layer = result["review_or_context_only_time_layers"][0]
    assert layer["layer_state"] == "UNKNOWN_PRIMARY_LAYER_REVIEW_REQUIRED"
    assert layer["primary_team_identity_candidate_ids"] == []
    assert layer["missing_primary_team_identity_count"] == 1


def test_missing_team_layer_is_order_invariant():
    known = node("known", team=TEAM_A, actor=ACTOR_A)
    missing = node("missing", team=None, actor=ACTOR_B)
    forward = build([known, missing])
    reverse = build([missing, known])
    forward_layer = forward["review_or_context_only_time_layers"][0]
    reverse_layer = reverse["review_or_context_only_time_layers"][0]
    assert forward_layer["layer_state"] == reverse_layer["layer_state"]
    assert forward_layer["missing_primary_team_identity_node_ids"] == reverse_layer[
        "missing_primary_team_identity_node_ids"
    ]
    assert forward["node_assignment_type_counts"] == reverse["node_assignment_type_counts"]


def test_missing_team_layer_assigns_each_node_once_and_preserves_claim_guards():
    rows = [
        node("known", team=TEAM_A, actor=ACTOR_A),
        node("missing", team=None, actor=ACTOR_B),
    ]
    result = build(rows)
    assignments = result["node_assignment_records"]
    assignment_ids = [item["selected_action_node_id"] for item in assignments]
    assert sorted(assignment_ids) == ["known", "missing"]
    assert len(assignment_ids) == len(set(assignment_ids)) == len(rows)
    assert all(item["assignment_status"] == "REVIEW_REQUIRED" for item in assignments)
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["sequence_truth"] is False
    assert result["possession_truth"] is False
    assert result["tactical_truth"] is False
    assert result["production_release"] is False
