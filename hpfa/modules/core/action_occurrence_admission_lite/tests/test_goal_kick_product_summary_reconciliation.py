from __future__ import annotations

from hpfa.modules.core.action_occurrence_admission_lite.src.action_grammar_public_adapter import (
    _reconcile_goal_kick_product_summary,
)


def _goal_candidate(candidate_id: str, bucket: str, outcome: str) -> dict:
    return {
        "action_occurrence_candidate_id": candidate_id,
        "interaction_type": "GOAL_KICK_RESTART_PASS_SEMANTIC_CANDIDATE",
        "attributes": {
            "provider_distance_bucket_candidate": bucket,
            "pass_outcome_candidate": outcome,
            "provider_distance_bucket_is_measured_physical_distance": False,
            "provider_distance_bucket_is_tactical_strategy_truth": False,
        },
        "action_occurrence_candidate_is_event_truth": False,
        "physical_action_identity_truth": False,
        "independent_support_vote_count": 0,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
    }


def test_final_product_goal_kick_rows_repair_stale_zero_summary_without_new_evidence() -> None:
    first = _goal_candidate("gk_1", "LONG", "SUCCESS")
    second = _goal_candidate("gk_2", "MEDIUM", "FAILURE")
    unrelated = {
        "action_occurrence_candidate_id": "other_1",
        "interaction_type": "INTRA_ACTOR_ACTION_GRAMMAR_CANDIDATE",
    }
    payload = {
        "action_occurrence_candidates": [first, second, unrelated],
        "action_occurrence_candidate_count": 3,
        "goal_kick_restart_pass_candidate_count": 0,
        "goal_kick_restart_pass_candidates": [],
        "goal_kick_provider_distance_bucket_counts": {},
        "goal_kick_pass_outcome_counts": {},
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }

    _reconcile_goal_kick_product_summary(payload)

    assert payload["action_occurrence_candidate_count"] == 3
    assert payload["goal_kick_restart_pass_candidate_count"] == 2
    assert payload["goal_kick_restart_pass_candidates"] == [first, second]
    assert payload["goal_kick_provider_distance_bucket_counts"] == {"LONG": 1, "MEDIUM": 1}
    assert payload["goal_kick_pass_outcome_counts"] == {"FAILURE": 1, "SUCCESS": 1}
    assert payload["goal_kick_summary_basis"] == "FINAL_ADMITTED_OCCURRENCE_PRODUCT_STATE"
    assert payload["goal_kick_summary_creates_new_evidence"] is False
    assert payload["goal_kick_summary_can_authorize_emit"] is False
    assert payload["canonical_event_count"] == "UNKNOWN"
    assert payload["true_action_count"] == "UNKNOWN"
    assert payload["production_release"] is False
