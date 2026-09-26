from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.rich_multiformat_analysis_lane import (
    _m01_possession_construction_synthesis,
)


def test_m01_keeps_denominators_separate_and_preserves_unresolved_start_burden() -> None:
    c03 = {
        "construct_id": "C03_PROCESS_DEVELOPMENT_SIGNATURE",
        "signatures": [
            {
                "team_identity_candidate_id": "team_a",
                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                "process_start_zone_candidates": ["DEFENSIVE_THIRD"],
            },
            {
                "team_identity_candidate_id": "team_a",
                "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                "process_start_zone_candidates": [],
            },
        ],
    }
    circulation = {
        "module_id": "visible_circulation_fate_profile_v1",
        "profiles": [
            {
                "team_identity_candidate_id": "team_a",
                "eligible_circulation_process_n": 3,
                "visible_fate_counts": {
                    "SHOT_LINKED_VISIBLE": 1,
                    "OTHER_VISIBLE_OR_UNRESOLVED": 2,
                },
            }
        ],
    }
    goalkeeper = {
        "binding_state": "GOALKEEPER_RESTART_TO_VISIBLE_CONSEQUENCE_CONTEXT",
        "rows": [
            {
                "team_identity_candidate_id": "team_a",
                "process_continuation_status": "VISIBLE_SAME_TEAM_CONTINUATION",
                "next_visible_process_family_candidates": ["POSITIONAL_ATTACK_CANDIDATE"],
            }
        ],
    }

    result = _m01_possession_construction_synthesis(c03, circulation, goalkeeper)
    assert result["status"] == "PASS"
    profile = result["profiles"][0]
    assert profile["eligible_process_signature_n"] == 2
    assert profile["unresolved_process_start_zone_n"] == 1
    assert profile["visible_circulation_process_n"] == 3
    assert profile["goalkeeper_restart_context_n"] == 1
    assert profile["denominator_basis"]["process_signatures"] != profile["denominator_basis"]["circulation"]


def test_m01_does_not_promote_visible_construction_context_to_possession_or_plan_truth() -> None:
    result = _m01_possession_construction_synthesis(
        {
            "construct_id": "C03_PROCESS_DEVELOPMENT_SIGNATURE",
            "signatures": [
                {
                    "team_identity_candidate_id": "team_a",
                    "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
                    "process_start_zone_candidates": ["DEFENSIVE_THIRD"],
                }
            ],
        },
        {"module_id": "visible_circulation_fate_profile_v1", "profiles": []},
        {"binding_state": "GOALKEEPER_RESTART_TO_VISIBLE_CONSEQUENCE_CONTEXT", "rows": []},
    )
    profile = result["profiles"][0]
    assert result["pool_views_create_independent_evidence"] is False
    assert result["possession_truth"] is False
    assert result["possession_control_truth"] is False
    assert result["tactical_plan_truth"] is False
    assert result["causal_truth"] is False
    assert profile["possession_truth"] is False
    assert profile["build_up_tactical_plan_truth"] is False
    assert profile["creates_independent_support"] is False


def test_m01_empty_input_is_not_available() -> None:
    result = _m01_possession_construction_synthesis(
        {"construct_id": "C03_PROCESS_DEVELOPMENT_SIGNATURE", "signatures": []},
        {"module_id": "visible_circulation_fate_profile_v1", "profiles": []},
        {"binding_state": "GOALKEEPER_RESTART_TO_VISIBLE_CONSEQUENCE_CONTEXT", "rows": []},
    )
    assert result["status"] == "NOT_AVAILABLE"
    assert result["profile_count"] == 0
