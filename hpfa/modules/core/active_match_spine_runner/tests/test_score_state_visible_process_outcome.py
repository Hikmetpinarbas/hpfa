from hpfa.modules.core.active_match_spine_runner.src.score_state_visible_process_outcome import (
    CLAIM_CEILING,
    build_score_state_visible_process_outcome_context,
)


def _identity():
    return {
        "team_identity_candidates": [
            {
                "team_identity_candidate_id": "TEAM_A",
                "team_aliases_raw": ["Team A"],
            },
            {
                "team_identity_candidate_id": "TEAM_B",
                "team_aliases_raw": ["Team B"],
            },
        ]
    }


def _game_state():
    return {
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


def _sig(team, start, family="POSITIONAL_ATTACK_CANDIDATE", shot=False, loss=False, recovery=False):
    return {
        "team_identity_candidate_id": team,
        "process_start_candidate": start,
        "process_family_candidate": family,
        "shot_present_annotation_candidate": shot,
        "visible_loss_transition_candidate_present": loss,
        "visible_recovery_transition_candidate_present": recovery,
    }


def test_score_state_profile_binds_visible_process_outcomes_without_causal_promotion():
    signatures = [
        _sig("TEAM_A", 100, shot=True),
        _sig("TEAM_A", 300, loss=True),
        _sig("TEAM_A", 700, family="COUNTERATTACK_CANDIDATE", recovery=True),
        _sig("TEAM_A", 900, family="COUNTERATTACK_CANDIDATE", shot=True, loss=True),
    ]

    result = build_score_state_visible_process_outcome_context(
        _game_state(),
        _identity(),
        signatures,
    )

    assert result["status"] == "PASS"
    assert result["claim_ceiling"] == CLAIM_CEILING
    team_a = [
        row for row in result["profiles"]
        if row["team_identity_candidate_id"] == "TEAM_A"
    ]
    assert len(team_a) == 2

    level, trailing = team_a
    assert level["eligible_visible_process_n"] == 2
    assert level["shot_ending_process_n"] == 1
    assert level["visible_loss_process_n"] == 1
    assert level["shot_ending_share_candidate"] == 0.5
    assert level["eligible_visible_process_rate_per_10_minutes"] == 2.0

    assert trailing["eligible_visible_process_n"] == 2
    assert trailing["process_family_counts"] == {"COUNTERATTACK_CANDIDATE": 2}
    assert trailing["shot_ending_process_n"] == 1
    assert trailing["visible_loss_process_n"] == 1
    assert trailing["visible_recovery_process_n"] == 1

    assert result["score_state_is_causal_explanation"] is False
    assert result["score_state_profile_is_risk_appetite_truth"] is False
    assert result["score_state_profile_is_tactical_adaptation_truth"] is False
    assert result["score_state_profile_is_dominance_truth"] is False
    assert result["creates_independent_support"] is False


def test_boundary_process_belongs_to_next_score_state_segment():
    signatures = [_sig("TEAM_A", 600, shot=True)]

    result = build_score_state_visible_process_outcome_context(
        _game_state(),
        _identity(),
        signatures,
    )
    team_a = [
        row for row in result["profiles"]
        if row["team_identity_candidate_id"] == "TEAM_A"
    ]

    assert team_a[0]["eligible_visible_process_n"] == 0
    assert team_a[1]["eligible_visible_process_n"] == 1


def test_zero_process_segment_is_not_promoted_to_absence_truth():
    result = build_score_state_visible_process_outcome_context(
        _game_state(),
        _identity(),
        [_sig("TEAM_A", 100, shot=True)],
    )

    assert result["status"] == "PASS"
    team_b = [
        row for row in result["profiles"]
        if row["team_identity_candidate_id"] == "TEAM_B"
    ]
    assert team_b
    assert all(row["eligible_visible_process_n"] == 0 for row in team_b)
    assert all(row["zero_process_count_is_process_absence_truth"] is False for row in team_b)


def test_no_process_signature_input_is_not_available():
    result = build_score_state_visible_process_outcome_context(
        _game_state(),
        _identity(),
        [],
    )

    assert result["status"] == "NOT_AVAILABLE"
    assert result["score_state_profile_is_risk_appetite_truth"] is False


def test_unresolved_team_binding_requires_review():
    game_state = {
        "score_state_segments": [
            {
                "start_second_candidate": 0.0,
                "end_second_candidate": 600.0,
                "score_state_candidate": {"Unknown Team": 0},
            }
        ]
    }

    result = build_score_state_visible_process_outcome_context(
        game_state,
        _identity(),
        [],
    )

    assert result["status"] == "NOT_AVAILABLE"
    assert result["unresolved_team_labels"] == ["Unknown Team"]


def test_process_variant_board_binds_recurrent_motif_members_to_relative_score_state_without_causal_promotion():
    from hpfa.modules.core.active_match_spine_runner.src.score_state_visible_process_outcome import (
        bind_process_variant_board_score_state_context,
    )

    signatures = [
        {**_sig("TEAM_A", 100), "process_development_signature_id": "s1"},
        {**_sig("TEAM_A", 300), "process_development_signature_id": "s2"},
        {**_sig("TEAM_A", 700), "process_development_signature_id": "s3"},
    ]
    motifs = [{
        "process_motif_family_candidate_id": "m1",
        "team_identity_candidate_id": "TEAM_A",
        "member_process_development_signature_ids": ["s1", "s2", "s3"],
    }]
    board = {
        "status": "PASS",
        "rows": [{
            "process_motif_family_candidate_id": "m1",
            "team_identity_candidate_id": "TEAM_A",
            "process_family_candidate": "POSITIONAL_ATTACK_CANDIDATE",
            "member_process_n": 3,
        }],
    }

    result = bind_process_variant_board_score_state_context(
        _game_state(), _identity(), signatures, motifs, board
    )

    context = result["rows"][0]["visible_score_state_context"]
    assert context["member_process_n"] == 3
    assert context["bound_member_process_n"] == 3
    assert context["unresolved_member_process_n"] == 0
    assert context["relative_score_state_counts"] == {"DRAW": 2, "TRAILING": 1}
    assert context["score_state_context_is_causal_explanation"] is False
    assert context["score_state_context_is_tactical_adaptation_truth"] is False
    assert context["score_state_context_can_increase_claim_ceiling"] is False
    assert context["claim_ceiling"] == "MATCH_LOCAL_PROCESS_VARIANT_VISIBLE_SCORE_STATE_CONTEXT_ONLY"
