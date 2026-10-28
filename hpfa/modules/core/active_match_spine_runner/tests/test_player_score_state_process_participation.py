from hpfa.modules.core.active_match_spine_runner.src.player_score_state_process_participation import (
    CLAIM_CEILING,
    build_player_score_state_process_participation,
)


IDENTITY = {
    "team_identity_candidates": [
        {"team_identity_candidate_id": "A", "team_aliases_raw": ["Team A"]},
        {"team_identity_candidate_id": "B", "team_aliases_raw": ["Team B"]},
    ],
    "actor_identity_candidates": [
        {"actor_identity_candidate_id": "P1", "actor_aliases_raw": ["Player One"]},
        {"actor_identity_candidate_id": "P2", "actor_aliases_raw": ["Player Two"]},
    ],
}

GAME_STATE = {
    "score_state_segments": [
        {
            "start_second_candidate": 0.0,
            "end_second_candidate": 600.0,
            "score_state_candidate": {"Team A": 0, "Team B": 0},
        },
        {
            "start_second_candidate": 600.0,
            "end_second_candidate": 1200.0,
            "score_state_candidate": {"Team A": 0, "Team B": 1},
        },
    ]
}


def context(family, start, shot=False):
    return {
        "semantic_role": "CONTEXT_INTERVAL",
        "team_identity_candidate_id": "A",
        "process_family_candidate": family,
        "period_candidate": "1",
        "start_candidate": start,
        "end_candidate": start + 60,
        "shot_present_annotation_candidate": shot,
    }


def participant(actor, family, start):
    return {
        "semantic_role": "PARTICIPATION_INTERVAL",
        "team_identity_candidate_id": "A",
        "process_family_candidate": family,
        "period_candidate": "1",
        "start_candidate": start,
        "end_candidate": start + 60,
        "actor_identity_candidate_id": actor,
    }


def test_visible_player_participation_by_score_state_is_count_only():
    payload = {
        "process_participation_candidates": [
            context("POSITIONAL_ATTACK_CANDIDATE", 100, True),
            participant("P1", "POSITIONAL_ATTACK_CANDIDATE", 100),
            participant("P2", "POSITIONAL_ATTACK_CANDIDATE", 100),
            context("COUNTERATTACK_CANDIDATE", 700),
            participant("P1", "COUNTERATTACK_CANDIDATE", 700),
        ]
    }
    result = build_player_score_state_process_participation(
        GAME_STATE, IDENTITY, payload
    )
    p1 = [r for r in result["profiles"] if r["actor_identity_candidate_id"] == "P1"]

    assert result["status"] == "PASS"
    assert result["claim_ceiling"] == CLAIM_CEILING
    assert len(p1) == 2
    assert p1[0]["shot_ending_process_participation_n"] == 1
    assert p1[1]["process_family_counts"] == {"COUNTERATTACK_CANDIDATE": 1}
    assert result["player_rate_output_allowed"] is False
    assert result["team_score_state_duration_is_player_exposure"] is False
    assert result["visible_participation_is_causal_credit"] is False


def test_duplicate_participation_rows_do_not_inflate_counts():
    p = participant("P1", "POSITIONAL_ATTACK_CANDIDATE", 100)
    payload = {
        "process_participation_candidates": [
            context("POSITIONAL_ATTACK_CANDIDATE", 100),
            p,
            dict(p),
        ]
    }
    result = build_player_score_state_process_participation(
        GAME_STATE, IDENTITY, payload
    )
    p1 = [r for r in result["profiles"] if r["actor_identity_candidate_id"] == "P1"]

    assert p1[0]["visible_process_participation_n"] == 1
    assert result["zero_participation_is_non_participation_truth"] is False

def test_multi_score_state_player_gets_match_local_function_review_contract():
    payload = {
        "process_participation_candidates": [
            context("POSITIONAL_ATTACK_CANDIDATE", 100, True),
            participant("P1", "POSITIONAL_ATTACK_CANDIDATE", 100),
            context("COUNTERATTACK_CANDIDATE", 700),
            participant("P1", "COUNTERATTACK_CANDIDATE", 700),
        ]
    }
    result = build_player_score_state_process_participation(GAME_STATE, IDENTITY, payload)

    reviews = result["function_hypothesis_review_candidates"]
    review = next(r for r in reviews if r["actor_identity_candidate_id"] == "P1")

    assert review["review_state"] == "MATCH_LOCAL_FUNCTION_CONTEXT_VARIATION_REVIEW_CANDIDATE"
    assert review["observed_score_state_context_n"] == 2
    assert review["observed_process_family_n"] == 2
    assert review["process_mix_varies_across_observed_score_states"] is True
    assert review["creates_new_evidence"] is False
    assert review["can_authorize_player_value_claim"] is False
    assert review["stable_role_truth"] is False
    assert review["causal_contribution_truth"] is False
    assert review["off_ball_role_truth"] is False
    assert review["counter_scenario_candidates"]
    assert review["hypothesis_falsifier_conditions"]
    assert review["invalidation_conditions"]
    assert review["falsifier_is_invalidator"] is False
    assert review["absence_is_falsifier"] is False
    assert review["withdrawal_conditions"]
    assert review["claim_ceiling"] == "MATCH_LOCAL_CONTEXT_CONDITIONED_PLAYER_FUNCTION_REVIEW_CANDIDATE_ONLY"


def test_single_score_state_player_does_not_get_variation_review_candidate():
    payload = {
        "process_participation_candidates": [
            context("POSITIONAL_ATTACK_CANDIDATE", 100, True),
            participant("P1", "POSITIONAL_ATTACK_CANDIDATE", 100),
        ]
    }
    result = build_player_score_state_process_participation(GAME_STATE, IDENTITY, payload)
    review = next(r for r in result["function_hypothesis_review_candidates"] if r["actor_identity_candidate_id"] == "P1")
    assert review["review_state"] == "INSUFFICIENT_MULTI_CONTEXT_VARIATION_FOR_REVIEW"
    assert review["process_mix_varies_across_observed_score_states"] is False

