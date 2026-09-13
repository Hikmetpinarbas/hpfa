from __future__ import annotations

from pathlib import Path

from hpfa.modules.core.visible_action_sequence_candidates_lite.src.anchor_centered_sequence_branch_map_projection import (
    build_anchor_centered_sequence_branch_maps,
)


def _layer(
    layer_id: str,
    team: str,
    period: str,
    time: float,
    occurrence_ids: list[str],
    *,
    action_family: str = "PASS",
) -> dict:
    return {
        "visible_action_time_layer_candidate_id": layer_id,
        "team_identity_candidate_ids": [team],
        "period_candidate": period,
        "start_candidate": time,
        "action_family_counts": {action_family: len(occurrence_ids)},
        "supporting_action_occurrence_candidate_ids": occurrence_ids,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "time_layer_is_sequence_truth": False,
        "canonical_event_count": "UNKNOWN",
    }


def _sequence(
    sequence_id: str,
    team: str,
    period: str,
    anchor: str,
    successor: str,
    consequence_id: str,
    *,
    consequence: str = "SAME_TEAM_CONTINUATION_CANDIDATE",
) -> dict:
    return {
        "visible_action_sequence_candidate_id": sequence_id,
        "team_identity_candidate_id": team,
        "period_candidate": period,
        "time_layer_candidate_ids": [anchor, successor],
        "supporting_consequence_candidate_ids": [consequence_id],
        "consequence_candidate_counts": {consequence: 1},
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


def test_shared_anchor_three_successors_freezes_one_comparable_set_then_one_branch_map() -> None:
    team = "team_a"
    anchor = _layer("layer_anchor", team, "2", 2862.64, ["occ_a", "occ_b"])
    successors = [
        _layer("layer_1", team, "2", 2869.64, ["occ_c"], action_family="PASS"),
        _layer("layer_2", team, "2", 2872.64, ["occ_d"], action_family="CARRY"),
        _layer("layer_3", team, "2", 2873.64, ["occ_e"], action_family="DRIBBLE"),
    ]
    sequences = [
        _sequence("seq_1", team, "2", "layer_anchor", "layer_1", "con_1"),
        _sequence("seq_2", team, "2", "layer_anchor", "layer_2", "con_2"),
        _sequence("seq_3", team, "2", "layer_anchor", "layer_3", "con_3"),
    ]

    result = build_anchor_centered_sequence_branch_maps(_payload([anchor] + successors, sequences))

    assert result["status"] == "PASS"
    assert result["branch_comparison_question_contract_status"] == "PASS"
    assert result["branch_comparable_set_count"] == 1
    comparable_set = result["branch_comparable_sets"][0]
    assert comparable_set["eligible_case_count"] == 3
    assert comparable_set["eligible_denominator_frozen_before_outcome_attachment"] is True
    assert comparable_set["outcome_used_in_eligibility"] is False
    assert comparable_set["post_anchor_branch_structure_used_in_eligibility"] is False
    assert comparable_set["dependency_burden"] == "SHARED_VISIBLE_ANCHOR_DEPENDENCY_DOMINATED"
    assert comparable_set["dependency_independence_proven"] is False
    assert comparable_set["statistical_independence_proven"] is False

    assert result["anchor_centered_sequence_branch_map_count"] == 1
    assert result["total_visible_branch_count"] == 3
    assert result["comparable_set_frozen_before_branch_map"] is True
    assert result["eligible_denominator_frozen_before_branch_consequence_attachment"] is True
    assert result["outcome_used_in_comparison_admission"] is False
    assert result["outcome_used_in_branch_partition"] is False
    branch_map = result["anchor_centered_sequence_branch_maps"][0]
    assert branch_map["comparable_set_id"] == comparable_set["comparable_set_id"]
    assert branch_map["anchor_time_layer_ref"] == "layer_anchor"
    assert branch_map["shared_prefix_support_n"] == 3
    assert branch_map["eligible_denominator_n"] == 3
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
    assert all(row["consequence_attached_after_comparable_set_freeze"] is True for row in branch_map["branch_records"])
    assert branch_map["branch_map_is_tactical_plan_truth"] is False
    assert branch_map["branch_map_is_causal_truth"] is False
    assert branch_map["canonical_event_count"] == "UNKNOWN"
    assert branch_map["true_action_count"] == "UNKNOWN"


def test_post_anchor_branch_structure_can_vary_without_becoming_admission_key() -> None:
    team = "team_a"
    layers = [
        _layer("anchor", team, "1", 10.0, ["occ_anchor"]),
        _layer("pass_next", team, "1", 11.0, ["occ_pass"], action_family="PASS"),
        _layer("carry_next", team, "1", 12.0, ["occ_carry"], action_family="CARRY"),
    ]
    sequences = [
        _sequence("pass_branch", team, "1", "anchor", "pass_next", "con_pass"),
        _sequence("carry_branch", team, "1", "anchor", "carry_next", "con_carry"),
    ]

    result = build_anchor_centered_sequence_branch_maps(_payload(layers, sequences))

    assert result["branch_comparable_set_count"] == 1
    assert result["branch_comparable_sets"][0]["eligible_case_count"] == 2
    assert result["anchor_centered_sequence_branch_map_count"] == 1
    assert result["anchor_centered_sequence_branch_maps"][0]["successor_branch_count"] == 2
    assert result["post_anchor_branch_structure_used_in_comparison_admission"] is False


def test_consequence_changes_do_not_change_comparable_set_or_branch_map_identity() -> None:
    team = "team_a"
    layers = [
        _layer("anchor", team, "1", 10.0, ["occ_anchor"]),
        _layer("left", team, "1", 11.0, ["occ_left"]),
        _layer("right", team, "1", 12.0, ["occ_right"]),
    ]
    first_sequences = [
        _sequence("seq_left", team, "1", "anchor", "left", "con_left", consequence="SUCCESS_CANDIDATE"),
        _sequence("seq_right", team, "1", "anchor", "right", "con_right", consequence="FAILURE_CANDIDATE"),
    ]
    second_sequences = [
        _sequence("seq_left", team, "1", "anchor", "left", "con_left", consequence="FAILURE_CANDIDATE"),
        _sequence("seq_right", team, "1", "anchor", "right", "con_right", consequence="SUCCESS_CANDIDATE"),
    ]

    first = build_anchor_centered_sequence_branch_maps(_payload(layers, first_sequences))
    second = build_anchor_centered_sequence_branch_maps(_payload(layers, second_sequences))

    assert first["branch_comparable_sets"][0]["comparable_set_id"] == second["branch_comparable_sets"][0]["comparable_set_id"]
    assert first["anchor_centered_sequence_branch_maps"][0]["branch_map_id"] == second["anchor_centered_sequence_branch_maps"][0]["branch_map_id"]
    assert first["anchor_centered_sequence_branch_maps"][0]["branch_partition"] == second["anchor_centered_sequence_branch_maps"][0]["branch_partition"]
    assert first["anchor_centered_sequence_branch_maps"][0]["branch_consequence_profiles"] != second["anchor_centered_sequence_branch_maps"][0]["branch_consequence_profiles"]


def test_single_visible_route_does_not_create_comparable_set_or_branch_map() -> None:
    team = "team_a"
    layers = [
        _layer("a", team, "1", 1.0, ["occ_1"]),
        _layer("b", team, "1", 2.0, ["occ_2"]),
    ]
    result = build_anchor_centered_sequence_branch_maps(
        _payload(layers, [_sequence("seq", team, "1", "a", "b", "con")])
    )
    assert result["branch_comparable_set_count"] == 0
    assert result["anchor_centered_sequence_branch_map_count"] == 0
    assert result["total_visible_branch_count"] == 0


def test_two_cases_same_successor_freeze_denominator_but_do_not_fabricate_divergence() -> None:
    team = "team_a"
    layers = [
        _layer("a", team, "1", 1.0, ["occ_1"]),
        _layer("b", team, "1", 2.0, ["occ_2"]),
    ]
    sequences = [
        _sequence("seq_1", team, "1", "a", "b", "con_1"),
        _sequence("seq_2", team, "1", "a", "b", "con_2"),
    ]
    result = build_anchor_centered_sequence_branch_maps(_payload(layers, sequences))

    assert result["branch_comparable_set_count"] == 1
    assert result["branch_comparable_sets"][0]["eligible_case_count"] == 2
    assert result["anchor_centered_sequence_branch_map_count"] == 0


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
    assert result["branch_comparable_set_count"] == 0
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
    assert result["branch_comparable_set_count"] == 0
    assert result["anchor_centered_sequence_branch_map_count"] == 0
    assert "upstream_truth_promotion_breached" in result["hard_block_hits"]


def test_no_sample_match_identity_leak() -> None:
    source = Path(
        "hpfa/modules/core/visible_action_sequence_candidates_lite/src/anchor_centered_sequence_branch_map_projection.py"
    ).read_text(encoding="utf-8")
    for token in ("Sporting", "Galatasaray", "Fenerbahce", "Roma", "10.09.2026"):
        assert token not in source
