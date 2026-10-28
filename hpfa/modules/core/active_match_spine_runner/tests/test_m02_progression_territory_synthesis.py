from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.rich_multiformat_analysis_lane import (
    _m02_progression_territory_synthesis,
)


def test_m02_preserves_visible_counts_and_unresolved_burden() -> None:
    c03 = {
        "construct_id": "C03_PROCESS_DEVELOPMENT_SIGNATURE",
        "signatures": [
            {
                "team_identity_candidate_id": "team_a",
                "process_family_candidate": "POSITIONAL_ATTACK",
                "process_start_zone_candidates": ["DEFENSIVE_THIRD"],
                "process_end_zone_candidates": ["FINAL_THIRD"],
                "provider_attack_axis_admitted": True,
                "provider_attack_axis_net_longitudinal_delta_candidate": 25.0,
            },
            {
                "team_identity_candidate_id": "team_a",
                "process_family_candidate": "COUNTERATTACK",
                "process_start_zone_candidates": [],
                "process_end_zone_candidates": ["PENALTY_AREA"],
                "provider_attack_axis_admitted": False,
                "provider_attack_axis_net_longitudinal_delta_candidate": 99.0,
            },
        ],
    }
    route = {
        "module_id": "visible_process_route_breadth_profile_v1",
        "profiles": [
            {
                "team_identity_candidate_id": "team_a",
                "process_family_candidate": "POSITIONAL_ATTACK",
                "eligible_process_n": 1,
            }
        ],
    }
    result = _m02_progression_territory_synthesis(c03, route)
    assert result["status"] == "PASS"
    assert result["profile_count"] == 1
    profile = result["profiles"][0]
    assert profile["eligible_process_signature_n"] == 2
    assert profile["unresolved_start_zone_process_n"] == 1
    assert profile["visible_end_zone_candidate_counts"] == {
        "FINAL_THIRD": 1,
        "PENALTY_AREA": 1,
    }
    assert profile["provider_attack_axis_delta_admitted_process_n"] == 1
    assert profile["provider_attack_axis_net_longitudinal_delta_sum_candidate"] == 25.0


def test_m02_does_not_turn_pool_views_into_independent_support_or_control_truth() -> None:
    result = _m02_progression_territory_synthesis(
        {
            "construct_id": "C03_PROCESS_DEVELOPMENT_SIGNATURE",
            "signatures": [
                {
                    "team_identity_candidate_id": "team_a",
                    "process_family_candidate": "POSITIONAL_ATTACK",
                    "process_start_zone_candidates": ["MIDDLE_THIRD"],
                    "process_end_zone_candidates": ["FINAL_THIRD"],
                }
            ],
        },
        {"module_id": "visible_process_route_breadth_profile_v1", "profiles": []},
    )
    profile = result["profiles"][0]
    assert result["pool_views_create_independent_evidence"] is False
    assert result["territory_is_possession_control_truth"] is False
    assert result["territory_is_team_shape_truth"] is False
    assert result["territory_is_dominance_truth"] is False
    assert result["physical_trajectory_truth"] is False
    assert profile["creates_independent_support"] is False
    assert profile["progression_synthesis_is_tactical_superiority_truth"] is False


def test_m02_empty_input_is_not_available_not_failure() -> None:
    result = _m02_progression_territory_synthesis(
        {"construct_id": "C03_PROCESS_DEVELOPMENT_SIGNATURE", "signatures": []},
        {"module_id": "visible_process_route_breadth_profile_v1", "profiles": []},
    )
    assert result["status"] == "NOT_AVAILABLE"
    assert result["profile_count"] == 0
