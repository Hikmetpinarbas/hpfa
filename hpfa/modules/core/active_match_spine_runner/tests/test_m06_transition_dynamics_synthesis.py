from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.rich_multiformat_analysis_lane import (
    _m06_transition_dynamics_synthesis,
)


def test_m06_combines_existing_transition_contexts_without_score() -> None:
    m05 = {
        "profiles": [
            {
                "team_identity_candidate_id": "team_a",
                "visible_loss_context_n": 2,
                "visible_recovery_context_n": 3,
            }
        ]
    }
    counter = {
        "rows": [
            {
                "team_identity_candidate_id": "team_a",
                "next_visible_process_family_candidates": ["POSITIONAL_ATTACK_CANDIDATE"],
                "visible_counter_to_positional_successor_candidate": True,
                "seconds_to_next_visible_process_candidate": 4.0,
            },
            {
                "team_identity_candidate_id": "team_a",
                "next_visible_process_family_candidates": [],
                "visible_counter_to_positional_successor_candidate": False,
                "seconds_to_next_visible_process_candidate": None,
            },
        ]
    }
    mix = {
        "comparisons": [
            {
                "team_identity_candidate_id": "team_a",
                "composition_total_variation_distance_candidate": 0.25,
            }
        ]
    }
    result = _m06_transition_dynamics_synthesis(m05, counter, mix)
    assert result["status"] == "PASS"
    profile = result["profiles"][0]
    assert profile["counterattack_context_n"] == 2
    assert profile["counter_to_positional_successor_candidate_n"] == 1
    assert profile["counterattack_successor_latency_observed_n"] == 1
    assert profile["counterattack_successor_latency_min_candidate"] == 4.0
    assert profile["adjacent_process_mix_comparison_n"] == 1
    assert profile["process_mix_composition_distance_max_candidate"] == 0.25


def test_m06_truth_locks_are_preserved() -> None:
    result = _m06_transition_dynamics_synthesis(
        {"profiles": [{"team_identity_candidate_id": "team_a"}]},
        {"rows": []},
        {"comparisons": []},
    )
    profile = result["profiles"][0]
    assert result["component_views_create_independent_support"] is False
    assert result["transition_phase_truth"] is False
    assert result["momentum_truth"] is False
    assert result["tactical_adaptation_truth"] is False
    assert result["causal_truth"] is False
    assert result["coach_intention_truth"] is False
    assert profile["transition_stabilization_truth"] is False
    assert profile["creates_independent_support"] is False


def test_m06_empty_context_is_not_available() -> None:
    result = _m06_transition_dynamics_synthesis(
        {"profiles": []},
        {"rows": []},
        {"comparisons": []},
    )
    assert result["status"] == "NOT_AVAILABLE"
    assert result["profile_count"] == 0
