from hpfa.modules.core.active_match_spine_runner.src.aerial_duel_first_visible_state import (
    CLAIM_CEILING,
    build_aerial_duel_first_visible_state_context,
)


def _trace(trace_id, team, start, labels, period="1", actor=None):
    return {
        "trackable_action_trace_candidate_id": trace_id,
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "period_candidate": period,
        "start_candidate": start,
        "raw_labels": labels,
    }


def _process(team, family, start, end, period="1"):
    return {
        "semantic_role": "CONTEXT_INTERVAL",
        "team_identity_candidate_id": team,
        "process_family_candidate": family,
        "period_candidate": period,
        "start_candidate": start,
        "end_candidate": end,
    }


def test_aerial_win_does_not_become_control_truth():
    traces = {
        "trackable_action_trace_candidates": [
            _trace("a1", "TEAM_A", 100, ["Aerial challenges won"], actor="P1"),
            _trace("n1", "TEAM_A", 104, ["Passes accurate"], actor="P2"),
        ]
    }
    processes = {
        "process_participation_candidates": [
            _process("TEAM_A", "POSITIONAL_ATTACK_CANDIDATE", 101, 120),
        ]
    }

    result = build_aerial_duel_first_visible_state_context(traces, processes)

    assert result["status"] == "PASS"
    assert result["admitted_aerial_label_trace_context_row_count"] == 1
    row = result["rows"][0]
    assert row["provider_aerial_duel_outcome_candidate"] == "PROVIDER_REVIEWED_AERIAL_DUEL_WON_CANDIDATE"
    assert row["first_visible_team_relation_to_aerial_actor_team"] == "SAME_TEAM_FIRST_VISIBLE_ACTION"
    assert row["next_visible_process_family_candidates"] == ["POSITIONAL_ATTACK_CANDIDATE"]
    assert row["provider_aerial_duel_outcome_is_ball_control_truth"] is False
    assert row["first_visible_team_action_is_second_ball_control_truth"] is False
    assert row["first_visible_team_action_is_possession_truth"] is False
    assert result["claim_ceiling"] == CLAIM_CEILING
    assert result["admitted_aerial_label_trace_count_is_physical_duel_count"] is False
    assert result["admitted_trace_coverage_is_complete_aerial_duel_inventory"] is False
    assert result["provider_pair_completeness_not_assumed"] is True


def test_aerial_loss_can_still_have_same_team_first_visible_action():
    traces = {
        "trackable_action_trace_candidates": [
            _trace("a1", "TEAM_A", 100, ["Aerial challenges lost"]),
            _trace("n1", "TEAM_A", 103, ["Recoveries"]),
        ]
    }

    result = build_aerial_duel_first_visible_state_context(
        traces,
        {"process_participation_candidates": []},
    )

    row = result["rows"][0]
    assert row["provider_aerial_duel_outcome_candidate"] == "PROVIDER_REVIEWED_AERIAL_DUEL_LOST_CANDIDATE"
    assert row["first_visible_team_relation_to_aerial_actor_team"] == "SAME_TEAM_FIRST_VISIBLE_ACTION"
    assert row["binding_state"] == "FIRST_VISIBLE_TEAM_OBSERVED_PROCESS_NOT_BOUND"


def test_mixed_team_same_timestamp_is_review_required_not_total_ordered():
    traces = {
        "trackable_action_trace_candidates": [
            _trace("a1", "TEAM_A", 100, ["Aerial challenges won"]),
            _trace("n1", "TEAM_A", 105, ["Pass"]),
            _trace("n2", "TEAM_B", 105, ["Challenge"]),
        ]
    }

    result = build_aerial_duel_first_visible_state_context(
        traces,
        {"process_participation_candidates": []},
    )

    assert result["status"] == "REVIEW_REQUIRED"
    row = result["rows"][0]
    assert row["binding_state"] == "REVIEW_REQUIRED_MIXED_TEAM_FIRST_VISIBLE_LAYER"
    assert row["first_visible_team_relation_to_aerial_actor_team"] == "UNRESOLVED"
    assert row["same_timestamp_total_order_allowed"] is False


def test_no_visible_followup_is_not_failure():
    traces = {
        "trackable_action_trace_candidates": [
            _trace("a1", "TEAM_A", 100, ["Aerial challenges won"]),
        ]
    }

    result = build_aerial_duel_first_visible_state_context(
        traces,
        {"process_participation_candidates": []},
    )

    row = result["rows"][0]
    assert row["binding_state"] == "NO_VISIBLE_FOLLOWUP"
    assert row["no_visible_followup_is_failure"] is False


def test_non_aerial_duel_is_not_promoted():
    traces = {
        "trackable_action_trace_candidates": [
            _trace("d1", "TEAM_A", 100, ["Challenges won"]),
            _trace("n1", "TEAM_A", 105, ["Pass"]),
        ]
    }

    result = build_aerial_duel_first_visible_state_context(
        traces,
        {"process_participation_candidates": []},
    )

    assert result["status"] == "NOT_AVAILABLE"
    assert result["admitted_aerial_label_trace_context_row_count"] == 0


def test_full_trackable_trace_surface_has_priority_over_primary_occurrence_subset():
    traces = {
        "primary_occurrence_trace_candidates": [
            _trace("subset1", "TEAM_A", 90, ["Challenges won"]),
        ],
        "trackable_action_trace_candidates": [
            _trace("a1", "TEAM_A", 100, ["Aerial challenges won"]),
            _trace("n1", "TEAM_B", 105, ["Pass"]),
        ],
    }

    result = build_aerial_duel_first_visible_state_context(
        traces,
        {"process_participation_candidates": []},
    )

    assert result["admitted_aerial_label_trace_context_row_count"] == 1
    assert result["rows"][0]["source_trackable_action_trace_candidate_id"] == "a1"
    assert result["rows"][0]["first_visible_team_relation_to_aerial_actor_team"] == "OPPONENT_TEAM_FIRST_VISIBLE_ACTION"
