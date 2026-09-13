from __future__ import annotations

from hpfa.modules.core.analyst_episode_locator_lite.src.process_actor_participation_concentration_projection import (
    build_process_actor_participation_concentration_projection,
)


def _row(
    row_id: str,
    role: str,
    *,
    actor: str | None = None,
    family: str = "POSITIONAL_ATTACK_CANDIDATE",
    team: str = "team_a",
    period: str = "1",
    start: str = "10",
    end: str = "20",
) -> dict[str, object]:
    return {
        "process_participation_candidate_id": row_id,
        "semantic_role": role,
        "process_family_candidate": family,
        "team_identity_candidate_id": team,
        "actor_identity_candidate_id": actor,
        "period_candidate": period,
        "start_candidate": start,
        "end_candidate": end,
        "reflection_dependency_state": "SOURCE_LOCAL_NO_REFLECTION_VOTE",
    }


def _payload(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "module_id": "analyst_episode_process_participation_projection_v1",
        "status": "PASS",
        "process_participation_candidates": rows,
        "process_participation_candidate_count": len(rows),
        "annotation_count_is_action_count": False,
        "annotation_count_is_independent_support_count": False,
        "reflection_adds_independent_vote": False,
        "absence_is_counterevidence": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def test_one_actor_gets_at_most_one_vote_per_process_instance() -> None:
    rows = [
        _row("ctx1", "CONTEXT_INTERVAL"),
        _row("a1", "PARTICIPATION_INTERVAL", actor="actor_a"),
        _row("a2", "PARTICIPATION_INTERVAL", actor="actor_a"),
        _row("a3", "PARTICIPATION_INTERVAL", actor="actor_a"),
        _row("b1", "PARTICIPATION_INTERVAL", actor="actor_b"),
        _row("ctx2", "CONTEXT_INTERVAL", start="30", end="40"),
        _row("a4", "PARTICIPATION_INTERVAL", actor="actor_a", start="30", end="40"),
        _row("c1", "PARTICIPATION_INTERVAL", actor="actor_c", start="30", end="40"),
    ]

    report = build_process_actor_participation_concentration_projection(_payload(rows))
    profile = report["process_actor_concentration_profiles"][0]

    assert profile["actor_participation_definition"] == "ONE_ACTOR_ONE_VOTE_PER_PROCESS_INSTANCE"
    assert profile["actor_process_counts"] == {
        "actor_a": 2,
        "actor_b": 1,
        "actor_c": 1,
    }
    assert profile["actor_process_presence_rates"]["actor_a"] == 1.0
    assert profile["actor_participation_shares"]["actor_a"] == 0.5
    assert profile["actor_hhi"] == 0.375
    assert profile["action_weighted_concentration_produced"] is False
    assert report["duplicate_actor_annotation_within_process_suppressed"] == 2


def test_dyad_is_undirected_coparticipation_not_pass_relation() -> None:
    rows = [
        _row("ctx1", "CONTEXT_INTERVAL"),
        _row("a1", "PARTICIPATION_INTERVAL", actor="actor_b"),
        _row("a2", "PARTICIPATION_INTERVAL", actor="actor_a"),
        _row("ctx2", "CONTEXT_INTERVAL", start="30", end="40"),
        _row("a3", "PARTICIPATION_INTERVAL", actor="actor_a", start="30", end="40"),
        _row("a4", "PARTICIPATION_INTERVAL", actor="actor_c", start="30", end="40"),
    ]

    report = build_process_actor_participation_concentration_projection(_payload(rows))
    profile = report["process_actor_concentration_profiles"][0]

    assert profile["dyad_process_counts"] == {
        "actor_a|actor_b": 1,
        "actor_a|actor_c": 1,
    }
    assert profile["dyad_process_presence_rates"] == {
        "actor_a|actor_b": 0.5,
        "actor_a|actor_c": 0.5,
    }
    assert profile["dyad_hhi"] == 0.5
    assert profile["dyad_is_pass_relation_truth"] is False
    assert profile["recipient_relation_used"] is False
    assert profile["next_passer_receiver_heuristic_used"] is False


def test_context_without_actor_observation_is_coverage_gap_not_absence_vote() -> None:
    rows = [
        _row("ctx1", "CONTEXT_INTERVAL"),
        _row("a1", "PARTICIPATION_INTERVAL", actor="actor_a"),
        _row("ctx2", "CONTEXT_INTERVAL", start="30", end="40"),
    ]

    report = build_process_actor_participation_concentration_projection(_payload(rows))
    profile = report["process_actor_concentration_profiles"][0]

    assert report["status"] == "REVIEW_REQUIRED"
    assert profile["eligible_context_process_count"] == 2
    assert profile["actor_observable_process_count"] == 1
    assert profile["actor_participation_observation_missing_process_count"] == 1
    assert profile["actor_process_counts"] == {"actor_a": 1}
    assert profile["actor_process_presence_rates"] == {"actor_a": 1.0}
    assert profile["absence_is_counterevidence"] is False
    assert "context_intervals_without_actor_participation_observation" in report["review_hits"]


def test_participation_without_context_is_not_promoted_to_process_instance() -> None:
    rows = [
        _row("ctx1", "CONTEXT_INTERVAL"),
        _row("a1", "PARTICIPATION_INTERVAL", actor="actor_a"),
        _row("orphan", "PARTICIPATION_INTERVAL", actor="actor_b", start="30", end="40"),
    ]

    report = build_process_actor_participation_concentration_projection(_payload(rows))
    profile = report["process_actor_concentration_profiles"][0]

    assert report["participant_only_process_signature_count"] == 1
    assert profile["actor_process_counts"] == {"actor_a": 1}
    assert report["status"] == "REVIEW_REQUIRED"


def test_claim_ceiling_forbids_dependency_and_tactical_truth_escalation() -> None:
    rows = [
        _row("ctx1", "CONTEXT_INTERVAL"),
        _row("a1", "PARTICIPATION_INTERVAL", actor="actor_a"),
        _row("b1", "PARTICIPATION_INTERVAL", actor="actor_b"),
    ]

    report = build_process_actor_participation_concentration_projection(_payload(rows))
    profile = report["process_actor_concentration_profiles"][0]

    assert report["canonical_event_count"] == "UNKNOWN"
    assert report["true_action_count"] == "UNKNOWN"
    assert report["production_release"] is False
    assert report["high_actor_concentration_is_player_indispensability_truth"] is False
    assert report["low_actor_concentration_is_tactical_flexibility_truth"] is False
    assert report["dyad_coparticipation_is_pass_relation_truth"] is False
    assert report["process_persistence_or_personnel_effect_claimed"] is False
    assert profile["dependency_independence_proven"] is False
    assert profile["statistical_independence_proven"] is False
    assert profile["independent_support_vote_count"] == 0


def test_upstream_truth_escalation_fails_closed() -> None:
    payload = _payload([])
    payload["canonical_event_count"] = 12

    report = build_process_actor_participation_concentration_projection(payload)

    assert report["status"] == "FAIL_CLOSED"
    assert "canonical_event_count_claimed" in report["hard_block_hits"]
