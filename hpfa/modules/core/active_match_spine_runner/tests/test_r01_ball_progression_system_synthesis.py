from __future__ import annotations

from hpfa.modules.core.active_match_spine_runner.src.rich_multiformat_analysis_lane import (
    _r01_ball_progression_system_synthesis,
)


def m01(team: str = "team_a") -> dict:
    return {
        "synthesis_id": "M01_POSSESSION_CONSTRUCTION",
        "profiles": [
            {
                "team_identity_candidate_id": team,
                "eligible_process_signature_n": 4,
                "claim_ceiling": "MATCH_LOCAL_VISIBLE_POSSESSION_CONSTRUCTION_CONTEXT_CANDIDATE_ONLY",
            }
        ],
    }


def m02(team: str = "team_a") -> dict:
    return {
        "synthesis_id": "M02_PROGRESSION_AND_TERRITORY",
        "profiles": [
            {
                "team_identity_candidate_id": team,
                "eligible_process_signature_n": 4,
                "claim_ceiling": "MATCH_LOCAL_VISIBLE_PROGRESSION_TERRITORY_SYNTHESIS_CANDIDATE_ONLY",
            }
        ],
    }


def test_r01_complete_team_profile_passes_without_scalar_score() -> None:
    result = _r01_ball_progression_system_synthesis(m01(), m02())
    assert result["status"] == "PASS"
    assert result["complete_profile_count"] == 1
    profile = result["profiles"][0]
    assert profile["coverage_state"] == "M01_AND_M02_VISIBLE"
    assert profile["scalar_ball_progression_score_emitted"] is False
    assert result["scalar_ball_progression_score_emitted"] is False
    assert result["component_views_create_independent_support"] is False


def test_r01_partial_component_is_review_required_not_negative_evidence() -> None:
    result = _r01_ball_progression_system_synthesis(m01(), {"profiles": []})
    assert result["status"] == "REVIEW_REQUIRED"
    assert result["complete_profile_count"] == 0
    profile = result["profiles"][0]
    assert profile["coverage_state"] == "M01_ONLY_VISIBLE"
    assert profile["missing_component_is_negative_evidence"] is False
    assert result["missing_component_is_negative_evidence"] is False


def test_r01_preserves_truth_locks() -> None:
    result = _r01_ball_progression_system_synthesis(m01(), m02())
    assert result["possession_truth"] is False
    assert result["territorial_control_truth"] is False
    assert result["team_shape_truth"] is False
    assert result["tactical_plan_truth"] is False
    assert result["superiority_truth"] is False
    assert result["causal_truth"] is False
    profile = result["profiles"][0]
    assert profile["territorial_control_truth"] is False
    assert profile["superiority_truth"] is False


def test_r01_no_components_is_not_available() -> None:
    result = _r01_ball_progression_system_synthesis({"profiles": []}, {"profiles": []})
    assert result["status"] == "NOT_AVAILABLE"
    assert result["profile_count"] == 0
