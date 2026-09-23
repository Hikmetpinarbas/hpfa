from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.rich_multiformat_analysis_lane import (
    _m05_loss_recovery_dynamics_synthesis,
)


def test_m05_separates_loss_and_recovery_denominators() -> None:
    loss = {
        "binding_state": "LOSS_TO_FIRST_OPPONENT_FOLLOWUP_PROCESS_CONTEXT",
        "rows": [
            {
                "anchor_team_identity_candidate_ids": ["team_a"],
                "next_opponent_process_family_candidates": ["COUNTERATTACK_CANDIDATE"],
                "next_opponent_process_binding_state": "SINGLE_OPPONENT_VISIBLE_PROCESS_FAMILY_MATCH",
            }
        ],
    }
    recovery = {
        "binding_state": "RECOVERY_FIRST_FOLLOWUP_TO_VISIBLE_PROCESS_CONTEXT",
        "rows": [
            {
                "team_identity_candidate_ids": ["team_a"],
                "next_visible_process_family_candidates": ["POSITIONAL_ATTACK_CANDIDATE"],
                "next_process_binding_state": "SINGLE_VISIBLE_PROCESS_FAMILY_MATCH",
            },
            {
                "team_identity_candidate_ids": [],
                "next_visible_process_family_candidates": [],
                "next_process_binding_state": "NO_VISIBLE_PROCESS_INTERVAL_MATCH",
            },
        ],
    }
    result = _m05_loss_recovery_dynamics_synthesis(loss, recovery)
    assert result["status"] == "PASS"
    assert result["unresolved_recovery_team_row_n"] == 1
    profile = result["profiles"][0]
    assert profile["visible_loss_context_n"] == 1
    assert profile["visible_recovery_context_n"] == 1
    assert profile["loss_denominator"] != profile["recovery_denominator"]
    assert profile["loss_next_opponent_process_family_counts"] == {
        "COUNTERATTACK_CANDIDATE": 1
    }
    assert profile["recovery_next_own_process_family_counts"] == {
        "POSITIONAL_ATTACK_CANDIDATE": 1
    }


def test_m05_does_not_promote_loss_recovery_to_success_failure_or_causality() -> None:
    result = _m05_loss_recovery_dynamics_synthesis(
        {
            "binding_state": "LOSS_TO_FIRST_OPPONENT_FOLLOWUP_PROCESS_CONTEXT",
            "rows": [{"anchor_team_identity_candidate_ids": ["team_a"]}],
        },
        {
            "binding_state": "RECOVERY_FIRST_FOLLOWUP_TO_VISIBLE_PROCESS_CONTEXT",
            "rows": [{"team_identity_candidate_ids": ["team_a"]}],
        },
    )
    profile = result["profiles"][0]
    assert result["loss_is_failure_truth"] is False
    assert result["recovery_is_success_truth"] is False
    assert result["transition_truth"] is False
    assert result["causal_truth"] is False
    assert profile["loss_is_defensive_transition_truth"] is False
    assert profile["recovery_is_attacking_transition_truth"] is False
    assert profile["successor_process_is_causal_consequence_truth"] is False
    assert profile["creates_independent_support"] is False


def test_m05_empty_context_is_not_available() -> None:
    result = _m05_loss_recovery_dynamics_synthesis({"rows": []}, {"rows": []})
    assert result["status"] == "NOT_AVAILABLE"
    assert result["profile_count"] == 0
