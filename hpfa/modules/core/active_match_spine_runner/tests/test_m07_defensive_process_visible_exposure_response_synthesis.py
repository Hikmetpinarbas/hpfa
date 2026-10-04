from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.rich_multiformat_analysis_lane import (
    _m07_defensive_process_visible_exposure_response_synthesis,
)


def test_m07_exposes_visible_defensive_context_and_keeps_p05_gap_explicit() -> None:
    m09 = {
        "profiles": [
            {
                "team_identity_candidate_id": "team_a",
                "opponent_exposure_direction_rows": [
                    {
                        "opponent_team_identity_candidate_id": "team_b",
                        "observation_state": "VISIBLE_PROCESS_PROFILE_AVAILABLE",
                        "eligible_process_n": 5,
                        "shot_ending_process_n": 2,
                        "visible_loss_process_n": 1,
                        "visible_recovery_process_n": 0,
                    },
                    {
                        "opponent_team_identity_candidate_id": "team_b",
                        "observation_state": "UNOBSERVABLE_WITH_CURRENT_DATA",
                    },
                ],
            }
        ]
    }
    m05 = {"profiles": [{"team_identity_candidate_id": "team_a", "visible_recovery_context_n": 3}]}
    m02 = {"profiles": [{"team_identity_candidate_id": "team_b", "eligible_process_signature_n": 7}]}

    result = _m07_defensive_process_visible_exposure_response_synthesis(m09, m05, m02)
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["p05_organized_defence_owner_status"] == "GAP"
    profile = result["profiles"][0]
    assert profile["opponent_team_identity_candidate_id"] == "team_b"
    assert profile["defensive_exposure_direction_n"] == 2
    assert profile["visible_defensive_exposure_direction_n"] == 1
    assert profile["unresolved_defensive_exposure_direction_n"] == 1
    assert profile["opponent_visible_process_n"] == 5
    assert profile["opponent_shot_ending_process_n"] == 2
    assert profile["own_loss_recovery_dynamics"]["visible_recovery_context_n"] == 3
    assert profile["opponent_progression_territory_context"]["eligible_process_signature_n"] == 7


def test_m07_never_promotes_exposure_to_defensive_success_or_tracking_truth() -> None:
    result = _m07_defensive_process_visible_exposure_response_synthesis(
        {
            "profiles": [
                {
                    "team_identity_candidate_id": "team_a",
                    "opponent_exposure_direction_rows": [],
                }
            ]
        },
        {"profiles": []},
        {"profiles": []},
    )
    profile = result["profiles"][0]
    assert result["organized_defence_truth"] is False
    assert result["team_shape_truth"] is False
    assert result["compactness_truth"] is False
    assert result["pressure_geometry_truth"] is False
    assert result["causal_truth"] is False
    assert profile["defensive_success_truth"] is False
    assert profile["opponent_progression_prevention_truth"] is False
    assert profile["opponent_non_shot_is_prevention_truth"] is False
    assert profile["opponent_visible_loss_is_forced_turnover_truth"] is False
    assert profile["creates_independent_support"] is False


def test_m07_empty_context_is_not_available() -> None:
    result = _m07_defensive_process_visible_exposure_response_synthesis(
        {"profiles": []},
        {"profiles": []},
        {"profiles": []},
    )
    assert result["status"] == "NOT_AVAILABLE"
    assert result["profile_count"] == 0
