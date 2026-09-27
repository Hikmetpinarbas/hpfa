from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.rich_multiformat_analysis_lane import (
    _m09_opponent_interaction_synthesis,
)


def test_m09_groups_six_phase_and_reciprocal_context_by_team() -> None:
    c03 = {
        "reciprocal_team_process_comparisons": [
            {
                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                "team_a_identity_candidate_id": "team_a",
                "team_b_identity_candidate_id": "team_b",
                "team_a_profile": {"eligible_process_n": 5},
                "team_b_profile": {"eligible_process_n": 4},
                "comparison_basis": "SAME_MATCH_SAME_PROCESS_FAMILY_DESCRIPTIVE_PROFILE",
            }
        ],
        "six_phase_team_matrix": [
            {
                "team_identity_candidate_id": "team_a",
                "opponent_team_identity_candidate_id": "team_b",
                "canonical_phase_slot": "ESTABLISHED_ATTACK",
                "perspective": "ATTACK",
                "observation_state": "VISIBLE_PROCESS_PROFILE_AVAILABLE",
            },
            {
                "team_identity_candidate_id": "team_a",
                "opponent_team_identity_candidate_id": "team_b",
                "canonical_phase_slot": "ESTABLISHED_DEFENCE",
                "perspective": "DEFENCE",
                "observation_state": "UNOBSERVABLE_WITH_CURRENT_DATA",
            },
            {
                "team_identity_candidate_id": "team_b",
                "opponent_team_identity_candidate_id": "team_a",
                "canonical_phase_slot": "ESTABLISHED_ATTACK",
                "perspective": "ATTACK",
                "observation_state": "VISIBLE_PROCESS_PROFILE_AVAILABLE",
            },
        ],
    }
    result = _m09_opponent_interaction_synthesis(c03)
    assert result["status"] == "PASS"
    assert result["profile_count"] == 2
    team_a = next(row for row in result["profiles"] if row["team_identity_candidate_id"] == "team_a")
    assert team_a["six_phase_direction_n"] == 2
    assert team_a["visible_six_phase_direction_n"] == 1
    assert team_a["unresolved_six_phase_direction_n"] == 1
    assert team_a["reciprocal_same_family_comparison_n"] == 1


def test_m09_preserves_opponent_interaction_truth_locks() -> None:
    c03 = {
        "reciprocal_team_process_comparisons": [],
        "six_phase_team_matrix": [
            {
                "team_identity_candidate_id": "team_a",
                "perspective": "DEFENCE",
                "observation_state": "VISIBLE_PROCESS_PROFILE_AVAILABLE",
            }
        ],
    }
    result = _m09_opponent_interaction_synthesis(c03)
    profile = result["profiles"][0]
    assert result["pool_views_create_independent_evidence"] is False
    assert result["opponent_response_truth"] is False
    assert result["defensive_success_truth"] is False
    assert result["tactical_superiority_truth"] is False
    assert result["causal_truth"] is False
    assert profile["opponent_exposure_is_defensive_success_truth"] is False
    assert profile["opponent_non_shot_is_prevention_truth"] is False
    assert profile["opponent_visible_loss_is_forced_turnover_truth"] is False
    assert profile["reciprocal_difference_is_opponent_response_truth"] is False
    assert profile["creates_independent_support"] is False


def test_m09_empty_context_is_not_available() -> None:
    result = _m09_opponent_interaction_synthesis(
        {"reciprocal_team_process_comparisons": [], "six_phase_team_matrix": []}
    )
    assert result["status"] == "NOT_AVAILABLE"
    assert result["profile_count"] == 0
