from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.anchor_centered_sequence_branch_map_projection import (
    build_anchor_centered_sequence_branch_maps,
)


def _layer(layer_id: str, team: str, period: str, time: float, occurrence_ids: list[str]) -> dict:
    return {
        "visible_action_time_layer_candidate_id": layer_id,
        "team_identity_candidate_ids": [team],
        "period_candidate": period,
        "start_candidate": time,
        "action_family_counts": {"PASS": len(occurrence_ids)},
        "supporting_action_occurrence_candidate_ids": occurrence_ids,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "time_layer_is_sequence_truth": False,
        "canonical_event_count": "UNKNOWN",
    }


def _sequence(sequence_id: str, team: str, period: str, anchor: str, successor: str, consequence_id: str) -> dict:
    return {
        "visible_action_sequence_candidate_id": sequence_id,
        "team_identity_candidate_id": team,
        "period_candidate": period,
        "time_layer_candidate_ids": [anchor, successor],
        "supporting_consequence_candidate_ids": [consequence_id],
        "consequence_candidate_counts": {"SAME_TEAM_CONTINUATION_CANDIDATE": 1},
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "visible_sequence_candidate_is_sequence_truth": False,
        "visible_sequence_candidate_is_possession_truth": False,
        "canonical_event_count": "UNKNOWN",
    }


def _payload(layers: list[dict], sequences: list[dict]) -> dict:
    return {
        "status": "PASS",
        "primary_sequence_projection_mode": "OCCURRENCE_TEMPORAL_PRIMARY",
        "occurrence_temporal_primary_inventory_admitted": True,
        "visible_action_time_layer_candidates": layers,
        "visible_action_sequence_candidates": sequences,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "sequence_truth": False,
        "possession_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_shared_anchor_three_successors_yields_one_branch_map_not_three_recurrences() -> None:
    team = "team_a"
    anchor = _layer("layer_anchor", team, "2", 2862.64, ["occ_a", "occ_b"])
    successors = [
        _layer("layer_1", team, "2", 2869.64, ["occ_c"]),
        _layer("layer_2", team, "2", 2872.64, ["occ_d"]),
        _layer("layer_3", team, "2", 2873.64, ["occ_e"]),
    ]
    sequences = [
        _sequence("seq_1", team, "2", "layer_anchor", "layer_1", "con_1"),
        _sequence("seq_2", team, "2", "layer_anchor", "layer_2", "con_2"),
        _sequence("seq_3", team, "2", "layer_anchor", "layer_3", "con_3"),
    ]

    result = build_anchor_centered_sequence_branch_maps(_payload([anchor] + successors, sequences))

    assert result["status"] == "PASS"
    assert result["anchor_centered_sequence_branch_map_count"] == 1
    assert result["total_visible_branch_count"] == 3
    branch_map = result["anchor_centered_sequence_branch_maps"][0]
    assert branch_map["anchor_time_layer_ref"] == "layer_anchor"
    assert branch_map["predecessor_branch_count"] == 0
    assert branch_map["successor_branch_count"] == 3
    assert branch_map["total_visible_branch_count"] == 3
    assert branch_map["branch_count_is_recurrence_count"] is False
    assert {row["neighbor_time_layer_ref"] for row in branch_map["branch_records"]} == {
        "layer_1",
        "layer_2",
        "layer_3",
    }
    assert all(row["branch_support_count_is_recurrence_count"] is False for row in branch_map["branch_records"])
    assert branch_map["branch_map_is_tactical_plan_truth"] is False
    assert branch_map["branch_map_is_causal_truth"] is False
    assert branch_map["canonical_event_count"] == "UNKNOWN"
    assert branch_map["true_action_count"] == "UNKNOWN"


def test_single_visible_route_does_not_create_branch_map() -> None:
    team = "team_a"
    layers = [
        _layer("a", team, "1", 1.0, ["occ_1"]),
        _layer("b", team, "1", 2.0, ["occ_2"]),
    ]
    result = build_anchor_centered_sequence_branch_maps(
        _payload(layers, [_sequence("seq", team, "1", "a", "b", "con")])
    )
    assert result["anchor_centered_sequence_branch_map_count"] == 0
    assert result["total_visible_branch_count"] == 0


def test_same_anchor_identifier_across_teams_is_not_cross_team_branch_fusion() -> None:
    layers = [
        _layer("shared_anchor", "team_a", "1", 10.0, ["occ_a"]),
        _layer("a_next", "team_a", "1", 11.0, ["occ_b"]),
        _layer("b_next", "team_b", "1", 11.0, ["occ_c"]),
    ]
    sequences = [
        _sequence("seq_a", "team_a", "1", "shared_anchor", "a_next", "con_a"),
        _sequence("seq_b", "team_b", "1", "shared_anchor", "b_next", "con_b"),
    ]
    result = build_anchor_centered_sequence_branch_maps(_payload(layers, sequences))
    assert result["anchor_centered_sequence_branch_map_count"] == 0


def test_upstream_sequence_truth_promotion_fails_closed() -> None:
    team = "team_a"
    payload = _payload(
        [
            _layer("a", team, "1", 1.0, ["occ_1"]),
            _layer("b", team, "1", 2.0, ["occ_2"]),
            _layer("c", team, "1", 3.0, ["occ_3"]),
        ],
        [
            _sequence("seq_1", team, "1", "a", "b", "con_1"),
            _sequence("seq_2", team, "1", "a", "c", "con_2"),
        ],
    )
    payload["sequence_truth"] = True
    result = build_anchor_centered_sequence_branch_maps(payload)
    assert result["status"] == "FAIL_CLOSED"
    assert result["anchor_centered_sequence_branch_map_count"] == 0
    assert "upstream_truth_promotion_breached" in result["hard_block_hits"]


def test_no_sample_match_identity_leak() -> None:
    source = Path(
        "hpfa/modules/core/visible_action_sequence_candidates_lite/src/anchor_centered_sequence_branch_map_projection.py"
    ).read_text(encoding="utf-8")
    for token in ("Sporting", "Galatasaray", "Fenerbahce", "Roma", "10.09.2026"):
        assert token not in source
